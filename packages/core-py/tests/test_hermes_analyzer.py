"""Tests for the Hermes → IR analyzer (round-trip support)."""

from __future__ import annotations

from pathlib import Path

import pytest

from praxis_core.analyzers.hermes import analyze_hermes_project
from praxis_core.ir.models import NodeKind
from praxis_core.pipeline import migrate


@pytest.fixture(scope="module")
def round_tripped(sample_root: Path, tmp_path_factory: pytest.TempPathFactory):
    """Emit the baseline fixture as Hermes, then analyze it back."""
    out = tmp_path_factory.mktemp("hermes-rt")
    migrate(sample_root, out)
    return analyze_hermes_project(out)


def _names_by_kind(ir, kind: NodeKind) -> set[str]:
    target = kind.value
    return {
        n.name for n in ir.nodes if (n.kind.value if hasattr(n.kind, "value") else n.kind) == target
    }


def test_hermes_analyzer_finds_all_skills(round_tripped) -> None:
    skills = _names_by_kind(round_tripped, NodeKind.SKILL)
    assert skills == {"daily_digest", "support_triage", "weekly_digest"}


def test_hermes_analyzer_finds_all_tools(round_tripped) -> None:
    tools = _names_by_kind(round_tripped, NodeKind.TOOL)
    assert tools == {
        "fetch_articles",
        "dedupe_seen",
        "llm_summarize",
        "slack_post",
        "classify_ticket",
        "ticket_router",
    }


def test_hermes_analyzer_finds_memory_stores(round_tripped) -> None:
    memory = _names_by_kind(round_tripped, NodeKind.MEMORY_STORE)
    assert memory == {"seen_articles", "ticket_history"}


def test_hermes_analyzer_finds_prompts(round_tripped) -> None:
    prompts = _names_by_kind(round_tripped, NodeKind.PROMPT)
    assert "summarize" in prompts and "classify" in prompts


def test_hermes_analyzer_emits_control_edges_skill_to_tool(round_tripped) -> None:
    """Each skill should have CONTROL edges into the tools its procedure calls."""
    from praxis_core.ir.models import EdgeKind

    control_edges = [
        e
        for e in round_tripped.edges
        if (e.kind.value if hasattr(e.kind, "value") else e.kind) == EdgeKind.CONTROL.value
    ]
    assert control_edges, "Skills should emit CONTROL edges to their tools."


def test_hermes_analyzer_handles_missing_hermes_dir(tmp_path: Path) -> None:
    """Pointing at an empty directory should not crash; it just returns no nodes."""
    ir = analyze_hermes_project(tmp_path)
    assert ir.nodes == []
    assert ir.edges == []


def test_hermes_analyzer_accepts_inner_hermes_dir(tmp_path: Path, sample_root: Path) -> None:
    """Passing the inner `hermes/` dir works the same as passing the outer dir."""
    out = tmp_path / "out"
    migrate(sample_root, out)
    direct = analyze_hermes_project(out / "hermes")
    via_outer = analyze_hermes_project(out)
    # Same set of node names (kind, name) regardless of which path is given.
    direct_keys = {(n.kind, n.name) for n in direct.nodes}
    outer_keys = {(n.kind, n.name) for n in via_outer.nodes}
    assert direct_keys == outer_keys
