"""Hold the connecting flight vs let passengers misconnect, passenger value in the cost, and the cascade beyond the
next flight."""

from pathlib import Path
from typing import Any

import pytest

from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.passengers import Connection
from app.engine.scenarios import Context, _misconnect_goodwill, analyse_delay
from app.engine.store import OpsStore
from tests.ops_fixture import F1, t, write_ops

H1 = "G9301_202611211130"  # SHJ-CAI 11:30, the onward flight of CONN01/02 (MCT KHI/SHJ/CAI 55 min)


@pytest.fixture(scope="module")
def ops(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_ops(tmp_path_factory.mktemp("data"))


def ctx_with(ops: Path, **settings: Any) -> Context:
    s = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0), **settings)
    return Context(OpsStore(ops), s, Explainer("", s.ai_model, "low", 1))


def options(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {o["key"]: o for o in result["options"]}


def test_hold_is_offered_when_misconnecting_costs_more(ops: Path) -> None:
    # F1 60 min late lands 11:00; with the 55-minute MCT the passengers need H1 to leave at 11:55: a 25-minute hold
    ctx = ctx_with(ops, cost_misconnect_goodwill=10_000)
    held = options(analyse_delay(ctx, F1, 60, priority.DEFAULT_WEIGHTS))["hold:absorb"]
    assert held["kind"] == "hold"
    assert held["holds"] == [{"flight_id": H1, "flight_number": "G9301", "minutes": 25, "connections_kept": 2}]
    assert "hold G9301 25 min (2 connections kept)" in held["label"]
    assert held["misconnects"] == 0
    assert held["cascade"]["aircraft"] == 2  # the delayed aircraft and the held flight's aircraft
    assert any(leg["flight_id"] == H1 and leg["delay_minutes"] == 25 for leg in held["legs"])


def test_no_hold_when_letting_them_misconnect_is_cheaper(ops: Path) -> None:
    # default goodwill: 25 minutes x AED 400 on a full A320 costs more than rebooking two occasional travellers
    keys = options(analyse_delay(ctx_with(ops), F1, 60, priority.DEFAULT_WEIGHTS))
    assert not any(k.startswith("hold:") for k in keys)


def test_holds_never_exceed_the_limit(ops: Path) -> None:
    # 150 min late: the passengers would need a 115-minute hold, above the 60-minute limit
    ctx = ctx_with(ops, cost_misconnect_goodwill=10_000)
    keys = options(analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS))
    assert not any(k.startswith("hold:") for k in keys)


def test_goodwill_grows_with_loyalty_and_frequency(ops: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = ctx_with(ops)
    missed = options(analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS))["absorb"]
    assert missed["cost_breakdown"]["misconnect_goodwill"] == 2 * 150  # two occasional non-members
    result = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)
    conns = list(result["misconnections"])
    assert len(conns) == 2

    def platinum(_: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "pnr": c["pnr"],
                "customer_key": c["customer_key"],
                "loyalty_tier_synthetic": "Platinum",
                "travel_frequency_band": "frequent",
            }
            for c in conns
        ]

    monkeypatch.setattr(ctx.store, "passengers_on", platinum)
    as_objects = [Connection(**c) for c in conns]
    assert _misconnect_goodwill(ctx, as_objects) == 2 * 150 * (1 + 2 * 1.0 + 1.0)  # 4x a casual traveller


def test_cascade_looks_past_the_next_flight(ops: Path) -> None:
    absorb = options(analyse_delay(ctx_with(ops), F1, 150, priority.DEFAULT_WEIGHTS))["absorb"]
    # F1 +150 runs on to F2, F3 and F4 on the same aircraft: 4 flights, 2 of them beyond the next flight
    assert absorb["cascade"]["flights_delayed"] == 4
    assert absorb["cascade"]["aircraft"] == 1
    assert absorb["cascade"]["beyond_next_flight"] == 2
    assert absorb["cascade"]["delay_ends"] is not None
