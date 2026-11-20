"""The optional demo scenario: delayed inbound, misconnecting passengers, next onward flight fully booked."""

from pathlib import Path

from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_delay
from app.engine.store import OpsStore
from app.ingest.demo import add_demo_scenario
from tests.ops_fixture import t, write_ops


def test_demo_scenario_protects_care_tier_when_next_flight_is_full(tmp_path: Path) -> None:
    ops = write_ops(tmp_path)
    added = add_demo_scenario(ops)
    assert added == {"demo_flights": 9, "demo_pax_segments": 50, "demo_customers": 25}

    # The scripted demo is tuned for a flat 40-min turn and 45-min default MCT; pin them so this test checks the
    # scenario mechanics, independent of the measured per-station defaults in Settings.
    settings = Settings(
        database_url="postgresql+psycopg://unused",
        now_utc=t(0),
        min_turn_minutes=40,
        min_turn_by_station={},
        default_mct_minutes=45,
    )
    ctx = Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))
    result = analyse_delay(ctx, "G9901_202611220500", 150, priority.DEFAULT_WEIGHTS)

    assert len(result["misconnections"]) == 24  # every seated connecting passenger misses G9951
    alternatives = {a["flight_number"]: a for a in result["rebooking"]["alternatives"]}
    assert alternatives["G9953"]["available_seats"] == 0  # next flight is full
    assert alternatives["G9955"]["available_seats"] == 8
    assert result["rebooking"]["protected"] <= 8
    rows = result["passengers"]
    care = [r for r in rows if r["tier"] == 1]
    assert {r["ssr"] for r in care} >= {"WCHR", "UMNR", "PREG"}
    assert all(r["assigned_flight"] == "G9955" for r in care)  # mandated care is protected first
    staff = next(r for r in rows if r["non_revenue"])
    assert staff["assigned_flight"] is None
    assert rows[-1]["non_revenue"] is True
