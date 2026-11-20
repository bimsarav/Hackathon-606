"""Scenario analysis: the two MVP flows (UC5 briefing: "identify impact, evaluate recovery, recommend an action").

A. ``analyse_delay``: a flight is delayed. Propagate along the aircraft rotation (7-day horizon), re-check every
   connection, compare recovery options (absorb the delay | swap with a same-type aircraft at the hub), cost them,
   recommend the cheapest, then prioritise and re-accommodate the passengers who still miss connections.
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
from app.engine.care import CareRules, care_for
from app.engine.cost import CostModel, care_cost, eu261_compensation_eur, great_circle_km
from app.engine.explain import Explainer, template_message
from app.engine.network import RotationPlan, TurnTimes, absorb_delay, swap_rotations
from app.engine.passengers import Connection, connections_at_risk
from app.engine.store import Leg, OpsStore

SWAP_SEARCH = timedelta(hours=3)
MAX_SWAP_OPTIONS = 3


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
def _option_kpis(ctx: Context, key: str, label: str, plan: RotationPlan, cancelled: set[str]) -> dict[str, Any]:
    delayed = plan.delayed()
    connections = connections_at_risk(
        ctx.store,
        plan,
        cancelled,
        [t.leg.flight_id for t in delayed],
        ctx.settings.default_mct_minutes,
        ctx.max_connection,
    )
    missed = [c for c in connections if c.missed]
    cm = ctx.cost
    delay_cost = plan.total_delay_minutes * cm.delay_per_minute
    care = sum(care_cost(cm, t.delay_minutes, overnight=False) * t.leg.booked_pax for t in delayed)
    eu = sum(_eu261(ctx, t.leg) * t.leg.booked_pax for t in delayed if t.delay_minutes >= 180)
    misconnect_cost = len(missed) * (cm.rebooking_handling + cm.meal_voucher)
    total = delay_cost + care + eu * cm.eur_to_aed + misconnect_cost
    return {
        "key": key,
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
        },
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
        "_missed": missed,
    }


def analyse_delay(
    ctx: Context, flight_id: str, delay_minutes: int, weights: dict[str, float], selected_key: str | None = None
) -> dict[str, Any]:
    """``selected_key``: the option a controller picked; passengers and costs then follow that option."""
    leg = ctx.store.leg(flight_id)
    if leg is None:
        raise ScenarioError(f"Flight {flight_id} is not in the operating window")
    horizon_end = leg.std + timedelta(days=ctx.settings.horizon_days)
    rest = [x for x in ctx.store.tail_legs(leg.tail, leg.std, horizon_end) if x.std > leg.std]
    delay = timedelta(minutes=delay_minutes)

    options = [
        _option_kpis(
            ctx, "absorb", f"Absorb the delay on {leg.tail}", absorb_delay(leg, rest, delay, ctx.min_turn), set()
        )
    ]
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
                    _option_kpis(ctx, f"swap:{tail}", f"Swap: {tail} takes over {rest[0].flight_number}", plan, set())
                )
        options += sorted(swaps, key=lambda o: o["cost_aed"])[:MAX_SWAP_OPTIONS]

    options.sort(key=lambda o: (o["cost_aed"], o["misconnects"]))
    best = options[0]
    chosen = next((o for o in options if o["key"] == selected_key), best)
    missed: list[Connection] = chosen["_missed"]
    for o in options:
        o.pop("_missed")

    # Passengers who still miss a connection under the chosen option: rank and re-accommodate.
    pax_plan = _reaccommodate_misconnects(ctx, missed, chosen, weights)
    runner_up = next((o for o in options if o["key"] != chosen["key"]), None)

    def brief(o: dict[str, Any]) -> dict[str, Any]:
        return {
            "what": o["label"],
            "flights_delayed": o["legs_delayed"],
            "extra_delay_minutes": o["total_delay_minutes"],
            "passengers_missing_connections": o["misconnects"],
            "estimated_cost_aed": round(o["cost_aed"]),
        }

    facts = {
        "late_flight": f"{leg.flight_number} from {leg.origin} to {leg.destination}",
        "delay_minutes": delay_minutes,
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
def analyse_cancellation(ctx: Context, flight_id: str, weights: dict[str, float]) -> dict[str, Any]:
    leg = ctx.store.leg(flight_id)
    if leg is None:
        raise ScenarioError(f"Flight {flight_id} is not in the operating window")
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
    alts = ctx.store.alternatives(
        leg.origin,
        leg.destination,
        after,
        leg.std + timedelta(hours=ctx.settings.rebooking_window_hours),
        [leg.flight_id],
    )
    result = rebooking.plan(ranked, alts, leg.sta, deadline)
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
    free_seats = sum(int(str(a["available_seats"])) for a in result.alternatives)
    seated = sum(1 for r in ranked)
    unprotected = result.unprotected_passengers
    cost = {
        "eu261_compensation": round(eu * seated * cm.eur_to_aed),
        "passenger_care": round(payload["rebooking"]["care_cost_aed"]),
        "rebooking_handling": round(seated * cm.rebooking_handling),
    }
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
        "passengers_to_move": seated,
        "free_seats_on_other_flights_within_24h": free_seats,
        "passengers_rebooked": result.protected_passengers,
        "passengers_without_seat": unprotected,
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
        "eu261_per_passenger_eur": eu,
        "onward_connections": len(onward),
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
                "frequency": p.get("travel_frequency_band"),
                "fare": p["fare"],
                "fare_family": p.get("fare_family_synthetic"),
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
        "Crew legality is not checked (no crew data); crew control must confirm any swap.",
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
