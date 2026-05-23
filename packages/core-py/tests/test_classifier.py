"""Portability classifier — one test per documented mapping rule."""

from __future__ import annotations

from praxis_core.ir.models import Intent, Node, NodeKind, Provenance
from praxis_core.scoring.classifier import _classify


def _node(node_kind: NodeKind, /, **metadata) -> Node:  # noqa: ANN003
    return Node(
        id=f"{node_kind.value}.x.abc",
        kind=node_kind,
        name="x",
        provenance=Provenance(framework="openclaw"),
        metadata=metadata,
    )


def test_http_tool_is_portable() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="http", kind="tool"))
    assert p.tier == "portable"


def test_pure_python_tool_is_portable() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="python", kind="tool", pure=True))
    assert p.tier == "portable"


def test_impure_python_tool_needs_review() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="python", kind="tool", pure=False))
    assert p.tier == "needs_review"


def test_subprocess_tool_is_unsupported() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="subprocess", kind="tool"))
    assert p.tier == "unsupported"


def test_router_tool_is_partial() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="python", kind="router", pure=False))
    assert p.tier == "partial"
    assert p.blockers, "Router migration must surface blockers."


def test_kv_memory_is_portable() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "kv"}))
    assert p.tier == "portable"


def test_vector_memory_needs_review() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "vector", "dim": 1536}))
    assert p.tier == "needs_review"


def test_sql_memory_is_unsupported() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "sql"}))
    assert p.tier == "unsupported"


def test_cron_scheduler_is_portable() -> None:
    p = _classify(_node(NodeKind.SCHEDULER, trigger_kind="cron", spec="0 9 * * *"))
    assert p.tier == "portable"


def test_webhook_scheduler_is_partial() -> None:
    p = _classify(_node(NodeKind.SCHEDULER, trigger_kind="webhook", path="/hooks/x"))
    assert p.tier == "partial"


def test_workflow_with_branches_needs_review() -> None:
    n = _node(NodeKind.WORKFLOW, has_branches=True, raw_steps=[])
    n.intent = Intent(description="x", confidence=0.95, source="static")
    p = _classify(n)
    assert p.tier == "needs_review"
    assert any("branch" in b.lower() for b in p.blockers)


def test_workflow_with_low_confidence_is_partial_not_portable() -> None:
    n = _node(NodeKind.WORKFLOW, has_branches=False, raw_steps=[])
    n.intent = Intent(description="x", confidence=0.3, source="static")
    p = _classify(n)
    assert p.tier == "partial"


def test_workflow_with_high_confidence_is_portable() -> None:
    n = _node(NodeKind.WORKFLOW, has_branches=False, raw_steps=[])
    n.intent = Intent(description="x", confidence=0.95, source="static")
    p = _classify(n)
    assert p.tier == "portable"
