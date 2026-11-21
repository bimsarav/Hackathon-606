"""The optional demo scenario: delayed inbound, misconnecting passengers, next onward flight fully booked."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

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
    assert added == {"demo_flights": 9, "demo_pax_segments": 48, "demo_customers": 24, "demo_mct": 1}

    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    ctx = Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))
    result = analyse_delay(ctx, "G9901_202611220500", 150, priority.DEFAULT_WEIGHTS)

    assert len(result["misconnections"]) == 23  # every seated connecting passenger misses G9951
    alternatives = {a["flight_number"]: a for a in result["rebooking"]["alternatives"]}
    assert alternatives["G9953"]["available_seats"] == 0  # next flight is full
    assert alternatives["G9955"]["available_seats"] == 8
    assert result["rebooking"]["protected"] <= 8
    rows = result["passengers"]
    care = [r for r in rows if r["tier"] == 1]
    assert {r["ssr"] for r in care} >= {"WCHR", "PREG"}
    assert "UMNR" not in {r["ssr"] for r in rows}  # unaccompanied minors are out of scope
    assert all(r["assigned_flight"] == "G9955" for r in care)  # mandated care is protected first
    rebooked = next(r for r in rows if r["assigned_flight"] == "G9955")
    care = rebooked["care"]
    assert care["wait_minutes"] >= 17 * 60  # lands 10:00Z, new flight 03:00Z next day
    assert care["hotel"] is True
    assert care["transport"] is True
    assert care["refund_option"] is True
    assert any("transit visa" in f for f in care["flags"])
    assert "hotel room" in rebooked["message"]
    assert result["rebooking"]["hotel_rooms"] == len(rows)
    staff = next(r for r in rows if r["non_revenue"])
    assert staff["assigned_flight"] is None
    assert rows[-1]["non_revenue"] is True


def test_demo_append_tolerates_required_columns(tmp_path: Path) -> None:
    """Regression (2026-11-20 outage): DuckDB writes columns without nulls as required (non-nullable)."""
    ops = write_ops(tmp_path)
    flights = pq.read_table(ops / "flights.parquet")
    strict = pa.schema([field.with_nullable(False) for field in flights.schema]).append(
        pa.field("dep_dly", pa.float64(), nullable=False)
    )
    flights = flights.append_column("dep_dly", pa.array([0.0] * flights.num_rows)).cast(strict)
    pq.write_table(flights, ops / "flights.parquet")
    assert add_demo_scenario(ops)["demo_flights"] == 9
    assert pq.read_table(ops / "flights.parquet").num_rows == flights.num_rows + 9
