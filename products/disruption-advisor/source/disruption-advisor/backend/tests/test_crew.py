"""Crew FDP check: the roster is ingested without names, each flight gets its tightest crew
member's headroom (max FDP - planned FDP), and every recovery option is checked against it."""

from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import _crew_brief
from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_delay
from app.engine.store import OpsStore
from app.ingest import build, convert
from tests.ops_fixture import F1, F2, t, write_crew, write_ops


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Context:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    write_crew(ops)
    s = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    return Context(OpsStore(ops), s, Explainer("", s.ai_model, "low", 1))


def options(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {o["key"]: o for o in result["options"]}


def test_headroom_from_the_roster_else_from_the_flight_numbers_history(ctx: Context) -> None:
    legs = {leg.flight_number: leg for leg in ctx.store.tail_legs("T1", t(0), t(23))}
    roster = ctx.store.crew_headroom(legs["G9002"])
    assert roster is not None
    assert (roster.minutes, roster.crew_type, roster.source) == (100, "CP", "roster")
    estimate = ctx.store.crew_headroom(legs["G9003"])
    assert estimate is not None
    assert (estimate.minutes, estimate.source, estimate.flights) == (170, "estimated", 40)
    assert ctx.store.crew_headroom(legs["G9004"]) is None


def test_a_long_delay_is_alerted_as_an_fdp_breach(ctx: Context) -> None:
    # F1 150 min late: G9002 leaves 156 min late (100 min headroom: 56 over), G9003 147 late (170 estimated: 23 left)
    absorb = options(analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS))["absorb"]
    crew = absorb["crew"]
    assert crew["status"] == "over"
    assert (crew["flights_over"], crew["flights_tight"], crew["flights_unknown"]) == (1, 1, 2)
    assert crew["worst"]["flight_number"] == "G9002"
    assert crew["worst"]["minutes_left"] == -56
    tight = next(f for f in crew["flights"] if f["status"] == "tight")
    assert (tight["flight_number"], tight["minutes_left"], tight["source"]) == ("G9003", 23, "estimated")
    over = next(f for f in crew["flights"] if f["status"] == "over")
    assert (over["origin"], over["destination"], over["new_std"]) == ("SHJ", "LHE", t(13, 21))
    assert absorb["cost_breakdown"]["reserve_crew"] == 0  # alert only: a breach adds no cost by default


def test_a_breach_can_be_costed_when_configured(ctx: Context) -> None:
    costed = Context(ctx.store, ctx.settings.model_copy(update={"cost_reserve_crew": 15000.0}), ctx.explainer)
    absorb = options(analyse_delay(costed, F1, 150, priority.DEFAULT_WEIGHTS))["absorb"]
    assert absorb["cost_breakdown"]["reserve_crew"] == 15000


def test_cancelling_the_round_trip_avoids_the_crew_problem(ctx: Context) -> None:
    cancel = options(analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS))[f"cancel:{F2}"]
    assert cancel["crew"]["status"] == "unknown"  # G9002/G9003 are cancelled; the others have no crew data
    assert cancel["cost_breakdown"]["reserve_crew"] == 0


def test_a_short_delay_stays_within_the_limits(ctx: Context) -> None:
    crew = options(analyse_delay(ctx, F1, 60, priority.DEFAULT_WEIGHTS))["absorb"]["crew"]
    assert crew["status"] == "ok"
    assert crew["flights_over"] == 0
    assert crew["flights"] == []
    assert crew["worst"]["flight_number"] == "G9002"
    assert crew["worst"]["minutes_left"] == 34


def test_the_agent_sees_counts_and_margins_only(ctx: Context) -> None:
    absorb = options(analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS))["absorb"]
    brief = _crew_brief(absorb["crew"])
    assert brief == {
        "status": "over",
        "flights_over_max_fdp": 1,
        "flights_tight": 1,
        "flights_without_crew_data": 2,
        "least_minutes_left": -56,
        "least_margin_flight": "G9002",
        "basis": "roster",
    }


def test_ingest_drops_names_and_builds_headroom_per_flight(tmp_path: Path) -> None:
    src = tmp_path / "input" / "parquet" / "crew"
    src.mkdir(parents=True)

    def row(crew_id: int, crew_type: str, planned: float, max_fdp: float, fn: str = "G9002") -> dict[str, Any]:
        return {
            "flight_number": fn,
            "flight_reference": "G9_1",
            "crew_reference": crew_id,
            "crew_type": crew_type,
            "crew_id": crew_id,
            "first_name": "Secret",
            "last_name": "Person",
            "sign_in_utc": datetime(2026, 11, 20, 9, 45),
            "sign_out_utc": None,
            "planned_fdp_value": planned,
            "actual_fdp_value": planned + 10,
            "planned_max_fdp_value": max_fdp,
            "actual_max_fdp_value": 0.0,
            "is_pic": crew_type == "CP",
            "tail": "T1",
            "std_utc": datetime(2026, 11, 20, 10, 45),
            "sta_utc": datetime(2026, 11, 20, 13, 45),
            "origin": "SHJ",
            "destination": "LHE",
            "pax": 150,
            "status_code": "SCH",
            "model": "A320",
            "carrier_code": "G9",
        }

    pq.write_table(
        pa.Table.from_pylist([row(1, "CP", 560, 660), row(2, "FO", 560, 690), row(3, "CC", 560, 780)]),
        src / "crew.parquet",
    )
    raw = tmp_path / "raw"
    raw.mkdir()
    assert convert.convert_crew(tmp_path / "input", raw) == {"crew_rows": 3}
    copied = pq.read_schema(raw / "crew.parquet").names
    assert "first_name" not in copied
    assert "last_name" not in copied

    ops = tmp_path / "ops"
    ops.mkdir()
    c = duckdb.connect()
    c.execute("CREATE VIEW flights AS SELECT 'G9002_202611201045' AS flight_id")
    c.execute("CREATE VIEW history_flights AS SELECT 'none' AS flight_id")

    def out(name: str, sql: str) -> int:
        c.execute(f"COPY ({sql}) TO '{ops / name}.parquet' (FORMAT parquet)")
        c.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM '{ops / name}.parquet'")
        return int(c.execute(f"SELECT count(*) FROM {name}").fetchone()[0])  # type: ignore[index]

    counts = build._crew(c, raw / "crew.parquet", ops, "('G9')", out)
    assert counts["crew_flights"] == 1
    flight = pq.read_table(ops / "crew_flights.parquet").to_pylist()[0]
    assert (flight["flight_id"], flight["headroom_minutes"], flight["tightest"]) == ("G9002_202611201045", 100, "CP")
    assert "crew_id" not in pq.read_schema(ops / "crew_flights.parquet").names
    analysis = (ops / "crew_fdp.json").read_text()
    assert "Secret" not in analysis
    assert '"in_window": 1' in analysis


def test_crew_api_reports_no_roster(client: TestClient, auth: dict[str, str]) -> None:
    assert client.get("/api/v1/crew/fdp").status_code == 401
    assert client.get("/api/v1/crew/fdp", headers=auth).status_code == 404  # the shared fixture has no roster
