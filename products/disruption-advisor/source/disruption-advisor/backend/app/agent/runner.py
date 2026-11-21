"""Phase 3 agent loop (ADR 0010): Claude chooses which read-only engine tools to call and recommends one engine
option; a deterministic planner with the same tools answers when the AI is off, fails, refuses or runs out of
budget. Nothing here changes data: the caller saves the outcome as a normal scenario for a person to approve.

The loop is append-only (each assistant turn is passed back unchanged), uses adaptive thinking with progress
updates (`display: "updates"`) for the trace, server-side refusal fallback, and strict tool schemas.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

import anthropic

from app.agent.tools import TOOLS, AgentTools, ToolError, to_json
from app.engine import strategy as strategies

log = logging.getLogger(__name__)

BETAS = ["server-side-fallback-2026-07-01", "thinking-display-updates-2026-08-18"]
SYSTEM = """You are a disruption analyst in an airline operations control centre (OCC) for Air Arabia (G9), hub
Sharjah (SHJ). A controller asks you to look at one flight. Investigate it with the tools, then recommend ONE
recovery option for the controller to review with submit_recommendation.

How to work:
- Start with flight_status. If no delay is given, use the planning delay from the delay risk, else 60 minutes.
- Use assess_delay to get the engine's options, then compare_strategies and passenger_impact for the options that
  matter (usually each strategy's pick). Look at the aircraft rotation if it helps explain the options.
- Recommend an option the engine produced (its key from assess_delay). Prefer the controller's strategy when one is
  given; recommend another strategy's pick only when the figures clearly justify it, and say why.
- Every number you mention must come from a tool result. Never invent flights, times, costs or passengers.
- You only recommend. A person approves or overrides; nothing is executed.
- Before each tool call, write one short sentence for the controller on what you are checking and why.
- Reasons, risks and checks: plain English, one sentence each, no jargon (say "flights", "missed connections").
Finish within about 8 tool calls."""


class MessagesClient(Protocol):
    """The part of the Anthropic client the loop uses (lets tests pass a scripted fake)."""

    @property
    def beta(self) -> Any: ...


@dataclass
class Limits:
    max_tool_calls: int = 12
    timeout_s: float = 120.0
    effort: str = "medium"
    model: str = "claude-opus-5-5"
    max_tokens: int = 16000


@dataclass
class Step:
    n: int
    tool: str
    input: dict[str, Any]
    summary: str
    note: str = ""
    error: bool = False
    ms: int = 0
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


@dataclass
class Outcome:
    source: str  # "ai:<model>" | "planner"
    final: dict[str, Any]
    steps: list[Step]
    fallback_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class AgentStoppedError(RuntimeError):
    """The AI loop could not finish (no key, API error, refusal, budget); the planner takes over."""


def _goal_text(flight_id: str, delay: int | None, strategy: str | None, note: str) -> str:
    parts = [f"Flight: {flight_id}."]
    parts.append(f"Departure delay: {delay} minutes." if delay else "Delay: not given (use the predicted one).")
    parts.append(f"Controller's strategy: {strategies.label(strategy)}." if strategy else "No strategy preference.")
    if note:
        parts.append(f"Controller's note: {note}")
    return " ".join(parts)


def run_ai(
    client: MessagesClient | None,
    tools: AgentTools,
    flight_id: str,
    delay: int | None,
    strategy: str | None,
    note: str,
    limits: Limits,
    on_step: Callable[[Step], None],
    steps: list[Step],
) -> Outcome:
    """Appends to ``steps`` as it goes, so the trace survives when the loop stops early."""
    if client is None:
        raise AgentStoppedError("AI is not configured (no API key)")
    started = time.monotonic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": _goal_text(flight_id, delay, strategy, note)}]
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    nudged = False
    while True:
        remaining = limits.timeout_s - (time.monotonic() - started)
        if remaining <= 5:
            raise AgentStoppedError(f"time limit ({limits.timeout_s:.0f} s) reached")
        try:
            response = client.beta.messages.create(
                model=limits.model,
                max_tokens=limits.max_tokens,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
                thinking={"type": "adaptive", "display": "updates"},
                output_config={"effort": limits.effort},
                cache_control={"type": "ephemeral"},
                betas=BETAS,
                fallbacks="default",
                timeout=remaining,
            )
        except anthropic.APIStatusError as exc:
            raise AgentStoppedError(f"AI service error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise AgentStoppedError("AI service unreachable") from exc
        for k in usage:
            usage[k] += int(getattr(response.usage, k, 0) or 0)
        if response.stop_reason == "refusal":
            raise AgentStoppedError("the AI declined the request")
        if response.stop_reason == "max_tokens":
            raise AgentStoppedError("the AI response was cut off")
        messages.append({"role": "assistant", "content": response.content})  # unchanged (preserved thinking)

        notes = [b.thinking.strip() for b in response.content if b.type == "thinking" and (b.thinking or "").strip()]
        notes += [b.text.strip() for b in response.content if b.type == "text" and b.text.strip()]
        calls = [b for b in response.content if b.type == "tool_use"]
        if not calls:
            if nudged:
                raise AgentStoppedError("the AI stopped without a recommendation")
            nudged = True
            messages.append(
                {"role": "user", "content": "Please finish by calling submit_recommendation with one option key."}
            )
            continue
        results = []
        for i, call in enumerate(calls):
            if len(steps) >= limits.max_tool_calls:
                raise AgentStoppedError(f"tool-call limit ({limits.max_tool_calls}) reached")
            t0 = time.monotonic()
            args = call.input if isinstance(call.input, dict) else {}
            try:
                result = tools.run(call.name, args)
                summary, is_error, content = AgentTools.summary(call.name, result), False, to_json(result)
            except ToolError as exc:
                summary, is_error, content = str(exc), True, f"Error: {exc}"
            step = Step(
                len(steps) + 1,
                call.name,
                args,
                summary,
                note=" ".join(notes) if i == 0 else "",
                error=is_error,
                ms=int((time.monotonic() - t0) * 1000),
            )
            steps.append(step)
            on_step(step)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": is_error})
        if tools.final is not None:
            return Outcome(f"ai:{limits.model}", tools.final, steps, usage=usage)
        messages.append({"role": "user", "content": results})


def run_planner(
    tools: AgentTools,
    flight_id: str,
    delay: int | None,
    strategy: str | None,
    on_step: Callable[[Step], None],
    steps: list[Step] | None = None,
) -> tuple[dict[str, Any], list[Step]]:
    """Deterministic fallback: the same tools in a fixed order; recommends the chosen strategy's pick."""
    steps = list(steps or [])

    def call(name: str, args: dict[str, Any], note: str) -> dict[str, Any]:
        t0 = time.monotonic()
        result = tools.run(name, args)
        step = Step(
            len(steps) + 1,
            name,
            args,
            AgentTools.summary(name, result),
            note=note,
            ms=int((time.monotonic() - t0) * 1000),
        )
        steps.append(step)
        on_step(step)
        return result

    status = call("flight_status", {"flight_id": flight_id}, "Planner: read the flight and its predicted delay.")
    if delay is None:
        delay = (status.get("delay_risk") or {}).get("planning_delay_minutes") or 60
        delay = max(int(delay), 15)
    strategy = strategy or strategies.DEFAULT
    assessed = call(
        "assess_delay", {"flight_id": flight_id, "delay_minutes": delay}, f"Planner: assess a {delay}-minute delay."
    )
    call("compare_strategies", {}, "Planner: compare the strategies' picks.")
    pick = next(s["pick"] for s in assessed["strategies"] if s["key"] == strategy)
    impact = call(
        "passenger_impact", {"option_key": pick}, f"Planner: passenger impact of the {strategies.label(strategy)} pick."
    )
    option = next(o for o in assessed["options"] if o["key"] == pick)
    others = [s for s in assessed["strategies"] if s["key"] != strategy and s["pick"] != pick]
    reasons = [
        f"It is the {strategies.label(strategy).lower()} option among {len(assessed['options'])} the engine compared.",
        f"Estimated cost AED {option['cost_aed']:,}, {option['missed_connections']} missed connections, "
        f"{option['passengers_without_seat']} passengers without a seat.",
    ]
    if others:
        reasons.append(
            "Other strategies would pick " + ", ".join(f"{s['pick']} ({s['label'].lower()})" for s in others) + "."
        )
    risks = []
    if impact["without_seat"]:
        risks.append(f"{impact['without_seat']} passengers have no seat within the rebooking window.")
    if option["cancelled_flights"]:
        risks.append(f"Cancels {', '.join(option['cancelled_flights'])}; revenue loss is not counted.")
    checks = ["Crew control confirms the plan is legal for the crews (no crew data in the tool)."]
    if option["kind"] == "swap":
        checks.append("Maintenance and station confirm the swap aircraft is serviceable and ready.")
    call(
        "submit_recommendation",
        {"option_key": pick, "strategy": strategy, "reasons": reasons[:4], "risks": risks[:4], "checks": checks[:4]},
        "Planner: recommend the strategy's pick.",
    )
    if tools.final is None:  # pragma: no cover - submit_recommendation always sets it for an engine option
        raise RuntimeError("planner produced no recommendation")
    return tools.final, steps


def run_agent(
    client: MessagesClient | None,
    tools: AgentTools,
    flight_id: str,
    delay: int | None,
    strategy: str | None,
    note: str,
    limits: Limits,
    on_step: Callable[[Step], None],
) -> Outcome:
    """AI first; on any stop, the planner answers with a fresh tool state (the AI's steps stay in the trace)."""
    steps: list[Step] = []
    try:
        return run_ai(client, tools, flight_id, delay, strategy, note, limits, on_step, steps)
    except AgentStoppedError as exc:
        reason = str(exc)
        log.warning("agent fell back to the planner: %s", reason)
    tools.assessment, tools.final = None, None
    final, steps = run_planner(tools, flight_id, delay, strategy, on_step, steps)
    return Outcome("planner", final, steps, fallback_reason=reason)
