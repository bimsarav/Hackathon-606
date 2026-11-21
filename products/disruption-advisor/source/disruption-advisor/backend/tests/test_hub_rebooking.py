"""Gap 3: rebooking through the SHJ hub on connections the airline sells (fares list), and booking class in the
fare value (UC5 "fare paid, fare family, booking class")."""

from datetime import timedelta
from typing import Any

import pytest

from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_cancellation
from app.engine.store import OpsStore
from tests.ops_fixture import F1, t, write_ops


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Context:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    return Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))


def test_sold_connections_and_mct_decide_which_hub_itineraries_exist(ctx: Context) -> None:
    store, hour = ctx.store, timedelta(hours=1)
    pairs = store.via_hub("KHI", "CAI", "SHJ", t(0), t(23), [F1], timedelta(minutes=55), 20 * hour)
    assert [(a.flight_number, b.flight_number) for a, b in pairs] == [("G9007", "G9004")]  # 14:00 -> 18:15
    assert all(b.std - a.sta >= timedelta(minutes=55) for a, b in pairs)
    # LHE-SHJ-CAI is sold, but its only same-day pair (17:30 -> 18:15) is shorter than the 50-minute minimum
    assert store.via_hub("LHE", "CAI", "SHJ", t(0), t(23), [], timedelta(minutes=50), 20 * hour) == []
    # KHI-SHJ-BKK is not sold as a connection in the fares list: never offered
    assert store.via_hub("KHI", "BKK", "SHJ", t(0), t(23, day=22), [], timedelta(minutes=10), 20 * hour) == []


def test_cancelled_inbound_reprotects_the_whole_journey_through_the_hub(ctx: Context) -> None:
    result = analyse_cancellation(ctx, F1, priority.DEFAULT_WEIGHTS)
    rows = {r["customer_key"]: r for r in result["passengers"]}
    # CONN01/02 fly KHI-SHJ-CAI; the only other KHI-SHJ flight (G9007, 14:00) is too late for their 11:30 onward
    # flight, so they move to G9007 plus a later SHJ-CAI flight that keeps the 55-minute connection
    for key in ("c0000001", "c0000002"):
        row = rows[key]
        assert row["assigned_flight"].startswith("G9007/"), row["assigned_flight"]
        assert row["onward_ok"] is True
        assert "through SHJ" in row["assignment_reason"]
    via = [a for a in result["rebooking"]["alternatives"] if a["via"] == "SHJ"]
    assert via
    assert all(a["for_destination"] == "CAI" for a in via)
    assert result["rebooking"]["unprotected"] == 0


def test_seats_on_a_flight_shared_by_itineraries_are_not_double_booked(ctx: Context) -> None:
    result = analyse_cancellation(ctx, F1, priority.DEFAULT_WEIGHTS)
    used: dict[str, int] = {}
    for row in result["passengers"]:
        for flight_id in (row["assigned_flight_id"] or "").split("+"):
            if flight_id:
                used[flight_id] = used.get(flight_id, 0) + 1
    free = {f.flight_id: f.available_seats for f in (ctx.store.leg(fid) for fid in used) if f}
    assert all(used[fid] <= free[fid] for fid in used)


def _p(**kw: Any) -> dict[str, Any]:
    return {"fare_family_synthetic": "Value", **kw}


def test_booking_class_enters_the_fare_value_with_a_fare_family_fallback() -> None:
    low, high = (
        priority.fare_value(_p(booking_class_level=0.1), 0.5),
        priority.fare_value(_p(booking_class_level=0.9), 0.5),
    )
    assert high - low == pytest.approx(0.3 * 0.8)
    unknown = priority.fare_value(_p(booking_class_level=None), 0.5)  # e.g. a staff or promo code
    assert unknown == pytest.approx(0.5 * 0.5 + 0.3 * 0.5 + 0.2 * 0.5)  # falls back to the Value family (0.5)
