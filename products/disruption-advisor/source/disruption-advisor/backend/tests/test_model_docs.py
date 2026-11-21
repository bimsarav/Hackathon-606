"""Model view data: bundled write-ups match docs/testing, parse into blocks; endpoints are evaluator only."""

from pathlib import Path

from fastapi.testclient import TestClient

from app import model_docs

DOCS_TESTING = Path(__file__).resolve().parents[2] / "docs" / "testing"


def test_bundled_write_ups_match_the_documents() -> None:
    for name in ("model-selection.md", "reward-model-selection.md"):
        source = DOCS_TESTING / name
        if source.exists():  # not present inside the container image
            bundled = "delay-model-selection.md" if name == "model-selection.md" else name
            assert (model_docs.DOCS / bundled).read_text() == source.read_text(), f"copy {name} to app/data/model_docs"


def test_markdown_becomes_blocks() -> None:
    blocks = model_docs.parse(
        "# Title\n\nSome **bold** text with [a link](x.md).\n\n## Part\n- one\n- two\n\n> note\n\n"
        "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    )
    assert [b["type"] for b in blocks] == ["title", "paragraph", "heading", "bullets", "quote", "table"]
    assert blocks[1]["text"] == "Some **bold** text with a link."
    assert blocks[3]["items"] == ["one", "two"]
    assert blocks[5] == {"type": "table", "header": ["A", "B"], "rows": [["1", "2"], ["3", "4"]]}


def test_real_write_ups_have_their_result_tables() -> None:
    docs = model_docs.documents()
    for key in ("delay_selection", "reward_selection"):
        tables = [b for b in docs[key] if b["type"] == "table"]
        assert len(tables) >= 2
        assert all(len(row) == len(t["header"]) for t in tables for row in t["rows"])
    assert any(
        r[0].startswith("LightGBM, tuned") for b in docs["delay_selection"] if b["type"] == "table" for r in b["rows"]
    )


def test_model_endpoints_are_for_the_evaluator_only(
    client: TestClient, auth: dict[str, str], evaluator_auth: dict[str, str]
) -> None:
    for path in ("/api/v1/risk/model-docs", "/api/v1/risk/reward-model"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth).status_code == 403
    docs = client.get("/api/v1/risk/model-docs", headers=evaluator_auth).json()
    assert set(docs) == {"delay_selection", "reward_selection"}
    # the test data folder has no reward card (stage 4 did not run on the fixture): a clear 404, not a crash
    assert client.get("/api/v1/risk/reward-model", headers=evaluator_auth).status_code in {200, 404}
