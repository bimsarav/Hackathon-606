"""Phase 3 (ADR 0011): cancel / consolidate a round trip, passenger KPIs for every option, and strategies."""

from datetime import timedelta
from typing import Any

import pytest

from app.config import Settings
from app.engine import priority
from app.engine import strategy as strategies
from app.engine.explain import Explainer
from app.engine.network import absorb_delay, cancel_round_trip, round_trip_pairs
from app.engine.scenarios import Context, ScenarioError, analyse_delay
from app.engine.store import OpsStore
from tests.ops_fixture import F1, F2, F3, t, write_ops

TURN = timedelta(minutes=40)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Context:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    return Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))


@pytest.fixture(scope="module")
def result(ctx: Context) -> dict[str, Any]:
    return analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)


def test_cancelling_the_round_trip_stops_the_delay_spreading(ctx: Context) -> None:
    f1, *rest = ctx.store.tail_legs("T1", t(0), t(0) + timedelta(days=3))
    absorbed = absorb_delay(f1, rest, timedelta(minutes=150), TURN)
    assert round_trip_pairs(rest, absorbed, f1.std + timedelta(hours=24)) == [0]  # F2/F3 SHJ-LHE-SHJ
    plan = cancel_round_trip(f1, rest, timedelta(minutes=150), TURN, 0)
    assert F2 not in plan.timings
    assert F3 not in plan.timings
    f4 = rest[2].flight_id
    assert plan.timings[f1.flight_id].delay_minutes == 150
    assert plan.timings[f4].delay_minutes == 0  # T1 is back at SHJ at 12:30, F4 leaves at 18:15 on time
    assert plan.total_delay_minutes < absorbed.total_delay_minutes


def test_no_pair_is_offered_when_the_delay_never_reaches_it(ctx: Context) -> None:
    f1, *rest = ctx.store.tail_legs("T1", t(0), t(0) + timedelta(days=3))
    absorbed = absorb_delay(f1, rest, timedelta(minutes=0), TURN)
    assert round_trip_pairs(rest, absorbed, f1.std + timedelta(hours=24)) == []


def test_round_trip_is_consolidated_when_everyone_fits_on_same_route_flights(result: dict[str, Any]) -> None:
    option = next(o for o in result["options"] if o["key"] == f"cancel:{F2}")
    assert option["kind"] == "consolidate"
    assert option["label"].startswith("Consolidate: cancel G9002/G9003")
    assert [c["flight_number"] for c in option["cancelled_flights"]] == ["G9002", "G9003"]
    assert option["cancelled_passengers"] == 10
    assert option["passengers_without_seat"] == 0
    assert option["cost_breakdown"]["cancellation"] > 0
    assert option["misconnects"] == 2  # F1 is still late: its connecting passengers still miss H1


def test_every_option_has_passenger_kpis(result: dict[str, Any]) -> None:
    for o in result["options"]:
        for field in (
            "passengers_rebooked",
            "passengers_without_seat",
            "passenger_delay_minutes",
            "cancelled_passengers",
        ):
            assert isinstance(o[field], int), (o["key"], field)
    absorb = next(o for o in result["options"] if o["key"] == "absorb")
    assert absorb["cancelled_flights"] == []
    assert absorb["kind"] == "absorb"


def test_each_strategy_picks_its_best_option(result: dict[str, Any]) -> None:
    options = {o["key"]: o for o in result["options"]}
    picks = {s["key"]: s["pick"] for s in result["strategies"]}
    assert set(picks) == {"lowest_cost", "protect_passengers", "least_delay"}
    assert options[picks["lowest_cost"]]["cost_aed"] == min(o["cost_aed"] for o in options.values())
    assert options[picks["least_delay"]]["passenger_delay_minutes"] == min(
        o["passenger_delay_minutes"] for o in options.values()
    )
    assert options[picks["protect_passengers"]]["passengers_without_seat"] == min(
        o["passengers_without_seat"] for o in options.values()
    )
    assert result["strategy"] == "lowest_cost"
    assert result["recommended_key"] == picks["lowest_cost"]
    for key, o in options.items():
        assert o["picked_by"] == [s for s, k in picks.items() if k == key]


def test_switching_strategy_changes_the_recommendation_not_the_numbers(ctx: Context, result: dict[str, Any]) -> None:
    other = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS, strategy="least_delay")
    picks = {s["key"]: s["pick"] for s in other["strategies"]}
    assert other["recommended_key"] == picks["least_delay"] == other["options"][0]["key"]
    assert other["selected_key"] == other["recommended_key"]

    def numbers(r: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        return {o["key"]: (o["cost_aed"], o["misconnects"], o["passenger_delay_minutes"]) for o in r["options"]}

    assert numbers(other) == numbers(result)


def test_selecting_the_cancel_option_lists_its_cancelled_passengers(ctx: Context) -> None:
    chosen = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS, selected_key=f"cancel:{F2}")
    groups = {r["group"] for r in chosen["passengers"]}
    assert groups == {"missed_connection", "cancelled"}
    cancelled = [r for r in chosen["passengers"] if r["group"] == "cancelled"]
    assert {r["assigned_flight"] for r in cancelled} == {"G9011", "G9012"}
    assert next(r for r in cancelled if r["pnr"] == "RTA")["assigned_flight"] == "G9011"
    assert chosen["rebooking"]["unprotected"] == 0 or chosen["rebooking"]["protected"] >= 10


def test_unknown_strategy_is_rejected(ctx: Context) -> None:
    with pytest.raises(ScenarioError):
        analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS, strategy="fastest")


def test_ties_are_broken_by_option_key() -> None:
    def opt(key: str) -> dict[str, Any]:
        return {
            "key": key,
            "cost_aed": 100.0,
            "misconnects": 0,
            "total_delay_minutes": 10,
            "legs": [],
            "passengers_without_seat": 0,
            "cancelled_passengers": 0,
            "passenger_delay_minutes": 50,
        }

    options = [opt("swap:B"), opt("absorb"), opt("swap:A")]
    assert strategies.picks(options) == dict.fromkeys(strategies.STRATEGIES, "absorb")
    assert [o["key"] for o in strategies.order(list(reversed(options)), "least_delay")] == [
        "absorb",
        "swap:A",
        "swap:B",
    ]


def test_at_equal_cost_keeping_the_schedule_beats_cancelling() -> None:
    base = {
        "cost_aed": 100.0,
        "misconnects": 0,
        "total_delay_minutes": 10,
        "passengers_without_seat": 0,
        "cancelled_passengers": 0,
        "passenger_delay_minutes": 50,
    }
    swap = {**base, "key": "swap:Z", "cancelled_flights": [], "legs": [{"operated_by": "Z", "scheduled_tail": "T1"}]}
    cancel = {**base, "key": "cancel:A", "cancelled_flights": [{"flight_id": "A"}, {"flight_id": "B"}], "legs": []}
    assert strategies.picks([cancel, swap]) == dict.fromkeys(strategies.STRATEGIES, "swap:Z")
