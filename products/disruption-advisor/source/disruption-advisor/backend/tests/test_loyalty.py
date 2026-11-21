"""Loyalty per the airline's loyalty sample: tier ladder and priority, family accounts."""

from typing import Any

import pytest

from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_cancellation
from app.engine.store import OpsStore
from app.ingest.build import LOYALTY_PRIORITY
from tests.ops_fixture import X1, t, write_ops


@pytest.fixture(scope="module")
def rows(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, Any]]:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    ctx = Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))
    return {r["customer_key"]: r for r in analyse_cancellation(ctx, X1, priority.DEFAULT_WEIGHTS)["passengers"]}


def test_tier_ladder_and_priority_follow_the_airline_sample() -> None:
    assert (
        LOYALTY_PRIORITY
        == priority.LOYALTY_PRIORITY
        == {
            "Basic": "Lowest",
            "Silver": "Low",
            "Gold": "Medium",
            "Platinum": "High",
        }
    )
    values = [priority.TIER_VALUE[x] for x in (None, "Basic", "Silver", "Gold", "Platinum")]
    assert values == sorted(values)
    assert values[1] > values[0]  # enrolment alone counts above a non-member
    assert "Blue" not in priority.TIER_VALUE


def test_family_account_members_travel_on_the_head_of_family_tier(rows: dict[str, dict[str, Any]]) -> None:
    head, spouse = rows["b0000001"], rows["b0000002"]  # PNRB: Silver head, non-member spouse, lap infant
    assert head["loyalty_effective_tier"] == spouse["loyalty_effective_tier"] == "Silver"
    assert head["loyalty_via_family"] is False
    assert spouse["loyalty_via_family"] is True
    assert spouse["family_account"] is True
    assert head["family_head"] is True
    assert spouse["contributions"]["loyalty"] == head["contributions"]["loyalty"] > 0
    assert "Loyalty Silver (priority Low) via the family account" in spouse["reason"]


def test_member_and_non_member_scoring(rows: dict[str, dict[str, Any]]) -> None:
    gold, plain = rows["g0000001"], rows["f0000001"]
    assert gold["loyalty_effective_priority"] == "Medium"
    assert gold["loyalty_points"] == 132000
    assert gold["contributions"]["loyalty"] > 0
    assert plain["loyalty_effective_tier"] is None
    assert plain["contributions"]["loyalty"] == 0
    assert "Loyalty" not in plain["reason"]
