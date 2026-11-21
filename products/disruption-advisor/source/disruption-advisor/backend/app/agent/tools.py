"""Read-only engine tools for the phase 3 agent (ADR 0010).

Every tool returns compact JSON built from flight facts and counts: no names, PNRs, contact details, passenger
IDs or customer keys ever leave the engine (ADR 0007; tests/test_agent.py checks every request). The numbers come
from the engine; the agent only chooses which questions to ask and which engine option to recommend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.engine import priority
from app.engine import strategy as strategies
from app.engine.scenarios import Context, ScenarioError, analyse_delay

FLIGHT_ID_RE = r"^[A-Z0-9]{2,8}_\d{12}$"
OPTION_KEY_RE = r"^[A-Za-z0-9:_\-]{1,40}$"
StrategyKey = Literal["lowest_cost", "protect_passengers", "least_delay"]


# Input validation in code (strict tool schemas support types and enums only, not patterns or ranges).
class FindFlights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(pattern=r"^[A-Za-z0-9]{1,8}$")
    day: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class FlightArg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flight_id: str = Field(pattern=FLIGHT_ID_RE)


class AssessDelay(FlightArg):
    delay_minutes: int = Field(ge=15, le=1440)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OptionArg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_key: str = Field(pattern=OPTION_KEY_RE)


class Watchlist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(ge=1, le=15)


Line = Annotated[str, Field(min_length=1, max_length=300)]


class Submit(OptionArg):
    strategy: StrategyKey
    reasons: list[Line] = Field(min_length=2, max_length=4)
    risks: list[Line] = Field(max_length=4)
    checks: list[Line] = Field(max_length=4)


ARGS: dict[str, type[BaseModel]] = {
    "find_flights": FindFlights,
    "flight_status": FlightArg,
    "aircraft_rotation": FlightArg,
    "assess_delay": AssessDelay,
    "compare_strategies": NoArgs,
    "passenger_impact": OptionArg,
    "watchlist": Watchlist,
    "submit_recommendation": Submit,
}


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


S = {"type": "string"}
INT = {"type": "integer"}
LINES = {"type": "array", "items": S}
FLIGHT_ID = {"type": "string", "description": "flight id like G9519_202611210200 (flight number _ UTC yyyymmddhhmm)"}
TOOLS: list[dict[str, Any]] = [
    {
        "name": "find_flights",
        "description": "Find flights in the operating window by flight number or station code (e.g. G9519, SHJ); "
        "day is an optional UTC date yyyy-mm-dd or null. Returns flight ids, UTC times, route, aircraft and load.",
        "input_schema": _obj({"text": S, "day": {"anyOf": [S, {"type": "null"}]}}),
    },
    {
        "name": "flight_status",
        "description": "One flight: schedule, aircraft, booked passengers, and the phase 2 delay risk (chance of a "
        "15/60+ min delay, planning delay, main reasons, connecting passengers) when available.",
        "input_schema": _obj({"flight_id": FLIGHT_ID}),
    },
    {
        "name": "aircraft_rotation",
        "description": "The flights of the flight's aircraft from that flight onwards (next 48 h), with the "
        "scheduled ground time before each one.",
        "input_schema": _obj({"flight_id": FLIGHT_ID}),
    },
    {
        "name": "assess_delay",
        "description": "Run the engine's delay scenario for a flight and a departure delay (15-1440 minutes): every "
        "recovery option (absorb, swap aircraft, cancel or consolidate a later round trip) with cost, aircraft "
        "delay, passenger delay, missed connections, cancelled passengers and passengers left without a seat, "
        "plus each strategy's pick.",
        "input_schema": _obj({"flight_id": FLIGHT_ID, "delay_minutes": INT}),
    },
    {
        "name": "compare_strategies",
        "description": "For the last assessed delay: the pick of each strategy (lowest cost, protect passengers, "
        "least delay) side by side with the same figures.",
        "input_schema": _obj({}),
    },
    {
        "name": "passenger_impact",
        "description": "For one option key of the last assessed delay: missed connections, cancelled passengers, "
        "rebooked, left without a seat, hotel rooms, care cost, priority tiers and special-assistance counts. "
        "Counts only.",
        "input_schema": _obj({"option_key": S}),
    },
    {
        "name": "watchlist",
        "description": "Phase 2 watchlist: up to `limit` (1-15) flights in the next 7 days with the most expected "
        "missed connections from predicted delays.",
        "input_schema": _obj({"limit": INT}),
    },
    {
        "name": "submit_recommendation",
        "description": "Finish: recommend ONE option key from the last assess_delay result, under one strategy, "
        "for the controller to review. Nothing is executed; the controller approves or overrides. Give 2-4 short "
        "reasons, up to 4 risks and up to 4 checks the controller should make before approving (one sentence "
        "each).",
        "input_schema": _obj(
            {
                "option_key": S,
                "strategy": {"type": "string", "enum": list(strategies.STRATEGIES)},
                "reasons": LINES,
                "risks": LINES,
                "checks": LINES,
            }
        ),
    },
]
TOOLS = [{**tool, "strict": True} for tool in TOOLS]
FINAL_TOOL = "submit_recommendation"


class ToolError(ValueError):
    """A tool was called with something the engine cannot answer; returned to the model as an error result."""


@dataclass
class Assessment:
    flight_id: str
    delay_minutes: int
    result: dict[str, Any]


@dataclass
class AgentTools:
    ctx: Context  # an engine context whose explainer writes templates only (no nested AI calls)
    assessment: Assessment | None = None
    final: dict[str, Any] | None = None
    _impacts: dict[str, dict[str, Any]] = field(default_factory=dict)

    # --- dispatch ---------------------------------------------------------------------------------------
    def run(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        model = ARGS.get(name)
        if model is None:
            raise ToolError(f"Unknown tool {name}")
        try:
            valid = model.model_validate(args)
        except ValidationError as exc:
            raise ToolError(f"Invalid input for {name}: {exc.errors(include_url=False)}") from exc
        result: dict[str, Any] = getattr(self, f"_t_{name}")(**valid.model_dump())
        return result

    @staticmethod
    def summary(name: str, result: dict[str, Any]) -> str:
        """One line for the trace shown to the controller."""
        if name == "assess_delay":
            picks = ", ".join(f"{s['label']}: {s['pick']}" for s in result["strategies"])
            return f"{len(result['options'])} options; picks: {picks}"
        if name == "find_flights":
            return f"{len(result['flights'])} flights found"
        if name == "passenger_impact":
            return (
                f"{result['option_key']}: {result['missed_connections']} missed connections, "
                f"{result['cancelled_passengers']} cancelled, {result['rebooked']} rebooked, "
                f"{result['without_seat']} without a seat"
            )
        if name == "flight_status":
            f = result["flight"]
            risk = result.get("delay_risk")
            extra = f", 60+ min delay risk {risk['p_60']:.0%}" if risk else ""
            return f"{f['flight_number']} {f['origin']}-{f['destination']} {f['std']}, {f['booked_pax']} booked{extra}"
        if name == "aircraft_rotation":
            return f"{result['tail']}: {len(result['flights'])} flights in 48 h"
        if name == "compare_strategies":
            return "; ".join(f"{p['strategy']}: {p['option_key']}" for p in result["picks"])
        if name == "watchlist":
            return f"{len(result['flights'])} flights"
        if name == FINAL_TOOL:
            return f"recommends {result['option_key']} ({result['strategy']})"
        return json.dumps(result)[:200]

    # --- tools ------------------------------------------------------------------------------------------
    def _t_find_flights(self, text: str, day: str | None = None) -> dict[str, Any]:
        rows = self.ctx.store.search_flights(text.upper(), day, 15)
        keep = ("flight_id", "flight_number", "origin", "destination", "std", "sta", "tail", "booked_pax", "capacity")
        return {"flights": [{k: r.get(k) for k in keep} for r in rows]}

    def _leg(self, flight_id: str) -> Any:
        leg = self.ctx.store.leg(flight_id)
        if leg is None:
            raise ToolError(f"Flight {flight_id} is not in the operating window")
        return leg

    def _t_flight_status(self, flight_id: str) -> dict[str, Any]:
        leg = self._leg(flight_id)
        out: dict[str, Any] = {
            "flight": {
                "flight_id": leg.flight_id,
                "flight_number": leg.flight_number,
                "origin": leg.origin,
                "destination": leg.destination,
                "std": leg.std,
                "sta": leg.sta,
                "tail": leg.tail,
                "aircraft_model": leg.aircraft_model,
                "capacity": leg.capacity,
                "booked_pax": leg.booked_pax,
            }
        }
        store = self.ctx.store
        if store.has_risk:
            rows = store.query(
                """SELECT p_15, p_60, planning_delay_minutes, risk_band, reasons, connecting_pax, expected_misconnects
                   FROM flight_risk WHERE flight_id = ?""",
                [flight_id],
            )
            if rows:
                r = rows[0]
                out["delay_risk"] = {
                    "p_15": round(float(r["p_15"]), 3),
                    "p_60": round(float(r["p_60"]), 3),
                    "planning_delay_minutes": r["planning_delay_minutes"],
                    "band": r["risk_band"],
                    "reasons": [x["text"] for x in json.loads(r["reasons"] or "[]")][:3],
                    "connecting_passengers": r["connecting_pax"],
                    "expected_missed_connections": round(float(r["expected_misconnects"]), 1),
                }
        return out

    def _t_aircraft_rotation(self, flight_id: str) -> dict[str, Any]:
        leg = self._leg(flight_id)
        legs = self.ctx.store.tail_legs(leg.tail, leg.std, leg.std + timedelta(hours=48))
        flights, prev_sta = [], None
        for x in legs:
            flights.append(
                {
                    "flight_id": x.flight_id,
                    "flight_number": x.flight_number,
                    "route": f"{x.origin}-{x.destination}",
                    "std": x.std,
                    "sta": x.sta,
                    "booked_pax": x.booked_pax,
                    "ground_minutes_before": int((x.std - prev_sta).total_seconds() // 60) if prev_sta else None,
                }
            )
            prev_sta = x.sta
        return {"tail": leg.tail, "flights": flights}

    def _analyse(self, flight_id: str, delay: int, selected: str | None = None) -> dict[str, Any]:
        try:
            return analyse_delay(self.ctx, flight_id, delay, priority.DEFAULT_WEIGHTS, selected)
        except ScenarioError as exc:
            raise ToolError(str(exc)) from exc

    def _t_assess_delay(self, flight_id: str, delay_minutes: int) -> dict[str, Any]:
        result = self._analyse(flight_id, delay_minutes)
        self.assessment, self._impacts = Assessment(flight_id, delay_minutes, result), {}
        return {
            "flight_id": flight_id,
            "delay_minutes": delay_minutes,
            "options": [_option_brief(o) for o in result["options"]],
            "strategies": result["strategies"],
            "assumptions": result["assumptions"],
        }

    def _need_assessment(self) -> Assessment:
        if self.assessment is None:
            raise ToolError("Run assess_delay first")
        return self.assessment

    def _t_compare_strategies(self) -> dict[str, Any]:
        a = self._need_assessment()
        options = {o["key"]: o for o in a.result["options"]}
        out = []
        for s in a.result["strategies"]:
            o = options[s["pick"]]
            out.append({"strategy": s["key"], "label": s["label"], "option_key": o["key"], **_option_brief(o)})
        return {"picks": out, "same_pick_for_all": len({p["option_key"] for p in out}) == 1}

    def _t_passenger_impact(self, option_key: str) -> dict[str, Any]:
        a = self._need_assessment()
        if option_key not in {o["key"] for o in a.result["options"]}:
            raise ToolError(f"Option {option_key} is not in the last assessment")
        if option_key not in self._impacts:
            r = self._analyse(a.flight_id, a.delay_minutes, option_key)
            rows, reb = r["passengers"], r.get("rebooking") or {}
            o = next(x for x in r["options"] if x["key"] == option_key)
            self._impacts[option_key] = {
                "option_key": option_key,
                "missed_connections": o["misconnects"],
                "cancelled_passengers": o["cancelled_passengers"],
                "rebooked": reb.get("protected", 0),
                "without_seat": reb.get("unprotected", 0),
                "groups_split": reb.get("groups_split", 0),
                "hotel_rooms": reb.get("hotel_rooms", 0),
                "care_cost_aed": reb.get("care_cost_aed", 0),
                "priority_tiers": r.get("tier_counts", {}),
                "special_assistance": sum(1 for x in rows if x.get("ssr")),
                "with_infants": sum(1 for x in rows if x.get("infants")),
                "rebooked_on": _count_by(x["assigned_flight"] for x in rows if x.get("assigned_flight")),
            }
        return self._impacts[option_key]

    def _t_watchlist(self, limit: int) -> dict[str, Any]:
        store = self.ctx.store
        if not store.has_risk:
            return {"flights": [], "note": "Delay-risk data is not available"}
        now = self.ctx.settings.now_utc
        rows = store.query(
            """SELECT f.flight_id, f.flight_number, f.origin, f.destination, f.std, r.p_60, r.risk_band,
                      r.planning_delay_minutes, r.expected_misconnects
               FROM flights f JOIN flight_risk r USING (flight_id)
               WHERE f.std >= ? AND f.std < ? ORDER BY r.expected_misconnects DESC, f.std LIMIT ?""",
            [now, now + timedelta(days=7), limit],
        )
        for r in rows:
            r["p_60"], r["expected_misconnects"] = (
                round(float(r["p_60"]), 3),
                round(float(r["expected_misconnects"]), 1),
            )
        return {"flights": rows}

    def _t_submit_recommendation(
        self, option_key: str, strategy: str, reasons: list[str], risks: list[str], checks: list[str]
    ) -> dict[str, Any]:
        a = self._need_assessment()
        if option_key not in {o["key"] for o in a.result["options"]}:
            raise ToolError(f"Option {option_key} is not one the engine produced; choose from the last assessment")
        if strategy not in strategies.STRATEGIES:
            raise ToolError(f"Unknown strategy {strategy}")
        self.final = {
            "flight_id": a.flight_id,
            "delay_minutes": a.delay_minutes,
            "option_key": option_key,
            "strategy": strategy,
            "reasons": reasons[:4],
            "risks": risks[:4],
            "checks": checks[:4],
        }
        return {"accepted": True, "option_key": option_key, "strategy": strategy}


def _option_brief(o: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": o["key"],
        "kind": o["kind"],
        "label": o["label"],
        "cost_aed": round(o["cost_aed"]),
        "aircraft_delay_minutes": o["total_delay_minutes"],
        "flights_delayed": o["legs_delayed"],
        "passenger_delay_minutes": o["passenger_delay_minutes"],
        "missed_connections": o["misconnects"],
        "cancelled_flights": [c["flight_number"] for c in o["cancelled_flights"]],
        "cancelled_passengers": o["cancelled_passengers"],
        "passengers_without_seat": o["passengers_without_seat"],
        "picked_by": o["picked_by"],
    }


def _count_by(values: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def to_json(value: Any) -> str:
    """Tool results as JSON text (datetimes as ISO strings)."""
    return json.dumps(value, default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v), sort_keys=True)
