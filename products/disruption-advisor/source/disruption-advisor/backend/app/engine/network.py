"""Aircraft-rotation delay propagation and same-type aircraft swaps (pure functions, no I/O).

Rules (assumptions are configurable and shown in the UI):
- A leg cannot depart before its scheduled time, nor before the aircraft is ready: previous new arrival + minimum
  turn time. Block time stays as scheduled.
- A swap exchanges the remaining rotations of two aircraft of the same seat count from a common station, so
  both rotations stay continuous (decision Q28: same type only; equipment change is a later phase).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.engine.store import Leg


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


def propagate(legs: list[Leg], ready_at: datetime, min_turn: timedelta, operated_by: str) -> list[LegTiming]:
    """Fly ``legs`` in order with an aircraft that is ready to depart at ``ready_at``."""
    out: list[LegTiming] = []
    ready = ready_at
    for leg in legs:
        new_std = max(leg.std, ready)
        new_sta = new_std + (leg.sta - leg.std)
        out.append(LegTiming(leg, operated_by, new_std, new_sta))
        ready = new_sta + min_turn
    return out


def absorb_delay(disrupted: Leg, rest: list[Leg], delay: timedelta, min_turn: timedelta) -> RotationPlan:
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
    min_turn: timedelta,
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
    candidate_ready = (before[-1].sta + min_turn) if before else takeover_from
    delayed_ready = disrupted.std + delay + (disrupted.sta - disrupted.std) + min_turn

    plan = RotationPlan()
    # The disrupted leg itself still arrives late (the delay is on the inbound leg).
    first = LegTiming(disrupted, disrupted.tail, disrupted.std + delay, disrupted.sta + delay)
    plan.timings[disrupted.flight_id] = first
    for t in propagate(rest, candidate_ready, min_turn, candidate_tail):
        plan.timings[t.leg.flight_id] = t
    for t in propagate(after, delayed_ready, min_turn, disrupted.tail):
        plan.timings[t.leg.flight_id] = t
    return plan


def first_departure_from(legs: list[Leg], station: str, not_before: datetime) -> Leg | None:
    return next((leg for leg in legs if leg.origin == station and leg.std >= not_before), None)
