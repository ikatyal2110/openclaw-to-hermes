"""Resolver invariants: dangling edges flagged, duplicates removed, nodes deduped."""
from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import Edge, EdgeKind, Node, NodeKind, Provenance
from praxis_core.resolver import resolve


def _node(node_id: str, **kwargs) -> Node:  # noqa: ANN003
    return Node(
        id=node_id,
        kind=kwargs.pop("kind", NodeKind.TOOL),
        name=kwargs.pop("name", node_id),
        provenance=Provenance(framework="openclaw"),
        **kwargs,
    )


def test_drops_orphan_edges_and_emits_diagnostic() -> None:
    ir = IRGraph()
    ir.nodes.append(_node("a"))
    ir.edges.append(Edge(**{"from": "a"}, to="missing", kind=EdgeKind.CONTROL))
    resolve(ir)
    assert ir.edges == []
    assert any("missing" in d.message for d in ir.diagnostics)


def test_dedupes_duplicate_edges() -> None:
    ir = IRGraph()
    ir.nodes.append(_node("a"))
    ir.nodes.append(_node("b"))
    ir.edges.append(Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL))
    ir.edges.append(Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL))
    resolve(ir)
    assert len(ir.edges) == 1


def test_keeps_different_edge_kinds_between_same_nodes() -> None:
    ir = IRGraph()
    ir.nodes.append(_node("a"))
    ir.nodes.append(_node("b"))
    ir.edges.append(Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL))
    ir.edges.append(Edge(**{"from": "a"}, to="b", kind=EdgeKind.DATA))
    resolve(ir)
    assert len(ir.edges) == 2


def test_dedupes_nodes_keeping_the_richer() -> None:
    ir = IRGraph()
    spare = _node("x")
    rich = _node("x", description="rich", capabilities=[])
    rich.metadata = {"foo": "bar", "baz": 1}
    ir.nodes.append(spare)
    ir.nodes.append(rich)
    resolve(ir)
    assert len(ir.nodes) == 1
    assert ir.nodes[0].description == "rich"
