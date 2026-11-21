"""Phase 2: delay-risk prediction (ADR 0008). Runs as ingest stage 3, after the operating picture.

For every flight in the operating window it estimates P(departure delay >= t) for t in THRESHOLDS minutes, from
features that are known 7 days ahead (schedule, aircraft plan, bookings, recent station and route delay rates
ending 7 days before the flight). One LightGBM classifier per threshold, trained with recency weights (half-life
HALF_LIFE_DAYS, so the seasonal level follows recent months), made monotone across thresholds: a delay curve S(t).
LightGBM's own probabilities are used: an isotonic step fitted on a separate month made calibration worse because
delay levels shift from month to month (tested 2026-11-21, recorded in docs/testing/model-card.md).

Validation is time-ordered (never random):
  evaluation model   train < TEST_START, test TEST_START..history end (the last TEST_DAYS days)
  production model   same recipe on all history
The model card reports the evaluation model's test metrics next to a route x departure-hour baseline.

Outputs (ops folder):
  flight_risk.parquet       per flight: p_5 .. p_180, planning delay (exceeded with 20% chance), band, reasons,
                            connecting passengers and expected missed connections
  connection_risk.parquet   per connecting passenger: connection time, MCT, slack, misconnect risk
  model_card.json           data ranges, features, metrics, reliability, assumptions
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import duckdb
import lightgbm as lgb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger("ingest.delay_risk")

THRESHOLDS = (5, 15, 30, 60, 120, 180)
REASON_THRESHOLD = 60  # reasons explain the risk of a delay of an hour or more
TEST_DAYS = 28
HALF_LIFE_DAYS = 109  # tuned (T-511, docs/testing/model-selection.md)
LAST_WEEK_DAYS = 7
LAG_FROM, LAG_TO = 35, 7  # recent delay rates: days [flight - 35, flight - 7], so they are known 7 days ahead
MIN_CONNECTION, MAX_CONNECTION = 15, 20 * 60  # minutes (decision Q8)
HUB_OFFSET_HOURS = 4  # the aircraft day is counted in hub time (SHJ, UTC+4)
BANDS = ((0.30, "high"), (0.15, "medium"))  # on P(delay >= 60 min); base rate about 10%
PARAMS: dict[
    str, Any
] = {  # tuned with Optuna on time-ordered validation blocks (T-511, docs/testing/model-selection.md)
    "objective": "binary",
    "learning_rate": 0.0391,
    "num_leaves": 11,
    "min_data_in_leaf": 60,
    "feature_fraction": 0.99,
    "bagging_fraction": 0.856,
    "bagging_freq": 1,
    "lambda_l2": 17.25,
    "cat_smooth": 14.7,
    "min_data_per_group": 79,
    "seed": 7,
    "deterministic": True,
    "force_row_wise": True,
    "num_threads": 4,
    "verbose": -1,
}
ROUNDS = 120
CATEGORICAL = ("origin", "destination", "prev_origin", "aircraft_model")
NUMERIC = (
    "hour_local",
    "weekday",
    "leg_of_day",
    "turn_buffer",
    "load_factor",
    "station_rate",
    "route_rate",
    "network_rate",
)
FEATURES = CATEGORICAL + NUMERIC
WEEKDAYS = ("Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays")


@dataclass
class Frame:
    flight_id: np.ndarray
    part: np.ndarray  # "history" (labelled) or "window" (to score)
    std: np.ndarray  # datetime64
    delay: np.ndarray  # departure delay, minutes; NaN for the window
    arr_delay: np.ndarray  # arrival delay, minutes; NaN for the window (used for missed connections)
    x: np.ndarray  # float matrix in FEATURES order (categories as integer codes)
    raw: dict[str, np.ndarray]  # readable feature values for the reasons
    route_hour: np.ndarray  # baseline key


def _frame(con: duckdb.DuckDBPyConnection, ops: Path) -> Frame:
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE allf AS
        SELECT flight_id, tail, origin, destination, std, sta, aircraft_model, capacity, booked_pax,
               date_diff('minute', std, atd)::DOUBLE AS delay, date_diff('minute', sta, ata)::DOUBLE AS arr_delay,
               'history' AS part
        FROM '{ops}/history_flights.parquet' WHERE operated AND NOT coalesce(diverted, FALSE)
        UNION ALL
        SELECT flight_id, tail, origin, destination, std, sta, aircraft_model, capacity, booked_pax,
               NULL::DOUBLE, NULL::DOUBLE, 'window'
        FROM '{ops}/flights.parquet'""")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE feat AS
        WITH b AS (
            SELECT a.*, timezone(coalesce(t.tz, 'UTC'), timezone('UTC', a.std)) AS std_local,
                   CAST(a.std + INTERVAL {HUB_OFFSET_HOURS} HOUR AS DATE) AS hub_day, CAST(a.std AS DATE) AS d
            FROM allf a LEFT JOIN '{ops}/airports.parquet' t ON t.iata = a.origin),
        seq AS (
            SELECT *,
                   row_number() OVER (PARTITION BY tail, hub_day ORDER BY std) AS leg_of_day,
                   lag(sta) OVER (PARTITION BY tail ORDER BY std) AS prev_sta,
                   lag(origin) OVER (PARTITION BY tail ORDER BY std) AS prev_origin
            FROM b),
        daily AS (
            SELECT origin, destination, d, count(*) AS n, sum((delay >= 15)::INTEGER) AS k
            FROM b WHERE part = 'history' GROUP BY ALL),
        st AS (
            SELECT s.origin, s.d, sum(x.k) / sum(x.n) AS rate
            FROM (SELECT DISTINCT origin, d FROM b) s
            JOIN daily x ON x.origin = s.origin AND x.d BETWEEN s.d - {LAG_FROM} AND s.d - {LAG_TO}
            GROUP BY ALL),
        rt AS (
            SELECT s.origin, s.destination, s.d, sum(x.k) / sum(x.n) AS rate
            FROM (SELECT DISTINCT origin, destination, d FROM b) s
            JOIN daily x ON x.origin = s.origin AND x.destination = s.destination
                        AND x.d BETWEEN s.d - {LAG_FROM} AND s.d - {LAG_TO}
            GROUP BY ALL),
        nw AS (
            SELECT s.d, sum(x.k) / sum(x.n) AS rate
            FROM (SELECT DISTINCT d FROM b) s JOIN daily x ON x.d BETWEEN s.d - {LAG_FROM} AND s.d - {LAG_TO}
            GROUP BY ALL)
        SELECT q.flight_id, q.part, q.std, q.delay, q.arr_delay, q.origin, q.destination,
               coalesce(q.prev_origin, '(none)') AS prev_origin,
               coalesce(q.aircraft_model, '(unknown)') AS aircraft_model,
               hour(q.std_local) AS hour_local, isodow(q.std_local) AS weekday, q.leg_of_day,
               CASE WHEN date_diff('minute', q.prev_sta, q.std) BETWEEN 0 AND 720
                    THEN date_diff('minute', q.prev_sta, q.std) END AS turn_buffer,
               CASE WHEN q.capacity > 0 THEN least(q.booked_pax / q.capacity, 1.5) END AS load_factor,
               st.rate AS station_rate, rt.rate AS route_rate, nw.rate AS network_rate,
               q.origin || '-' || q.destination || '@' || hour(q.std_local) AS route_hour
        FROM seq q
        LEFT JOIN st ON st.origin = q.origin AND st.d = q.d
        LEFT JOIN rt ON rt.origin = q.origin AND rt.destination = q.destination AND rt.d = q.d
        LEFT JOIN nw ON nw.d = q.d
        ORDER BY q.std, q.flight_id""")
    codes = ", ".join(f"dense_rank() OVER (ORDER BY {c}) - 1 AS {c}_code" for c in CATEGORICAL)
    data = con.execute(f"SELECT *, {codes} FROM feat ORDER BY std, flight_id").fetchnumpy()
    columns = [np.asarray(data[f"{c}_code"], dtype=float) for c in CATEGORICAL] + [
        np.asarray(_floats(data[c]), dtype=float) for c in NUMERIC
    ]
    return Frame(
        flight_id=np.asarray(data["flight_id"]),
        part=np.asarray(data["part"]),
        std=np.asarray(data["std"], dtype="datetime64[m]"),
        delay=np.asarray(_floats(data["delay"]), dtype=float),
        arr_delay=np.asarray(_floats(data["arr_delay"]), dtype=float),
        x=np.column_stack(columns),
        raw={c: np.asarray(data[c]) for c in FEATURES},
        route_hour=np.asarray(data["route_hour"]),
    )


def _floats(column: Any) -> np.ndarray:
    """Masked or object arrays from DuckDB -> float array with NaN for missing values."""
    if isinstance(column, np.ma.MaskedArray):
        return np.asarray(np.ma.filled(column.astype(float), np.nan))
    return np.array([np.nan if v is None else float(v) for v in column], dtype=float)


def _recency_weights(frame: Frame, train: np.ndarray, as_of: np.datetime64) -> np.ndarray:
    """A flight's weight halves every HALF_LIFE_DAYS days of age before `as_of`."""
    age_days = ((as_of - frame.std[train]) / np.timedelta64(1, "D")).astype(float)
    return np.asarray(0.5 ** (np.clip(age_days, 0, None) / HALF_LIFE_DAYS), dtype=float)


class DelayCurve:
    """Calibrated P(delay >= t) for each threshold, monotone in t."""

    def __init__(self, frame: Frame, train: np.ndarray, as_of: np.datetime64, arrival: bool = False) -> None:
        self.boosters: dict[int, lgb.Booster] = {}
        cat = list(range(len(CATEGORICAL)))
        weight = _recency_weights(frame, train, as_of)
        label = frame.arr_delay if arrival else frame.delay
        known = train & ~np.isnan(label)
        weight = weight[known[train]]
        for t in THRESHOLDS:
            y = (label >= t).astype(int)
            data = lgb.Dataset(frame.x[known], y[known], weight=weight, categorical_feature=cat, free_raw_data=False)
            self.boosters[t] = lgb.train(PARAMS, data, num_boost_round=ROUNDS)

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Rows x thresholds, non-increasing along the thresholds."""
        p = np.column_stack([np.asarray(self.boosters[t].predict(x)) for t in THRESHOLDS])
        return np.minimum.accumulate(p, axis=1)

    def contributions(self, x: np.ndarray) -> np.ndarray:
        """TreeSHAP contributions (log-odds) of the reason model; last column is the bias."""
        return np.asarray(self.boosters[REASON_THRESHOLD].predict(x, pred_contrib=True))


def survival(p_row: np.ndarray | list[float], minutes: float) -> float:
    """P(delay >= minutes) from the curve: linear between thresholds, flat below the first, 0 far beyond the last."""
    p = [float(v) for v in p_row]
    if minutes <= THRESHOLDS[0]:
        return p[0]
    for (t0, p0), (t1, p1) in pairwise(zip(THRESHOLDS, p, strict=True)):
        if minutes <= t1:
            return float(p0 + (p1 - p0) * (minutes - t0) / (t1 - t0))
    # beyond the last threshold: halve the tail every further 120 minutes
    return float(p[-1] * 0.5 ** ((minutes - THRESHOLDS[-1]) / 120))


# representative delay (minutes) of each band of the curve: below 5, 5-15, 15-30, 30-60, 60-120, 120-180, 180+
BAND_VALUES = (0.0, 10.0, 22.0, 45.0, 90.0, 150.0, 210.0)


def _masses(curve: list[float] | np.ndarray) -> np.ndarray:
    s = np.concatenate([[1.0], np.asarray(curve, dtype=float), [0.0]])
    return np.asarray(np.clip(s[:-1] - s[1:], 0, None), dtype=float)


def miss_probability(
    arrival_curve: list[float] | np.ndarray, onward_curve: list[float] | np.ndarray, slack: float
) -> float:
    """P(inbound arrival delay - onward departure delay > slack), the two delays taken as independent."""
    a, d = _masses(arrival_curve), _masses(onward_curve)
    values = np.asarray(BAND_VALUES)
    late = (values[:, None] - values[None, :]) > slack
    return float(min(max((a[:, None] * d[None, :] * late).sum(), 0.0), 1.0))


def planning_delay(p_row: np.ndarray | list[float], exceed: float = 0.2) -> int | None:
    """Delay (minutes) exceeded with the given probability; None when even 5 minutes is less likely than that."""
    p = [float(v) for v in p_row]
    if p[0] < exceed:
        return None
    for (t0, p0), (t1, p1) in pairwise(zip(THRESHOLDS, p, strict=True)):
        if p1 < exceed <= p0:
            return round(t0 + (p0 - exceed) / (p0 - p1) * (t1 - t0)) if p0 > p1 else t0
    return THRESHOLDS[-1]


def _band(p60: float) -> str:
    return next((name for floor, name in BANDS if p60 >= floor), "low")


def _phrase(feature: str, value: Any, origin: str) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    match feature:
        case "origin":
            return f"departures from {value} are often late"
        case "destination":
            return f"flights to {value} are often late"
        case "prev_origin":
            return None if value == "(none)" else f"the aircraft comes in from {value} just before"
        case "aircraft_model":
            return f"aircraft type {value}"
        case "hour_local":
            return f"{int(value):02d}:00 local departure time"
        case "weekday":
            return f"{WEEKDAYS[int(value) - 1]} run late more often"
        case "leg_of_day":
            return f"flight {int(value)} of the aircraft's day: earlier delays carry over" if value > 1 else None
        case "turn_buffer":
            return f"only {int(value)} minutes between the previous arrival and this departure"
        case "load_factor":
            return f"{round(float(value) * 100)}% of seats booked"
        case "station_rate":
            return f"{origin} departures were late {round(float(value) * 100)}% of the time recently"
        case "route_rate":
            return f"this route was late {round(float(value) * 100)}% of the time recently"
        case "network_rate":
            return f"the whole network was late {round(float(value) * 100)}% of the time recently"
    return None


def reasons(frame: Frame, row: int, contrib: np.ndarray, top: int = 3) -> list[dict[str, Any]]:
    """Top features that raise the risk of a 60+ minute delay, in plain words, with their SHAP contribution."""
    order = np.argsort(-contrib[: len(FEATURES)])
    out: list[dict[str, Any]] = []
    for i in order:
        if contrib[i] <= 0.02 or len(out) == top:
            break
        name = FEATURES[i]
        value = frame.raw[name][row]
        text = _phrase(name, value.item() if hasattr(value, "item") else value, str(frame.raw["origin"][row]))
        if text:
            out.append({"feature": name, "text": text, "contribution": round(float(contrib[i]), 3)})
    return out


def brier(y: np.ndarray, p: np.ndarray) -> float:
    """Mean squared error of the probabilities (lower is better)."""
    return float(np.mean((np.asarray(p, dtype=float) - y) ** 2))


def auc(y: np.ndarray, p: np.ndarray) -> float:
    """Area under the ROC curve via the rank-sum (Mann-Whitney) statistic, ties averaged."""
    p = np.asarray(p, dtype=float)
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sorted_p = p[order]
    i = 0
    while i < len(p):
        j = i
        while j + 1 < len(p) and sorted_p[j + 1] == sorted_p[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    pos = y == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _metrics(y: np.ndarray, p: np.ndarray, base: np.ndarray | None = None) -> dict[str, Any]:
    two_classes = 0 < y.sum() < len(y)
    out: dict[str, Any] = {
        "observed_rate": round(float(y.mean()), 4),
        "auc": round(float(auc(y, p)), 4) if two_classes else None,
        "brier": round(float(brier(y, p)), 4),
        "climatology_brier": round(float(brier(y, np.full(len(y), y.mean()))), 4),
    }
    if base is not None:
        out["baseline_auc"] = round(float(auc(y, base)), 4) if two_classes else None
        out["baseline_brier"] = round(float(brier(y, base)), 4)
    return out


def _reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, Any]]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for lo, hi in pairwise(edges):
        m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if m.sum():
            out.append(
                {
                    "from": round(float(lo), 1),
                    "to": round(float(hi), 1),
                    "flights": int(m.sum()),
                    "predicted": round(float(p[m].mean()), 3),
                    "observed": round(float(y[m].mean()), 3),
                }
            )
    return out


# Cut-offs the app uses (risk bands) plus a plain 50% rule, for the confusion matrices.
OPERATING_POINTS: tuple[tuple[str, int, float, str], ...] = (
    ("departure", 15, 0.50, "Departure 15+ min late, flagged when the chance is 50% or more"),
    ("departure", 60, BANDS[0][0], "Departure 60+ min late, flagged as High (30% or more)"),
    ("departure", 60, BANDS[1][0], "Departure 60+ min late, flagged as Medium or High (15% or more)"),
    ("arrival", 15, 0.50, "Arrival 15+ min late, flagged when the chance is 50% or more"),
    ("arrival", 60, BANDS[0][0], "Arrival 60+ min late, flagged when the chance is 30% or more"),
)
SWEEP_CUTOFFS = tuple(round(c, 2) for c in np.arange(0.05, 0.951, 0.05))
ROLLING_THRESHOLDS = (15, 60)
ROLLING_MONTHS = 5


def confusion(y: np.ndarray, p: np.ndarray, cutoff: float) -> dict[str, Any]:
    """Confusion matrix and the usual rates for 'flag when p >= cutoff'."""
    actual, flagged = np.asarray(y, dtype=bool), np.asarray(p) >= cutoff
    tp, fp = int((actual & flagged).sum()), int((~actual & flagged).sum())
    fn, tn = int((actual & ~flagged).sum()), int((~actual & ~flagged).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    return {
        "cutoff": cutoff,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": None if precision is None else round(precision, 4),
        "recall": None if recall is None else round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round((tp + tn) / len(actual), 4) if len(actual) else None,
        "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
        "flagged_share": round(float(flagged.mean()), 4) if len(actual) else None,
    }


def _sweep(y: np.ndarray, p: np.ndarray) -> list[dict[str, Any]]:
    """Precision, recall and F1 for every cut-off from 5% to 95%."""
    out = []
    for c in SWEEP_CUTOFFS:
        m = confusion(y, p, c)
        out.append({k: m[k] for k in ("cutoff", "precision", "recall", "f1", "flagged_share")})
    return out


def _top_share(y: np.ndarray, p: np.ndarray, share: float = 0.10) -> dict[str, Any]:
    """How often the riskiest `share` of flights were really late, against the overall rate (lift)."""
    k = max(int(len(y) * share), 1)
    top = np.argsort(-np.asarray(p), kind="mergesort")[:k]
    hit, base = float(np.mean(y[top])), float(np.mean(y))
    return {"share": share, "flights": k, "late_rate": round(hit, 4), "overall_rate": round(base, 4),
            "lift": round(hit / base, 2) if base else None}  # fmt: skip


def _classification(y: np.ndarray, p: np.ndarray, cutoffs: list[tuple[float, str]]) -> dict[str, Any]:
    return {
        "operating_points": [{"label": label, **confusion(y, p, c)} for c, label in cutoffs],
        "sweep": _sweep(y, p),
        "top_10_percent": _top_share(y, p),
    }


def _rolling(frame: Frame, hist: np.ndarray) -> list[dict[str, Any]]:
    """Monthly walk-forward check: for each of the last ROLLING_MONTHS months, train on everything before the
    month (same recipe) and test on that month. Less tied to the single 28-day test period used for tuning."""
    months = np.unique(frame.std[hist].astype("datetime64[M]"))[-ROLLING_MONTHS:]
    cat = list(range(len(CATEGORICAL)))
    folds = []
    for month in months:
        start = month.astype("datetime64[m]")
        stop = (month + np.timedelta64(1, "M")).astype("datetime64[m]")
        train, test = hist & (frame.std < start), hist & (frame.std >= start) & (frame.std < stop)
        if not train.any() or not test.any():
            continue
        weight = _recency_weights(frame, train, start)
        fold: dict[str, Any] = {"month": str(month), "train_flights": int(train.sum()), "test_flights": int(test.sum())}
        for t in ROLLING_THRESHOLDS:
            y = (frame.delay >= t).astype(int)
            booster = lgb.train(
                PARAMS, lgb.Dataset(frame.x[train], y[train], weight=weight, categorical_feature=cat), ROUNDS
            )
            p = np.asarray(booster.predict(frame.x[test]))
            fold[str(t)] = _metrics(y[test], p, _baseline(frame, train, test, t))
        folds.append(fold)
    return folds


def _baseline(frame: Frame, train: np.ndarray, rows: np.ndarray, threshold: int) -> np.ndarray:
    """Route x departure-hour historical rate in the training data (smoothed toward the overall rate)."""
    y = (frame.delay[train] >= threshold).astype(float)
    overall = float(y.mean())
    stats: dict[str, list[float]] = {}
    for key, v in zip(frame.route_hour[train], y, strict=True):
        s = stats.setdefault(str(key), [0.0, 0.0])
        s[0] += v
        s[1] += 1
    prior = 20.0
    return np.array(
        [
            (stats.get(str(k), [0.0, 0.0])[0] + prior * overall) / (stats.get(str(k), [0.0, 0.0])[1] + prior)
            for k in frame.route_hour[rows]
        ]
    )


def _connections(con: duckdb.DuckDBPyConnection, ops: Path, risk: pa.Table, default_mct: int) -> pa.Table:
    """Connecting passengers of every window flight with the misconnect risk S(connection time - MCT)."""
    con.register("risk_in", risk)
    rows = con.execute(f"""
        WITH seg AS (
            SELECT p.pnr, p.customer_key, p.passenger_id, p.flight_id, p.origin, p.destination, f.std, f.sta,
                   f.flight_number
            FROM '{ops}/pax_segments.parquet' p JOIN '{ops}/flights.parquet' f USING (flight_id)
            WHERE p.pax_type <> 'IN'),
        pairs AS (
            SELECT i.pnr, i.customer_key, i.passenger_id, i.flight_id AS inbound_flight_id,
                   i.flight_number AS inbound_flight_number, o.flight_id AS outbound_flight_id,
                   o.flight_number AS outbound_flight_number, i.origin, i.destination AS hub,
                   o.destination AS final_destination, date_diff('minute', i.sta, o.std) AS connection_minutes,
                   row_number() OVER (PARTITION BY i.pnr, i.customer_key, i.flight_id ORDER BY o.std) AS rn
            FROM seg i JOIN seg o ON o.pnr = i.pnr AND o.customer_key = i.customer_key AND o.origin = i.destination
                 AND date_diff('minute', i.sta, o.std) BETWEEN {MIN_CONNECTION} AND {MAX_CONNECTION})
        SELECT pairs.* EXCLUDE (rn), coalesce(m.min_minutes, {default_mct}) AS mct_minutes,
               m.min_minutes IS NULL AS default_mct,
               [r.a_5, r.a_15, r.a_30, r.a_60, r.a_120, r.a_180] AS a,
               [o.p_5, o.p_15, o.p_30, o.p_60, o.p_120, o.p_180] AS d
        FROM pairs
        JOIN risk_in r ON r.flight_id = pairs.inbound_flight_id
        JOIN risk_in o ON o.flight_id = pairs.outbound_flight_id
        LEFT JOIN '{ops}/mct.parquet' m
          ON m.origin = pairs.origin AND m.hub = pairs.hub AND m.destination = pairs.final_destination
        WHERE rn = 1
        ORDER BY inbound_flight_id, pnr, customer_key""").fetchall()
    con.unregister("risk_in")
    names = [
        "pnr", "customer_key", "passenger_id", "inbound_flight_id", "inbound_flight_number", "outbound_flight_id",
        "outbound_flight_number", "origin", "hub", "final_destination", "connection_minutes", "mct_minutes",
        "default_mct",
    ]  # fmt: skip
    out: dict[str, list[Any]] = {n: [] for n in [*names, "slack_minutes", "misconnect_risk"]}
    for r in rows:
        values = dict(zip(names, r[: len(names)], strict=True))
        slack = int(values["connection_minutes"]) - int(values["mct_minutes"])
        for n in names:
            out[n].append(values[n])
        out["slack_minutes"].append(slack)
        out["misconnect_risk"].append(round(miss_probability(r[len(names)], r[len(names) + 1], slack), 4))
    return pa.table(out)


def _connection_backtest(
    con: duckdb.DuckDBPyConnection,
    ops: Path,
    frame: Frame,
    rows: np.ndarray,
    arrival: np.ndarray,
    departure: np.ndarray,
    default_mct: int,
) -> list[dict[str, Any]]:
    """Test weeks: hub flight pairs (arrive at SHJ, leave SHJ 15-240 min later). Predicted miss probability against
    what happened: actual arrival + MCT later than the actual onward departure."""
    con.register(
        "pred_t",
        pa.table(
            {
                "flight_id": [str(frame.flight_id[i]) for i in rows],
                **{f"a_{t}": arrival[:, j].tolist() for j, t in enumerate(THRESHOLDS)},
                **{f"p_{t}": departure[:, j].tolist() for j, t in enumerate(THRESHOLDS)},
            }
        ),
    )
    pairs = con.execute(f"""
        SELECT date_diff('minute', i.sta, o.std) - {default_mct} AS slack,
               (i.ata + INTERVAL {default_mct} MINUTE > o.atd)::INTEGER AS missed,
               [p.a_5, p.a_15, p.a_30, p.a_60, p.a_120, p.a_180] AS a,
               [q.p_5, q.p_15, q.p_30, q.p_60, q.p_120, q.p_180] AS d
        FROM '{ops}/history_flights.parquet' i
        JOIN pred_t p ON p.flight_id = i.flight_id
        JOIN '{ops}/history_flights.parquet' o ON o.origin = i.destination
        JOIN pred_t q ON q.flight_id = o.flight_id
             AND date_diff('minute', i.sta, o.std) BETWEEN {MIN_CONNECTION} AND 240
        WHERE i.destination = 'SHJ' AND i.operated AND o.operated AND i.ata IS NOT NULL AND o.atd IS NOT NULL
        """).fetchall()
    con.unregister("pred_t")
    bands = ((-999, 0, "no slack"), (1, 30, "1-30 min"), (31, 60, "31-60 min"), (61, 120, "61-120 min"),
             (121, 999, "over 120 min"))  # fmt: skip
    out = []
    for lo, hi, name in bands:
        sel = [r for r in pairs if lo <= r[0] <= hi]
        if sel:
            pred = [miss_probability(r[2], r[3], r[0]) for r in sel]
            out.append(
                {
                    "slack": name,
                    "pairs": len(sel),
                    "predicted": round(float(np.mean(pred)), 3),
                    "observed": round(float(np.mean([r[1] for r in sel])), 3),
                }
            )
    return out


def _last_week(con: duckdb.DuckDBPyConnection, ops: Path, frame: Frame, hist: np.ndarray) -> dict[str, Any]:
    """Replay of the last LAST_WEEK_DAYS days of history: a model trained only on the flights before that week
    predicts each flight (features known 7 days ahead, as in production), then the predictions are compared with
    what really happened. Honest by construction: the model never saw these flights or their delay rates."""
    end = frame.std[hist].max()
    start = end - np.timedelta64(LAST_WEEK_DAYS, "D")
    train, test = hist & (frame.std < start), hist & (frame.std >= start)
    p = DelayCurve(frame, train, start).predict(frame.x[test])
    j15, j60 = THRESHOLDS.index(15), THRESHOLDS.index(60)
    delay = frame.delay[test]
    y15, y60 = (delay >= 15).astype(int), (delay >= REASON_THRESHOLD).astype(int)
    p15, p60 = p[:, j15], p[:, j60]
    band = np.array([_band(float(v)) for v in p60])
    flagged = band != "low"
    names = dict(con.execute(f"SELECT flight_id, flight_number FROM '{ops}/history_flights.parquet'").fetchall())
    rows: list[dict[str, Any]] = []
    for k, i in enumerate(np.flatnonzero(test)):
        outcome = (
            ("hit" if y60[k] else "false_alarm") if flagged[k] else ("missed" if y60[k] else None)
        )  # None: correctly quiet
        if outcome is None:
            continue
        fid = str(frame.flight_id[i])
        rows.append(
            {
                "flight_id": fid,
                "flight_number": names.get(fid),
                "origin": str(frame.raw["origin"][i]),
                "destination": str(frame.raw["destination"][i]),
                "std": str(frame.std[i]),
                "p_15": round(float(p15[k]), 3),
                "p_60": round(float(p60[k]), 3),
                "band": str(band[k]),
                "actual_delay_minutes": int(delay[k]),
                "outcome": outcome,
            }
        )
    rows.sort(key=lambda r: (-r["actual_delay_minutes"], r["flight_id"]))
    two = 0 < y60.sum() < len(y60)
    return {
        "from": str(start.astype("datetime64[D]")),
        "to": str(end.astype("datetime64[D]")),
        "trained_on": f"flights before {start.astype('datetime64[D]')!s} ({int(train.sum())})",
        "flights": int(test.sum()),
        "late_15_rate": round(float(y15.mean()), 4),
        "late_60_rate": round(float(y60.mean()), 4),
        "auc_15": round(float(auc(y15, p15)), 4) if 0 < y15.sum() < len(y15) else None,
        "auc_60": round(float(auc(y60, p60)), 4) if two else None,
        "brier_60": round(float(brier(y60, p60)), 4),
        "flag_60": {"label": "flagged = high or medium band", **confusion(y60, p60, BANDS[1][0])},
        "flag_15": {"label": "flagged = 50% or more chance of 15+ min", **confusion(y15, p15, 0.5)},
        "high_band": {
            "flights": int((band == "high").sum()),
            "late_60": int(((band == "high") & (y60 == 1)).sum()),
        },
        "rows": rows[:150],
        "rows_total": len(rows),
    }


def run(ops: Path, default_mct: int = 50) -> dict[str, Any]:
    """Train, evaluate, score the window; write flight_risk, connection_risk and the model card."""
    con = duckdb.connect()
    frame = _frame(con, ops)
    hist = frame.part == "history"
    end = frame.std[hist].max()
    test_start = end - np.timedelta64(TEST_DAYS, "D")
    train_e, test_e = hist & (frame.std < test_start), hist & (frame.std >= test_start)

    evaluation = DelayCurve(frame, train_e, test_start)
    p_test = evaluation.predict(frame.x[test_e])
    metrics = {}
    for j, t in enumerate(THRESHOLDS):
        y = (frame.delay[test_e] >= t).astype(int)
        metrics[str(t)] = _metrics(y, p_test[:, j], _baseline(frame, train_e, test_e, t))
    y60 = (frame.delay[test_e] >= REASON_THRESHOLD).astype(int)
    reliability = _reliability(y60, p_test[:, THRESHOLDS.index(REASON_THRESHOLD)])

    production = DelayCurve(frame, hist, end)
    arrival_eval = DelayCurve(frame, train_e, test_start, arrival=True)
    arrival = DelayCurve(frame, hist, end, arrival=True)
    known_arr = test_e & ~np.isnan(frame.arr_delay)
    a_test = arrival_eval.predict(frame.x[known_arr])
    arrival_metrics = {
        str(t): _metrics((frame.arr_delay[known_arr] >= t).astype(int), a_test[:, j])
        for j, t in enumerate(THRESHOLDS)
        if t in (15, 60)
    }
    classification: dict[str, Any] = {}
    for kind, t in sorted({(k, t) for k, t, _, _ in OPERATING_POINTS}):
        if kind == "departure":
            y_k, p_k = (frame.delay[test_e] >= t).astype(int), p_test[:, THRESHOLDS.index(t)]
        else:
            y_k, p_k = (frame.arr_delay[known_arr] >= t).astype(int), a_test[:, THRESHOLDS.index(t)]
        cutoffs = [(c, label) for k, tt, c, label in OPERATING_POINTS if (k, tt) == (kind, t)]
        classification[f"{kind}_{t}"] = _classification(y_k, p_k, cutoffs)
    rolling = _rolling(frame, hist)
    last_week = _last_week(con, ops, frame, hist)
    (ops / "last_week.json").write_text(json.dumps(last_week, indent=2))
    test_rows = np.flatnonzero(test_e)
    connection_check = _connection_backtest(
        con, ops, frame, test_rows, arrival_eval.predict(frame.x[test_rows]), p_test, default_mct
    )
    win = np.flatnonzero(frame.part == "window")
    p_win = production.predict(frame.x[win])
    a_win = arrival.predict(frame.x[win])
    contrib = production.contributions(frame.x[win])
    j60 = THRESHOLDS.index(REASON_THRESHOLD)
    risk = pa.table(
        {
            "flight_id": [str(frame.flight_id[i]) for i in win],
            **{f"p_{t}": [round(float(v), 4) for v in p_win[:, j]] for j, t in enumerate(THRESHOLDS)},
            **{f"a_{t}": [round(float(v), 4) for v in a_win[:, j]] for j, t in enumerate(THRESHOLDS)},
            "planning_delay_minutes": [planning_delay(r) for r in p_win],
            "risk_band": [_band(float(r[j60])) for r in p_win],
            "reasons": [json.dumps(reasons(frame, int(i), contrib[k])) for k, i in enumerate(win)],
        }
    )
    connections = _connections(con, ops, risk, default_mct)
    con.register("risk_t", risk)
    con.register("conn_t", connections)
    risk = con.sql("""
        SELECT r.*, coalesce(c.n, 0)::INTEGER AS connecting_pax,
               round(coalesce(c.expected, 0), 2) AS expected_misconnects
        FROM risk_t r LEFT JOIN (SELECT inbound_flight_id, count(*) AS n, sum(misconnect_risk) AS expected
                                 FROM conn_t GROUP BY 1) c ON c.inbound_flight_id = r.flight_id
        ORDER BY r.flight_id""").to_arrow_table()
    pq.write_table(risk, ops / "flight_risk.parquet")
    pq.write_table(connections, ops / "connection_risk.parquet")

    def day(v: np.datetime64) -> str:
        return str(v.astype("datetime64[D]"))

    card = {
        "model": (
            f"LightGBM binary classifier per threshold, recency-weighted (half-life {HALF_LIFE_DAYS} days), "
            "hyperparameters tuned (ADR 0008)"
        ),
        "versions": {"lightgbm": lgb.__version__},
        "trained_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "departure delay (actual - scheduled departure) of at least t minutes, G9 operated flights",
        "thresholds_minutes": list(THRESHOLDS),
        "features": list(FEATURES),
        "evaluation": {
            "train": f"{day(frame.std[hist].min())} .. {day(test_start)} ({int(train_e.sum())} flights)",
            "test": f"{day(test_start)} .. {day(end)} ({int(test_e.sum())} flights)",
            "metrics_by_threshold": metrics,
            "reliability_60": reliability,
            "arrival_model_metrics": arrival_metrics,
            "connection_backtest": connection_check,
            "classification": classification,
            "rolling_monthly": rolling,
            "baseline": "historical rate of the same route and local departure hour (smoothed)",
        },
        "production": {
            "train": f"{day(frame.std[hist].min())} .. {day(end)} ({int(hist.sum())} flights)",
            "scored_flights": len(win),
            "bands_on_p60": {"high": BANDS[0][0], "medium": BANDS[1][0]},
        },
        "assumptions": [
            "Only information known 7 days ahead is used (schedule, aircraft plan, bookings, delay rates up to 7 days "
            "before the flight); actual times of the day itself are not used.",
            "Missed-connection risk = P(inbound arrival delay - onward departure delay > connection time - MCT), from "
            "a separate arrival-delay model and the onward flight's departure-delay model, taken as independent. "
            "Where the hub has no MCT rule for the journey, the default MCT is used and flagged.",
            "Risk is a probability from past behaviour, not a schedule decision; a person decides on any action.",
            "Delays of 2 hours or more are rare (under 1% in the test weeks) and the model over-estimates them; "
            "treat P(120+) and P(180+) as a ranking, not a level.",
        ],
        "connections": {"pairs": connections.num_rows, "default_mct_minutes": default_mct},
    }
    (ops / "model_card.json").write_text(json.dumps(card, indent=2))
    log.info("delay risk: test AUC(60) %s vs baseline %s", metrics["60"]["auc"], metrics["60"]["baseline_auc"])
    return {"scored": len(win), "connections": connections.num_rows, "auc_60": metrics["60"]["auc"]}


def default_mct_from_env(value: str | None) -> int:
    try:
        return int(value) if value else 50
    except ValueError:
        return 50


__all__ = ["THRESHOLDS", "DelayCurve", "planning_delay", "run", "survival"]
