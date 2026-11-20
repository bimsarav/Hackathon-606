"""Plain-English explanations and passenger message drafts.

The engine decides; the language model only rewrites the engine's machine-readable reasons into readable text.
Privacy (Q3, treated as real data): no names, PNRs, contact details or customer keys are sent; only flight
numbers, stations, times, counts and the reasons. When no API key is set, the call fails or the model declines,
a deterministic template is used, so the product always works.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, cast

import anthropic
from anthropic.types.beta import BetaOutputConfigParam, BetaUserMessageParam

log = logging.getLogger(__name__)

SYSTEM = (
    "You write very short, plain-English text for busy airline staff and passengers. Use only the facts in the JSON "
    "you are given; never invent flights, times, amounts or policies. Write like a calm, clear colleague: short "
    "sentences, everyday words, no jargon (say 'flights' not 'legs', 'missed connections' not 'misconnects', "
    "'swap the aircraft' not 'rotation exchange'), no lists of every option, no cost breakdowns, no markdown, "
    "no emojis."
)


@dataclass(frozen=True)
class Text:
    text: str
    source: str  # "ai:<model>" or "template"


class Explainer:
    def __init__(self, api_key: str, model: str, effort: str, timeout_s: float) -> None:
        self.model, self.effort = model, effort
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=2) if api_key else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _ask(self, instruction: str, facts: dict[str, Any], max_tokens: int) -> str | None:
        if self._client is None:
            return None
        try:
            messages: list[BetaUserMessageParam] = [
                {
                    "role": "user",
                    "content": f"{instruction}\n\nFacts (JSON):\n{json.dumps(facts, default=str, sort_keys=True)}",
                }
            ]
            output_config = cast(BetaOutputConfigParam, {"effort": self.effort})
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM,
                output_config=output_config,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=messages,
            )
        except anthropic.APIStatusError as exc:
            log.warning("ai call failed", extra={"status": exc.status_code})
            return None
        except anthropic.APIConnectionError:
            log.warning("ai call failed: connection")
            return None
        if response.stop_reason == "refusal":
            return None
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text or None

    # --- explanations and messages ---------------------------------------------------------------------
    def recommendation(self, facts: dict[str, Any]) -> Text:
        ai = self._ask(
            "Explain the decision to an operations duty manager in at most 3 short sentences (under 60 words in "
            "total). Sentence 1: what happened. Sentence 2: what we do (the chosen option; if it is not the "
            "recommendation, say so plainly). Sentence 3: why, compared with the next best choice. If no option can "
            "save the missed connections, say that in a few words and say how many passengers are rebooked. Use at "
            "most 3 numbers. Round money to the nearest thousand AED.",
            facts,
            1500,
        )
        return Text(ai, f"ai:{self.model}") if ai else Text(template_recommendation(facts), "template")

    def cancellation(self, facts: dict[str, Any]) -> Text:
        ai = self._ask(
            "Explain the rebooking plan to an operations duty manager in at most 3 short sentences (under 60 words). "
            "Say how many passengers must move, how many get a seat and how many do not, and who goes first. Use at "
            "most 3 numbers.",
            facts,
            1500,
        )
        return Text(ai, f"ai:{self.model}") if ai else Text(template_cancellation(facts), "template")

    def passenger_message(self, facts: dict[str, Any]) -> Text:
        ai = self._ask(
            "Write a text message to the passenger, at most 45 words, simple and friendly, starting 'Dear "
            "customer'. Say what happened to their journey (if a late inbound flight made them miss their "
            "connection, say exactly that), their new flight and time if they have one, the care while they wait "
            "(hotel, transport, meals) and, if allowed, that they may choose a refund with a free return to origin or "
            "a date change. Mention special assistance only if listed.",
            facts,
            1000,
        )
        return Text(ai, f"ai:{self.model}") if ai else Text(template_message(facts), "template")


def _thousands(aed: float) -> str:
    return f"AED {round(aed / 1000):,}k" if aed >= 1000 else f"AED {aed:,.0f}"


def template_recommendation(f: dict[str, Any]) -> str:
    c, alt = f["chosen_option"], f.get("next_best_alternative")
    what = "We recommend" if f.get("chosen_is_the_recommendation", True) else "You chose (not the recommendation)"
    text = f"{f['late_flight']} is {f['delay_minutes']} minutes late. {what}: {c['what']}."
    if alt:
        text += (
            f" This delays {c['flights_delayed']} flight(s) and costs about {_thousands(c['estimated_cost_aed'])},"
            f" against {_thousands(alt['estimated_cost_aed'])} for the next choice."
        )
    if c["passengers_missing_connections"]:
        text += (
            f" {c['passengers_missing_connections']} passengers still miss their connection:"
            f" {f.get('passengers_rebooked', 0)} are rebooked, {f.get('passengers_without_seat', 0)} have no seat yet."
        )
    return text


def template_cancellation(f: dict[str, Any]) -> str:
    return (
        f"{f['cancelled_flight']} is cancelled and {f['passengers_to_move']} passengers must move. "
        f"{f['passengers_rebooked']} get a seat on another flight within 24 hours; "
        f"{f['passengers_without_seat']} do not and are offered the next day with a hotel, or a refund. "
        "Passengers needing special assistance and families with babies go first; staff travel goes last."
    )


def template_message(f: dict[str, Any]) -> str:
    if f.get("late_inbound_flight"):
        what = (
            f"your flight {f['late_inbound_flight']} arrived late, so you missed your connection {f['flight']} "
            f"to {f['destination']}."
        )
    else:
        what = f"your flight {f['flight']} from {f['origin']} to {f['destination']} is {f['event']}."
    if f.get("new_flight"):
        plan = f" Your new flight is {f['new_flight']}, departing {f['new_departure']}."
    else:
        plan = " We will contact you with the next available flight, or you can ask for a refund."
    care = f" {f['care']}" if f.get("care") else ""
    return f"Dear customer, {what}{plan}{care} We are sorry for the trouble."
