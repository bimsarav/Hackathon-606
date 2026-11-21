"""Live delay models: departure and arrival delay predicted from what is known on the day (T-621, ADR 0011).

The planning models (app/ml/delay_risk.py) use only information known 7 days ahead and reach AUC about 0.77 for a
60+ minute delay. Delay is driven mostly by what happens on the day, so these models add three inputs that the
punctuality data contains for every past flight:

  inbound_arr_delay   arrival delay of the aircraft's previous leg (actual, or the current ETA when still airborne)
  inbound_dep_delay   departure delay of the aircraft's previous leg
  dep_delay           this flight's own departure delay (actual, or a what-if) - arrival model only

Three model sets, each one LightGBM classifier per threshold (monotone curve, like the planning models):
  dep      departure delay, given the inbound aircraft's delay
  arr_in   arrival delay, given the inbound aircraft's delay
  arr_dep  arrival delay, given the flight's own departure delay (and the inbound delay when known)

Missing inputs stay missing (LightGBM handles them), so a partial what-if still works. With no live input the API
falls back to the planning curves.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import lightgbm as lgb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from app.ml import delay_risk as dr

KINDS = ("dep", "arr_in", "arr_dep")
LIVE_FEATURES = {
    "dep": ("inbound_arr_delay", "inbound_dep_delay"),
    "arr_in": ("inbound_arr_delay", "inbound_dep_delay"),
    "arr_dep": ("inbound_arr_delay", "inbound_dep_delay", "dep_delay"),
}
MAX_INBOUND_GAP = 720  # minutes between the previous leg's scheduled departure and this one's: older is "no inbound"
FOLDER = "live_models"
WINDOW_FILE = "window_features.parquet"
CARD_FILE = "live_model_card.json"


def inbound_features(con: duckdb.DuckDBPyConnection, ops: Path, frame: dr.Frame) -> dict[str, np.ndarray]:
    """Previous-leg delays of the same aircraft, aligned with the frame (NaN for the window and for first legs)."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE inbound AS
        WITH h AS (
            SELECT flight_id, tail, std,
                   date_diff('minute', sta, ata)::DOUBLE AS ad, date_diff('minute', std, atd)::DOUBLE AS dd
            FROM '{ops}/history_flights.parquet' WHERE operated AND NOT coalesce(diverted, FALSE))
        SELECT flight_id,
               CASE WHEN date_diff('minute', lag(std) OVER w, std) <= {MAX_INBOUND_GAP} THEN lag(ad) OVER w END AS ia,
               CASE WHEN date_diff('minute', lag(std) OVER w, std) <= {MAX_INBOUND_GAP} THEN lag(dd) OVER w END AS id
        FROM h WINDOW w AS (PARTITION BY tail ORDER BY std)""")
    data = con.execute("SELECT flight_id, ia, id FROM inbound").fetchnumpy()
    position = {f: i for i, f in enumerate(data["flight_id"])}
    ia, idd = dr._floats(data["ia"]), dr._floats(data["id"])
    out = {
        "inbound_arr_delay": np.full(len(frame.flight_id), np.nan),
        "inbound_dep_delay": np.full(len(frame.flight_id), np.nan),
    }
    for i, f in enumerate(frame.flight_id):
        j = position.get(str(f))
        if j is not None:
            out["inbound_arr_delay"][i], out["inbound_dep_delay"][i] = ia[j], idd[j]
    out["dep_delay"] = frame.delay
    return out


def matrix(kind: str, base: np.ndarray, live: dict[str, np.ndarray]) -> np.ndarray:
    return np.column_stack([base, *[live[name] for name in LIVE_FEATURES[kind]]])


def _label(kind: str, frame: dr.Frame) -> np.ndarray:
    return frame.delay if kind == "dep" else frame.arr_delay


def _expected_minutes(p_row: np.ndarray) -> float:
    return float(np.dot(dr._masses(p_row), np.asarray(dr.BAND_VALUES)))


class LiveModels:
    def __init__(self, boosters: dict[str, dict[int, lgb.Booster]], card: dict[str, Any] | None = None) -> None:
        self.boosters = boosters
        self.card = card or {}

    @classmethod
    def train(cls, frame: dr.Frame, live: dict[str, np.ndarray], train: np.ndarray, as_of: np.datetime64) -> LiveModels:
        weight = dr._recency_weights(frame, train, as_of)
        cat = list(range(len(dr.CATEGORICAL)))
        boosters: dict[str, dict[int, lgb.Booster]] = {}
        for kind in KINDS:
            x, label = matrix(kind, frame.x, live), _label(kind, frame)
            known = train & ~np.isnan(label)
            w = weight[known[train]]
            boosters[kind] = {}
            for t in dr.THRESHOLDS:
                data = lgb.Dataset(
                    x[known], (label[known] >= t).astype(int), weight=w, categorical_feature=cat, free_raw_data=False
                )
                boosters[kind][t] = lgb.train(dr.PARAMS, data, num_boost_round=dr.ROUNDS)
        return cls(boosters)

    def predict(self, kind: str, x: np.ndarray) -> np.ndarray:
        """Rows x thresholds, non-increasing along the thresholds."""
        p = np.column_stack([np.asarray(self.boosters[kind][t].predict(x)) for t in dr.THRESHOLDS])
        return np.minimum.accumulate(p, axis=1)

    def save(self, ops: Path) -> None:
        folder = ops / FOLDER
        folder.mkdir(exist_ok=True)
        for kind, per_t in self.boosters.items():
            for t, booster in per_t.items():
                booster.save_model(str(folder / f"{kind}_{t}.txt"))

    @classmethod
    def load(cls, ops: Path) -> LiveModels | None:
        folder, card = ops / FOLDER, ops / CARD_FILE
        files = {(k, t): folder / f"{k}_{t}.txt" for k in KINDS for t in dr.THRESHOLDS}
        if not (ops / WINDOW_FILE).exists() or not all(f.exists() for f in files.values()):
            return None
        boosters = {k: {t: lgb.Booster(model_file=str(files[(k, t)])) for t in dr.THRESHOLDS} for k in KINDS}
        return cls(boosters, json.loads(card.read_text()) if card.exists() else {})


def _skill(y: np.ndarray, p: np.ndarray) -> float:
    base = float(((y.mean() - y) ** 2).mean())
    return round(1 - float(((p - y) ** 2).mean()) / base, 3) if base > 0 else 0.0


def evaluate(
    frame: dr.Frame,
    live: dict[str, np.ndarray],
    models: LiveModels,
    test: np.ndarray,
    planning: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Held-out accuracy of every live model next to its planning model on the same flights."""
    out: dict[str, Any] = {}
    for kind in KINDS:
        label = _label(kind, frame)
        rows = test & ~np.isnan(label)
        sel = rows[test]  # positions inside the test subset
        p = models.predict(kind, matrix(kind, frame.x, live)[rows])
        plan = planning["dep" if kind == "dep" else "arr"][sel]
        actual = np.clip(label[rows], 0, None)
        entry: dict[str, Any] = {"flights": int(rows.sum())}
        for t in (15, 60):
            j = dr.THRESHOLDS.index(t)
            y = (label[rows] >= t).astype(int)
            entry[str(t)] = {
                "auc": round(float(dr.auc(y, p[:, j])), 4),
                "brier": round(float(((p[:, j] - y) ** 2).mean()), 4),
                "skill": _skill(y, p[:, j]),
                "planning_auc": round(float(dr.auc(y, plan[:, j])), 4),
                "planning_brier": round(float(((plan[:, j] - y) ** 2).mean()), 4),
                "planning_skill": _skill(y, plan[:, j]),
            }
        entry["mae_minutes"] = round(
            float(np.mean([abs(_expected_minutes(r) - a) for r, a in zip(p, actual, strict=True)])), 2
        )
        entry["planning_mae_minutes"] = round(
            float(np.mean([abs(_expected_minutes(r) - a) for r, a in zip(plan, actual, strict=True)])), 2
        )
        out[kind] = entry
    return out


def write_window_features(ops: Path, frame: dr.Frame) -> None:
    """The planning features of the flights to score, so the API can predict one flight with live inputs."""
    win = np.flatnonzero(frame.part == "window")
    table = pa.table(
        {"flight_id": [str(frame.flight_id[i]) for i in win]}
        | {name: [float(v) for v in frame.x[win, j]] for j, name in enumerate(dr.FEATURES)}
    )
    pq.write_table(table, ops / WINDOW_FILE)


def window_matrix(ops: Path) -> tuple[list[str], np.ndarray]:
    t = pq.read_table(ops / WINDOW_FILE).to_pydict()
    ids = [str(v) for v in t["flight_id"]]
    return ids, np.column_stack([np.asarray(t[name], dtype=float) for name in dr.FEATURES])


def summarise(p_row: np.ndarray) -> dict[str, Any]:
    """The curve in the shape the API returns."""
    return {
        "p": {str(t): round(float(v), 4) for t, v in zip(dr.THRESHOLDS, p_row, strict=True)},
        "expected_minutes": round(_expected_minutes(p_row)),
        "planning_delay_minutes": dr.planning_delay(p_row),
        "risk_band": dr._band(float(p_row[dr.THRESHOLDS.index(dr.REASON_THRESHOLD)])),
    }
