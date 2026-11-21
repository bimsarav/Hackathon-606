"""Engine rules on the hand-made network (tests/ops_fixture.py)."""

from datetime import timedelta
from pathlib import Path

import pytest

from app.config import Settings
from app.engine import priority
from app.engine.cost import eu261_compensation_eur, great_circle_km
from app.engine.explain import Explainer
from app.engine.network import absorb_delay, propagate, swap_rotations
from app.engine.scenarios import Context, ScenarioError, analyse_cancellation, analyse_delay
from app.engine.store import Leg, OpsStore
from tests.ops_fixture import F1, X1, t, write_ops


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Context:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    return Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))


def _legs(ctx: Context, tail: str) -> list[Leg]:
    return ctx.store.tail_legs(tail, t(0), t(0) + timedelta(days=3))


def test_delay_propagates_until_turn_slack_absorbs_it(ctx: Context) -> None:
    f1, f2, f3, f4 = _legs(ctx, "T1")
    plan = absorb_delay(f1, [f2, f3, f4], timedelta(minutes=150), timedelta(minutes=40))
    delays = [plan.timings[x.flight_id].delay_minutes for x in (f1, f2, f3, f4)]
    # F1 +150 → arrives 12:30 → F2 ready 13:10 (+145) → arrives 16:10 → F3 ready 16:50 (+140) → F4 ready 20:30 (+135)
    assert delays == [150, 145, 140, 135]
    assert plan.total_delay_minutes == 570


def test_propagate_respects_schedule_when_aircraft_is_early(ctx: Context) -> None:
    legs = _legs(ctx, "T2")
    timings = propagate(legs, t(5), timedelta(minutes=40), "T2")
    assert [x.delay_minutes for x in timings] == [0, 0]


def test_swap_moves_the_knock_on_delay_off_the_downstream_rotation(ctx: Context) -> None:
    f1, *rest = _legs(ctx, "T1")
    plan = swap_rotations(f1, rest, timedelta(minutes=150), timedelta(minutes=40), "T2", _legs(ctx, "T2"))
    assert plan is not None
    assert plan.timings[rest[0].flight_id].operated_by == "T2"
    assert plan.timings[rest[0].flight_id].delay_minutes == 0  # T2 was on the ground at SHJ since 07:00
    # The late T1 now flies T2's SHJ-BKK at 11:00: ready 13:10 → +130.
    g2 = _legs(ctx, "T2")[1]
    assert plan.timings[g2.flight_id].operated_by == "T1"
    assert plan.timings[g2.flight_id].delay_minutes == 130
    assert (
        plan.total_delay_minutes
        < absorb_delay(f1, rest, timedelta(minutes=150), timedelta(minutes=40)).total_delay_minutes
    )


def test_swap_rejected_when_candidate_is_elsewhere(ctx: Context) -> None:
    """A candidate whose rotation does not touch SHJ at the takeover time cannot take over."""
    f1, *rest = _legs(ctx, "T1")
    lhe_based = [x for x in _legs(ctx, "T1") if x.origin == "LHE"]
    assert swap_rotations(f1, rest, timedelta(minutes=150), timedelta(minutes=40), "TX", lhe_based) is None


def test_delay_scenario_recommends_the_cheapest_option_and_finds_misconnects(ctx: Context) -> None:
    result = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)
    keys = [o["key"] for o in result["options"]]
    assert "absorb" in keys
    assert "swap:T2" in keys
    assert "swap:T4" in keys
    assert result["recommended_key"] != "absorb"  # a swap or consolidation beats carrying 570 delay minutes
    costs = [o["cost_aed"] for o in result["options"]]
    assert costs == sorted(costs)
    # F1 arrives 12:30; H1 departs 11:30 → both connecting passengers miss it (MCT 55 from the hub table).
    missed = result["misconnections"]
    assert {m["customer_key"] for m in missed} == {"c0000001", "c0000002"}
    assert all(m["mct_minutes"] == 55 for m in missed)
    assert result["explanation"]["source"] == "template"


def test_unknown_flight_is_reported(ctx: Context) -> None:
    with pytest.raises(ScenarioError):
        analyse_delay(ctx, "G9999_202611210000", 60, priority.DEFAULT_WEIGHTS)


def test_cancellation_protects_care_tier_first_and_keeps_bookings_together(ctx: Context) -> None:
    result = analyse_cancellation(ctx, X1, priority.DEFAULT_WEIGHTS)
    rows = result["passengers"]
    assert len(rows) == 10  # 11 on the booking list; the lap infant travels with an adult
    # Tier 1 (wheelchair + family with an infant: 3 seats) comes first; the score orders within the tier.
    assert [r["tier"] for r in rows[:3]] == [1, 1, 1]
    assert "WCHR" in {r["ssr"] for r in rows[:3]}
    assert rows[0]["tier"] == 1
    family = [r for r in rows if r["pnr"] == "PNRB"]
    assert {r["tier"] for r in family} == {1}  # travelling with an infant
    assert len({r["assigned_flight_id"] for r in family}) == 1  # kept together
    assert rows[-1]["non_revenue"] is True
    assert rows[-1]["assigned_flight_id"] is None
    assert result["rebooking"]["protected"] + result["rebooking"]["unprotected"] == 10
    assert result["rebooking"]["protected"] <= 7  # 2 + 5 free seats
    assert result["solver_status"] == "OPTIMAL"


def test_weights_change_the_order_but_never_cross_tiers(ctx: Context) -> None:
    loyalty_only = dict.fromkeys(priority.ATTRIBUTES, 0.0) | {"loyalty": 100.0}
    rows = analyse_cancellation(ctx, X1, loyalty_only)["passengers"]
    tiers = [r["tier"] for r in rows if not r["non_revenue"]]
    assert tiers == sorted(tiers)
    tier3 = [r for r in rows if r["tier"] == 3 and not r["non_revenue"]]
    assert tier3[0]["loyalty_tier"] == "Gold"


def test_eu261_bands() -> None:
    assert eu261_compensation_eur("AE", "DE", 5000) == 0  # departure outside the EU
    assert eu261_compensation_eur("DE", "AE", 1200) == 250
    assert eu261_compensation_eur("DE", "AE", 3000) == 400
    assert eu261_compensation_eur("DE", "AE", 5000) == 600
    assert eu261_compensation_eur("DE", "ES", 4000) == 400  # intra-EU over 1,500 km
    assert 2400 < great_circle_km(25.33, 55.52, 41.27, 28.75) < 3200  # SHJ-IST


def test_store_loads_and_reports_ready(tmp_path: Path) -> None:
    store = OpsStore(write_ops(tmp_path))
    assert store.ready()
    assert store.mct_minutes("KHI", "SHJ", "CAI", default=45) == 55
    assert store.mct_minutes("DOH", "SHJ", "BKK", default=45) == 45


def test_explanations_are_short_and_plain(ctx: Context) -> None:
    delay = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)
    cancel = analyse_cancellation(ctx, X1, priority.DEFAULT_WEIGHTS)
    for text in (delay["explanation"]["text"], cancel["explanation"]["text"]):
        assert len(text.split()) <= 70
        assert " leg" not in text
        assert "misconnect" not in text


def test_missed_connection_message_names_the_late_inbound_flight(ctx: Context) -> None:
    rows = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)["passengers"]
    assert rows
    assert "G9001 arrived late, so you missed your connection G9301" in rows[0]["message"]


def test_selected_option_drives_the_passenger_plan(ctx: Context) -> None:
    base = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS)
    other = next(o["key"] for o in base["options"] if o["key"] != base["recommended_key"])
    chosen = analyse_delay(ctx, F1, 150, priority.DEFAULT_WEIGHTS, selected_key=other)
    assert chosen["selected_key"] == other
    assert chosen["recommended_key"] == base["recommended_key"]
    assert "not the recommendation" in chosen["explanation"]["text"]
