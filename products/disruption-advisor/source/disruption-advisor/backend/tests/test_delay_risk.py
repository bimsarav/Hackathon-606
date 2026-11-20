"""Phase 2 delay-risk model (ADR 0008): curve maths, learning a planted pattern, outputs and the risk API."""

import json
from pathlib import Path

import duckdb
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ml import delay_risk as dr
from tests.ops_fixture import F1, write_ops

CURVE = [0.8, 0.6, 0.4, 0.2, 0.05, 0.01]  # P(delay >= 5, 15, 30, 60, 120, 180)


def test_survival_interpolates_between_thresholds() -> None:
    assert dr.survival(CURVE, 0) == 0.8
    assert dr.survival(CURVE, 15) == pytest.approx(0.6)
    assert dr.survival(CURVE, 45) == pytest.approx(0.3)
    assert dr.survival(CURVE, 300) < 0.01


def test_auc_and_brier_match_textbook_values() -> None:
    y = np.array([0, 0, 1, 1])
    assert dr.auc(y, np.array([0.1, 0.4, 0.35, 0.8])) == pytest.approx(0.75)
    assert dr.auc(y, np.array([0.5, 0.5, 0.5, 0.5])) == pytest.approx(0.5)
    assert dr.brier(y, np.array([0.0, 0.0, 1.0, 1.0])) == 0.0


def test_planning_delay_is_exceeded_with_20_percent_chance() -> None:
    assert dr.planning_delay(CURVE) == 60
    assert dr.planning_delay([0.1, 0.05, 0.02, 0.01, 0.0, 0.0]) is None
    assert dr.planning_delay([1, 1, 1, 1, 1, 0.9]) == 180


def test_miss_probability_grows_as_slack_shrinks_and_onward_delay_helps() -> None:
    on_time = [0.0] * 6
    tight, loose = dr.miss_probability(CURVE, on_time, 10), dr.miss_probability(CURVE, on_time, 100)
    assert tight > loose > 0
    assert dr.miss_probability(CURVE, CURVE, 10) < tight  # a late onward flight saves some connections
    assert dr.miss_probability(on_time, on_time, -5) == 1.0  # below MCT and nobody late: missed by the rule


@pytest.fixture(scope="module")
def ops(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = write_ops(tmp_path_factory.mktemp("risk"))
    dr.run(path, default_mct=50)
    return path


def test_model_learns_the_planted_pattern_and_writes_outputs(ops: Path) -> None:
    con = duckdb.connect()
    p60 = dict(con.execute(f"SELECT flight_id, p_60 FROM '{ops}/flight_risk.parquet'").fetchall())
    assert p60[F1] > 0.4  # KHI-SHJ morning: late 60+ on 70% of history days
    assert p60["G9101_202611210600"] < 0.15  # DOH-SHJ: almost never late
    card = json.loads((ops / "model_card.json").read_text())
    assert card["evaluation"]["metrics_by_threshold"]["60"]["auc"] > 0.8
    assert card["evaluation"]["connection_backtest"]
    row = con.execute(f"SELECT reasons FROM '{ops}/flight_risk.parquet' WHERE flight_id = ?", [F1]).fetchone()
    assert row is not None
    reasons = json.loads(row[0])
    assert reasons
    assert all(r["contribution"] > 0 for r in reasons)
    conn = con.execute(
        f"""SELECT count(*), min(misconnect_risk), max(misconnect_risk), bool_and(NOT default_mct)
            FROM '{ops}/connection_risk.parquet' WHERE inbound_flight_id = ?""",
        [F1],
    ).fetchone()
    assert conn is not None
    assert conn[0] > 0
    assert 0 <= conn[1] <= conn[2] <= 1
    assert conn[3]  # KHI/SHJ/CAI has an MCT rule in the fixture


def test_training_is_deterministic(ops: Path, tmp_path: Path) -> None:
    again = write_ops(tmp_path)
    dr.run(again, default_mct=50)
    first = duckdb.connect().execute(f"SELECT * FROM '{ops}/flight_risk.parquet' ORDER BY flight_id").fetchall()
    second = duckdb.connect().execute(f"SELECT * FROM '{again}/flight_risk.parquet' ORDER BY flight_id").fetchall()
    assert first == second


def test_watchlist_and_flight_risk_api(client: TestClient, auth: dict[str, str]) -> None:
    body = client.get("/api/v1/risk/watchlist?band=all&sort=delay", headers=auth).json()
    assert body["flights"]
    p60 = [f["p_60"] for f in body["flights"]]
    assert p60 == sorted(p60, reverse=True)
    assert F1 in {f["flight_id"] for f in body["flights"]}
    assert body["totals"]["flights"] == len(body["flights"])
    detail = client.get(f"/api/v1/risk/flights/{F1}", headers=auth).json()
    assert detail["flight"]["reasons"]
    assert detail["connections"]
    assert "pnr" in detail["connections"][0]
    assert "name" not in detail["connections"][0]
    assert client.get("/api/v1/risk/model", headers=auth).json()["thresholds_minutes"] == list(dr.THRESHOLDS)
    assert client.get("/api/v1/risk/flights/G9999_202611210000", headers=auth).status_code == 404
    assert client.get("/api/v1/risk/flights/bad id", headers=auth).status_code == 422
    assert client.get("/api/v1/risk/watchlist").status_code == 401
