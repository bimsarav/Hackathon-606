"""Phase 5 reward recommendation (ADR 0010): severity, proxy preferences, eligibility and the budget fit."""

from typing import Any

import pytest

from app.engine import rewards as rw


def person(
    i: int, sev: float = 60.0, value: float = 50.0, member: bool = True, non_rev: bool = False, **prefs: float
) -> rw.Person:
    base = {rw.MEAL: 0.5, rw.VOUCHER: 0.5, rw.LOUNGE: 0.4, rw.MILES: 0.5 if member else 0.0, rw.TICKET: 0.3}
    base.update(prefs)
    return rw.Person(
        pnr=f"P{i:05d}",
        customer_key=f"{i:016x}",
        passenger_id=f"PAX{i}",
        route="SHJ-CAI",
        tier=3,
        value=value,
        severity=sev,
        severity_reasons=[],
        disrupted_minutes=180,
        loyalty_member=member,
        non_revenue=non_rev,
        prefs=base,
        pref_reasons={k: [] for k in base},
    )


def test_severity_grows_with_delay_connection_wait_and_vulnerability() -> None:
    short, _ = rw.severity(30, False, False, None, False)
    long, _ = rw.severity(240, False, False, None, False)
    missed, reasons = rw.severity(240, False, True, 300, True)
    cancelled, _ = rw.severity(None, True, False, None, False)
    assert short < long < missed <= 100
    assert any("connection" in r for r in reasons)
    assert cancelled > long
    assert rw.flight_severity(15, False)["label"] == "minor"
    assert rw.flight_severity(None, True)["label"] == "major"


def test_preferences_follow_the_booking_clues() -> None:
    meal_buyer, why = rw.preferences({"has_meal": True, "children": 1, "is_loyalty_member": False})
    plain, _ = rw.preferences({"is_loyalty_member": False})
    assert meal_buyer[rw.MEAL] > plain[rw.MEAL]
    assert "bought a meal on the booking" in why[rw.MEAL]
    assert meal_buyer[rw.MILES] == 0.0  # miles only make sense for loyalty members
    gold, _ = rw.preferences(
        {
            "is_loyalty_member": True,
            "loyalty_tier_synthetic": "Gold",
            "travel_frequency_band": "frequent",
            "has_seat": True,
        }
    )
    assert gold[rw.MILES] > plain[rw.MILES]
    assert gold[rw.LOUNGE] > plain[rw.LOUNGE]


def test_eligibility_rules() -> None:
    rules = rw.RewardRules()
    p = person(1, sev=50.0, member=False)
    kinds = {o.kind for o in rw.eligible_options(p, rules)}
    assert rw.MILES not in kinds
    assert rw.TICKET not in kinds
    assert {rw.MEAL, rw.VOUCHER, rw.LOUNGE} <= kinds
    severe = person(2, sev=90.0)
    assert rw.TICKET in {o.kind for o in rw.eligible_options(severe, rules)}


def test_zero_budget_gives_nothing_and_a_big_budget_gives_the_full_plan() -> None:
    people = [person(i, sev=40 + i) for i in range(20)]
    none = rw.recommend(people, 0)
    assert none["planned_spend_aed"] == 0
    assert none["rewarded"] == 0
    full = rw.recommend(people, 1_000_000)
    assert full["planned_spend_aed"] == full["ideal_spend_aed"]
    assert full["budget_covers_share"] == 1.0
    assert full["rewarded"] == 20


@pytest.mark.parametrize("budget", [500, 1500, 3000, 6000])
def test_plan_never_exceeds_the_budget_and_spend_matches_the_rows(budget: int) -> None:
    people = [person(i, sev=30 + 3 * (i % 25), value=(i * 7) % 100, member=i % 3 == 0) for i in range(60)]
    plan = rw.recommend(people, budget)
    spent = sum(r["reward"]["cost_aed"] for r in plan["rows"] if r["reward"])
    assert spent == plan["planned_spend_aed"] <= budget
    assert sum(v["spend_aed"] for v in plan["by_type"].values()) == spent


def test_tighter_budget_never_rewards_more_and_keeps_the_most_affected() -> None:
    people = [person(i, sev=30 + 2 * i, value=50) for i in range(30)]
    small, large = rw.recommend(people, 1000), rw.recommend(people, 4000)
    assert small["planned_spend_aed"] <= large["planned_spend_aed"]

    def got(plan: dict[str, Any], pnr: str) -> float:
        row = next(r for r in plan["rows"] if r["pnr"] == pnr)
        return row["reward"]["cost_aed"] if row["reward"] else 0.0

    worst, mildest = "P00029", "P00000"
    assert got(small, worst) >= got(small, mildest)


def test_non_revenue_passengers_get_no_goodwill_reward_and_the_plan_is_deterministic() -> None:
    people = [person(i, non_rev=(i == 0)) for i in range(5)]
    plan = rw.recommend(people, 10_000)
    staff = next(r for r in plan["rows"] if r["pnr"] == "P00000")
    assert staff["reward"] is None
    assert "Non-revenue" in staff["note"]
    assert rw.recommend(people, 700) == rw.recommend(people, 700)


# ------------------------------------------------------------------------------ preference model (synthetic data)
def _passengers(n: int = 20000) -> list[dict[str, Any]]:
    import random

    rnd = random.Random(3)  # noqa: S311  (synthetic test data)
    out = []
    for i in range(n):
        member = rnd.random() < 0.3
        out.append(
            {
                "customer_key": f"{i // 2:016x}",
                "fare_family_synthetic": rnd.choice(["Basic", "Value", "Ultimate", "Other"]),
                "sales_channel": rnd.choice(["Web", "IOS", "TravelAgent", "LCC"]),
                "has_meal": rnd.random() < 0.5,
                "has_seat": rnd.random() < 0.4,
                "ancillaries": rnd.random() * 100,
                "fare": 200 + rnd.random() * 600,
                "baggage_kg": rnd.choice([0, 20, 30]),
                "pnr_size": rnd.choice([1, 1, 2, 4]),
                "children": rnd.choice([0, 0, 0, 1]),
                "infants": 0,
                "is_loyalty_member": member,
                "loyalty_tier_synthetic": rnd.choice(["Blue", "Silver", "Gold", "Platinum"]) if member else None,
                "travel_frequency_band": rnd.choice(["occasional", "regular", "frequent"]),
                "flown_segments_12m": rnd.randint(0, 40),
            }
        )
    return out


@pytest.fixture(scope="module")
def trained() -> tuple[Any, dict[str, Any], Any]:
    from app.ml import reward_pref as rp

    history = rp.generate_history(_passengers())
    booster, card = rp.train(history)
    return rp, history, rp.RewardModel(booster, card)


def test_synthetic_history_is_deterministic_and_labelled(trained: tuple[Any, dict[str, Any], Any]) -> None:
    rp, history, model = trained
    again = rp.generate_history(_passengers())
    assert (again["accepted"] == history["accepted"]).all()
    assert model.card["synthetic_training_data"] is True
    assert "SIMULATED" in model.card["warning"]
    assert model.summary()["synthetic_training_data"] is True
    miles_rows = history["reward_type"] == rp.CATEGORIES["reward_type"].index(rw.MILES)
    assert (history["is_member"][miles_rows] > 0).all()  # miles are only offered to loyalty members


def test_model_beats_the_baselines_on_held_out_passengers(trained: tuple[Any, dict[str, Any], Any]) -> None:
    _, _, model = trained
    m = model.card["metrics_on_held_out_passengers"]
    assert m["auc"] > m["baseline_type_average"]["auc"] + 0.03
    assert m["auc"] > m["baseline_proxy_rules"]["auc"]
    assert m["brier"] < m["baseline_type_average"]["brier"]


def test_model_learns_who_takes_which_reward(trained: tuple[Any, dict[str, Any], Any]) -> None:
    _rp, _, model = trained
    base = _passengers(1)[0] | {"has_meal": False, "children": 0, "has_seat": False}
    buyer = base | {"has_meal": True}
    p = model.accept([base, buyer], [(rw.MEAL, 50.0, 60.0)] * 2)
    assert p[1] > p[0] + 0.1  # a passenger who bought a meal takes a meal voucher more often
    seat = base | {"has_seat": True, "fare_family_synthetic": "Ultimate"}
    q = model.accept([base, seat], [(rw.LOUNGE, 120.0, 60.0)] * 2)
    assert q[1] > q[0] + 0.1
    casual = base | {"is_loyalty_member": True, "loyalty_tier_synthetic": "Blue", "travel_frequency_band": "occasional"}
    loyal = base | {"is_loyalty_member": True, "loyalty_tier_synthetic": "Gold", "travel_frequency_band": "frequent"}
    r = model.accept([casual, loyal], [(rw.MILES, 200.0, 60.0)] * 2)
    assert r[1] > r[0] + 0.05  # a frequent Gold member takes miles more often than a casual Blue one


def test_plan_uses_the_model_and_still_respects_the_budget(trained: tuple[Any, dict[str, Any], Any]) -> None:
    _, _, model = trained
    pax = []
    for i, p in enumerate(_passengers(80)):
        pax.append(
            p
            | {
                "pnr": f"P{i:05d}",
                "customer_key": f"{i:016x}",
                "pax_type": "AD",
                "origin": "SHJ",
                "destination": "CAI",
                "fare": p["fare"],
                "revenue_type": "REV",
                "passenger_id": f"PAX{i}",
                "ssr_code": None,
                "infants": 0,
                "children": 0,
            }
        )
    people = rw.people_for(pax, {}, "DELAY", 200, {}, model)
    assert all(p.accept for p in people)
    plan = rw.recommend(people, 2500)
    assert plan["planned_spend_aed"] <= 2500
    top = next(r for r in plan["rows"] if r["reward"])
    assert 0 < top["reward"]["acceptance"] <= 1
    assert top["why"][0].startswith("predicted acceptance")
