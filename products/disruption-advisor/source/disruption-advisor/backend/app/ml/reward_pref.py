"""Phase 5: passenger reward preference model (ADR 0012). Runs as ingest stage 4.

Question answered: how likely is THIS passenger to accept THIS reward (type and amount) after a disruption of THIS
severity? The score replaces the proxy rules in app/engine/rewards.py.

IMPORTANT, stated in the model card and the UI: no real redemption history exists. The training data is SYNTHETIC:
`generate_history` simulates past offers and accepted/declined outcomes for the real passenger profiles from an
assumed behaviour model (the assumptions are listed in BEHAVIOUR below). The trained model therefore reproduces
those assumptions, not real customer choices. It is a working pipeline to be retrained on real redemption data:
replace `generate_history` with the airline's offer log and nothing else changes.

Outputs (ops folder, Parquet / text):
  reward_history_synthetic.parquet   the simulated offers and outcomes (labelled synthetic)
  reward_model.txt                   the LightGBM model
  reward_model_card.json             data, features, metrics against baselines, calibration, assumptions
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import lightgbm as lgb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from app.engine import rewards as rw
from app.ml.delay_risk import _reliability, auc, brier

log = logging.getLogger("ingest.reward_pref")

SEED = 7
MAX_PASSENGERS = 150_000
OFFERS_PER_PASSENGER = 2
HOLDOUT_SHARE = 0.2
ROUNDS = 200
PARAMS: dict[
    str, Any
] = {  # tuned with Optuna on grouped validation folds (tuning record: docs/testing/reward-model-selection.md)
    "objective": "binary",
    "learning_rate": 0.0347,
    "num_leaves": 37,
    "min_data_in_leaf": 192,
    "feature_fraction": 0.9365,
    "bagging_fraction": 0.8902,
    "bagging_freq": 1,
    "lambda_l2": 0.7849,
    "cat_smooth": 8.0119,
    "min_data_per_group": 101,
    "seed": SEED,
    "deterministic": True,
    "force_row_wise": True,
    "num_threads": 4,
    "verbose": -1,
}
CATEGORIES: dict[str, tuple[str, ...]] = {
    "fare_family": ("Basic", "Value", "Ultimate", "Other", "Staff/ID", "Bus"),
    "sales_channel": ("TravelAgent", "APIAgencies", "SITECORE", "LCC", "Web", "IOS", "ANDROID", "GOQUO"),
    "loyalty_tier": ("none", "Basic", "Silver", "Gold", "Platinum"),  # airline loyalty sample ladder
    "frequency": ("occasional", "regular", "frequent", "unknown"),
    "reward_type": (rw.MEAL, rw.VOUCHER, rw.LOUNGE, rw.MILES, rw.TICKET),
}
NUMERIC = (
    "has_meal",
    "has_seat",
    "ancillaries",
    "fare",
    "baggage_kg",
    "pnr_size",
    "children",
    "infants",
    "flown_12m",
    "is_member",
    "upcoming_segments",
    "has_connection",
    "has_return",
    "amount_aed",
    "severity",
)
FEATURES = tuple(CATEGORIES) + NUMERIC
CAT_INDEX = list(range(len(CATEGORIES)))
AMOUNTS: dict[str, tuple[float, ...]] = {
    rw.MEAL: (50.0,),
    rw.VOUCHER: (100.0, 200.0, 400.0),
    rw.LOUNGE: (120.0,),
    rw.MILES: (100.0, 200.0, 400.0),  # AED value of the miles
    rw.TICKET: (600.0,),
}
BEHAVIOUR = [
    "A passenger who bought a meal on the booking, or travels with children, is more likely to accept a meal voucher.",
    "Online and app bookers and price-conscious fares (Basic, Value) are more likely to accept gift vouchers.",
    "Passengers who paid for a seat, Ultimate fares and frequent travellers are more likely to accept a lounge pass; "
    "families are less likely.",
    "Miles are accepted almost only by loyalty members, more by frequent travellers and Silver tier or above.",
    "Free tickets are accepted more by frequent travellers, Gold or Platinum members, Ultimate fares and groups.",
    "Passengers with a flight coming up take gift vouchers, miles and tickets more readily (they can use them), "
    "those with a return flight booked take free tickets most, and those connecting through the hub take lounge passes "
    "more readily.",
    "Everyone accepts more after a more severe disruption; each passenger also has a personal taste (random effect), "
    "and acceptance of an amount peaks when it matches the severity.",
]
HISTORY_COLUMNS = (
    "passenger_ref",
    *FEATURES,
    "accepted",
)


def _code(kind: str, value: Any) -> float:
    options = CATEGORIES[kind]
    return float(options.index(str(value))) if str(value) in options else float(len(options))


effective_tier = rw.effective_tier  # the better of the own and the family-account tier (priority rule)


def features_of(p: dict[str, Any]) -> dict[str, float]:
    """One passenger row (as from OpsStore.passengers_on) -> the model's passenger features."""
    tier = effective_tier(p)
    return {
        "fare_family": _code("fare_family", p.get("fare_family_synthetic")),
        "sales_channel": _code("sales_channel", p.get("sales_channel")),
        "loyalty_tier": _code("loyalty_tier", tier if tier else "none"),
        "frequency": _code("frequency", p.get("travel_frequency_band") or "unknown"),
        "has_meal": float(bool(p.get("has_meal"))),
        "has_seat": float(bool(p.get("has_seat"))),
        "ancillaries": float(p.get("ancillaries") or 0.0),
        "fare": float(p.get("fare") or 0.0),
        "baggage_kg": float(p.get("baggage_kg") or 0.0),
        "pnr_size": float(p.get("pnr_size") or 1),
        "children": float(p.get("children") or 0),
        "infants": float(p.get("infants") or 0),
        "flown_12m": float(p.get("flown_segments_12m") or 0),
        "is_member": float(bool(p.get("is_loyalty_member"))),
        "upcoming_segments": float(p.get("upcoming_segments") or 0),
        "has_connection": float(bool(p.get("has_connection"))),
        "has_return": float(bool(p.get("has_return"))),
    }


def matrix(passengers: list[dict[str, Any]], offers: list[tuple[str, float, float]]) -> np.ndarray:
    """Rows aligned with `offers` = (reward type, amount AED, severity); `passengers[i]` belongs to `offers[i]`."""
    cols: dict[str, list[float]] = {f: [] for f in FEATURES}
    for p, (kind, amount, sev) in zip(passengers, offers, strict=True):
        f = features_of(p)
        f.update({"reward_type": _code("reward_type", kind), "amount_aed": amount, "severity": sev})
        for k in FEATURES:
            cols[k].append(f[k])
    return np.column_stack([np.asarray(cols[k], dtype=float) for k in FEATURES])


# ------------------------------------------------------------------------------ synthetic behaviour
def _logit(m: dict[str, np.ndarray], taste: np.ndarray) -> np.ndarray:
    """Assumed behaviour (see BEHAVIOUR): the log-odds of accepting, per row of offers."""
    kind = m["reward_type"].astype(int)
    sev = m["severity"] / 100.0
    amount = m["amount_aed"]
    fam, chan, tier, freq = (m[k].astype(int) for k in ("fare_family", "sales_channel", "loyalty_tier", "frequency"))
    digital = np.isin(chan, [CATEGORIES["sales_channel"].index(c) for c in ("Web", "IOS", "ANDROID", "SITECORE")])
    price = np.isin(fam, [CATEGORIES["fare_family"].index(c) for c in ("Basic", "Value")])
    ultimate = fam == CATEGORIES["fare_family"].index("Ultimate")
    frequent = freq == CATEGORIES["frequency"].index("frequent")
    family = (m["children"] + m["infants"]) > 0
    member = m["is_member"] > 0
    upcoming = m["upcoming_segments"] > 0
    connecting = m["has_connection"] > 0
    returning = m["has_return"] > 0
    silver_up = tier >= CATEGORIES["loyalty_tier"].index("Silver")
    gold_up = tier >= CATEGORIES["loyalty_tier"].index("Gold")
    meal, voucher, lounge, miles, ticket = (CATEGORIES["reward_type"].index(k) for k in CATEGORIES["reward_type"])

    z = np.full(len(kind), -0.6) + 1.6 * sev
    z += np.where(
        kind == meal,
        0.2 + 1.3 * m["has_meal"] + 0.9 * family - 0.4 * ultimate,
        0.0,
    )
    z += np.where(
        kind == voucher,
        -0.1
        + 0.8 * digital
        + 0.6 * price
        + 0.4 * np.log1p(amount / 100.0) * (1 - sev)
        - 0.3 * ultimate
        + 0.35 * upcoming,
        0.0,
    )
    z += np.where(
        kind == lounge,
        -0.7 + 1.1 * m["has_seat"] + 0.8 * ultimate + 0.6 * frequent - 0.7 * family + 0.3 * connecting,
        0.0,
    )
    z += np.where(
        kind == miles,
        -1.8 + 3.0 * member + 0.9 * frequent * member + 0.6 * silver_up + 0.4 * upcoming * member,
        0.0,
    )
    z += np.where(
        kind == ticket,
        -1.0
        + 0.9 * frequent
        + 0.8 * gold_up
        + 0.6 * ultimate
        + 0.5 * (m["pnr_size"] >= 2)
        + 0.5 * returning
        + 0.3 * upcoming,
        0.0,
    )
    z -= 0.25 * ((amount / 100.0) - 6.0 * sev) ** 2 / 4.0  # an amount that matches the severity is preferred
    return np.asarray(z + taste[np.arange(len(kind)), kind], dtype=float)


def generate_history(passengers: list[dict[str, Any]], seed: int = SEED) -> dict[str, np.ndarray]:
    """SYNTHETIC offers and outcomes for real passenger profiles (see the module docstring)."""
    rng = np.random.default_rng(seed)
    n = len(passengers)
    per_passenger = [features_of(p) for p in passengers]
    base = {k: np.asarray([f[k] for f in per_passenger]) for k in per_passenger[0]}
    refs = np.asarray([str(p.get("customer_key", i)) for i, p in enumerate(passengers)])
    _, customer_idx = np.unique(refs, return_inverse=True)
    taste_by_customer = rng.normal(0.0, 0.5, size=(int(customer_idx.max()) + 1, len(CATEGORIES["reward_type"])))
    rows: dict[str, list[np.ndarray]] = {k: [] for k in FEATURES}
    outcome: list[np.ndarray] = []
    owner: list[np.ndarray] = []
    truth: list[np.ndarray] = []
    for _ in range(OFFERS_PER_PASSENGER):
        sev = rng.beta(2.2, 2.5, size=n) * 100.0
        kind = rng.integers(0, len(CATEGORIES["reward_type"]), size=n)
        member = base["is_member"] > 0
        kind = np.where((kind == CATEGORIES["reward_type"].index(rw.MILES)) & ~member, rng.integers(0, 3, size=n), kind)
        ticket_ok = sev >= 60
        kind = np.where(
            (kind == CATEGORIES["reward_type"].index(rw.TICKET)) & ~ticket_ok, rng.integers(0, 3, size=n), kind
        )
        amount = np.zeros(n)
        for k, name in enumerate(CATEGORIES["reward_type"]):
            idx = np.flatnonzero(kind == k)
            amount[idx] = rng.choice(AMOUNTS[name], size=len(idx))
        m = {f: base[f] for f in base} | {"reward_type": kind.astype(float), "amount_aed": amount, "severity": sev}
        p_accept = 1.0 / (1.0 + np.exp(-_logit(m, taste_by_customer[customer_idx])))
        accepted = (rng.random(n) < p_accept).astype(int)
        for name_ in FEATURES:
            rows[name_].append(m[name_])
        outcome.append(accepted)
        owner.append(refs)
        truth.append(p_accept)
    out: dict[str, np.ndarray] = {k: np.concatenate(v) for k, v in rows.items()}
    out["accepted"] = np.concatenate(outcome)
    out["p_true"] = np.concatenate(truth)  # the simulator's own probability: the best any model could do
    out["passenger_ref"] = np.concatenate(owner)
    return out


# ------------------------------------------------------------------------------ training and use
def _split(refs: np.ndarray, seed: int = SEED) -> np.ndarray:
    """True for training rows. Whole passengers are held out together, never split across train and test."""
    rng = np.random.default_rng(seed + 1)
    unique = np.unique(refs)
    held = set(rng.choice(unique, size=int(len(unique) * HOLDOUT_SHARE), replace=False).tolist())
    return np.asarray([r not in held for r in refs])


def _x(history: dict[str, np.ndarray]) -> np.ndarray:
    return np.column_stack([history[k].astype(float) for k in FEATURES])


def train(history: dict[str, np.ndarray]) -> tuple[lgb.Booster, dict[str, Any]]:
    train_rows = _split(history["passenger_ref"])
    x, y = _x(history), history["accepted"].astype(int)
    booster = lgb.train(
        PARAMS,
        lgb.Dataset(x[train_rows], y[train_rows], categorical_feature=CAT_INDEX, feature_name=list(FEATURES)),
        num_boost_round=ROUNDS,
    )
    test = ~train_rows
    p = np.asarray(booster.predict(x[test]))
    yt = y[test]
    kinds = history["reward_type"][test].astype(int)
    by_type = {}
    for k, name in enumerate(CATEGORIES["reward_type"]):
        sel = kinds == k
        if sel.sum() > 50 and 0 < yt[sel].sum() < sel.sum():
            by_type[name] = {
                "offers": int(sel.sum()),
                "acceptance_rate": round(float(yt[sel].mean()), 4),
                "auc": round(float(auc(yt[sel], p[sel])), 4),
            }
    # baselines: the average acceptance of the reward type, and the proxy rules of the first version
    overall = float(y[train_rows].mean())
    rate = {}
    for k in range(5):
        picked = y[train_rows][history["reward_type"][train_rows].astype(int) == k]
        rate[k] = float(picked.mean()) if len(picked) else overall  # a reward type absent from a tiny history
    type_avg = np.asarray([rate[k] for k in kinds])
    proxy = _proxy_scores(history, test)
    metrics = {
        "auc": round(float(auc(yt, p)), 4),
        "brier": round(float(brier(yt, p)), 4),
        "baseline_type_average": {
            "auc": round(float(auc(yt, type_avg)), 4),
            "brier": round(float(brier(yt, type_avg)), 4),
        },
        "baseline_proxy_rules": {"auc": round(float(auc(yt, proxy)), 4)},
        "observed_acceptance_rate": round(float(yt.mean()), 4),
        "by_reward_type": by_type,
        "reliability": _reliability(yt, p),
    }
    card = {
        "synthetic_training_data": True,
        "warning": (
            "Trained on SIMULATED redemption history (no real history exists). It reproduces the assumed behaviour "
            "below, not real customer choices. Retrain on the airline's offer log when it exists."
        ),
        "assumed_behaviour": BEHAVIOUR,
        "trained_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "versions": {"lightgbm": lgb.__version__},
        "features": list(FEATURES),
        "categories": {k: list(v) for k, v in CATEGORIES.items()},
        "history": {
            "offers": len(y),
            "passengers": len(np.unique(history["passenger_ref"])),
            "train_offers": int(train_rows.sum()),
            "test_offers": int(test.sum()),
        },
        "metrics_on_held_out_passengers": metrics,
    }
    return booster, card


def _proxy_scores(history: dict[str, np.ndarray], rows: np.ndarray) -> np.ndarray:
    """What the first version (proxy rules) would have scored each held-out offer."""
    out = []
    names = CATEGORIES["reward_type"]
    for i in np.flatnonzero(rows):
        p = {
            "fare_family_synthetic": CATEGORIES["fare_family"][int(history["fare_family"][i])]
            if history["fare_family"][i] < len(CATEGORIES["fare_family"])
            else None,
            "sales_channel": CATEGORIES["sales_channel"][int(history["sales_channel"][i])]
            if history["sales_channel"][i] < len(CATEGORIES["sales_channel"])
            else None,
            "loyalty_tier_synthetic": None
            if history["loyalty_tier"][i] == 0
            else CATEGORIES["loyalty_tier"][int(history["loyalty_tier"][i])],
            "travel_frequency_band": CATEGORIES["frequency"][int(history["frequency"][i])]
            if history["frequency"][i] < len(CATEGORIES["frequency"])
            else "unknown",
            "has_meal": history["has_meal"][i] > 0,
            "has_seat": history["has_seat"][i] > 0,
            "children": history["children"][i],
            "infants": history["infants"][i],
            "pnr_size": history["pnr_size"][i],
            "upcoming_segments": history["upcoming_segments"][i],
            "has_connection": history["has_connection"][i] > 0,
            "has_return": history["has_return"][i] > 0,
            "is_loyalty_member": history["is_member"][i] > 0,
        }
        out.append(rw.preferences(p)[0][names[int(history["reward_type"][i])]])
    return np.asarray(out)


class RewardModel:
    """The trained acceptance model, loaded by the API."""

    def __init__(self, booster: lgb.Booster, card: dict[str, Any]) -> None:
        self.booster = booster
        self.card = card

    @classmethod
    def load(cls, ops: Path) -> RewardModel | None:
        model, card = ops / "reward_model.txt", ops / "reward_model_card.json"
        if not (model.exists() and card.exists()):
            return None
        return cls(lgb.Booster(model_file=str(model)), json.loads(card.read_text()))

    def accept(self, passengers: list[dict[str, Any]], offers: list[tuple[str, float, float]]) -> np.ndarray:
        """P(accept) for each (passenger, offer) pair."""
        if not offers:
            return np.zeros(0)
        return np.asarray(self.booster.predict(matrix(passengers, offers)))

    def summary(self) -> dict[str, Any]:
        m = self.card["metrics_on_held_out_passengers"]
        return {
            "kind": "trained model",
            "synthetic_training_data": True,
            "auc": m["auc"],
            "baseline_proxy_rules_auc": m["baseline_proxy_rules"]["auc"],
            "trained_at": self.card["trained_at"],
        }


def load_passengers(ops: Path) -> list[dict[str, Any]]:
    """Real passenger profiles of the operating window: revenue passengers, infants excluded."""
    con = duckdb.connect()
    have = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{ops}/pax_segments.parquet'").fetchall()}
    family = ", ".join(
        f"p.{c}" if c in have else f"NULL AS {c}" for c in ("family_account_synthetic", "family_tier_synthetic")
    )  # data built before the family-account rule has no such columns
    later = "ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING"
    person = "PARTITION BY pnr, customer_key ORDER BY dep_utc"
    rows = con.execute(
        f"""WITH s AS (
              SELECT *, count(*) OVER ({person} {later}) AS upcoming_segments,
                     lead(origin) OVER ({person}) AS next_origin, lead(dep_utc) OVER ({person}) AS next_dep,
                     list(destination) OVER ({person} {later}) AS later_destinations
              FROM '{ops}/pax_segments.parquet')
            SELECT p.customer_key, p.fare_family_synthetic, p.sales_channel, p.has_meal, p.has_seat, p.ancillaries,
                   p.fare, p.baggage_kg, p.pnr_size, p.children, p.infants,
                   c.is_loyalty_member, c.loyalty_tier_synthetic, c.travel_frequency_band, c.flown_segments_12m,
                   {family}, p.upcoming_segments,
                   coalesce(p.next_origin = p.destination
                            AND date_diff('hour', p.dep_utc, p.next_dep) <= {rw.CONNECTION_WINDOW_HOURS}, FALSE),
                   coalesce(list_contains(p.later_destinations, p.origin), FALSE)
            FROM s p LEFT JOIN '{ops}/customers.parquet' c USING (customer_key)
            WHERE p.pax_type <> 'IN' AND p.revenue_type <> 'NON_REV'
            ORDER BY hash(p.pnr, p.customer_key, p.flight_id) LIMIT {MAX_PASSENGERS}"""
    ).fetchall()
    cols = (
        "customer_key",
        "fare_family_synthetic",
        "sales_channel",
        "has_meal",
        "has_seat",
        "ancillaries",
        "fare",
        "baggage_kg",
        "pnr_size",
        "children",
        "infants",
        "is_loyalty_member",
        "loyalty_tier_synthetic",
        "travel_frequency_band",
        "flown_segments_12m",
        "family_account_synthetic",
        "family_tier_synthetic",
        "upcoming_segments",
        "has_connection",
        "has_return",
    )
    return [dict(zip(cols, r, strict=True)) for r in rows]


def run(ops: Path) -> dict[str, Any]:
    """Ingest stage 4: simulate the history for the real passenger profiles, train, write the outputs."""
    passengers = load_passengers(ops)
    if not passengers:
        log.warning("stage 4 skipped: no passengers loaded (no bookings data)")
        return {"skipped": True, "reason": "no passengers"}
    history = generate_history(passengers)
    booster, card = train(history)
    booster.save_model(str(ops / "reward_model.txt"))
    (ops / "reward_model_card.json").write_text(json.dumps(card, indent=2))
    pq.write_table(
        pa.table({k: history[k] for k in HISTORY_COLUMNS}),
        ops / "reward_history_synthetic.parquet",
    )
    log.info(
        "reward preference model (synthetic history): AUC %s vs proxy rules %s",
        card["metrics_on_held_out_passengers"]["auc"],
        card["metrics_on_held_out_passengers"]["baseline_proxy_rules"]["auc"],
    )
    return {"offers": card["history"]["offers"], "auc": card["metrics_on_held_out_passengers"]["auc"]}
