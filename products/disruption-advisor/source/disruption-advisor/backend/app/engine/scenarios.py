"""Scenario analysis: the two MVP flows (UC5 briefing: "identify impact, evaluate recovery, recommend an action").

A. ``analyse_delay``: a flight is delayed. Propagate along the aircraft rotation (7-day horizon), re-check every
   connection, compare recovery options (absorb the delay | swap with a same-type aircraft at the hub | cancel or
   consolidate a later round trip, phase 3), cost them, re-accommodate the passengers each option leaves behind,
   and recommend the pick of the chosen strategy (lowest cost by default; app/engine/strategy.py).
B. ``analyse_cancellation``: a flight is cancelled. Rank its passengers (tiers + weights), assign them to
   alternatives within available seats (CP-SAT, PNRs together), and cost and explain the plan.

Results are plain JSON-serialisable dicts; the API stores them with the scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.config import Settings
from app.engine import priority, rebooking
from app.engine import strategy as strategies
from app.engine.care import CareRules, care_for
from app.engine.cost import CostModel, care_cost, eu261_compensation_eur, great_circle_km
from app.engine.explain import Explainer, template_message
from app.engine.network import (
    RotationPlan,
    TurnTimes,
    absorb_delay,
    cancel_round_trip,
    hold_flight,
    round_trip_pairs,
    swap_rotations,
)
from app.engine.passengers import Connection, connections_at_risk
from app.engine.store import Leg, OpsStore

SWAP_SEARCH = timedelta(hours=3)
MAX_SWAP_OPTIONS = 3
MAX_HOLD_CANDIDATES = 5  # onward flights tried for a hold, most missed connections first
HOLD_STEP = 5  # holds are rounded up to 5 minutes
FREQUENCY_BONUS = {"frequent": 1.0, "regular": 0.5}
HUB = "SHJ"  # rebooking through the hub (gap 3)
HUB_ARRIVAL_SLACK = timedelta(hours=12)  # a hub itinerary leaves within the window and may arrive up to 12 h later
CANCEL_WINDOW = timedelta(hours=24)  # round trips considered for cancellation (ADR 0011)
MAX_CANCEL_OPTIONS = 3
CONSOLIDATE_WITHIN_MINUTES = 360  # every cancelled passenger rebooked on the same route within 6 h
NO_SEAT_DELAY_MINUTES = 24 * 60  # passenger delay counted for someone without a seat (assumption, shown in the UI)


@dataclass(frozen=True)
class Context:
    store: OpsStore
    settings: Settings
    explainer: Explainer

    @property
    def cost(self) -> CostModel:
        s = self.settings
        return CostModel(
            s.cost_delay_per_minute,
            s.cost_hotel_per_night,
            s.cost_meal_voucher,
            s.cost_rebooking_handling,
            s.eur_to_aed,
        )

    @property
    def care_rules(self) -> CareRules:
        s = self.settings
        return CareRules(
            s.care_meal_after_minutes,
            s.care_meal_every_minutes,
            s.care_hotel_after_minutes,
            s.care_refund_offer_after_minutes,
            s.cost_meal_voucher,
            s.cost_hotel_per_night,
            s.cost_transport,
        )

    @property
    def min_turn(self) -> TurnTimes:
        s = self.settings
        return TurnTimes(
            timedelta(minutes=s.min_turn_minutes),
            {k: timedelta(minutes=v) for k, v in s.min_turn_by_station.items()},
        )

    @property
    def max_connection(self) -> timedelta:
        return timedelta(minutes=self.settings.max_connection_minutes)


class ScenarioError(ValueError):
    """The requested scenario cannot be analysed (unknown flight, outside the data window, ...)."""


def _leg_json(leg: Leg) -> dict[str, Any]:
    return {
        "flight_id": leg.flight_id,
        "flight_number": leg.flight_number,
        "airline": leg.airline,
        "tail": leg.tail,
        "origin": leg.origin,
        "destination": leg.destination,
        "std": leg.std,
        "sta": leg.sta,
        "capacity": leg.capacity,
        "booked_seats": leg.booked_seats,
        "booked_pax": leg.booked_pax,
        "aircraft_model": leg.aircraft_model,
        "capacity_source": leg.capacity_source,
    }


def _eu261(ctx: Context, leg: Leg) -> int:
    rows = ctx.store.query(
        "SELECT iata, country, lat, lon FROM airports WHERE iata IN (?, ?)", [leg.origin, leg.destination]
    )
    a = {r["iata"]: r for r in rows}
    o, d = a.get(leg.origin), a.get(leg.destination)
    if not o or not d or not o["lat"] or not d["lat"]:
        return 0
    km = great_circle_km(float(o["lat"]), float(o["lon"]), float(d["lat"]), float(d["lon"]))
    return eu261_compensation_eur(o["country"], d["country"], km)


# ---------------------------------------------------------------------------------------------------------------
# A. Delay
# ---------------------------------------------------------------------------------------------------------------
def _option_kpis(ctx: Context, key: str, label: str, plan: RotationPlan, cancelled_legs: list[Leg]) -> dict[str, Any]:
    cancelled = {x.flight_id for x in cancelled_legs}
    delayed = plan.delayed()
    connections = connections_at_risk(
        ctx.store,
        plan,
        cancelled,
        [t.leg.flight_id for t in delayed],
        ctx.settings.default_mct_minutes,
        ctx.max_connection,
    )
    # Passengers on a cancelled flight are rebooked as cancelled passengers, not counted again as missed connections.
    missed = [
        c
        for c in connections
        if c.missed and c.inbound_flight_id not in cancelled and c.outbound_flight_id not in cancelled
    ]
    cm = ctx.cost
    delay_cost = plan.total_delay_minutes * cm.delay_per_minute
    care = sum(care_cost(cm, t.delay_minutes, overnight=False) * t.leg.booked_pax for t in delayed)
    eu = sum(_eu261(ctx, t.leg) * t.leg.booked_pax for t in delayed if t.delay_minutes >= 180)
    misconnect_cost = len(missed) * (cm.rebooking_handling + cm.meal_voucher)
    goodwill = _misconnect_goodwill(ctx, missed)
    total = delay_cost + care + eu * cm.eur_to_aed + misconnect_cost + goodwill
    return {
        "key": key,
        "kind": key.split(":")[0],
        "label": label,
        "total_delay_minutes": plan.total_delay_minutes,
        "legs_delayed": len(delayed),
        "delayed_passengers": plan.delayed_passengers,
        "misconnects": len(missed),
        "connections_checked": len(connections),
        "eu261_compensation_eur": eu,
        "cost_aed": round(total, 0),
        "cost_breakdown": {
            "aircraft_delay": round(delay_cost),
            "passenger_care": round(care),
            "eu261_compensation": round(eu * cm.eur_to_aed),
            "misconnect_handling": round(misconnect_cost),
            "misconnect_goodwill": round(goodwill),
        },
        "cascade": _cascade(plan),
        "holds": [],
        "legs": [
            {
                "flight_id": t.leg.flight_id,
                "flight_number": t.leg.flight_number,
                "origin": t.leg.origin,
                "destination": t.leg.destination,
                "std": t.leg.std,
                "new_std": t.new_std,
                "new_sta": t.new_sta,
                "delay_minutes": t.delay_minutes,
                "operated_by": t.operated_by,
                "scheduled_tail": t.leg.tail,
                "booked_pax": t.leg.booked_pax,
            }
            for t in sorted(plan.timings.values(), key=lambda t: t.new_std)
        ],
        "cancelled_flights": [
            {
                "flight_id": x.flight_id,
                "flight_number": x.flight_number,
                "origin": x.origin,
                "destination": x.destination,
                "std": x.std,
                "booked_pax": x.booked_pax,
            }
            for x in cancelled_legs
        ],
        "cancelled_passengers": 0,  # set from the rebooking list (seated passengers) in _option_passengers
        "_missed": missed,
        "_cancelled": cancelled_legs,
        "_plan": plan,
    }


def _misconnect_goodwill(ctx: Context, missed: list[Connection]) -> float:
    """Goodwill cost of the missed connections, by passenger value: a frequent or high-tier loyal traveller (own tier
    or the family account's) is worth more to keep (user 2026-11-21). Base x (1 + 2 x tier value + frequency)."""
    if not missed:
        return 0.0
    keys = {(c.pnr, c.customer_key) for c in missed}
    rows = {
        (p["pnr"], p["customer_key"]): p for p in ctx.store.passengers_on(sorted({c.inbound_flight_id for c in missed}))
    }
    base, total = ctx.settings.cost_misconnect_goodwill, 0.0
    for key in keys:
        p = rows.get(key, {})
        family = p.get("family_tier_synthetic") if p.get("family_account_synthetic") else None
        tier = max(priority.TIER_VALUE.get(p.get("loyalty_tier_synthetic"), 0.0), priority.TIER_VALUE.get(family, 0.0))
        total += base * (1 + 2 * tier + FREQUENCY_BONUS.get(str(p.get("travel_frequency_band")), 0.0))
    return total


def _cascade(plan: RotationPlan) -> dict[str, Any]:
    """How far the delay spreads: flights and aircraft delayed, how many beyond the first two flights of each
    aircraft, and when the last delayed flight lands (user 2026-11-21: look past the next flight)."""
    delayed = plan.delayed()
    by_tail: dict[str, list[Any]] = {}
    for timing in delayed:
        by_tail.setdefault(timing.operated_by, []).append(timing)
    return {
        "flights_delayed": len(delayed),
        "aircraft": len(by_tail),
        "beyond_next_flight": sum(max(len(ts) - 2, 0) for ts in by_tail.values()),
        "delay_ends": max((ts.new_sta for ts in delayed), default=None),
        "passenger_delay_minutes": sum(ts.delay_minutes * ts.leg.booked_pax for ts in delayed),
    }


def _with_holds(ctx: Context, base: dict[str, Any], horizon_end: datetime) -> dict[str, Any] | None:
    """Hold variant of an option (user 2026-11-21): for each onward flight that its connecting passengers would miss,
    try holding it just long enough (up to HOLD_MAX) for them to make the minimum connection time. The hold delays that
    flight and its aircraft's later flights (knock-on on another aircraft) and can break other connections; it is
    kept only when the option's total cost, including the passengers' goodwill cost, goes down."""
    missed: list[Connection] = base["_missed"]
    plan: RotationPlan = base["_plan"]
    by_outbound: dict[str, list[Connection]] = {}
    for c in missed:
        by_outbound.setdefault(c.outbound_flight_id, []).append(c)
    current: dict[str, Any] = base
    holds: list[dict[str, Any]] = []
    for outbound_id, conns in sorted(by_outbound.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:MAX_HOLD_CANDIDATES]:
        out = ctx.store.leg(outbound_id)
        if out is None or outbound_id in plan.timings:
            continue  # unknown, or already moved by this option (e.g. flown by the delayed aircraft)
        need = 0
        for c in conns:
            inbound = plan.timings.get(c.inbound_flight_id)
            if inbound is not None:
                need = max(
                    need, int((inbound.new_sta + timedelta(minutes=c.mct_minutes) - out.std).total_seconds() // 60)
                )
        minutes = -(-need // HOLD_STEP) * HOLD_STEP
        if minutes <= 0 or minutes > ctx.settings.hold_max_minutes:
            continue
        rotation = [x for x in ctx.store.tail_legs(out.tail, out.std, horizon_end) if x.std > out.std]
        trial_plan = hold_flight(plan, out, minutes, rotation, ctx.min_turn)
        trial = _option_kpis(ctx, base["key"], base["label"], trial_plan, base["_cancelled"])
        if trial["cost_aed"] < current["cost_aed"]:
            kept = len(conns) - sum(1 for m in trial["_missed"] if m.outbound_flight_id == outbound_id)
            plan, current = trial_plan, trial
            holds.append(
                {
                    "flight_id": out.flight_id,
                    "flight_number": out.flight_number,
                    "minutes": minutes,
                    "connections_kept": kept,
                }
            )
    if not holds:
        return None
    what = ", ".join(f"{h['flight_number']} {h['minutes']} min" for h in holds)
    kept = sum(int(h["connections_kept"]) for h in holds)
    option = _option_kpis(
        ctx, f"hold:{base['key']}", f"{base['label']} + hold {what} ({kept} connections kept)", plan, base["_cancelled"]
    )
    option["kind"], option["holds"] = "hold", holds
    return option


def _option_passengers(ctx: Context, o: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    """Re-accommodate everyone the option leaves behind (missed connections and cancelled flights), add the
    passenger KPIs and the cancellation cost to ``o``, and return the passenger payload for display."""
    parts: list[tuple[str, dict[str, Any]]] = []
    if o["_missed"]:
        parts.append(("missed_connection", _reaccommodate_misconnects(ctx, o["_missed"], o, weights)))
    cancel_cost = 0.0
    excluded = [x.flight_id for x in o["_cancelled"]]
    for leg in o["_cancelled"]:
        rebooked = _rebook_cancelled(ctx, leg, weights, excluded)
        parts.append(("cancelled", rebooked["payload"]))
        cancel_cost += sum(rebooked["cost"].values())
    payload = _merge_payloads(parts)
    reb = payload["rebooking"] or {}
    rows = payload["passengers"]
    o["passengers_rebooked"] = reb.get("protected", 0)
    o["passengers_without_seat"] = reb.get("unprotected", 0)
    o["passenger_delay_minutes"] = (
        sum(leg["delay_minutes"] * leg["booked_pax"] for leg in o["legs"])
        + sum(r["arrival_delay_minutes"] or 0 for r in rows if r["assigned_flight_id"])
        + NO_SEAT_DELAY_MINUTES * o["passengers_without_seat"]
    )
    if o["_cancelled"]:
        o["cost_breakdown"]["cancellation"] = round(cancel_cost)
        o["cost_aed"] = round(o["cost_aed"] + cancel_cost, 0)
        a, b = o["_cancelled"]
        cancelled_rows = [r for r in rows if r["group"] == "cancelled"]
        o["cancelled_passengers"] = len(cancelled_rows)
        consolidated = bool(cancelled_rows) and all(
            r["assigned_flight_id"] and (r["arrival_delay_minutes"] or 0) <= CONSOLIDATE_WITHIN_MINUTES
            for r in cancelled_rows
        )
        if consolidated:
            o["kind"] = "consolidate"
            o["label"] = (
                f"Consolidate: cancel {a.flight_number}/{b.flight_number}, "
                f"passengers move to other {a.origin}-{a.destination} flights"
            )
    return payload


def _merge_payloads(parts: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """One passenger list for the option: each group keeps its own priority order and is labelled."""
    if not parts:
        return {"passengers": [], "rebooking": None}
    rows, tiers = [], {"1": 0, "2": 0, "3": 0, "non_revenue": 0}
    reb = {
        "alternatives": [],
        "protected": 0,
        "unprotected": 0,
        "groups_split": 0,
        "care_cost_aed": 0,
        "hotel_rooms": 0,
    }
    for group, part in parts:
        rows += [{**r, "group": group} for r in part["passengers"]]
        for k, v in part.get("tier_counts", {}).items():
            tiers[k] = tiers.get(k, 0) + v
        if part["rebooking"]:
            reb["alternatives"] += part["rebooking"]["alternatives"]
            for k in ("protected", "unprotected", "groups_split", "care_cost_aed", "hotel_rooms"):
                reb[k] += part["rebooking"][k]
    return {"passengers": rows, "tier_counts": tiers, "rebooking": reb}


def analyse_delay(
    ctx: Context,
    flight_id: str,
    delay_minutes: int,
    weights: dict[str, float],
    selected_key: str | None = None,
    strategy: str = strategies.DEFAULT,
) -> dict[str, Any]:
    """``selected_key``: the option a controller picked; passengers and costs then follow that option.
    ``strategy``: which strategy's pick is the recommendation (app/engine/strategy.py)."""
    if strategy not in strategies.STRATEGIES:
        raise ScenarioError(f"Unknown strategy {strategy}")
    leg = ctx.store.leg(flight_id)
    if leg is None:
        raise ScenarioError(f"Flight {flight_id} is not in the operating window")
    horizon_end = leg.std + timedelta(days=ctx.settings.horizon_days)
    rest = [x for x in ctx.store.tail_legs(leg.tail, leg.std, horizon_end) if x.std > leg.std]
    delay = timedelta(minutes=delay_minutes)

    absorbed = absorb_delay(leg, rest, delay, ctx.min_turn)
    options = [_option_kpis(ctx, "absorb", f"Absorb the delay on {leg.tail}", absorbed, [])]
    if rest and rest[0].origin == leg.destination:
        takeover = rest[0].std
        candidates = ctx.store.tails_at_station(
            leg.destination, takeover - SWAP_SEARCH, takeover + SWAP_SEARCH, leg.capacity, leg.tail
        )
        swaps = []
        for tail in candidates:
            cand_legs = ctx.store.tail_legs(tail, takeover - timedelta(days=1), horizon_end)
            plan = swap_rotations(leg, rest, delay, ctx.min_turn, tail, cand_legs)
            if plan is not None:
                swaps.append(
                    _option_kpis(ctx, f"swap:{tail}", f"Swap: {tail} takes over {rest[0].flight_number}", plan, [])
                )
        options += sorted(swaps, key=strategies.lowest_cost)[:MAX_SWAP_OPTIONS]
    for i in round_trip_pairs(rest, absorbed, leg.std + CANCEL_WINDOW)[:MAX_CANCEL_OPTIONS]:
        a, b = rest[i], rest[i + 1]
        options.append(
            _option_kpis(
                ctx,
                f"cancel:{a.flight_id}",
                f"Cancel round trip {a.flight_number}/{b.flight_number} ({a.origin}-{a.destination}-{a.origin})",
                cancel_round_trip(leg, rest, delay, ctx.min_turn, i),
                [a, b],
            )
        )

    # Hold the connecting flight instead of letting passengers miss it, where that is cheaper (user 2026-11-21):
    # tried on absorbing the delay and on the cheapest swap.
    bases = [o for o in options if o["kind"] == "absorb"] + sorted(
        (o for o in options if o["kind"] == "swap"), key=strategies.lowest_cost
    )[:1]
    options += [h for h in (_with_holds(ctx, b, horizon_end) for b in bases) if h is not None]

    payloads = {o["key"]: _option_passengers(ctx, o, weights) for o in options}
    missed_by_option: dict[str, list[Connection]] = {o["key"]: o.pop("_missed") for o in options}
    for o in options:
        o.pop("_cancelled")
        o.pop("_plan")
    picks = strategies.picks(options)
    for o in options:
        o["picked_by"] = [name for name, key in picks.items() if key == o["key"]]
    options = strategies.order(options, strategy)
    best = next(o for o in options if o["key"] == picks[strategy])
    chosen = next((o for o in options if o["key"] == selected_key), best)
    missed = missed_by_option[chosen["key"]]
    pax_plan = payloads[chosen["key"]]
    runner_up = next((o for o in options if o["key"] != chosen["key"]), None)

    def brief(o: dict[str, Any]) -> dict[str, Any]:
        return {
            "what": o["label"],
            "flights_delayed": o["legs_delayed"],
            "flights_cancelled": len(o["cancelled_flights"]),
            "extra_delay_minutes": o["total_delay_minutes"],
            "passengers_missing_connections": o["misconnects"],
            "passengers_without_seat": o["passengers_without_seat"],
            "estimated_cost_aed": round(o["cost_aed"]),
        }

    facts = {
        "late_flight": f"{leg.flight_number} from {leg.origin} to {leg.destination}",
        "delay_minutes": delay_minutes,
        "strategy": strategies.label(strategy),
        "chosen_option": brief(chosen),
        "chosen_is_the_recommendation": chosen["key"] == best["key"],
        "recommended_option": brief(best),
        "next_best_alternative": brief(runner_up) if runner_up else None,
        "connections_can_be_saved": chosen["misconnects"] < max(o["misconnects"] for o in options),
        "passengers_rebooked": (pax_plan.get("rebooking") or {}).get("protected", 0),
        "passengers_without_seat": (pax_plan.get("rebooking") or {}).get("unprotected", 0),
        "hotel_rooms_needed": (pax_plan.get("rebooking") or {}).get("hotel_rooms", 0),
    }
    narrative = ctx.explainer.recommendation(facts)
    return {
        "type": "DELAY",
        "flight": _leg_json(leg),
        "delay_minutes": delay_minutes,
        "options": options,
        "strategy": strategy,
        "strategies": [{"key": k, "label": v[0], "pick": picks[k]} for k, v in strategies.STRATEGIES.items()],
        "recommended_key": best["key"],
        "selected_key": chosen["key"],
        "explanation": {"text": narrative.text, "source": narrative.source},
        "misconnections": [vars(c) for c in missed],
        **pax_plan,
        "assumptions": _assumptions(ctx),
    }


def _reaccommodate_misconnects(
    ctx: Context, missed: list[Connection], option: dict[str, Any], weights: dict[str, float]
) -> dict[str, Any]:
    if not missed:
        return {"passengers": [], "rebooking": None}
    new_arrival = {leg["flight_id"]: leg["new_sta"] for leg in option["legs"]}
    by_route: dict[tuple[str, str], list[Connection]] = {}
    for c in missed:
        by_route.setdefault((c.hub, c.final_destination), []).append(c)
    pax_rows = {
        (p["pnr"], p["customer_key"]): p
        for p in ctx.store.passengers_on(sorted({c.outbound_flight_id for c in missed}))
    }
    all_ranked, assignments, alternatives = [], [], []
    for (hub, dest), conns in by_route.items():
        ready = max(new_arrival.get(c.inbound_flight_id, datetime.min) for c in conns) + timedelta(
            minutes=max(c.mct_minutes for c in conns)
        )
        alts = ctx.store.alternatives(
            hub,
            dest,
            ready,
            ready + timedelta(hours=ctx.settings.rebooking_window_hours),
            sorted({c.outbound_flight_id for c in conns}),
        )
        people = [pax_rows[(c.pnr, c.customer_key)] for c in conns if (c.pnr, c.customer_key) in pax_rows]
        ranked = priority.rank(people, weights, {(c.pnr, c.customer_key) for c in conns}, {})
        original = ctx.store.leg(conns[0].outbound_flight_id)
        result = rebooking.plan(ranked, alts, original.sta if original else ready, {})
        all_ranked += ranked
        assignments += result.assignments
        alternatives += result.alternatives
    inbound = {(c.pnr, c.customer_key): c.inbound_flight_id.split("_")[0] for c in missed}
    waiting_from: dict[tuple[str, str], datetime | None] = {}
    for c in missed:
        arrival = new_arrival.get(c.inbound_flight_id)
        if arrival is None:
            leg = ctx.store.leg(c.inbound_flight_id)
            arrival = leg.sta if leg else None
        waiting_from[(c.pnr, c.customer_key)] = arrival
    hub = missed[0].hub
    return _passenger_payload(
        ctx,
        all_ranked,
        assignments,
        alternatives,
        event="missed_connection",
        inbound=inbound,
        waiting_from=waiting_from,
        station=hub,
        transfer=True,
    )


# ---------------------------------------------------------------------------------------------------------------
# B. Cancellation
# ---------------------------------------------------------------------------------------------------------------
def _rebook_cancelled(ctx: Context, leg: Leg, weights: dict[str, float], exclude: list[str]) -> dict[str, Any]:
    """Rank the passengers of a cancelled flight (tiers + weights) and rebook them on other flights of the same
    route (CP-SAT, PNRs together, onward connections kept where possible); ``exclude`` lists cancelled flights."""
    passengers = ctx.store.passengers_on([leg.flight_id])
    connections = connections_at_risk(
        ctx.store,
        RotationPlan(),
        {leg.flight_id},
        [leg.flight_id],
        ctx.settings.default_mct_minutes,
        ctx.max_connection,
    )
    onward = {(c.pnr, c.customer_key) for c in connections}
    deadline = {}
    for c in connections:
        out = ctx.store.leg(c.outbound_flight_id)
        if out:
            deadline[(c.pnr, c.customer_key)] = out.std - timedelta(minutes=c.mct_minutes)
    seg_counts = (
        {
            (r["pnr"], r["customer_key"]): int(r["n"])
            for r in ctx.store.query(
                """SELECT pnr, customer_key, count(*) AS n FROM pax_segments
           WHERE list_contains(?, pnr) AND dep_utc BETWEEN ? AND ? GROUP BY 1, 2""",
                [sorted({p["pnr"] for p in passengers}), leg.std - timedelta(hours=24), leg.std + timedelta(hours=24)],
            )
        }
        if passengers
        else {}
    )  # same journey = segments within 24 h (a return trip days later is not a connection)

    ranked = priority.rank(passengers, weights, onward, seg_counts)
    after = max(ctx.settings.now_utc, leg.std - timedelta(hours=3))
    until = leg.std + timedelta(hours=ctx.settings.rebooking_window_hours)
    excluded = sorted({leg.flight_id, *exclude})
    options: list[Leg | rebooking.Itinerary] = list(
        ctx.store.alternatives(leg.origin, leg.destination, after, until, excluded)
    )
    options += _hub_itineraries(ctx, leg, connections, after, until, excluded)
    final_destination = {(c.pnr, c.customer_key): c.final_destination for c in connections}
    final_arrival = {
        (c.pnr, c.customer_key): out.sta for c in connections if (out := ctx.store.leg(c.outbound_flight_id))
    }
    result = rebooking.plan(
        ranked, options, leg.sta, deadline, final_destination=final_destination, final_arrival=final_arrival
    )
    payload = _passenger_payload(
        ctx,
        ranked,
        result.assignments,
        result.alternatives,
        event="cancelled",
        waiting_from={(r.passenger["pnr"], r.passenger["customer_key"]): leg.std for r in ranked},
        station=leg.origin,
        transfer=False,
    )
    cm, eu = ctx.cost, _eu261(ctx, leg)
    seated = len(ranked)
    cost = {
        "eu261_compensation": round(eu * seated * cm.eur_to_aed),
        "passenger_care": round(payload["rebooking"]["care_cost_aed"]),
        "rebooking_handling": round(seated * cm.rebooking_handling),
    }
    return {"ranked": ranked, "result": result, "payload": payload, "cost": cost, "eu": eu, "onward": onward}


def _hub_itineraries(
    ctx: Context, leg: Leg, connections: list[Connection], after: datetime, until: datetime, excluded: list[str]
) -> list[rebooking.Itinerary]:
    """Rebooking through the hub (gap 3), only on connections the airline sells (fares list) and within the MCT:
    - the cancelled flight flies into the hub: connecting passengers may move to a new inbound flight AND a new onward
      flight to their final destination (their original onward flight is excluded, they already hold that seat);
    - the cancelled flight does not touch the hub (e.g. RKT-CCJ): everyone may travel through the hub."""
    hub, out = HUB, []

    def pairs(origin: str, destination: str, extra: list[str]) -> list[tuple[Leg, Leg]]:
        mct = ctx.store.mct_minutes(origin, hub, destination, default=ctx.settings.default_mct_minutes)
        return ctx.store.via_hub(
            origin,
            destination,
            hub,
            after,
            until + HUB_ARRIVAL_SLACK,
            excluded + extra,
            timedelta(minutes=mct),
            ctx.max_connection,
        )

    if leg.destination == hub:
        for dest in sorted({c.final_destination for c in connections}):
            held = sorted({c.outbound_flight_id for c in connections if c.final_destination == dest})
            out += [rebooking.Itinerary((a, b), for_destination=dest) for a, b in pairs(leg.origin, dest, held)]
    elif leg.origin != hub:
        out += [rebooking.Itinerary((a, b)) for a, b in pairs(leg.origin, leg.destination, [])]
    return out


def analyse_cancellation(ctx: Context, flight_id: str, weights: dict[str, float]) -> dict[str, Any]:
    leg = ctx.store.leg(flight_id)
    if leg is None:
        raise ScenarioError(f"Flight {flight_id} is not in the operating window")
    rebooked = _rebook_cancelled(ctx, leg, weights, [])
    result, payload, cost = rebooked["result"], rebooked["payload"], rebooked["cost"]
    free_seats = sum(int(str(a["available_seats"])) for a in result.alternatives)
    nxt = next(
        (
            x
            for x in ctx.store.tail_legs(leg.tail, leg.std, leg.std + timedelta(days=1))
            if x.std > leg.std and x.origin == leg.destination
        ),
        None,
    )
    facts = {
        "cancelled_flight": f"{leg.flight_number} from {leg.origin} to {leg.destination}",
        "passengers_to_move": len(rebooked["ranked"]),
        "free_seats_on_other_flights_within_24h": free_seats,
        "passengers_rebooked": result.protected_passengers,
        "passengers_without_seat": result.unprotected_passengers,
        "who_goes_first": "passengers needing special assistance and families with babies; "
        "then passengers with onward connections; staff travel last",
        "estimated_cost_aed": sum(cost.values()),
    }
    narrative = ctx.explainer.cancellation(facts)
    return {
        "type": "CANCEL",
        "flight": _leg_json(leg),
        "explanation": {"text": narrative.text, "source": narrative.source},
        "cost_aed": cost,
        "cost_total_aed": sum(cost.values()),
        "eu261_per_passenger_eur": rebooked["eu"],
        "onward_connections": len(rebooked["onward"]),
        "solver_status": result.solver_status,
        "aircraft_follow_on": _leg_json(nxt) if nxt else None,
        **payload,
        "assumptions": _assumptions(ctx),
    }


# ---------------------------------------------------------------------------------------------------------------
def _passenger_payload(
    ctx: Context,
    ranked: list[priority.Ranked],
    assignments: list[rebooking.Assignment],
    alternatives: list[dict[str, Any]],
    event: str,
    inbound: dict[tuple[str, str], str] | None = None,
    waiting_from: dict[tuple[str, str], datetime | None] | None = None,
    station: str | None = None,
    transfer: bool = False,
) -> dict[str, Any]:
    where: dict[tuple[str, str], rebooking.Assignment] = {}
    for assignment in assignments:
        for key in assignment.customer_keys:
            where[(assignment.pnr, key)] = assignment
    rules = ctx.care_rules
    station_tz = ctx.store.airport_tz().get(station or "")
    care_total = 0.0
    rows = []
    for pos, r in enumerate(ranked, start=1):
        p = r.passenger
        a = where.get((p["pnr"], p["customer_key"]))
        late_inbound = (inbound or {}).get((p["pnr"], p["customer_key"]))
        care = care_for(
            rules,
            (waiting_from or {}).get((p["pnr"], p["customer_key"])),
            a.new_std if a else None,
            station_tz,
            has_seat=bool(a and a.flight_id),
            transfer=transfer,
            ssr=p.get("ssr_code"),
            infants=p["infants"],
            new_flight=a.flight_number if a and a.flight_id else None,
        )
        care_total += care.cost(rules)
        rows.append(
            {
                "rank": pos,
                "pnr": p["pnr"],
                "customer_key": p["customer_key"],
                # the bookings carry no names (name-free format, 2026-11-21): the synthetic passenger ID identifies
                "name": p.get("passenger_id") or "-",
                "passenger_id": p.get("passenger_id"),
                "passport_number_synthetic": p.get("passport_number_synthetic"),
                "national_id_synthetic": p.get("national_id_synthetic"),
                "pax_type": p["pax_type"],
                "route": f"{p['origin']}-{p['destination']}",
                "flight_id": p["flight_id"],
                "tier": r.tier,
                "tier_reason": r.tier_reason,
                "score": r.score,
                "contributions": r.contributions,
                "non_revenue": r.non_revenue,
                "reason": priority.explain(r),
                "loyalty_tier": p.get("loyalty_tier_synthetic"),
                "loyalty_priority": p.get("loyalty_priority"),
                "loyalty_effective_tier": p.get("loyalty_effective_tier"),
                "loyalty_effective_priority": p.get("loyalty_effective_priority"),
                "loyalty_via_family": p.get("loyalty_via_family", False),
                "loyalty_points": p.get("available_points_synthetic"),
                "family_account": bool(p.get("family_account_synthetic")),
                "family_head": bool(p.get("family_head_synthetic")),
                "frequency": p.get("travel_frequency_band"),
                "fare": p["fare"],
                "fare_family": p.get("fare_family_synthetic"),
                "booking_code": p.get("booking_code"),
                "booking_class_level": p.get("booking_class_level"),
                "ancillaries": p["ancillaries"],
                "ssr": p.get("ssr_code"),
                "ssr_source": p.get("ssr_source"),
                "pnr_size": p["pnr_size"],
                "infants": p["infants"],
                "children": p["children"],
                "assigned_flight": a.flight_number if a else None,
                "assigned_flight_id": a.flight_id if a else None,
                "new_departure": a.new_std if a else None,
                "arrival_delay_minutes": a.arrival_delay_minutes if a else None,
                "onward_ok": a.onward_ok if a else None,
                "split": a.split if a else False,
                "assignment_reason": a.reason if a else "",
                "missed_inbound_flight": late_inbound,
                "care": {
                    "summary": care.summary,
                    "wait_minutes": care.wait_minutes,
                    "meals": care.meals,
                    "hotel": care.hotel,
                    "transport": care.transport,
                    "refund_option": care.refund_option,
                    "flags": care.flags,
                    "cost_aed": round(care.cost(rules)),
                },
                "message": template_message(
                    {
                        "flight": p["flight_id"].split("_")[0],
                        "late_inbound_flight": late_inbound,
                        "origin": p["origin"],
                        "destination": p["destination"],
                        "event": event,
                        "new_flight": a.flight_number if a and a.flight_id else None,
                        "new_departure": f"{a.new_std:%d %b %H:%M} UTC" if a and a.new_std else None,
                        "care": care.message_text(),
                    }
                ),
            }
        )
    tiers: dict[str, int] = {str(t): sum(1 for r in ranked if r.tier == t and not r.non_revenue) for t in (1, 2, 3)}
    tiers["non_revenue"] = sum(1 for r in ranked if r.non_revenue)
    return {
        "passengers": rows,
        "tier_counts": tiers,
        "rebooking": {
            "alternatives": alternatives,
            "protected": sum(a.seats for a in assignments if a.flight_id),
            "unprotected": sum(a.seats for a in assignments if not a.flight_id),
            "groups_split": sum(1 for a in assignments if a.split),
            "care_cost_aed": round(care_total),
            "hotel_rooms": sum(1 for row in rows if row["care"]["hotel"]),
        },
    }


def _assumptions(ctx: Context) -> list[str]:
    s = ctx.settings
    return [
        f"Demo clock: {s.now_utc:%Y-%m-%d %H:%M} UTC; data window per ingest report.",
        f"Minimum aircraft turn time: {', '.join(f'{k} {v}' for k, v in s.min_turn_by_station.items())} min, "
        f"elsewhere {s.min_turn_minutes} min (measured from 2026 actual turns); block times as scheduled.",
        f"Connections: same PNR, 15 min-{s.max_connection_minutes // 60} h; "
        f"hub MCT table, else {s.default_mct_minutes} min.",
        "Seat capacity: inventory allocation where available, otherwise aircraft layout inferred from the data; "
        "available = capacity - booked (never below zero).",
        "Loyalty tier, fare family and most special-service codes are synthetic (labelled in the passenger list).",
        f"Costs are assumed: delay AED {s.cost_delay_per_minute:g}/min, hotel AED {s.cost_hotel_per_night:g}, "
        f"meal AED {s.cost_meal_voucher:g}, handling AED {s.cost_rebooking_handling:g}; EU261 on EU/EEA/CH departures.",
        "Crew legality is not checked (no crew data); crew control must confirm any swap or cancellation.",
        f"Cancelling a round trip: its passengers are rebooked on the same route within "
        f"{s.rebooking_window_hours} h; revenue loss is not counted (no fare revenue per flight is supplied).",
        f"Passenger delay minutes count {NO_SEAT_DELAY_MINUTES // 60} h for each passenger left without a seat.",
        f"A missed connection costs AED {s.cost_misconnect_goodwill:g} goodwill x passenger value (1 + 2 x loyalty "
        f"tier value + 1 frequent / 0.5 regular); a connecting flight may be held up to {s.hold_max_minutes} min "
        "when that costs less, including the knock-on on its aircraft.",
    ]


def presets(ctx: Context) -> dict[str, list[dict[str, Any]]]:
    """Suggested demo flights (UC5 example scenario), found in the data:
    A: G9 arrivals into SHJ with a tight onward turn (≤ 70 min) and the most connecting passengers.
    B: G9 departures from SHJ where the alternatives within 24 h have fewer free seats than passengers,
       preferring flights that carry passengers in the mandated-care tier.
    """
    now = ctx.settings.now_utc
    delay = ctx.store.query(
        """WITH arr AS (
             SELECT a.flight_id, a.flight_number, a.origin, a.destination, a.std, a.sta, a.tail,
                    a.capacity_source = 'synthetic-demo' AS is_demo, min(b.std) AS next_std
             FROM flights a JOIN flights b ON b.tail = a.tail AND b.origin = a.destination
                  AND b.std > a.sta AND b.std < a.sta + INTERVAL 12 HOUR
             WHERE a.destination = 'SHJ' AND a.airline = 'G9' AND a.std >= ? AND a.std < ? + INTERVAL 4 DAY
             GROUP BY ALL)
           SELECT arr.flight_id, flight_number, origin, destination, std, tail, is_demo,
                  date_diff('minute', sta, next_std) AS turn_minutes,
                  (SELECT count(*) FROM pax_segments p JOIN pax_segments q ON q.pnr = p.pnr
                     AND q.customer_key = p.customer_key AND q.origin = 'SHJ'
                     AND q.dep_utc > arr.sta AND q.dep_utc < arr.sta + INTERVAL 6 HOUR
                   WHERE p.flight_id = arr.flight_id) AS connecting_pax
           FROM arr WHERE date_diff('minute', sta, next_std) <= 70
           ORDER BY is_demo DESC, connecting_pax DESC LIMIT 6""",
        [now, now],
    )
    cancel = ctx.store.query(
        """SELECT * FROM (
             SELECT f.flight_id, f.flight_number, f.origin, f.destination, f.std, f.tail, f.booked_seats,
                    (SELECT coalesce(sum(greatest(g.capacity - g.booked_seats, 0)), 0) FROM flights g
                      WHERE g.origin = f.origin AND g.destination = f.destination AND g.flight_id <> f.flight_id
                        AND g.std > f.std - INTERVAL 3 HOUR AND g.std <= f.std + INTERVAL 24 HOUR) AS free_seats,
                    (SELECT count(*) FROM pax_segments p WHERE p.flight_id = f.flight_id
                        AND (p.ssr_code IS NOT NULL OR p.infants > 0)) AS care_pax
             FROM flights f
             WHERE f.airline = 'G9' AND f.origin = 'SHJ' AND f.std >= ? AND f.std < ? + INTERVAL 4 DAY
               AND f.booked_seats > 120 AND f.capacity_source <> 'synthetic-demo')
           WHERE free_seats BETWEEN 20 AND booked_seats - 20 AND care_pax > 0
           ORDER BY care_pax DESC, abs(free_seats - booked_seats / 2) LIMIT 5""",
        [now, now],
    )
    return {"delay": delay, "cancel": cancel}
