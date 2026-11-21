"""Model comparison and hyperparameter tuning for the delay-risk model (ADR 0008, docs/architecture/adr/).

Offline research tool, not part of the API image. Needs: lightgbm, xgboost, catboost, scikit-learn, pandas, optuna
(install them in a scratch virtualenv). Run from `backend/`:

    python -m tools.model_selection <ops-folder> <output-folder> [--trials-lgb 40] [--trials-xgb 25]

Protocol (time-ordered, never random; no leakage):
  final test    the last 28 days of history. Scored ONCE, after every choice is made.
  validation    the three 28-day blocks before it. Expanding window: each block is predicted by a model trained
                only on the flights before the block. All comparison and tuning uses these blocks only.
  target        departure delay >= 15 and >= 60 minutes (the two thresholds the product reports).
  selection     mean Brier skill score (1 - Brier / climatology Brier) over blocks and thresholds; AUC is reported.
Candidates: route x hour baseline, prior (dummy), logistic regression, random forest, LightGBM (current settings,
class-weighted, tuned), XGBoost (default, tuned), CatBoost. Recency weights (half-life 60 days) are used by every
model so that the comparison is about the model, not the weighting; the half-life is tuned for the tuned models.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import warnings
from pathlib import Path
from typing import Any

import duckdb
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml import delay_risk as dr

log = logging.getLogger("model_selection")
THRESHOLDS = (15, 60)
BLOCK_DAYS = 28
VALIDATION_BLOCKS = 3
THREADS = 8
SEED = 7
CAT_IDX = list(range(len(dr.CATEGORICAL)))
NUM_IDX = list(range(len(dr.CATEGORICAL), len(dr.FEATURES)))


# ---------------------------------------------------------------- splits and scoring
def splits(frame: dr.Frame) -> tuple[list[tuple[np.ndarray, np.ndarray, np.datetime64]], tuple[Any, ...]]:
    hist = frame.part == "history"
    end = frame.std[hist].max()
    test_start = end - np.timedelta64(BLOCK_DAYS, "D")
    folds = []
    for k in range(VALIDATION_BLOCKS, 0, -1):
        start = test_start - np.timedelta64(BLOCK_DAYS * k, "D")
        stop = start + np.timedelta64(BLOCK_DAYS, "D")
        folds.append((hist & (frame.std < start), hist & (frame.std >= start) & (frame.std < stop), start))
    final = (hist & (frame.std < test_start), hist & (frame.std >= test_start), test_start)
    return folds, final


def weights(frame: dr.Frame, train: np.ndarray, as_of: np.datetime64, half_life: float) -> np.ndarray:
    age = ((as_of - frame.std[train]) / np.timedelta64(1, "D")).astype(float)
    return np.asarray(0.5 ** (np.clip(age, 0, None) / half_life), dtype=float)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    b, clim = dr.brier(y, p), dr.brier(y, np.full(len(y), y.mean()))
    return {
        "auc": dr.auc(y, p),
        "brier": b,
        "bss": 1 - b / clim,
        "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
    }


CATEGORY_LEVELS: dict[str, list[int]] = {}  # every code of the whole frame, so train and test share one dtype


def frame_df(x: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame(x, columns=list(dr.FEATURES))
    for c in dr.CATEGORICAL:
        df[c] = pd.Categorical(df[c].astype(int), categories=CATEGORY_LEVELS[c])
    return df


# ---------------------------------------------------------------- model factories: fit(x, y, w) -> predict(x)
def fit_lgb(params: dict[str, Any], rounds: int) -> Any:
    def go(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
        data = lgb.Dataset(x, y, weight=w, categorical_feature=CAT_IDX)
        return np.asarray(lgb.train(params, data, num_boost_round=rounds).predict(x_new))

    return go


def fit_xgb(params: dict[str, Any], rounds: int) -> Any:
    def go(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
        full = {
            "objective": "binary:logistic",
            "tree_method": "hist",
            "enable_categorical": True,
            "max_cat_to_onehot": 1,
            "nthread": THREADS,
            "seed": SEED,
            **params,
        }
        train = xgb.DMatrix(frame_df(x), label=y, weight=w, enable_categorical=True)
        booster = xgb.train(full, train, num_boost_round=rounds)
        return np.asarray(booster.predict(xgb.DMatrix(frame_df(x_new), enable_categorical=True)))

    return go


def fit_catboost(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    model = CatBoostClassifier(
        iterations=400, learning_rate=0.05, depth=6, l2_leaf_reg=3, random_seed=SEED, thread_count=THREADS, verbose=0
    )

    def ints(a: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(a, columns=list(dr.FEATURES))
        return df.astype(dict.fromkeys(dr.CATEGORICAL, int))

    model.fit(ints(x), y, cat_features=CAT_IDX, sample_weight=w)
    return np.asarray(model.predict_proba(ints(x_new))[:, 1])


def fit_logreg(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=30), CAT_IDX),
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), NUM_IDX),
        ]
    )
    model = make_pipeline(pre, LogisticRegression(C=1.0, max_iter=500))
    model.fit(x, y, logisticregression__sample_weight=w)
    return np.asarray(model.predict_proba(x_new)[:, 1])


def fit_forest(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    model = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=20, max_features=0.5, n_jobs=THREADS, random_state=SEED
    )
    model.fit(x, y, sample_weight=w)
    return np.asarray(model.predict_proba(x_new)[:, 1])


def fit_dummy(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    model = DummyClassifier(strategy="prior").fit(x, y, sample_weight=w)
    return np.asarray(model.predict_proba(x_new)[:, 1])


LGB_CURRENT = dict(dr.PARAMS, num_threads=THREADS)


def lgb_weighted(x: np.ndarray, y: np.ndarray, w: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """Class weights: positives weighted up to balance the classes (probabilities are then no longer calibrated)."""
    pos = float(w[y == 1].sum())
    w2 = np.where(y == 1, w * (float(w[y == 0].sum()) / pos), w)
    return fit_lgb(LGB_CURRENT, dr.ROUNDS)(x, y, w2, x_new)


# ---------------------------------------------------------------- evaluation of one candidate over blocks
def evaluate(frame: dr.Frame, blocks: list[tuple[Any, Any, Any]], fit: Any, half_life: float) -> dict[str, Any]:
    per_block = []
    for train, test, start in blocks:
        row: dict[str, Any] = {"block_start": str(start)[:10], "test_flights": int(test.sum())}
        w = weights(frame, train, start, half_life)
        for t in THRESHOLDS:
            y = (frame.delay >= t).astype(int)
            p = fit(frame.x[train], y[train], w, frame.x[test])
            row[str(t)] = metrics(y[test], p)
        per_block.append(row)
    mean = {
        str(t): {k: float(np.mean([b[str(t)][k] for b in per_block])) for k in ("auc", "brier", "bss", "logloss")}
        for t in THRESHOLDS
    }
    score = float(np.mean([mean[str(t)]["bss"] for t in THRESHOLDS]))
    return {"mean": mean, "score": score, "blocks": per_block}


def baseline_fit(frame: dr.Frame) -> Any:
    """Route x hour historical rate; works on row indices, so it is evaluated separately."""

    def run(blocks: list[tuple[Any, Any, Any]]) -> dict[str, Any]:
        per_block = []
        for train, test, start in blocks:
            row: dict[str, Any] = {"block_start": str(start)[:10]}
            for t in THRESHOLDS:
                y = (frame.delay >= t).astype(int)
                row[str(t)] = metrics(y[test], dr._baseline(frame, train, test, t))
            per_block.append(row)
        mean = {
            str(t): {k: float(np.mean([b[str(t)][k] for b in per_block])) for k in ("auc", "brier", "bss", "logloss")}
            for t in THRESHOLDS
        }
        return {"mean": mean, "score": float(np.mean([mean[str(t)]["bss"] for t in THRESHOLDS])), "blocks": per_block}

    return run


# ---------------------------------------------------------------- tuning
def tune_lgb(frame: dr.Frame, folds: list[Any], trials: int) -> dict[str, Any]:
    def objective(trial: optuna.Trial) -> float:
        params = dict(
            LGB_CURRENT,
            learning_rate=trial.suggest_float("learning_rate", 0.02, 0.15, log=True),
            num_leaves=trial.suggest_int("num_leaves", 8, 127, log=True),
            min_data_in_leaf=trial.suggest_int("min_data_in_leaf", 20, 400, log=True),
            feature_fraction=trial.suggest_float("feature_fraction", 0.5, 1.0),
            bagging_fraction=trial.suggest_float("bagging_fraction", 0.6, 1.0),
            bagging_freq=1,
            lambda_l2=trial.suggest_float("lambda_l2", 0.1, 50.0, log=True),
            cat_smooth=trial.suggest_float("cat_smooth", 5.0, 100.0, log=True),
            min_data_per_group=trial.suggest_int("min_data_per_group", 20, 200, log=True),
        )
        rounds = trial.suggest_int("rounds", 80, 600, step=20)
        half_life = trial.suggest_float("half_life", 20.0, 240.0, log=True)
        return evaluate(frame, folds, fit_lgb(params, rounds), half_life)["score"]

    return _optimise(objective, trials)


def tune_xgb(frame: dr.Frame, folds: list[Any], trials: int) -> dict[str, Any]:
    def objective(trial: optuna.Trial) -> float:
        params = {
            "eta": trial.suggest_float("eta", 0.02, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 9),
            "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 100.0, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "lambda": trial.suggest_float("lambda", 0.1, 50.0, log=True),
            "max_cat_threshold": 32,
        }
        rounds = trial.suggest_int("rounds", 80, 500, step=20)
        half_life = trial.suggest_float("half_life", 20.0, 240.0, log=True)
        return evaluate(frame, folds, fit_xgb(params, rounds), half_life)["score"]

    return _optimise(objective, trials)


def _optimise(objective: Any, trials: int) -> dict[str, Any]:
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=trials)
    return {
        "best_score": study.best_value,
        "best_params": study.best_params,
        "trials": [{"n": t.number, "score": t.value} for t in study.trials],
    }


def split_params(
    best: dict[str, Any], base: dict[str, Any], keys: tuple[str, ...]
) -> tuple[dict[str, Any], int, float]:
    params = dict(base, **{k: best[k] for k in keys})
    return params, int(best["rounds"]), float(best["half_life"])


# ---------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ops", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--trials-lgb", type=int, default=40)
    parser.add_argument("--trials-xgb", type=int, default=25)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    warnings.filterwarnings("ignore")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    args.out.mkdir(parents=True, exist_ok=True)

    frame = dr._frame(duckdb.connect(), args.ops)
    for i, c in enumerate(dr.CATEGORICAL):
        CATEGORY_LEVELS[c] = list(range(int(np.nanmax(frame.x[:, i])) + 1))
    folds, final = splits(frame)
    log.info(
        "folds: %s; final test from %s (%d flights)",
        [(str(s)[:10], int(te.sum())) for _, te, s in folds],
        str(final[2])[:10],
        int(final[1].sum()),
    )

    started = time.time()
    lgb_keys = (
        "learning_rate",
        "num_leaves",
        "min_data_in_leaf",
        "feature_fraction",
        "bagging_fraction",
        "lambda_l2",
        "cat_smooth",
        "min_data_per_group",
    )
    xgb_keys = ("eta", "max_depth", "min_child_weight", "subsample", "colsample_bytree", "lambda")

    log.info("tuning LightGBM (%d trials)", args.trials_lgb)
    tuned_lgb = tune_lgb(frame, folds, args.trials_lgb)
    lgb_params, lgb_rounds, lgb_hl = split_params(tuned_lgb["best_params"], dict(LGB_CURRENT, bagging_freq=1), lgb_keys)
    log.info("tuning XGBoost (%d trials)", args.trials_xgb)
    tuned_xgb = tune_xgb(frame, folds, args.trials_xgb)
    xgb_params, xgb_rounds, xgb_hl = split_params(tuned_xgb["best_params"], {"max_cat_threshold": 32}, xgb_keys)
    xgb_default = {"eta": 0.05, "max_depth": 6, "min_child_weight": 10, "subsample": 0.9, "colsample_bytree": 0.9}

    hl0 = float(dr.HALF_LIFE_DAYS)
    candidates: dict[str, tuple[Any, float]] = {
        "prior (dummy)": (fit_dummy, hl0),
        "logistic regression": (fit_logreg, hl0),
        "random forest": (fit_forest, hl0),
        "LightGBM, current settings": (fit_lgb(LGB_CURRENT, dr.ROUNDS), hl0),
        "LightGBM, class-weighted": (lgb_weighted, hl0),
        "LightGBM, tuned": (fit_lgb(lgb_params, lgb_rounds), lgb_hl),
        "XGBoost, default": (fit_xgb(xgb_default, 300), hl0),
        "XGBoost, tuned": (fit_xgb(xgb_params, xgb_rounds), xgb_hl),
        "CatBoost, default": (fit_catboost, hl0),
    }

    validation: dict[str, Any] = {"route x hour baseline": baseline_fit(frame)(folds)}
    for name, (fit, hl) in candidates.items():
        log.info("validation: %s", name)
        validation[name] = evaluate(frame, folds, fit, hl)
        validation[name]["half_life"] = hl
    ranking = sorted(validation, key=lambda n: validation[n]["score"], reverse=True)
    winner = next(n for n in ranking if n in candidates)
    log.info("validation ranking: %s", [(n, round(validation[n]["score"], 4)) for n in ranking])

    # Final test: scored once. Winner, the current model and the reference models.
    finals = ["route x hour baseline", "logistic regression", "LightGBM, current settings", "LightGBM, tuned"]
    if winner not in finals:
        finals.append(winner)
    final_report: dict[str, Any] = {}
    for name in finals:
        log.info("final test: %s", name)
        if name == "route x hour baseline":
            final_report[name] = baseline_fit(frame)([final])["mean"]
        else:
            fit, hl = candidates[name]
            final_report[name] = evaluate(frame, [final], fit, hl)["mean"]

    result = {
        "protocol": {
            "validation_blocks": [{"start": str(s)[:10], "flights": int(te.sum())} for _, te, s in folds],
            "final_test": {"start": str(final[2])[:10], "flights": int(final[1].sum())},
            "thresholds": list(THRESHOLDS),
            "selection_metric": "mean Brier skill score over blocks and thresholds",
            "seconds": round(time.time() - started),
        },
        "tuned": {
            "lightgbm": {
                "params": {k: lgb_params[k] for k in lgb_keys},
                "rounds": lgb_rounds,
                "half_life_days": lgb_hl,
                **{k: v for k, v in tuned_lgb.items() if k != "best_params"},
            },
            "xgboost": {
                "params": {k: xgb_params[k] for k in xgb_keys},
                "rounds": xgb_rounds,
                "half_life_days": xgb_hl,
                **{k: v for k, v in tuned_xgb.items() if k != "best_params"},
            },
        },
        "validation": validation,
        "ranking": ranking,
        "winner": winner,
        "final_test": final_report,
        "versions": {
            "lightgbm": lgb.__version__,
            "xgboost": xgb.__version__,
            "optuna": optuna.__version__,
            "numpy": np.__version__,
        },
    }
    (args.out / "model_selection.json").write_text(json.dumps(result, indent=2, default=float))
    log.info("done in %ds; winner on validation: %s", round(time.time() - started), winner)


if __name__ == "__main__":
    main()
