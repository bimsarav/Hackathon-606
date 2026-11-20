"""Seat-aware re-accommodation with Google OR-Tools CP-SAT.

Each PNR group (passengers of one booking on the disrupted segment) goes to at most one alternative flight, so
families and groups stay together. Seats on each alternative are limited to its available seats (capacity from
the inventory allocation incl. curtail/oversell, else the aircraft layout; minus booked). Lap infants need no
seat and travel with their adult. The objective protects higher tiers first (tier values dominate), then higher
scores, then earlier arrival. Groups larger than any alternative's free seats are split into individuals, and the
split is reported.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from ortools.sat.python import cp_model

from app.engine.priority import Ranked
from app.engine.store import Leg

TIER_BASE = {1: 100_000, 2: 5_000, 3: 200}
NON_REV_VALUE = 1
DELAY_PENALTY_PER_HOUR = 2


@dataclass
class Assignment:
    group_id: str
    pnr: str
    customer_keys: list[str]
    seats: int
    flight_id: str | None
    flight_number: str | None
    new_std: datetime | None
    arrival_delay_minutes: int | None
    onward_ok: bool | None = None
    split: bool = False
    reason: str = ""


@dataclass
class RebookingPlan:
    assignments: list[Assignment] = field(default_factory=list)
    alternatives: list[dict[str, object]] = field(default_factory=list)
    solver_status: str = ""

    @property
    def protected_passengers(self) -> int:
        return sum(a.seats for a in self.assignments if a.flight_id)

    @property
    def unprotected_passengers(self) -> int:
        return sum(a.seats for a in self.assignments if not a.flight_id)


def _value(r: Ranked) -> int:
    return NON_REV_VALUE if r.non_revenue else TIER_BASE[r.tier] + round(r.score)


def plan(
    ranked: list[Ranked],
    alternatives: list[Leg],
    original_sta: datetime,
    onward_deadline: dict[tuple[str, str], datetime],
    time_limit_s: float = 5.0,
) -> RebookingPlan:
    """``onward_deadline``: latest acceptable arrival per (pnr, customer_key) to keep an onward connection."""
    capacity = {a.flight_id: a.available_seats for a in alternatives}
    max_free = max(capacity.values(), default=0)

    # Build groups: one per PNR; split when larger than any free block.
    by_pnr: dict[str, list[Ranked]] = defaultdict(list)
    for r in ranked:
        by_pnr[r.passenger["pnr"]].append(r)
    groups: list[tuple[str, list[Ranked], bool]] = []
    for pnr, members in by_pnr.items():
        if len(members) > max_free > 0:
            groups += [(f"{pnr}:{i}", [m], True) for i, m in enumerate(members)]
        else:
            groups.append((pnr, members, False))

    model = cp_model.CpModel()
    x: dict[tuple[int, str], cp_model.IntVar] = {}
    objective = []
    for g, (_, members, _) in enumerate(groups):
        value = sum(_value(m) for m in members)
        for alt in alternatives:
            if len(members) > capacity[alt.flight_id]:
                continue
            var = model.new_bool_var(f"x_{g}_{alt.flight_id}")
            x[(g, alt.flight_id)] = var
            delay_h = max(int((alt.sta - original_sta).total_seconds() // 3600), 0)
            late_for_onward = sum(
                1
                for m in members
                if (dl := onward_deadline.get((m.passenger["pnr"], m.passenger["customer_key"]))) and alt.sta > dl
            )
            objective.append(
                var * (value - DELAY_PENALTY_PER_HOUR * delay_h * len(members) - TIER_BASE[2] * late_for_onward // 2)
            )
        model.add_at_most_one(v for (gi, _), v in x.items() if gi == g)
    for alt in alternatives:
        model.add(
            sum(len(groups[g][1]) * v for (g, fid), v in x.items() if fid == alt.flight_id) <= capacity[alt.flight_id]
        )
    model.maximize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 4
    status = solver.solve(model)

    legs = {a.flight_id: a for a in alternatives}
    result = RebookingPlan(solver_status=solver.status_name(status))
    for g, (gid, members, split) in enumerate(groups):
        chosen = (
            next((fid for (gi, fid), v in x.items() if gi == g and solver.value(v)), None)
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else None
        )
        keys = [m.passenger["customer_key"] for m in members]
        pnr = members[0].passenger["pnr"]
        if chosen:
            leg = legs[chosen]
            deadlines = [onward_deadline.get((pnr, k)) for k in keys]
            onward_ok = all(d is None or leg.sta <= d for d in deadlines) if any(deadlines) else None
            result.assignments.append(
                Assignment(
                    gid,
                    pnr,
                    keys,
                    len(members),
                    chosen,
                    leg.flight_number,
                    leg.std,
                    max(int((leg.sta - original_sta).total_seconds() // 60), 0),
                    onward_ok,
                    split,
                    "Seats available; group kept together" if not split else "Group split: no flight had enough seats",
                )
            )
        else:
            result.assignments.append(
                Assignment(
                    gid,
                    pnr,
                    keys,
                    len(members),
                    None,
                    None,
                    None,
                    None,
                    None,
                    split,
                    "No seat within the rebooking window: offer the next day with hotel and meals, or a refund",
                )
            )
    result.alternatives = [
        {
            "flight_id": a.flight_id,
            "flight_number": a.flight_number,
            "std": a.std,
            "sta": a.sta,
            "available_seats": a.available_seats,
            "capacity_source": a.capacity_source,
            "assigned": sum(asg.seats for asg in result.assignments if asg.flight_id == a.flight_id),
        }
        for a in alternatives
    ]
    return result
