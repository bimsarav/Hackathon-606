"""Phase 3 agent (ADR 0010): the tool-use loop with a scripted fake Claude client, privacy of every request, the
deterministic planner fallback, and the agent-run API."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.runner import Limits, Step, run_agent
from app.agent.tools import TOOLS, AgentTools, ToolError
from app.config import Settings
from app.engine.explain import Explainer
from app.engine.scenarios import Context
from app.engine.store import OpsStore
from tests.ops_fixture import F1, F2, PAX, t, write_ops

# Personal data in the fixture that must never reach the AI service.
PRIVATE = sorted(
    {p["pnr"] for p in PAX}
    | {p["customer_key"] for p in PAX}
    | {p["passenger_id"] for p in PAX}
    | {p["passport_number_synthetic"] for p in PAX}
)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Context:
    ops = write_ops(tmp_path_factory.mktemp("data"))
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    return Context(OpsStore(ops), settings, Explainer("", settings.ai_model, "low", 1))


def block(kind: str, **kw: Any) -> SimpleNamespace:
    return SimpleNamespace(type=kind, **kw)


def turn(*blocks: SimpleNamespace, stop: str = "tool_use") -> SimpleNamespace:
    usage = SimpleNamespace(
        input_tokens=1000, output_tokens=100, cache_read_input_tokens=800, cache_creation_input_tokens=0
    )
    return SimpleNamespace(content=list(blocks), stop_reason=stop, usage=usage)


def call(n: int, name: str, args: dict[str, Any]) -> SimpleNamespace:
    return block("tool_use", id=f"tu_{n}", name=name, input=args)


def note(text: str) -> SimpleNamespace:
    return block("thinking", thinking=text, signature="sig")


class FakeClient:
    """Plays back scripted responses and records every request."""

    def __init__(self, script: list[SimpleNamespace]) -> None:
        self.script = list(script)
        self.requests: list[str] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw: Any) -> SimpleNamespace:
        self.requests.append(json.dumps(kw, default=lambda o: vars(o) if hasattr(o, "__dict__") else str(o)))
        return self.script.pop(0)


def good_script(option_key: str) -> list[SimpleNamespace]:
    return [
        turn(note("Checking the flight and its predicted delay."), call(1, "flight_status", {"flight_id": F1})),
        turn(note("Assessing a 150-minute delay."), call(2, "assess_delay", {"flight_id": F1, "delay_minutes": 150})),
        turn(call(3, "compare_strategies", {}), call(4, "passenger_impact", {"option_key": option_key})),
        turn(
            note("Recommending the option that protects every passenger."),
            call(
                5,
                "submit_recommendation",
                {
                    "option_key": option_key,
                    "strategy": "protect_passengers",
                    "reasons": ["Everyone keeps a seat.", "Costs less than a swap."],
                    "risks": ["Two round-trip flights are cancelled."],
                    "checks": ["Crew control confirms the new pairing."],
                },
            ),
        ),
    ]


def test_tool_schemas_are_strict_and_use_only_supported_keywords() -> None:
    allowed = {"type", "properties", "required", "additionalProperties", "items", "enum", "anyOf", "description"}

    def walk(schema: dict[str, Any]) -> None:
        assert set(schema) <= allowed, set(schema) - allowed
        for sub in schema.get("properties", {}).values():
            walk(sub)
        for sub in schema.get("anyOf", []):
            walk(sub)
        if "items" in schema:
            walk(schema["items"])

    for tool in TOOLS:
        assert tool["strict"] is True
        assert tool["input_schema"]["additionalProperties"] is False
        walk(tool["input_schema"])


def test_ai_loop_recommends_an_engine_option_with_a_trace(ctx: Context) -> None:
    key = f"cancel:{F2}"
    client = FakeClient(good_script(key))
    seen: list[Step] = []
    outcome = run_agent(client, AgentTools(ctx), F1, None, None, "", Limits(), seen.append)
    assert outcome.source == "ai:claude-opus-5-5"
    assert outcome.final["option_key"] == key
    assert outcome.final["strategy"] == "protect_passengers"
    assert [s.tool for s in outcome.steps] == [
        "flight_status",
        "assess_delay",
        "compare_strategies",
        "passenger_impact",
        "submit_recommendation",
    ]
    assert seen == outcome.steps
    assert outcome.steps[0].note == "Checking the flight and its predicted delay."
    assert outcome.usage["input_tokens"] == 4000
    first = json.loads(client.requests[0])
    assert first["thinking"] == {"type": "adaptive", "display": "updates"}
    assert first["output_config"] == {"effort": "medium"}
    assert first["fallbacks"] == "default"
    assert "tool_choice" not in first  # forced tool use is rejected on Opus 5.5


def test_no_personal_data_is_sent_to_the_ai_service(ctx: Context) -> None:
    client = FakeClient(good_script(f"cancel:{F2}"))
    run_agent(client, AgentTools(ctx), F1, 150, "protect_passengers", "Busy evening at SHJ.", Limits(), lambda s: None)
    assert len(client.requests) == 4
    for request in client.requests:
        leaked = [value for value in PRIVATE if value in request]
        assert leaked == []


def test_an_option_the_engine_did_not_produce_is_refused_and_can_be_corrected(ctx: Context) -> None:
    script = good_script("absorb")
    bad = call(
        9,
        "submit_recommendation",
        {"option_key": "swap:INVENTED", "strategy": "lowest_cost", "reasons": ["a", "b"], "risks": [], "checks": []},
    )
    script.insert(3, turn(bad))
    client = FakeClient(script)
    outcome = run_agent(client, AgentTools(ctx), F1, 150, None, "", Limits(), lambda s: None)
    assert outcome.source.startswith("ai:")
    assert outcome.final["option_key"] == "absorb"
    refused = next(s for s in outcome.steps if s.input.get("option_key") == "swap:INVENTED")
    assert refused.error is True
    assert "not one the engine produced" in refused.summary


def test_without_an_api_key_the_planner_recommends_the_strategy_pick(ctx: Context) -> None:
    outcome = run_agent(None, AgentTools(ctx), F1, 150, "least_delay", "", Limits(), lambda s: None)
    assert outcome.source == "planner"
    assert "no API key" in (outcome.fallback_reason or "")
    tools = AgentTools(ctx)
    picks = {
        s["key"]: s["pick"] for s in tools.run("assess_delay", {"flight_id": F1, "delay_minutes": 150})["strategies"]
    }
    assert outcome.final["option_key"] == picks["least_delay"]
    assert outcome.final["strategy"] == "least_delay"
    assert [s.tool for s in outcome.steps][-1] == "submit_recommendation"
    assert len(outcome.final["reasons"]) >= 2


def test_planner_uses_the_predicted_delay_when_none_is_given(ctx: Context) -> None:
    outcome = run_agent(None, AgentTools(ctx), F1, None, None, "", Limits(), lambda s: None)
    assert outcome.final["delay_minutes"] >= 15
    assert outcome.final["strategy"] == "lowest_cost"


def test_refusal_and_step_limit_fall_back_and_keep_the_ai_steps(ctx: Context) -> None:
    refused = FakeClient([turn(call(1, "flight_status", {"flight_id": F1})), turn(stop="refusal")])
    outcome = run_agent(refused, AgentTools(ctx), F1, 150, None, "", Limits(), lambda s: None)
    assert outcome.source == "planner"
    assert outcome.fallback_reason == "the AI declined the request"
    assert outcome.steps[0].tool == "flight_status"
    assert [s.n for s in outcome.steps] == list(range(1, len(outcome.steps) + 1))

    looping = FakeClient([turn(call(i, "flight_status", {"flight_id": F1})) for i in range(10)])
    limited = run_agent(looping, AgentTools(ctx), F1, 150, None, "", Limits(max_tool_calls=3), lambda s: None)
    assert limited.source == "planner"
    assert "tool-call limit" in (limited.fallback_reason or "")


def test_tool_inputs_are_validated(ctx: Context) -> None:
    tools = AgentTools(ctx)
    with pytest.raises(ToolError):
        tools.run("assess_delay", {"flight_id": F1, "delay_minutes": 5})
    with pytest.raises(ToolError):
        tools.run("flight_status", {"flight_id": "DROP TABLE"})
    with pytest.raises(ToolError):
        tools.run("passenger_impact", {"option_key": "absorb"})  # nothing assessed yet
    with pytest.raises(ToolError):
        tools.run("delete_everything", {})
    rotation = tools.run("aircraft_rotation", {"flight_id": F1})
    assert [f["flight_number"] for f in rotation["flights"]] == ["G9001", "G9002", "G9003", "G9004"]
    assert rotation["flights"][1]["ground_minutes_before"] == 45
    found = tools.run("find_flights", {"text": "G9001", "day": None})
    assert [f["flight_id"] for f in found["flights"]] == [F1]
    assert isinstance(tools.run("watchlist", {"limit": 5})["flights"], list)


def test_agent_run_api_saves_a_scenario_for_approval(client: TestClient, auth: dict[str, str]) -> None:
    started = client.post("/api/v1/agent/runs", headers=auth, json={"flight_id": F1, "delay_minutes": 150})
    assert started.status_code == 202
    run = client.get(f"/api/v1/agent/runs/{started.json()['id']}", headers=auth).json()
    assert run["status"] == "DONE"
    assert run["source"] == "planner"  # tests run without an API key
    assert run["trace"][-1]["tool"] == "submit_recommendation"
    scenario = client.get(f"/api/v1/scenarios/{run['scenario_id']}", headers=auth).json()
    agent = scenario["result"]["agent"]
    assert agent["run_id"] == run["id"]
    assert scenario["result"]["selected_key"] == agent["option_key"] == run["recommendation"]["option_key"]
    listed = client.get("/api/v1/agent/runs", headers=auth).json()
    assert listed[0]["id"] == run["id"]
    assert "trace" not in listed[0]


def test_agent_run_api_validates_input(client: TestClient, auth: dict[str, str]) -> None:
    assert client.post("/api/v1/agent/runs", json={"flight_id": F1}).status_code == 401
    missing = client.post("/api/v1/agent/runs", headers=auth, json={"flight_id": "G9999_202611210000"})
    assert missing.status_code == 404
    bad = client.post("/api/v1/agent/runs", headers=auth, json={"flight_id": F1, "strategy": "fastest"})
    assert bad.status_code == 422
    assert client.get("/api/v1/agent/runs/00000000-0000-0000-0000-000000000000", headers=auth).status_code == 404
