"""Model comparison and hyperparameter tuning for the reward preference model (ADR 0012, docs/architecture/adr/).

Offline research tool, not part of the API image. Needs lightgbm, xgboost, catboost, scikit-learn, pandas, optuna in a
scratch virtualenv. Run from `backend/`:

    python -m tools.reward_model_selection <ops-folder> <output-folder> [--trials-lgb 40] [--trials-xgb 25]

IMPORTANT: the outcomes are SIMULATED (see app/ml/reward_pref.py). This run therefore measures how well each model
recovers the assumed behaviour, not how real customers behave. Because the simulator's own probability is known, the
best any model could possibly score (the "oracle") is reported next to every result.

Protocol (whole passengers are never split between train and test):
  final test   20% of the passengers, scored once at the end.
  validation   the other 80%, in 4 grouped folds; every comparison and every tuning trial uses these only.
  selection    mean log-loss over the folds (lower is better; the plan uses the probabilities themselves, so
               calibration matters more than ranking). AUC and Brier are reported too.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import warnings
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml import reward_pref as rp
from app.ml.delay_risk import auc, brier

log = logging.getLogger("reward_model_selection")
SEED = 7
FOLDS = 4
TEST_SHARE = 0.2
THREADS = 8
NUM_IDX = [i for i in range(len(rp.FEATURES)) if i not in rp.CAT_INDEX]
TYPE_IDX = list(rp.FEATURES).index("reward_type")
LEVELS = {name: list(range(len(values) + 1)) for name, values in rp.CATEGORIES.items()}  # +1: unknown


# ---------------------------------------------------------------- splits and scores
def split(refs: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """(test mask, list of validation-fold masks over the remaining rows)."""
    rng = np.random.default_rng(SEED + 2)
    unique = rng.permutation(np.unique(refs))
    n_test = int(len(unique) * TEST_SHARE)
    test_ids = set(unique[:n_test].tolist())
    rest = unique[n_test:]
    test = np.asarray([r in test_ids for r in refs])
    owner = {r: i % FOLDS for i, r in enumerate(rest.tolist())}
    folds = [np.asarray([(r not in test_ids) and owner[r] == k for r in refs]) for k in range(FOLDS)]
    return test, folds


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return {
        "auc": float(auc(y, p)),
        "brier": float(brier(y, p)),
        "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
    }


def frame(x: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame(x, columns=list(rp.FEATURES))
    for name in rp.CATEGORIES:
        df[name] = pd.Categorical(df[name].astype(int), categories=LEVELS[name])
    return df


# ---------------------------------------------------------------- models: fit(xtr, ytr, xte) -> p
def lgb_model(params: dict[str, Any], rounds: int) -> Any:
    def go(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
        data = lgb.Dataset(xtr, ytr, categorical_feature=rp.CAT_INDEX, feature_name=list(rp.FEATURES))
        return np.asarray(lgb.train(params, data, num_boost_round=rounds).predict(xte))

    return go


def xgb_model(params: dict[str, Any], rounds: int) -> Any:
    def go(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
        full = {
            "objective": "binary:logistic",
            "tree_method": "hist",
            "enable_categorical": True,
            "max_cat_to_onehot": 1,
            "nthread": THREADS,
            "seed": SEED,
            **params,
        }
        booster = xgb.train(full, xgb.DMatrix(frame(xtr), label=ytr, enable_categorical=True), num_boost_round=rounds)
        return np.asarray(booster.predict(xgb.DMatrix(frame(xte), enable_categorical=True)))

    return go


def catboost_model(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
    def ints(a: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(a, columns=list(rp.FEATURES)).astype(dict.fromkeys(rp.CATEGORIES, int))

    model = CatBoostClassifier(
        iterations=400, learning_rate=0.05, depth=6, random_seed=SEED, thread_count=THREADS, verbose=0
    )
    model.fit(ints(xtr), ytr, cat_features=rp.CAT_INDEX)
    return np.asarray(model.predict_proba(ints(xte))[:, 1])


def logreg_model(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=30), rp.CAT_INDEX),
            ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUM_IDX),
        ]
    )
    model = make_pipeline(pre, LogisticRegression(C=1.0, max_iter=500))
    model.fit(xtr, ytr)
    return np.asarray(model.predict_proba(xte)[:, 1])


def forest_model(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
    model = RandomForestClassifier(
        n_estimators=150, min_samples_leaf=50, max_features=0.5, n_jobs=THREADS, random_state=SEED
    )
    model.fit(xtr, ytr)
    return np.asarray(model.predict_proba(xte)[:, 1])


def type_average_model(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
    kinds = xtr[:, TYPE_IDX].astype(int)
    rate = {k: float(ytr[kinds == k].mean()) for k in np.unique(kinds)}
    return np.asarray([rate.get(int(k), float(ytr.mean())) for k in xte[:, TYPE_IDX]])


# ---------------------------------------------------------------- evaluation and tuning
def cross_validate(
    x: np.ndarray, y: np.ndarray, folds: list[np.ndarray], train_pool: np.ndarray, fit: Any
) -> dict[str, Any]:
    per_fold = []
    for k, held in enumerate(folds):
        train = train_pool & ~held
        p = fit(x[train], y[train], x[held])
        per_fold.append(metrics(y[held], p) | {"fold": k})
    mean = {m: float(np.mean([f[m] for f in per_fold])) for m in ("auc", "brier", "logloss")}
    return {"mean": mean, "folds": per_fold}


def tune(
    kind: str, x: np.ndarray, y: np.ndarray, folds: list[np.ndarray], pool: np.ndarray, trials: int
) -> dict[str, Any]:
    def objective(trial: optuna.Trial) -> float:
        if kind == "lightgbm":
            params = dict(
                rp.PARAMS,
                num_threads=THREADS,
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
            fit = lgb_model(params, trial.suggest_int("rounds", 80, 600, step=20))
        else:
            params = {
                "eta": trial.suggest_float("eta", 0.02, 0.2, log=True),
                "max_depth": trial.suggest_int("max_depth", 3, 9),
                "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 100.0, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "lambda": trial.suggest_float("lambda", 0.1, 50.0, log=True),
                "max_cat_threshold": 32,
            }
            fit = xgb_model(params, trial.suggest_int("rounds", 80, 500, step=20))
        return cross_validate(x, y, folds, pool, fit)["mean"]["logloss"]

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=trials)
    return {
        "best_logloss": study.best_value,
        "best_params": study.best_params,
        "trials": [t.value for t in study.trials],
    }


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
    started = time.time()

    history = rp.generate_history(rp.load_passengers(args.ops))
    x, y, truth = rp._x(history), history["accepted"].astype(int), history["p_true"]
    test, folds = split(history["passenger_ref"])
    pool = ~test
    log.info(
        "offers %d, passengers %d, test offers %d", len(y), len(np.unique(history["passenger_ref"])), int(test.sum())
    )

    log.info("tuning LightGBM (%d trials)", args.trials_lgb)
    t_lgb = tune("lightgbm", x, y, folds, pool, args.trials_lgb)
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
    lgb_tuned = dict(rp.PARAMS, num_threads=THREADS, bagging_freq=1, **{k: t_lgb["best_params"][k] for k in lgb_keys})
    lgb_rounds = int(t_lgb["best_params"]["rounds"])
    log.info("tuning XGBoost (%d trials)", args.trials_xgb)
    t_xgb = tune("xgboost", x, y, folds, pool, args.trials_xgb)
    xgb_keys = ("eta", "max_depth", "min_child_weight", "subsample", "colsample_bytree", "lambda")
    xgb_tuned = {"max_cat_threshold": 32, **{k: t_xgb["best_params"][k] for k in xgb_keys}}
    xgb_rounds = int(t_xgb["best_params"]["rounds"])

    candidates: dict[str, Any] = {
        "type average (baseline)": type_average_model,
        "logistic regression": logreg_model,
        "random forest": forest_model,
        "LightGBM, current settings": lgb_model(dict(rp.PARAMS, num_threads=THREADS), rp.ROUNDS),
        "LightGBM, tuned": lgb_model(lgb_tuned, lgb_rounds),
        "XGBoost, default": xgb_model(
            {"eta": 0.05, "max_depth": 6, "min_child_weight": 10, "subsample": 0.9, "colsample_bytree": 0.9}, 300
        ),
        "XGBoost, tuned": xgb_model(xgb_tuned, xgb_rounds),
        "CatBoost, default": catboost_model,
    }
    validation: dict[str, Any] = {}
    for name, fit in candidates.items():
        log.info("validation: %s", name)
        validation[name] = cross_validate(x, y, folds, pool, fit)
    ranking = sorted(validation, key=lambda n: validation[n]["mean"]["logloss"])
    winner = ranking[0]
    log.info("validation ranking: %s", [(n, round(validation[n]["mean"]["logloss"], 4)) for n in ranking])

    # The final test, scored once: reference models, the current and tuned LightGBM, the overall winner, the oracle.
    final: dict[str, Any] = {}
    for name in dict.fromkeys(
        ["type average (baseline)", "logistic regression", "LightGBM, current settings", "LightGBM, tuned", winner]
    ):
        log.info("final test: %s", name)
        final[name] = metrics(y[test], candidates[name](x[pool], y[pool], x[test]))
    final["proxy rules (first version)"] = {"auc": float(auc(y[test], rp._proxy_scores(history, test)))}
    final["oracle (simulator's true probability)"] = metrics(y[test], truth[test])

    result = {
        "synthetic_data": True,
        "protocol": {
            "offers": len(y),
            "passengers": len(np.unique(history["passenger_ref"])),
            "test_offers": int(test.sum()),
            "validation_folds": FOLDS,
            "selection_metric": "mean log-loss over grouped validation folds",
            "seconds": round(time.time() - started),
        },
        "tuned": {
            "lightgbm": {
                "params": {k: lgb_tuned[k] for k in lgb_keys},
                "rounds": lgb_rounds,
                "best_logloss": t_lgb["best_logloss"],
                "trials": t_lgb["trials"],
            },
            "xgboost": {
                "params": {k: xgb_tuned[k] for k in xgb_keys},
                "rounds": xgb_rounds,
                "best_logloss": t_xgb["best_logloss"],
                "trials": t_xgb["trials"],
            },
        },
        "validation": validation,
        "ranking": ranking,
        "winner": winner,
        "final_test": final,
        "versions": {"lightgbm": lgb.__version__, "xgboost": xgb.__version__, "optuna": optuna.__version__},
    }
    (args.out / "reward_model_selection.json").write_text(json.dumps(result, indent=2, default=float))
    log.info("done in %ds; winner on validation: %s", round(time.time() - started), winner)


if __name__ == "__main__":
    main()
