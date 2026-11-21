"""Model view data for the evaluator: the reward model's card and the model comparison and tuning write-ups.

The two write-ups (docs/testing/model-selection.md and reward-model-selection.md) are bundled in app/data/model_docs
and turned into simple blocks (title, heading, paragraph, bullets, quote, table) that the Model view renders. A test
keeps the bundled copies identical to the files in docs/testing. Both endpoints are for the evaluator role only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.auth import EvaluatorUser

DOCS = Path(__file__).parent / "data" / "model_docs"
SOURCES = {"delay_selection": "delay-model-selection.md", "reward_selection": "reward-model-selection.md"}
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(text: str) -> list[dict[str, Any]]:
    """Markdown subset used in the write-ups -> blocks. Links become their text; bold and code stay as markup."""
    blocks: list[dict[str, Any]] = []
    lines = [_LINK.sub(r"\1", line.rstrip()) for line in text.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append({"type": "title" if level == 1 else "heading", "text": line.lstrip("# ").strip()})
            i += 1
        elif line.startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            body = [r for r in rows[1:] if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            blocks.append({"type": "table", "header": rows[0], "rows": body})
        elif line.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:].strip())
                i += 1
            blocks.append({"type": "bullets", "items": items})
        elif line.startswith(">"):
            quote: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(quote)})
        else:
            para: list[str] = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "- ", ">")):
                para.append(lines[i].strip())
                i += 1
            blocks.append({"type": "paragraph", "text": " ".join(para)})
    return blocks


def documents() -> dict[str, list[dict[str, Any]]]:
    return {key: parse((DOCS / name).read_text(encoding="utf-8")) for key, name in SOURCES.items()}


router = APIRouter(prefix="/api/v1/risk", tags=["model"])


@router.get("/model-docs")
def model_docs(_: EvaluatorUser) -> dict[str, list[dict[str, Any]]]:
    """Model comparison and tuning write-ups for the delay model and the reward preference model."""
    return documents()


@router.get("/reward-model")
def reward_model_card(request: Request, _: EvaluatorUser) -> dict[str, Any]:
    """The reward preference model's card (synthetic training data warning, assumed behaviour, held-out scores)."""
    path = request.app.state.settings.data_dir / "ops" / "reward_model_card.json"
    try:
        return dict(json.loads(path.read_text()))
    except (OSError, ValueError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No reward model card yet (ingest stage 4)") from exc
