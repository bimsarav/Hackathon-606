"""Recovery cost estimate (decision Q15: assumed, configurable figures in AED) and EU261 exposure.

EU261 (Regulation (EC) No 261/2004) applies to flights departing an EU/EEA or Swiss airport, whatever the
carrier. Compensation by great-circle distance: up to 1,500 km EUR 250; 1,500-3,500 km EUR 400; over 3,500 km
EUR 600 (intra-EU over 1,500 km: EUR 400). It is due for cancellations and for arrival delays of 3 h or more,
unless extraordinary circumstances apply. These are estimates for comparing options, not entitlement decisions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EU261_COUNTRIES = frozenset(
    [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
        "IS",
        "LI",
        "NO",
        "CH",
    ]
)


@dataclass(frozen=True)
class CostModel:
    delay_per_minute: float
    hotel_per_night: float
    meal_voucher: float
    rebooking_handling: float
    eur_to_aed: float


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def eu261_compensation_eur(origin_country: str | None, dest_country: str | None, distance_km: float | None) -> int:
    """Compensation per passenger if EU261 applies to the leg (departure from EU/EEA/CH), else 0."""
    if origin_country not in EU261_COUNTRIES or distance_km is None:
        return 0
    intra_eu = dest_country in EU261_COUNTRIES
    if distance_km <= 1500:
        return 250
    if intra_eu or distance_km <= 3500:
        return 400
    return 600


def care_cost(model: CostModel, delay_minutes: int, overnight: bool) -> float:
    """Meals from 2 h; hotel when the passenger must stay overnight (generic rule, configurable)."""
    cost = model.meal_voucher if delay_minutes >= 120 else 0.0
    if overnight:
        cost += model.hotel_per_night + model.meal_voucher
    return cost
