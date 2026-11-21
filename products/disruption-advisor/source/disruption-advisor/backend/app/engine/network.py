"""Aircraft-rotation delay propagation and same-type aircraft swaps (pure functions, no I/O).

Rules (assumptions are configurable and shown in the UI):
- A leg cannot depart before its scheduled time, nor before the aircraft is ready: previous new arrival + minimum
  turn time. Block time stays as scheduled.
- A swap exchanges the remaining rotations of two aircraft of the same seat count from a common station, so
  both rotations stay continuous (decision Q28: same type only; equipment change is a later phase).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.engine.store import Leg


@dataclass(frozen=True)
class TurnTimes:
    """Minimum ground time between two legs of one aircraft, per station (measured), with a default."""

    default: timedelta
    by_station: Mapping[str, timedelta] = field(default_factory=dict)

    def at(self, station: str) -> timedelta:
        return self.by_station.get(station, self.default)


Turn = timedelta | TurnTimes


def turn_at(min_turn: Turn, station: str) -> timedelta:
    """Minimum turn at ``station``; a plain timedelta applies everywhere."""
    return min_turn.at(station) if isinstance(min_turn, TurnTimes) else min_turn


@dataclass(frozen=True)
class LegTiming:
    leg: Leg
    operated_by: str  # tail that operates the leg in this option
    new_std: datetime
    new_sta: datetime

    @property
    def delay_minutes(self) -> int:
        return max(int((self.new_std - self.leg.std).total_seconds() // 60), 0)


@dataclass
class RotationPlan:
    """New timings for every leg touched by an option, keyed by flight_id."""

    timings: dict[str, LegTiming] = field(default_factory=dict)

    def delayed(self) -> list[LegTiming]:
        return sorted((t for t in self.timings.values() if t.delay_minutes > 0), key=lambda t: t.new_std)

    @property
    def total_delay_minutes(self) -> int:
        return sum(t.delay_minutes for t in self.timings.values())

    @property
    def delayed_passengers(self) -> int:
        return sum(t.leg.booked_pax for t in self.delayed())


def propagate(legs: list[Leg], ready_at: datetime, min_turn: Turn, operated_by: str) -> list[LegTiming]:
    """Fly ``legs`` in order with an aircraft that is ready to depart at ``ready_at``."""
    out: list[LegTiming] = []
    ready = ready_at
    for leg in legs:
        new_std = max(leg.std, ready)
        new_sta = new_std + (leg.sta - leg.std)
        out.append(LegTiming(leg, operated_by, new_std, new_sta))
        ready = new_sta + turn_at(min_turn, leg.destination)
    return out


def absorb_delay(disrupted: Leg, rest: list[Leg], delay: timedelta, min_turn: Turn) -> RotationPlan:
    """Option 1: the same aircraft operates its rotation; the delay carries forward until slack absorbs it."""
    plan = RotationPlan()
    for t in propagate([disrupted, *rest], disrupted.std + delay, min_turn, disrupted.tail):
        plan.timings[t.leg.flight_id] = t
    return plan


@dataclass(frozen=True)
class SwapCandidate:
    tail: str
    station: str
    takes_over_from: str  # first flight_id of the disrupted rotation the candidate operates
    gives_up_from: str | None  # first flight_id of the candidate's own rotation now flown by the delayed aircraft


def swap_rotations(
    disrupted: Leg,
    rest: list[Leg],
    delay: timedelta,
    min_turn: Turn,
    candidate_tail: str,
    candidate_legs: list[Leg],
) -> RotationPlan | None:
    """Option 2: exchange the remaining rotations of the delayed aircraft and ``candidate_tail`` at the
    arrival station of the delayed leg. ``candidate_legs`` is the candidate's full rotation in the horizon.

    Returns None when the swap is not feasible (no common station continuity or nothing to take over).
    """
    station = disrupted.destination
    if not rest or rest[0].origin != station:
        return None
    takeover_from = rest[0].std
    # The candidate must be on the ground at the station: its last arrival there before the takeover,
    # and its next departure from the station (which the delayed aircraft will fly instead).
    ordered = sorted(candidate_legs, key=lambda leg: leg.std)
    split = sum(1 for leg in ordered if leg.sta <= takeover_from)
    before, after = ordered[:split], ordered[split:]
    if before and before[-1].destination != station:
        return None  # the candidate is somewhere else at takeover time
    if after and after[0].origin != station:
        return None  # the candidate is airborne at takeover time
    if not before and not after:
        return None
    candidate_ready = (before[-1].sta + turn_at(min_turn, before[-1].destination)) if before else takeover_from
    delayed_ready = disrupted.std + delay + (disrupted.sta - disrupted.std) + turn_at(min_turn, disrupted.destination)

    plan = RotationPlan()
    # The disrupted leg itself still arrives late (the delay is on the inbound leg).
    first = LegTiming(disrupted, disrupted.tail, disrupted.std + delay, disrupted.sta + delay)
    plan.timings[disrupted.flight_id] = first
    for t in propagate(rest, candidate_ready, min_turn, candidate_tail):
        plan.timings[t.leg.flight_id] = t
    for t in propagate(after, delayed_ready, min_turn, disrupted.tail):
        plan.timings[t.leg.flight_id] = t
    return plan


def round_trip_pairs(rest: list[Leg], absorbed: RotationPlan, until: datetime) -> list[int]:
    """Indexes i where ``rest[i]`` X→Y and ``rest[i + 1]`` Y→X form a round trip that departs by ``until`` and is
    still delayed when the delay is absorbed (cancelling a pair the delay never reaches would gain nothing)."""
    out = []
    for i in range(len(rest) - 1):
        a, b = rest[i], rest[i + 1]
        if a.std > until:
            break
        delayed = absorbed.timings.get(a.flight_id)
        if b.origin == a.destination and b.destination == a.origin and delayed and delayed.delay_minutes > 0:
            out.append(i)
    return out


def cancel_round_trip(disrupted: Leg, rest: list[Leg], delay: timedelta, min_turn: Turn, i: int) -> RotationPlan:
    """Option 3 (phase 3, ADR 0011): cancel the round trip ``rest[i]``/``rest[i + 1]``. The aircraft skips it and
    is back at the station where the pair started, so the rest of its rotation stays continuous and the delay stops
    spreading without another aircraft. The cancelled legs are not in the plan; the caller lists them."""
    plan = RotationPlan()
    kept = [*rest[:i], *rest[i + 2 :]]
    for t in propagate([disrupted, *kept], disrupted.std + delay, min_turn, disrupted.tail):
        plan.timings[t.leg.flight_id] = t
    return plan


def hold_flight(plan: RotationPlan, held: Leg, minutes: int, rotation: list[Leg], min_turn: Turn) -> RotationPlan:
    """Hold ``held`` for ``minutes`` so late connecting passengers can make it. The hold runs down that aircraft's
    own rotation (``rotation``: its later flights), so the knock-on on another aircraft is part of the plan. Flights
    already in ``plan`` keep the later of the two times."""
    out = RotationPlan(dict(plan.timings))
    for t in propagate([held, *rotation], held.std + timedelta(minutes=minutes), min_turn, held.tail):
        current = out.timings.get(t.leg.flight_id)
        if current is None or t.new_std > current.new_std:
            out.timings[t.leg.flight_id] = t
    return out


def first_departure_from(legs: list[Leg], station: str, not_before: datetime) -> Leg | None:
    return next((leg for leg in legs if leg.origin == station and leg.std >= not_before), None)
