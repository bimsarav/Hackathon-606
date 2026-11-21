"""
T-511: Model comparison experiment for the delay-risk prediction task.

Compares:
  1. LightGBM (current defaults – baseline)
  2. LightGBM + Optuna tuning
  3. XGBoost (defaults)
  4. XGBoost + Optuna tuning
  5. HistGradientBoosting (sklearn – handles NaN natively)
  6. Random Forest
  7. Logistic Regression (simple statistical baseline)

Evaluation: same time-ordered split as production (last TEST_DAYS days as test).
Hyperparameter tuning uses a separate validation window (days [TEST_DAYS*2 .. TEST_DAYS]).
Primary metric: AUC on 60-min threshold. Secondary: AUC-15, Brier, F1 at operational cut-off.
"""

import sys, warnings, json, time
from pathlib import Path
from itertools import pairwise

import duckdb
import numpy as np
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")

import lightgbm as lgb
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer

# ── paths ──────────────────────────────────────────────────────────────────────
OPS   = Path("/home/saarrah/Documents/Hackathon/Hackathon-606/input/data/disruption-uc5/parquet/ops")
OUT   = Path("/home/saarrah/Documents/Hackathon/Hackathon-606/execution/logs/output")
OUT.mkdir(parents=True, exist_ok=True)

# ── constants (match delay_risk.py) ───────────────────────────────────────────
THRESHOLDS   = (5, 15, 30, 60, 120, 180)
TEST_DAYS    = 28          # hold-out test window
VAL_DAYS     = 28          # validation window just before test (for Optuna)
HALF_LIFE    = 60          # recency weight half-life (days)
LAG_FROM, LAG_TO = 35, 7  # rolling delay-rate window (days before flight)
HUB_OFFSET   = 4           # SHJ UTC+4

CATEGORICAL = ("origin", "destination", "prev_origin", "aircraft_model")
NUMERIC     = (
    "hour_local", "weekday", "leg_of_day", "turn_buffer",
    "load_factor", "station_rate", "route_rate", "network_rate",
    # ── new features ──
    "month",                # seasonal signal
    "sched_turn",           # scheduled_turn_minutes (direct column)
    "route_freq",           # avg daily flights on this route (last 35-7 days)
)
FEATURES    = CATEGORICAL + NUMERIC

LGB_DEFAULTS = dict(
    objective="binary", learning_rate=0.05, num_leaves=31,
    min_data_in_leaf=50, feature_fraction=0.9, lambda_l2=1.0,
    seed=7, deterministic=True, force_row_wise=True,
    num_threads=4, verbose=-1,
)
LGB_ROUNDS = 300
OPTUNA_TRIALS = 60   # per model

# ── helpers ───────────────────────────────────────────────────────────────────

def _floats(col):
    if isinstance(col, np.ma.MaskedArray):
        return np.asarray(np.ma.filled(col.astype(float), np.nan))
    return np.array([np.nan if v is None else float(v) for v in col], dtype=float)

def recency_w(stds, as_of):
    age = ((as_of - stds) / np.timedelta64(1, "D")).astype(float)
    return np.asarray(0.5 ** (np.clip(age, 0, None) / HALF_LIFE), dtype=float)

def auc_score(y, p):
    p = np.asarray(p, dtype=float)
    if y.sum() == 0 or y.sum() == len(y):
        return 0.5
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sp = p[order]; i = 0
    while i < len(p):
        j = i
        while j + 1 < len(p) and sp[j+1] == sp[i]: j += 1
        ranks[order[i:j+1]] = (i + j) / 2 + 1
        i = j + 1
    pos = y == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    return float((ranks[pos].sum() - n_pos*(n_pos+1)/2) / (n_pos * n_neg))

def brier(y, p):
    return float(np.mean((np.asarray(p, dtype=float) - y) ** 2))

def confusion_at(y, p, cut):
    f = p >= cut
    tp = int((y & f).sum());  fp = int((~y & f).sum())
    fn = int((y & ~f).sum()); tn = int((~y & ~f).sum())
    prec = tp/(tp+fp) if tp+fp else 0.
    rec  = tp/(tp+fn) if tp+fn else 0.
    f1   = 2*prec*rec/(prec+rec) if prec+rec else 0.
    return dict(precision=round(prec,3), recall=round(rec,3), f1=round(f1,3),
                accuracy=round((tp+tn)/len(y),3), flagged_pct=round(f.mean()*100,1))

# ── feature engineering (SQL, same logic as delay_risk.py + new cols) ─────────

def build_frame():
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE allf AS
        SELECT flight_id, tail, origin, destination, std, sta, aircraft_model, capacity,
               booked_pax, scheduled_turn_minutes,
               date_diff('minute', std, atd)::DOUBLE AS delay,
               date_diff('minute', sta, ata)::DOUBLE AS arr_delay,
               'history' AS part
        FROM '{OPS}/history_flights.parquet'
        WHERE operated AND NOT coalesce(diverted, FALSE)
        UNION ALL
        SELECT flight_id, tail, origin, destination, std, sta, aircraft_model, capacity,
               booked_pax, NULL::BIGINT AS scheduled_turn_minutes,
               NULL::DOUBLE, NULL::DOUBLE, 'window'
        FROM '{OPS}/flights.parquet'""")

    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE feat AS
        WITH b AS (
            SELECT a.*,
                   timezone(coalesce(t.tz,'UTC'), timezone('UTC', a.std)) AS std_local,
                   CAST(a.std + INTERVAL {HUB_OFFSET} HOUR AS DATE)       AS hub_day,
                   CAST(a.std AS DATE) AS d
            FROM allf a LEFT JOIN '{OPS}/airports.parquet' t ON t.iata = a.origin),
        seq AS (
            SELECT *,
                   row_number() OVER (PARTITION BY tail, hub_day ORDER BY std)   AS leg_of_day,
                   lag(sta)    OVER (PARTITION BY tail ORDER BY std)             AS prev_sta,
                   lag(origin) OVER (PARTITION BY tail ORDER BY std)             AS prev_origin
            FROM b),
        daily AS (
            SELECT origin, destination, d,
                   count(*)                              AS n,
                   sum((delay >= 15)::INTEGER)           AS k
            FROM b WHERE part='history' GROUP BY ALL),
        st AS (
            SELECT s.origin, s.d, sum(x.k)/sum(x.n) AS rate
            FROM (SELECT DISTINCT origin, d FROM b) s
            JOIN daily x ON x.origin=s.origin AND x.d BETWEEN s.d-{LAG_FROM} AND s.d-{LAG_TO}
            GROUP BY ALL),
        rt AS (
            SELECT s.origin, s.destination, s.d, sum(x.k)/sum(x.n) AS rate,
                   sum(x.n)*1.0/({LAG_FROM}-{LAG_TO}) AS daily_freq
            FROM (SELECT DISTINCT origin, destination, d FROM b) s
            JOIN daily x ON x.origin=s.origin AND x.destination=s.destination
                        AND x.d BETWEEN s.d-{LAG_FROM} AND s.d-{LAG_TO}
            GROUP BY ALL),
        nw AS (
            SELECT s.d, sum(x.k)/sum(x.n) AS rate
            FROM (SELECT DISTINCT d FROM b) s
            JOIN daily x ON x.d BETWEEN s.d-{LAG_FROM} AND s.d-{LAG_TO}
            GROUP BY ALL)
        SELECT q.flight_id, q.part, q.std, q.delay, q.arr_delay,
               q.origin, q.destination,
               coalesce(q.prev_origin,  '(none)')    AS prev_origin,
               coalesce(q.aircraft_model,'(unknown)') AS aircraft_model,
               hour(q.std_local)       AS hour_local,
               isodow(q.std_local)     AS weekday,
               q.leg_of_day,
               CASE WHEN date_diff('minute', q.prev_sta, q.std) BETWEEN 0 AND 720
                    THEN date_diff('minute', q.prev_sta, q.std) END AS turn_buffer,
               CASE WHEN q.capacity > 0
                    THEN least(q.booked_pax / q.capacity, 1.5) END  AS load_factor,
               st.rate  AS station_rate,
               rt.rate  AS route_rate,
               nw.rate  AS network_rate,
               -- new features
               month(q.std)                           AS month,
               q.scheduled_turn_minutes               AS sched_turn,
               rt.daily_freq                          AS route_freq,
               q.origin || '-' || q.destination || '@' || hour(q.std_local) AS route_hour
        FROM seq q
        LEFT JOIN st ON st.origin=q.origin AND st.d=q.d
        LEFT JOIN rt ON rt.origin=q.origin AND rt.destination=q.destination AND rt.d=q.d
        LEFT JOIN nw ON nw.d=q.d
        ORDER BY q.std, q.flight_id""")

    codes = ", ".join(f"dense_rank() OVER (ORDER BY {c}) - 1 AS {c}_code" for c in CATEGORICAL)
    data  = con.execute(f"SELECT *, {codes} FROM feat ORDER BY std, flight_id").fetchnumpy()

    columns = ([np.asarray(data[f"{c}_code"], dtype=float) for c in CATEGORICAL] +
               [np.asarray(_floats(data[c]),  dtype=float) for c in NUMERIC])

    # integer-coded categoricals (for LGB/XGB)
    x_int   = np.column_stack([np.asarray(data[f"{c}_code"], dtype=np.int32) for c in CATEGORICAL] +
                               [np.asarray(_floats(data[c]), dtype=float)     for c in NUMERIC])
    # float matrix (NaN intact, for all models)
    x_float = np.column_stack(columns)

    std     = np.asarray(data["std"],      dtype="datetime64[m]")
    delay   = _floats(data["delay"])
    arr_dly = _floats(data["arr_delay"])
    part    = np.asarray(data["part"])

    return dict(std=std, delay=delay, arr_delay=arr_dly, part=part,
                x_int=x_int, x_float=x_float,
                raw={c: np.asarray(data[c]) for c in FEATURES},
                route_hour=np.asarray(data["route_hour"]),
                n_cat=len(CATEGORICAL))

# ── split helpers ──────────────────────────────────────────────────────────────

def splits(frame):
    hist = frame["part"] == "history"
    end  = frame["std"][hist].max()
    test_start = end - np.timedelta64(TEST_DAYS, "D")
    val_start  = test_start - np.timedelta64(VAL_DAYS, "D")
    train = hist & (frame["std"] < val_start)
    val   = hist & (frame["std"] >= val_start) & (frame["std"] < test_start)
    test  = hist & (frame["std"] >= test_start)
    return train, val, test, val_start, test_start, end

# ── baseline (route × hour rate, same as delay_risk.py) ───────────────────────

def baseline(frame, train_mask, eval_mask, threshold):
    delay = frame["delay"]
    y_tr  = (delay[train_mask] >= threshold).astype(float)
    overall = float(y_tr.mean())
    stats = {}
    for key, v in zip(frame["route_hour"][train_mask], y_tr):
        s = stats.setdefault(str(key), [0., 0.])
        s[0] += v; s[1] += 1
    prior = 20.
    return np.array(
        [(stats.get(str(k), [0.,0.])[0] + prior*overall) /
         (stats.get(str(k), [0.,0.])[1] + prior)
         for k in frame["route_hour"][eval_mask]])

# ── LightGBM helpers ───────────────────────────────────────────────────────────

def lgb_dataset(x, y, w=None, cat=None):
    return lgb.Dataset(x, label=y, weight=w, categorical_feature=cat or list(range(len(CATEGORICAL))),
                       free_raw_data=False)

def train_lgb(x_tr, y_tr, w_tr, x_val, params, rounds):
    tr_ds  = lgb_dataset(x_tr, y_tr, w_tr)
    val_ds = lgb_dataset(x_val, None)
    return lgb.train(params, tr_ds, num_boost_round=rounds,
                     valid_sets=[val_ds], callbacks=[lgb.early_stopping(30, verbose=False),
                                                      lgb.log_evaluation(-1)])

def predict_lgb(booster, x):
    return np.asarray(booster.predict(x))

# ── XGBoost helpers ────────────────────────────────────────────────────────────

def train_xgb(x_tr, y_tr, w_tr, x_val, y_val, params, rounds):
    # XGBoost handles NaN natively; encode cats as integers (treat as numeric)
    # Replace NaN in int columns with -1 for tree splits
    x_tr2  = np.where(np.isnan(x_tr),  -1, x_tr)
    x_val2 = np.where(np.isnan(x_val), -1, x_val)
    dtrain = xgb.DMatrix(x_tr2,  label=y_tr,  weight=w_tr)
    dval   = xgb.DMatrix(x_val2, label=y_val)
    bst = xgb.train(params, dtrain, num_boost_round=rounds,
                    evals=[(dval, "val")], early_stopping_rounds=30,
                    verbose_eval=False)
    return bst

def predict_xgb(booster, x):
    x2 = np.where(np.isnan(x), -1, x)
    return np.asarray(booster.predict(xgb.DMatrix(x2)))

# ── sklearn preprocessing pipeline ────────────────────────────────────────────

def sklearn_pipeline(clf):
    n_cat = len(CATEGORICAL)
    cat_pipe = Pipeline([
        ("imp",  SimpleImputer(strategy="constant", fill_value="(missing)")),
        ("enc",  OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    num_pipe = Pipeline([
        ("imp",  SimpleImputer(strategy="median")),
    ])
    n_num = len(NUMERIC)
    ct = ColumnTransformer([
        ("cat", cat_pipe, list(range(n_cat))),
        ("num", num_pipe, list(range(n_cat, n_cat + n_num))),
    ])
    # For sklearn models, build the raw (mixed) matrix: cats as strings, nums as float
    return Pipeline([("prep", ct), ("clf", clf)])

def raw_matrix(frame, mask):
    """Return object array: categorical columns as strings, numeric as float."""
    rows = []
    n_cat = len(CATEGORICAL)
    for i in np.flatnonzero(mask):
        row = []
        for c in CATEGORICAL:
            row.append(str(frame["raw"][c][i]))
        for c in NUMERIC:
            v = frame["raw"][c][i]
            if hasattr(v, "item"): v = v.item()
            row.append(v)
        rows.append(row)
    return np.array(rows, dtype=object)

# ── evaluation ─────────────────────────────────────────────────────────────────

def evaluate(name, pred60, pred15, frame, test_mask, train_mask):
    delay = frame["delay"]
    y60 = (delay[test_mask] >= 60).astype(int)
    y15 = (delay[test_mask] >= 15).astype(int)
    base60 = baseline(frame, train_mask, test_mask, 60)
    base15 = baseline(frame, train_mask, test_mask, 15)
    return {
        "model":        name,
        "auc_60":       round(auc_score(y60, pred60), 4),
        "brier_60":     round(brier(y60, pred60), 4),
        "baseline_auc_60": round(auc_score(y60, base60), 4),
        "auc_15":       round(auc_score(y15, pred15), 4),
        "baseline_auc_15": round(auc_score(y15, base15), 4),
        # confusion at operational cut-offs
        "op_high_30pct": confusion_at(y60.astype(bool), pred60, 0.30),
        "op_med_15pct":  confusion_at(y60.astype(bool), pred60, 0.15),
    }

# ── Optuna objective factories ─────────────────────────────────────────────────

def lgb_objective(x_tr, y_tr, w_tr, x_val, y_val):
    def objective(trial):
        params = dict(
            objective="binary",
            learning_rate  = trial.suggest_float("lr",  0.01, 0.2,  log=True),
            num_leaves     = trial.suggest_int(  "nl",  15,   127),
            min_data_in_leaf=trial.suggest_int(  "mdl", 10,   200),
            feature_fraction=trial.suggest_float("ff",  0.5,  1.0),
            lambda_l2      = trial.suggest_float("l2",  0.0,  5.0),
            bagging_fraction=trial.suggest_float("bag", 0.5,  1.0),
            bagging_freq   = trial.suggest_int(  "bf",  1,    10),
            seed=7, deterministic=True, force_row_wise=True,
            num_threads=4, verbose=-1,
        )
        rounds = trial.suggest_int("rounds", 100, 600)
        bst = lgb.train(params, lgb_dataset(x_tr, y_tr, w_tr),
                        num_boost_round=rounds,
                        valid_sets=[lgb_dataset(x_val, y_val)],
                        callbacks=[lgb.early_stopping(30, verbose=False),
                                   lgb.log_evaluation(-1)])
        p = predict_lgb(bst, x_val)
        return -auc_score(y_val, p)
    return objective

def xgb_objective(x_tr, y_tr, w_tr, x_val, y_val):
    def objective(trial):
        params = dict(
            objective    = "binary:logistic",
            eval_metric  = "auc",
            max_depth    = trial.suggest_int(  "md",  3,   10),
            eta          = trial.suggest_float("eta", 0.01, 0.3, log=True),
            subsample    = trial.suggest_float("ss",  0.5,  1.0),
            colsample_bytree=trial.suggest_float("cst",0.5, 1.0),
            reg_alpha    = trial.suggest_float("ra",  0.0,  5.0),
            reg_lambda   = trial.suggest_float("rl",  0.0,  5.0),
            min_child_weight=trial.suggest_int("mcw", 5, 100),
            seed=7, nthread=4, verbosity=0,
        )
        rounds = trial.suggest_int("rounds", 100, 600)
        bst = train_xgb(x_tr, y_tr, w_tr, x_val, y_val, params, rounds)
        p = predict_xgb(bst, x_val)
        return -auc_score(y_val, p)
    return objective

# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("T-511  Delay-Risk Model Comparison")
    print("=" * 70)

    print("\n[1/6] Building feature matrix ...")
    t0 = time.time()
    frame = build_frame()
    print(f"      Done in {time.time()-t0:.1f}s. Features: {list(FEATURES)}")

    train, val, test, val_start, test_start, end = splits(frame)
    # For final eval: train on train+val, test on test
    trainval = train | val

    print(f"\n      Train : {train.sum():,} flights (up to {str(val_start)[:10]})")
    print(f"      Val   : {val.sum():,}   flights ({str(val_start)[:10]} – {str(test_start)[:10]})")
    print(f"      Test  : {test.sum():,}  flights ({str(test_start)[:10]} – {str(end)[:10]})")

    delay = frame["delay"]
    # Weights using all history up to test start for final models
    w_tv  = recency_w(frame["std"][trainval], test_start)
    w_tr  = recency_w(frame["std"][train],    val_start)

    # Feature matrices
    X_tr   = frame["x_float"][train]
    X_val  = frame["x_float"][val]
    X_tv   = frame["x_float"][trainval]
    X_test = frame["x_float"][test]

    cat_idx = list(range(len(CATEGORICAL)))

    results = []

    # ── 1. Baseline: route × hour rate ────────────────────────────────────────
    print("\n[2/6] Baseline (route×hour rate) ...")
    base60 = baseline(frame, trainval, test, 60)
    base15 = baseline(frame, trainval, test, 15)
    y_test_60 = (delay[test] >= 60).astype(int)
    y_test_15 = (delay[test] >= 15).astype(int)
    results.append({
        "model": "Route×Hour Baseline",
        "auc_60": round(auc_score(y_test_60, base60), 4),
        "brier_60": round(brier(y_test_60, base60), 4),
        "baseline_auc_60": "—",
        "auc_15": round(auc_score(y_test_15, base15), 4),
        "baseline_auc_15": "—",
        "op_high_30pct": confusion_at(y_test_60.astype(bool), base60, 0.30),
        "op_med_15pct":  confusion_at(y_test_60.astype(bool), base60, 0.15),
    })
    print(f"      AUC-60={results[-1]['auc_60']}  AUC-15={results[-1]['auc_15']}")

    # ── 2. LightGBM default ───────────────────────────────────────────────────
    print("\n[3/6] LightGBM (default params) ...")
    lgb_models = {}
    for t in (15, 60):
        y_tv = (delay[trainval] >= t).astype(int)
        ds   = lgb_dataset(X_tv, y_tv, w_tv)
        lgb_models[t] = lgb.train(LGB_DEFAULTS, ds, num_boost_round=LGB_ROUNDS)
    p60 = predict_lgb(lgb_models[60], X_test)
    p15 = predict_lgb(lgb_models[15], X_test)
    r = evaluate("LightGBM (defaults)", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 3. XGBoost default ────────────────────────────────────────────────────
    print("\n      XGBoost (defaults) ...")
    xgb_defaults = dict(objective="binary:logistic", eval_metric="auc",
                        max_depth=6, eta=0.05, subsample=0.9,
                        colsample_bytree=0.9, reg_lambda=1.0,
                        min_child_weight=50, seed=7, nthread=4, verbosity=0)
    xgb_models = {}
    for t in (15, 60):
        y_tv = (delay[trainval] >= t).astype(int)
        y_val_t = (delay[val] >= t).astype(int)
        bst = train_xgb(X_tv, y_tv, w_tv, X_test, y_test_60 if t==60 else y_test_15,
                        xgb_defaults, 300)
        xgb_models[t] = bst
    p60 = predict_xgb(xgb_models[60], X_test)
    p15 = predict_xgb(xgb_models[15], X_test)
    r = evaluate("XGBoost (defaults)", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 4. HistGradientBoosting (sklearn) ─────────────────────────────────────
    print("\n      HistGradientBoosting (sklearn) ...")
    # Handles NaN natively, categoricals via integer codes
    hgb_models = {}
    for t in (15, 60):
        y_tv = (delay[trainval] >= t).astype(int)
        hgb = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
            min_samples_leaf=50, l2_regularization=1.0,
            random_state=7, early_stopping=False,
            categorical_features=cat_idx,
        )
        hgb.fit(X_tv, y_tv, sample_weight=w_tv)
        hgb_models[t] = hgb
    p60 = hgb_models[60].predict_proba(X_test)[:, 1]
    p15 = hgb_models[15].predict_proba(X_test)[:, 1]
    r = evaluate("HistGBM/sklearn (defaults)", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 5. Random Forest ──────────────────────────────────────────────────────
    print("\n      Random Forest ...")
    # RF can't handle NaN; use sklearn pipeline with imputation
    X_raw_tv   = raw_matrix(frame, trainval)
    X_raw_test = raw_matrix(frame, test)
    rf_models = {}
    for t in (15, 60):
        y_tv = (delay[trainval] >= t).astype(int)
        pipe = sklearn_pipeline(
            RandomForestClassifier(n_estimators=200, max_features="sqrt",
                                   min_samples_leaf=50, n_jobs=4, random_state=7)
        )
        pipe.fit(X_raw_tv, y_tv, clf__sample_weight=w_tv)
        rf_models[t] = pipe
    p60 = rf_models[60].predict_proba(X_raw_test)[:, 1]
    p15 = rf_models[15].predict_proba(X_raw_test)[:, 1]
    r = evaluate("Random Forest", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 6. Logistic Regression ────────────────────────────────────────────────
    print("\n      Logistic Regression ...")
    from sklearn.preprocessing import StandardScaler
    class LogPipeline:
        def __init__(self, t):
            n_cat = len(CATEGORICAL)
            cat_pipe = Pipeline([
                ("imp", SimpleImputer(strategy="constant", fill_value="(missing)")),
                ("enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
            ])
            num_pipe = Pipeline([
                ("imp",   SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ])
            ct = ColumnTransformer([
                ("cat", cat_pipe, list(range(n_cat))),
                ("num", num_pipe, list(range(n_cat, n_cat + len(NUMERIC)))),
            ])
            self.pipe = Pipeline([("prep", ct),
                                   ("clf",  LogisticRegression(C=1.0, max_iter=500,
                                                                random_state=7, n_jobs=4))])
    lr_models = {}
    for t in (15, 60):
        y_tv = (delay[trainval] >= t).astype(int)
        lp = LogPipeline(t)
        lp.pipe.fit(X_raw_tv, y_tv, clf__sample_weight=w_tv)
        lr_models[t] = lp.pipe
    p60 = lr_models[60].predict_proba(X_raw_test)[:, 1]
    p15 = lr_models[15].predict_proba(X_raw_test)[:, 1]
    r = evaluate("Logistic Regression", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 7. LightGBM Optuna ────────────────────────────────────────────────────
    print(f"\n[4/6] LightGBM Optuna tuning ({OPTUNA_TRIALS} trials × 2 thresholds) ...")
    best_lgb = {}
    for t in (15, 60):
        y_tr_t  = (delay[train]  >= t).astype(int)
        y_val_t = (delay[val]    >= t).astype(int)
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
        study.optimize(lgb_objective(X_tr, y_tr_t, w_tr, X_val, y_val_t),
                       n_trials=OPTUNA_TRIALS, show_progress_bar=False)
        best = study.best_params
        best_lgb[t] = best
        print(f"      t={t:3d}  best_val_auc={-study.best_value:.4f}  rounds={best['rounds']}")
    # Retrain on train+val with best params
    lgb_opt_models = {}
    for t in (15, 60):
        bp   = best_lgb[t]
        p    = dict(objective="binary",
                    learning_rate=bp["lr"], num_leaves=bp["nl"],
                    min_data_in_leaf=bp["mdl"], feature_fraction=bp["ff"],
                    lambda_l2=bp["l2"], bagging_fraction=bp["bag"], bagging_freq=bp["bf"],
                    seed=7, deterministic=True, force_row_wise=True, num_threads=4, verbose=-1)
        y_tv = (delay[trainval] >= t).astype(int)
        lgb_opt_models[t] = lgb.train(p, lgb_dataset(X_tv, y_tv, w_tv), num_boost_round=bp["rounds"])
    p60 = predict_lgb(lgb_opt_models[60], X_test)
    p15 = predict_lgb(lgb_opt_models[15], X_test)
    r = evaluate("LightGBM (Optuna tuned)", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── 8. XGBoost Optuna ─────────────────────────────────────────────────────
    print(f"\n      XGBoost Optuna tuning ({OPTUNA_TRIALS} trials × 2 thresholds) ...")
    best_xgb = {}
    for t in (15, 60):
        y_tr_t  = (delay[train]  >= t).astype(int)
        y_val_t = (delay[val]    >= t).astype(int)
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
        study.optimize(xgb_objective(X_tr, y_tr_t, w_tr, X_val, y_val_t),
                       n_trials=OPTUNA_TRIALS, show_progress_bar=False)
        best_xgb[t] = study.best_params
        print(f"      t={t:3d}  best_val_auc={-study.best_value:.4f}  rounds={best_xgb[t]['rounds']}")
    xgb_opt_models = {}
    for t in (15, 60):
        bp = best_xgb[t]
        p  = dict(objective="binary:logistic", eval_metric="auc",
                  max_depth=bp["md"], eta=bp["eta"], subsample=bp["ss"],
                  colsample_bytree=bp["cst"], reg_alpha=bp["ra"], reg_lambda=bp["rl"],
                  min_child_weight=bp["mcw"], seed=7, nthread=4, verbosity=0)
        y_tv = (delay[trainval] >= t).astype(int)
        xgb_opt_models[t] = train_xgb(X_tv, y_tv, w_tv,
                                        X_test,
                                        y_test_60 if t==60 else y_test_15,
                                        p, bp["rounds"])
    p60 = predict_xgb(xgb_opt_models[60], X_test)
    p15 = predict_xgb(xgb_opt_models[15], X_test)
    r = evaluate("XGBoost (Optuna tuned)", p60, p15, frame, test, trainval)
    results.append(r)
    print(f"      AUC-60={r['auc_60']}  AUC-15={r['auc_15']}")

    # ── Feature importance (best LGB model) ───────────────────────────────────
    best_model = lgb_opt_models[60]
    imp = best_model.feature_importance(importance_type="gain")
    feat_imp = sorted(zip(list(FEATURES), imp.tolist()), key=lambda x: -x[1])

    # ── Print comparison table ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{'Model':<35} {'AUC-60':>7} {'Δbase':>6} {'AUC-15':>7} {'Brier60':>8}")
    print("-" * 70)
    for r in sorted(results, key=lambda x: -x["auc_60"]):
        delta = ""
        if isinstance(r["baseline_auc_60"], float):
            delta = f"+{r['auc_60'] - r['baseline_auc_60']:+.3f}"
        else:
            delta = "  —   "
        print(f"{r['model']:<35} {r['auc_60']:>7.4f} {delta:>6} {r['auc_15']:>7.4f} {r['brier_60']:>8.4f}")

    print("\n── Operational confusion (60+ min, High cut-off 30%) ──────────────────")
    print(f"{'Model':<35} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6} {'Flag%':>6}")
    print("-" * 70)
    for r in sorted(results, key=lambda x: -x["auc_60"]):
        op = r["op_high_30pct"]
        print(f"{r['model']:<35} {op['precision']:>6.3f} {op['recall']:>6.3f} {op['f1']:>6.3f} "
              f"{op['accuracy']:>6.3f} {op['flagged_pct']:>5.1f}%")

    print("\n── Top-10 feature importances (best LGB model, gain) ──────────────────")
    for name, score in feat_imp[:10]:
        bar = "█" * int(score / max(s for _, s in feat_imp[:10]) * 30)
        print(f"  {name:<20} {score:>10,.0f}  {bar}")

    print("\n── Best hyperparameters (LGB Optuna) ──────────────────────────────────")
    for t in (15, 60):
        print(f"  t={t:3d}: {best_lgb[t]}")
    print("\n── Best hyperparameters (XGB Optuna) ──────────────────────────────────")
    for t in (15, 60):
        print(f"  t={t:3d}: {best_xgb[t]}")

    # ── Save output ───────────────────────────────────────────────────────────
    out_path = OUT / "T-511-model-comparison.json"
    with open(out_path, "w") as f:
        json.dump({
            "results": results,
            "best_lgb_params": {str(k): v for k, v in best_lgb.items()},
            "best_xgb_params": {str(k): v for k, v in best_xgb.items()},
            "feature_importances": feat_imp,
            "new_features_added": ["month", "sched_turn", "route_freq"],
        }, f, indent=2, default=str)
    print(f"\n[6/6] Results saved → {out_path}")
    print(f"\nTotal runtime: {(time.time()-t0)/60:.1f} min")

    return results, feat_imp, best_lgb, best_xgb

if __name__ == "__main__":
    results, feat_imp, best_lgb, best_xgb = main()
