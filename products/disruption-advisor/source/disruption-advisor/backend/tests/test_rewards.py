"""Phase 5 reward recommendation (ADR 0012): severity, proxy preferences, eligibility and the budget fit."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.engine import rewards as rw
from tests.ops_fixture import F1


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
                "loyalty_tier_synthetic": rnd.choice(["Basic", "Silver", "Gold", "Platinum"]) if member else None,
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
    casual = base | {
        "is_loyalty_member": True,
        "loyalty_tier_synthetic": "Basic",
        "travel_frequency_band": "occasional",
    }
    loyal = base | {"is_loyalty_member": True, "loyalty_tier_synthetic": "Gold", "travel_frequency_band": "frequent"}
    r = model.accept([casual, loyal], [(rw.MILES, 200.0, 60.0)] * 2)
    assert r[1] > r[0] + 0.05  # a frequent Gold member takes miles more often than a casual Basic one


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


def test_a_reward_never_repeats_what_the_care_plan_already_gives() -> None:
    rules = rw.RewardRules()
    plain = person(1, sev=70.0)
    fed = person(2, sev=70.0)
    fed.care_meals = 3
    housed = person(3, sev=70.0)
    housed.care_hotel = True
    kinds = {
        k: {o.kind for o in rw.eligible_options(p, rules)}
        for k, p in (("plain", plain), ("fed", fed), ("housed", housed))
    }
    assert rw.MEAL in kinds["plain"]
    assert rw.LOUNGE in kinds["plain"]
    assert rw.MEAL not in kinds["fed"]  # care already gives meal vouchers
    assert rw.LOUNGE not in kinds["housed"]  # care already gives a hotel room
    plan = rw.recommend([plain, fed, housed], 10_000)
    meals = [r for r in plan["rows"] if r["reward"] and r["reward"]["type"] == rw.MEAL]
    assert all(r["pnr"] == plain.pnr for r in meals)


# ------------------------------------------------------------------------------ the reward API (needs Docker)
def _scenario(client: TestClient, auth: dict[str, str], kind: str = "DELAY") -> dict[str, Any]:
    body: dict[str, Any] = {"kind": kind, "flight_id": F1}
    if kind == "DELAY":
        body["delay_minutes"] = 150
    created = client.post("/api/v1/scenarios", headers=auth, json=body)
    assert created.status_code == 201
    return dict(created.json())


def test_reward_plan_api_stays_within_the_budget_and_covers_the_flight(
    client: TestClient, auth: dict[str, str]
) -> None:
    scenario = _scenario(client, auth)
    plan = client.post(f"/api/v1/scenarios/{scenario['id']}/rewards", headers=auth, json={"budget_aed": 3000}).json()
    assert plan["budget_aed"] == 3000
    spent = sum(r["reward"]["cost_aed"] for r in plan["rows"] if r["reward"])
    assert spent == plan["planned_spend_aed"] <= 3000
    assert plan["passengers"] == len(plan["rows"]) > 0  # every passenger of the flight is considered
    assert plan["rewarded"] == sum(1 for r in plan["rows"] if r["reward"])
    assert plan["preference_model"]["kind"] in {"proxy rules", "trained model"}
    assert plan["disruption"]["label"] in {"minor", "moderate", "major", "severe"}
    assert plan["assumptions"]
    bigger = client.post(
        f"/api/v1/scenarios/{scenario['id']}/rewards", headers=auth, json={"budget_aed": 1_000_000}
    ).json()
    assert bigger["planned_spend_aed"] >= plan["planned_spend_aed"]
    assert bigger["planned_spend_aed"] == bigger["ideal_spend_aed"]  # a generous budget buys the whole plan
    again = client.post(f"/api/v1/scenarios/{scenario['id']}/rewards", headers=auth, json={"budget_aed": 3000}).json()
    assert again["rows"] == plan["rows"]  # deterministic


def test_reward_plan_api_never_repeats_what_the_care_plan_gives(client: TestClient, auth: dict[str, str]) -> None:
    for kind in ("DELAY", "CANCEL"):
        scenario = _scenario(client, auth, kind)
        care = {(p["pnr"], p["customer_key"]): p["care"] for p in scenario["result"]["passengers"]}
        plan = client.post(
            f"/api/v1/scenarios/{scenario['id']}/rewards", headers=auth, json={"budget_aed": 1_000_000}
        ).json()
        for row in plan["rows"]:
            given = care.get((row["pnr"], row["customer_key"]))
            kind_given = row["reward"]["type"] if row["reward"] else None
            if given and given["meals"] > 0:
                assert kind_given != rw.MEAL
            if given and given["hotel"]:
                assert kind_given != rw.LOUNGE


def test_reward_plan_api_validates_and_needs_a_sign_in(client: TestClient, auth: dict[str, str]) -> None:
    scenario = _scenario(client, auth)
    url = f"/api/v1/scenarios/{scenario['id']}/rewards"
    assert client.post(url, headers=auth, json={"budget_aed": -1}).status_code == 422
    assert client.post(url, headers=auth, json={"budget_aed": 10_000_000}).status_code == 422
    assert client.post(url, headers=auth, json={}).status_code == 422
    assert client.post(url, headers=auth, json={"budget_aed": 100, "extra": 1}).status_code == 422
    assert client.post(url, json={"budget_aed": 100}).status_code == 401
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (
        client.post(f"/api/v1/scenarios/{unknown}/rewards", headers=auth, json={"budget_aed": 100}).status_code == 404
    )
    zero = client.post(url, headers=auth, json={"budget_aed": 0}).json()
    assert zero["rewarded"] == 0
    assert zero["planned_spend_aed"] == 0


def test_reward_plan_approval_goes_to_the_audit_log(client: TestClient, auth: dict[str, str]) -> None:
    scenario = _scenario(client, auth)
    decision = client.post(
        f"/api/v1/scenarios/{scenario['id']}/decisions",
        headers=auth,
        json={"target": "rewards:3000", "action": "APPROVE", "comment": "within the goodwill budget"},
    )
    assert decision.status_code == 201
    logged = client.get(f"/api/v1/scenarios/{scenario['id']}/decisions", headers=auth).json()
    assert [(d["target"], d["action"]) for d in logged] == [("rewards:3000", "APPROVE")]
    assert logged[0]["decided_by"] == "pcu (PCU)"


# ------------------------------------------------------------------------------ ingest stage 4 on the small fixture
def test_stage_four_writes_a_labelled_model_and_the_history(tmp_path: Path) -> None:
    from app.ml import reward_pref as rp
    from tests.ops_fixture import write_ops

    ops = write_ops(tmp_path)
    assert len(rp.load_passengers(ops)) > 0
    out = rp.run(ops)
    assert out["offers"] > 0
    card = json.loads((ops / "reward_model_card.json").read_text())
    assert card["synthetic_training_data"] is True
    assert "SIMULATED" in card["warning"]
    assert (ops / "reward_history_synthetic.parquet").exists()
    model = rp.RewardModel.load(ops)
    assert model is not None
    probs = model.accept(rp.load_passengers(ops)[:3], [(rw.MEAL, 50.0, 60.0)] * 3)
    assert len(probs) == 3
    assert all(0.0 < float(p) < 1.0 for p in probs)
    assert rp.RewardModel.load(tmp_path / "nowhere") is None  # no model file: the plan falls back to the proxy rules


def test_a_family_account_lifts_the_loyalty_tier_the_reward_models_see() -> None:
    from app.ml import reward_pref as rp

    child = {"loyalty_tier_synthetic": None, "family_account_synthetic": True, "family_tier_synthetic": "Gold"}
    assert rp.effective_tier(child) == "Gold"  # a child on a Gold family account is not ranked below the head
    own_better = {
        "loyalty_tier_synthetic": "Platinum",
        "family_account_synthetic": True,
        "family_tier_synthetic": "Basic",
    }
    assert rp.effective_tier(own_better) == "Platinum"  # the better of the two
    no_account = {
        "loyalty_tier_synthetic": "Silver",
        "family_account_synthetic": False,
        "family_tier_synthetic": "Gold",
    }
    assert rp.effective_tier(no_account) == "Silver"
    assert rp.effective_tier({}) is None
    assert rp.features_of(child)["loyalty_tier"] > rp.features_of({})["loyalty_tier"]
    lifted, _ = rw.preferences({**child, "is_loyalty_member": False})
    plain, _ = rw.preferences({"is_loyalty_member": False})
    assert lifted[rw.TICKET] > plain[rw.TICKET]  # the proxy rules see the lifted tier too
    assert lifted[rw.MILES] == 0.0  # miles stay for members in their own right


# ------------------------------------------------------------------------------ upcoming segments (connection, return)
def _seg(flight: str, origin: str, dest: str, std: datetime) -> dict[str, Any]:
    return {"flight_number": flight, "origin": origin, "destination": dest, "std": std}


T0 = datetime(2026, 11, 21, 6, 0)


def test_upcoming_summary_tells_a_connection_from_a_return() -> None:
    connection = _seg("G9201", "SHJ", "CAI", T0 + timedelta(hours=5))
    ret = _seg("G9150", "CAI", "KHI", T0 + timedelta(days=7))
    later = rw.upcoming_summary([ret, connection], "KHI", "SHJ", T0)
    assert later["count"] == 2
    assert later["connection"] is True  # the NEXT segment leaves from where this flight lands, within 24 h
    assert later["return"] is True  # a later segment comes back to this flight's origin
    assert later["next"] == {"flight_number": "G9201", "route": "SHJ-CAI", "std": connection["std"].isoformat()}
    # a flight three days later from the arrival station is later travel, not a connection
    far = rw.upcoming_summary([_seg("G9300", "SHJ", "DEL", T0 + timedelta(days=3))], "KHI", "SHJ", T0)
    assert far["count"] == 1
    assert far["connection"] is False
    assert far["return"] is False
    # earlier segments and this flight itself do not count; nothing booked after
    assert rw.upcoming_summary([_seg("G9001", "SHJ", "KHI", T0 - timedelta(days=1))], "KHI", "SHJ", T0) == {
        "count": 0,
        "connection": False,
        "return": False,
        "next": None,
    }


def test_a_cancellation_hurts_more_when_the_journey_continues() -> None:
    plain, _ = rw.severity(None, True, False, None, False)
    with_connection, reasons = rw.severity(None, True, False, None, False, connection=True)
    with_both, more = rw.severity(None, True, False, None, False, connection=True, returning=True)
    assert plain < with_connection < with_both <= 100
    assert any("onward connection" in r for r in reasons)
    assert any("return flight" in r for r in more)
    # in a delay the connection is judged by the missed-connection rule, so the booking alone adds nothing
    assert (
        rw.severity(150, False, False, None, False, connection=True, returning=True)[0]
        == rw.severity(150, False, False, None, False)[0]
    )


def test_flights_coming_up_make_vouchers_miles_tickets_and_lounges_more_likely() -> None:
    member = {"is_loyalty_member": True, "travel_frequency_band": "regular"}
    plain, _ = rw.preferences(member)
    coming, why = rw.preferences({**member, "upcoming_segments": 2, "has_connection": True, "has_return": True})
    for kind in (rw.VOUCHER, rw.MILES, rw.TICKET, rw.LOUNGE):
        assert coming[kind] > plain[kind]
    assert "has a flight coming up to use it on" in why[rw.VOUCHER]
    assert "has a return flight booked" in why[rw.TICKET]
    assert "connecting through the hub" in why[rw.LOUNGE]
    assert coming[rw.MEAL] == plain[rw.MEAL]


def test_cancelled_passengers_with_a_connection_or_return_get_a_higher_severity_in_the_plan() -> None:
    def pax(i: int) -> dict[str, Any]:
        return {
            "pnr": f"P{i}", "customer_key": f"{i:016x}", "pax_type": "AD", "origin": "KHI", "destination": "SHJ",
            "fare": 400.0, "revenue_type": "REV", "passenger_id": f"PAX{i}", "ssr_code": None, "infants": 0,
            "children": 0, "ancillaries": 20.0, "pnr_size": 1, "fare_family_synthetic": "Value",
            "is_loyalty_member": False,
        }  # fmt: skip

    people = [pax(1), pax(2), pax(3)]
    keys = [(p["pnr"], p["customer_key"]) for p in people]
    up = {
        keys[0]: rw.upcoming_summary([_seg("G9201", "SHJ", "CAI", T0 + timedelta(hours=5))], "KHI", "SHJ", T0),
        keys[1]: rw.upcoming_summary([_seg("G9150", "SHJ", "KHI", T0 + timedelta(days=7))], "KHI", "SHJ", T0),
    }
    built = rw.people_for(people, {}, "CANCEL", None, {}, None, up)
    by_id = {p.passenger_id: p for p in built}
    assert by_id["PAX1"].severity > by_id["PAX3"].severity  # connection booked
    assert by_id["PAX2"].severity > by_id["PAX3"].severity  # return booked
    assert by_id["PAX1"].severity > by_id["PAX2"].severity  # a broken connection costs more than a return to re-plan
    assert by_id["PAX1"].has_connection
    assert by_id["PAX2"].has_return
    assert not by_id["PAX3"].upcoming_count
    plan = rw.recommend(built, 100_000)
    row = next(r for r in plan["rows"] if r["passenger_id"] == "PAX1")
    assert row["upcoming"]["connection"] is True
    assert row["upcoming"]["next"]["flight_number"] == "G9201"
    assert any("onward connection" in x for x in row["severity_reasons"])


def test_the_reward_api_reports_each_passengers_upcoming_flights(client: TestClient, auth: dict[str, str]) -> None:
    scenario = _scenario(client, auth, "CANCEL")
    plan = client.post(f"/api/v1/scenarios/{scenario['id']}/rewards", headers=auth, json={"budget_aed": 5000}).json()
    assert all({"count", "connection", "return", "next"} <= set(r["upcoming"]) for r in plan["rows"])
    linked = [r for r in plan["rows"] if r["upcoming"]["connection"]]
    assert linked  # the fixture's cancelled flight has passengers with an onward flight
    assert all(any("onward connection" in x for x in r["severity_reasons"]) for r in linked)
