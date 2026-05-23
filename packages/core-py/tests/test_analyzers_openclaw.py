"""Verifies each OpenClaw analyzer emits the expected nodes and edges from the fixture."""

from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.openclaw import analyze_openclaw_project
from praxis_core.ir.models import EdgeKind, NodeKind


def _kinds(ir, kind: NodeKind) -> list[str]:
    return sorted(n.name for n in ir.nodes if _node_kind(n) == kind.value)


def _node_kind(n) -> str:  # noqa: ANN001
    return n.kind if isinstance(n.kind, str) else n.kind.value


def _edge_kind(e) -> str:  # noqa: ANN001
    return e.kind if isinstance(e.kind, str) else e.kind.value


def test_analyzer_produces_expected_workflows(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    assert _kinds(ir, NodeKind.WORKFLOW) == ["daily_digest", "support_triage", "weekly_digest"]


def test_analyzer_produces_expected_tools(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    expected = sorted(
        [
            "fetch_articles",
            "dedupe_seen",
            "llm_summarize",
            "slack_post",
            "classify_ticket",
            "ticket_router",
        ]
    )
    assert _kinds(ir, NodeKind.TOOL) == expected


def test_analyzer_produces_expected_env(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    envs = _kinds(ir, NodeKind.ENV)
    for v in ["RSS_URL", "SLACK_CHANNEL", "OPENAI_API_KEY", "JIRA_BASE_URL", "JIRA_TOKEN"]:
        assert v in envs


def test_analyzer_produces_expected_memory(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    assert _kinds(ir, NodeKind.MEMORY_STORE) == ["seen_articles", "ticket_history"]


def test_analyzer_produces_expected_prompts(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    assert _kinds(ir, NodeKind.PROMPT) == [
        "classify",
        "classify_email",
        "extract_entities",
        "extract_entities_v2",
        "summarize",
        "summarize_weekly",
    ]


def test_analyzer_produces_expected_services(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    assert _kinds(ir, NodeKind.SERVICE) == ["jira", "openai"]


def test_cron_trigger_emits_scheduler(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    sched_names = _kinds(ir, NodeKind.SCHEDULER)
    assert any("cron" in name for name in sched_names)


def test_webhook_trigger_emits_scheduler(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    sched_names = _kinds(ir, NodeKind.SCHEDULER)
    assert any("webhook" in name for name in sched_names)


def test_workflow_emits_control_edges_to_tools(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    control_edges = [e for e in ir.edges if _edge_kind(e) == EdgeKind.CONTROL.value]
    assert control_edges, "Workflow steps should produce control edges to their plugins."


def test_workflow_emits_data_edges_between_consecutive_steps(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    data_edges = [e for e in ir.edges if _edge_kind(e) == EdgeKind.DATA.value]
    assert data_edges, "Adjacent workflow steps should produce data edges."


def test_intent_from_description_has_high_confidence(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    daily = next(
        n for n in ir.nodes if n.name == "daily_digest" and _node_kind(n) == NodeKind.WORKFLOW.value
    )
    assert daily.intent is not None
    assert daily.intent.confidence >= 0.9
