"""Passenger recovery priority: strict tiers first, then a configurable weighted score inside each tier.

Tier order (Q12, UC5: rights and mandatory assistance are respected independently of commercial scores):
  1 Mandated care: special assistance (WCHR/WCHS/WCHC, BLND, DEAF, MEDA, PREG) and PNRs travelling with an
    infant. (Unaccompanied minors are out of scope; future enhancement.)
  2 Urgency: an onward connection, or a multi-sector journey.
  3 Everyone else.
Non-revenue passengers come after all revenue passengers. The weighted score only orders passengers within the
same tier, so commercial value can never move someone across a tier.

Loyalty follows the airline's loyalty sample (user 2026-11-21): tiers Basic < Silver < Gold < Platinum carry the
recovery priority Lowest < Low < Medium < High; enrolment alone (Basic) already counts above a non-member; and a
family account travels on the head of family's tier, so a child or a non-member spouse on the family booking is not
ranked below the head (the better of the person's own tier and the family tier is used).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Unaccompanied minors (UMNR) are out of scope (user decision 2026-11-21; future enhancement).
CARE_SSRS = frozenset({"WCHR", "WCHS", "WCHC", "BLND", "DEAF", "MEDA", "PREG"})
LOYALTY_PRIORITY = {"Basic": "Lowest", "Silver": "Low", "Gold": "Medium", "Platinum": "High"}  # airline sample
PRIORITY_VALUE = {"Lowest": 0.25, "Low": 0.5, "Medium": 0.75, "High": 1.0}
TIER_VALUE: dict[str | None, float] = {None: 0.0}
TIER_VALUE.update({tier: PRIORITY_VALUE[prio] for tier, prio in LOYALTY_PRIORITY.items()})
FREQUENCY_VALUE = {"occasional": 0.2, "regular": 0.6, "frequent": 1.0, "unknown": 0.3}
FAMILY_VALUE = {"Basic": 0.2, "Value": 0.5, "Ultimate": 1.0, "Other": 0.4, "Staff/ID": 0.0, "Bus": 0.2}

ATTRIBUTES = ("loyalty", "frequency", "fare_value", "ancillaries", "journey", "booking")
DEFAULT_WEIGHTS: dict[str, float] = {
    "loyalty": 20,
    "frequency": 15,
    "fare_value": 20,
    "ancillaries": 10,
    "journey": 20,
    "booking": 15,
}
LABELS = {
    "loyalty": "Loyalty tier",
    "frequency": "Travel frequency",
    "fare_value": "Fare value",
    "ancillaries": "Ancillary purchases",
    "journey": "Journey complexity",
    "booking": "Family / group booking",
}


@dataclass
class Ranked:
    passenger: dict[str, Any]
    tier: int
    tier_reason: str
    score: float  # 0-100 within the tier
    contributions: dict[str, float] = field(default_factory=dict)  # points per attribute
    non_revenue: bool = False

    @property
    def sort_key(self) -> tuple[int, int, float]:
        return (1 if self.non_revenue else 0, self.tier, -self.score)


def _tier(p: dict[str, Any], has_onward: bool, segments: int) -> tuple[int, str]:
    if p.get("ssr_code") in CARE_SSRS:
        return 1, f"Mandated care: {p['ssr_code']}"
    if p.get("infants", 0) > 0:
        return 1, "Mandated care: travelling with an infant"
    if has_onward:
        return 2, "Urgent: onward connection"
    if segments > 1:
        return 2, "Urgent: multi-sector journey"
    return 3, "Standard"


def rank(
    passengers: list[dict[str, Any]],
    weights: dict[str, float],
    onward: set[tuple[str, str]],
    segments: dict[tuple[str, str], int],
) -> list[Ranked]:
    """Rank passengers (lap infants travel with their adult and are not ranked separately)."""
    weights = {a: max(float(weights.get(a, DEFAULT_WEIGHTS[a])), 0.0) for a in ATTRIBUTES}
    total_weight = sum(weights.values()) or 1.0
    fares = sorted(p["fare"] for p in passengers)

    def fare_pct(v: float) -> float:
        if len(fares) < 2:
            return 0.5
        below = sum(1 for f in fares if f < v)
        return below / (len(fares) - 1)

    out: list[Ranked] = []
    for p in passengers:
        own = p.get("loyalty_tier_synthetic")
        family = p.get("family_tier_synthetic") if p.get("family_account_synthetic") else None
        tier_name = max((x for x in (own, family) if x in LOYALTY_PRIORITY), key=TIER_VALUE.__getitem__, default=None)
        p = {
            **p,
            "loyalty_effective_tier": tier_name,
            "loyalty_effective_priority": LOYALTY_PRIORITY.get(tier_name or ""),
            "loyalty_via_family": bool(tier_name and tier_name != own),
        }
        if p["pax_type"] == "IN":
            continue
        key = (p["pnr"], p["customer_key"])
        has_onward, segs = key in onward, segments.get(key, 1)
        tier, reason = _tier(p, has_onward, segs)
        family = p.get("children", 0) + p.get("infants", 0) > 0
        values = {
            "loyalty": TIER_VALUE.get(tier_name, 0.0),
            "frequency": FREQUENCY_VALUE.get(str(p.get("travel_frequency_band") or "occasional"), 0.2),
            "fare_value": fare_value(p, fare_pct(p["fare"])),
            "ancillaries": min((p.get("ancillaries") or 0.0) / 150.0, 1.0),
            "journey": min(0.6 * has_onward + 0.2 * max(segs - 1, 0), 1.0),
            "booking": 1.0 if family else (0.5 if p.get("pnr_size", 1) >= 5 else 0.0),
        }
        contributions = {a: round(100 * weights[a] * values[a] / total_weight, 1) for a in ATTRIBUTES}
        out.append(
            Ranked(
                p,
                tier,
                reason,
                round(sum(contributions.values()), 1),
                contributions,
                non_revenue=p.get("revenue_type") == "NON_REV",
            )
        )
    out.sort(key=lambda r: r.sort_key)
    return out


def fare_value(p: dict[str, Any], paid_percentile: float) -> float:
    """Fare value 0-1 (UC5 "fare paid, fare family, booking class and booking value"): 50 % fare paid (percentile
    among the affected passengers), 30 % booking-class level from the fares list (share of passengers in cheaper
    classes; codes the fares list does not sell fall back to the fare family) and 20 % fare family."""
    family = FAMILY_VALUE.get(str(p.get("fare_family_synthetic")), 0.4)
    level = p.get("booking_class_level")
    booking_class = float(level) if level is not None else family
    return 0.5 * paid_percentile + 0.3 * booking_class + 0.2 * family


def explain(r: Ranked) -> str:
    top = sorted(((v, a) for a, v in r.contributions.items() if v > 0), reverse=True)[:3]
    parts = ", ".join(f"{LABELS[a]} +{v:g}" for v, a in top) or "no weighted factors"
    nonrev = " Non-revenue: placed after revenue passengers." if r.non_revenue else ""
    p = r.passenger
    loyalty = ""
    if p.get("loyalty_effective_tier"):
        via = " via the family account" if p.get("loyalty_via_family") else ""
        loyalty = f" Loyalty {p['loyalty_effective_tier']} (priority {p['loyalty_effective_priority']}){via}."
    return f"Tier {r.tier} ({r.tier_reason}). Score {r.score:g}/100: {parts}.{loyalty}{nonrev}"
