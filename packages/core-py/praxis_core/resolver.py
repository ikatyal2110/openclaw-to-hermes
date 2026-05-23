"""Resolve stage: validates cross-references, drops orphan edges with diagnostics, dedupes."""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import Diagnostic, Edge, Node


def resolve(ir: IRGraph) -> IRGraph:
    """Mutates `ir` in place: deduplicates nodes/edges, drops dangling refs."""
    _dedupe_nodes(ir)
    _drop_orphan_edges(ir)
    _dedupe_edges(ir)
    ir.sort()
    return ir


def _dedupe_nodes(ir: IRGraph) -> None:
    """If two analyzers emit the same node id, keep the one with the richer payload."""
    by_id: dict[str, int] = {}
    keep: list[Node] = []
    for node in ir.nodes:
        if node.id in by_id:
            existing = keep[by_id[node.id]]
            if _richness(node) > _richness(existing):
                keep[by_id[node.id]] = node
        else:
            by_id[node.id] = len(keep)
            keep.append(node)
    ir.nodes = keep


def _richness(n: Node) -> int:
    score = 0
    if n.description:
        score += 1
    score += len(n.capabilities)
    score += len(n.inputs) + len(n.outputs)
    if n.intent:
        score += 2
    score += len(n.metadata or {})
    return score


def _drop_orphan_edges(ir: IRGraph) -> None:
    node_ids = {n.id for n in ir.nodes}
    kept: list[Edge] = []
    for edge in ir.edges:
        missing = []
        if edge.from_ not in node_ids:
            missing.append(edge.from_)
        if edge.to not in node_ids:
            missing.append(edge.to)
        if missing:
            ir.diagnostics.append(
                Diagnostic(
                    level="warn",
                    code="PRX030",
                    message=f"Dangling edge {edge.from_} → {edge.to}; missing node(s): {', '.join(missing)}",
                    hint="Likely a name typo in a workflow step, plugin config, or memory reference.",
                )
            )
            continue
        kept.append(edge)
    ir.edges = kept


def _dedupe_edges(ir: IRGraph) -> None:
    seen: set[tuple[str, str, str, str | None]] = set()
    kept: list[Edge] = []
    for e in ir.edges:
        kind_val = e.kind if isinstance(e.kind, str) else e.kind.value
        key = (e.from_, e.to, kind_val, e.label)
        if key in seen:
            continue
        seen.add(key)
        kept.append(e)
    ir.edges = kept
