"""Strategies (phase 3, ADR 0011): fixed orderings over one list of recovery options.

Each strategy picks the option with the lowest key; ties are broken left to right, ending with the option key, so
the pick never depends on the order the options were produced in. "Lowest cost" is the phase 1-2 ranking, so old
scenarios keep their recommendation. Switching the strategy changes which option is recommended, never a number.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Option = dict[str, Any]


def _moved(o: Option) -> int:
    """Flights operated by another aircraft than planned (simpler for OCC when fewer)."""
    return sum(1 for leg in o["legs"] if leg["operated_by"] != leg["scheduled_tail"])


def _cancelled(o: Option) -> int:
    """Flights cancelled: at equal cost, keeping the schedule beats cancelling (revenue loss is not costed)."""
    return len(o.get("cancelled_flights", []))


def lowest_cost(o: Option) -> tuple[Any, ...]:
    return (o["cost_aed"], o["misconnects"], o["total_delay_minutes"], _cancelled(o), _moved(o), o["key"])


def protect_passengers(o: Option) -> tuple[Any, ...]:
    disrupted = o["misconnects"] + o.get("cancelled_passengers", 0)
    return (
        o.get("passengers_without_seat", 0),
        disrupted,
        o.get("passenger_delay_minutes", 0),
        o["cost_aed"],
        _cancelled(o),
        o["key"],
    )


def least_delay(o: Option) -> tuple[Any, ...]:
    return (o.get("passenger_delay_minutes", 0), o["cost_aed"], _cancelled(o), o["key"])


STRATEGIES: dict[str, tuple[str, Callable[[Option], tuple[Any, ...]]]] = {
    "lowest_cost": ("Lowest cost", lowest_cost),
    "protect_passengers": ("Protect passengers", protect_passengers),
    "least_delay": ("Least delay", least_delay),
}
DEFAULT = "lowest_cost"


def label(strategy: str) -> str:
    return STRATEGIES[strategy][0]


def picks(options: list[Option]) -> dict[str, str]:
    """Each strategy's best option key."""
    return {name: min(options, key=key)["key"] for name, (_, key) in STRATEGIES.items()}


def order(options: list[Option], strategy: str) -> list[Option]:
    return sorted(options, key=STRATEGIES[strategy][1])
