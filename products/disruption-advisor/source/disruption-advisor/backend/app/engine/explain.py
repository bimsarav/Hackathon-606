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
    "You write short, factual text for airline operations staff and passengers. Use only the facts in the JSON "
    "you are given; never invent flights, times, amounts or policies. Plain English, no markdown headings, "
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

    # --- recommendation narrative ------------------------------------------------------------------------
    def recommendation(self, facts: dict[str, Any]) -> Text:
        ai = self._ask(
            "Explain to an OCC duty manager, in at most 120 words, which recovery option is recommended and why, "
            "and what the main trade-off against the other options is. Mention numbers from the facts.",
            facts,
            2000,
        )
        return Text(ai, f"ai:{self.model}") if ai else Text(template_recommendation(facts), "template")

    def passenger_message(self, facts: dict[str, Any]) -> Text:
        ai = self._ask(
            "Draft a passenger notification (SMS-length, at most 70 words, English) about this disruption and "
            "the new arrangement. Address the passenger as 'Dear customer'. Include the care offered if any.",
            facts,
            1500,
        )
        return Text(ai, f"ai:{self.model}") if ai else Text(template_message(facts), "template")


def template_recommendation(f: dict[str, Any]) -> str:
    best = f["recommended"]
    others = "; ".join(
        f"{o['label']}: {o['total_delay_minutes']} delay min, {o['misconnects']} misconnects, AED {o['cost_aed']:,.0f}"
        for o in f["options"]
        if o["key"] != best["key"]
    )
    return (
        f"Recommended: {best['label']}. It gives {best['total_delay_minutes']} total delay minutes over "
        f"{best['legs_delayed']} leg(s), {best['misconnects']} missed connections and an estimated cost of "
        f"AED {best['cost_aed']:,.0f}, the lowest of the options compared. Alternatives: {others or 'none feasible'}."
    )


def template_message(f: dict[str, Any]) -> str:
    if f.get("new_flight"):
        body = (
            f"your flight {f['flight']} from {f['origin']} to {f['destination']} is {f['event']}. "
            f"We have rebooked you on {f['new_flight']} departing {f['new_departure']}."
        )
    else:
        body = (
            f"your flight {f['flight']} from {f['origin']} to {f['destination']} is {f['event']}. "
            "Our team will contact you with the next available option; you may also request a refund."
        )
    care = f" {f['care']}" if f.get("care") else ""
    return f"Dear customer, {body}{care} We apologise for the disruption."
