"""Mermaid flowchart rendering of the architecture graph."""
from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import EdgeKind, NodeKind, PortabilityTier

SHAPES = {
    NodeKind.WORKFLOW.value: ("[", "]"),
    NodeKind.TOOL.value: ("[/", "/]"),
    NodeKind.SCHEDULER.value: ("((", "))"),
    NodeKind.MEMORY_STORE.value: ("[(", ")]"),
    NodeKind.PROMPT.value: ('>"', '"]'),
    NodeKind.SERVICE.value: ("{{", "}}"),
    NodeKind.ENV.value: ('["', '"]'),
}

EDGE_STYLE = {
    EdgeKind.CONTROL.value: "-->",
    EdgeKind.DATA.value: "-->|data|",
    EdgeKind.TRIGGER.value: "==>",
    EdgeKind.DEPENDENCY.value: "-.->",
    EdgeKind.READS.value: "-.->|reads|",
    EdgeKind.WRITES.value: "-.->|writes|",
}

TIER_CLASS = {
    PortabilityTier.PORTABLE.value: "portable",
    PortabilityTier.PARTIAL.value: "partial",
    PortabilityTier.NEEDS_REVIEW.value: "needsReview",
    PortabilityTier.UNSUPPORTED.value: "unsupported",
}


def render_mermaid_graph(ir: IRGraph) -> str:
    lines: list[str] = ["flowchart LR"]
    lines.append("    classDef portable fill:#d4f7d4,stroke:#1a7f1a")
    lines.append("    classDef partial fill:#fff3c4,stroke:#a87900")
    lines.append("    classDef needsReview fill:#ffd9b3,stroke:#a55a00")
    lines.append("    classDef unsupported fill:#f7c2c2,stroke:#8a1a1a")
    lines.append("")

    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind == NodeKind.ENV.value:
            continue  # env vars clutter the graph; surface in report instead
        open_s, close_s = SHAPES.get(kind, ("[", "]"))
        safe_id = _safe(node.id)
        label = node.name.replace('"', "'")
        lines.append(f'    {safe_id}{open_s}"{kind}: {label}"{close_s}')

    lines.append("")

    for edge in ir.edges:
        kind = edge.kind if isinstance(edge.kind, str) else edge.kind.value
        style = EDGE_STYLE.get(kind, "-->")
        if _is_env(ir, edge.from_) or _is_env(ir, edge.to):
            continue
        from_id = _safe(edge.from_)
        to_id = _safe(edge.to)
        if edge.label:
            lines.append(f'    {from_id} {style} {to_id}')
        else:
            lines.append(f"    {from_id} {style} {to_id}")

    lines.append("")

    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind == NodeKind.ENV.value or not node.portability:
            continue
        tier = node.portability.tier if isinstance(node.portability.tier, str) else node.portability.tier.value
        cls = TIER_CLASS.get(tier)
        if cls:
            lines.append(f"    class {_safe(node.id)} {cls}")

    return "\n".join(lines)


def _safe(node_id: str) -> str:
    return node_id.replace(".", "_").replace("-", "_")


def _is_env(ir: IRGraph, node_id: str) -> bool:
    n = ir.node_by_id(node_id)
    if not n:
        return False
    return (n.kind if isinstance(n.kind, str) else n.kind.value) == NodeKind.ENV.value
