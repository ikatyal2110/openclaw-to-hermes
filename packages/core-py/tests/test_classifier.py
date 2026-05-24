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


def test_subprocess_tool_is_partial_via_wrapper() -> None:
    """v0.9: subprocess/shell runtimes are translatable via HTTP wrapper, not unsupported."""
    p = _classify(_node(NodeKind.TOOL, runtime="subprocess", kind="tool"))
    assert p.tier == "partial"
    assert p.blockers


def test_docker_tool_is_partial() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="docker", kind="tool"))
    assert p.tier == "partial"
    assert any("HTTP" in b or "Kubernetes" in b for b in p.blockers)


def test_lambda_tool_is_partial() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="lambda", kind="tool"))
    assert p.tier == "partial"


def test_grpc_tool_needs_review() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="grpc", kind="tool"))
    assert p.tier == "needs_review"


def test_graphql_tool_needs_review() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="graphql", kind="tool"))
    assert p.tier == "needs_review"


def test_node_pure_tool_is_portable() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="node", kind="tool", pure=True))
    assert p.tier == "portable"


def test_go_impure_tool_needs_review() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="go", kind="tool", pure=False))
    assert p.tier == "needs_review"


def test_https_tool_is_portable() -> None:
    p = _classify(_node(NodeKind.TOOL, runtime="https", kind="tool"))
    assert p.tier == "portable"


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


def test_sql_memory_is_partial_via_wrapper_tool() -> None:
    """v0.8: relational backends are translatable via a wrapper tool, not unsupported."""
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "sql"}))
    assert p.tier == "partial"
    assert p.blockers


def test_postgres_memory_is_partial_via_wrapper_tool() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "postgres"}))
    assert p.tier == "partial"


def test_redis_memory_is_portable_as_kv() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "redis"}))
    assert p.tier == "portable"


def test_sqlite_memory_needs_review() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "sqlite"}))
    assert p.tier == "needs_review"
    assert any("KV" in b or "tool" in b for b in p.blockers)


def test_dynamodb_memory_needs_review() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "dynamodb"}))
    assert p.tier == "needs_review"


def test_s3_memory_needs_review_as_blob_storage() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "s3"}))
    assert p.tier == "needs_review"
    assert any("bucket" in b.lower() or "tool" in b.lower() for b in p.blockers)


def test_unknown_memory_kind_has_actionable_blockers() -> None:
    p = _classify(_node(NodeKind.MEMORY_STORE, spec={"kind": "etcd"}))
    assert p.tier == "needs_review"
    assert p.blockers


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
