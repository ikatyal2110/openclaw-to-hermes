"""Graphviz DOT rendering of the architecture graph.

Sister renderer to mermaid.py. Same shape/color conventions, different output
format. Pipe through `dot -Tsvg` or `dot -Tpng` to render.
"""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import EdgeKind, Node, NodeKind, PortabilityTier

# Per-kind node shape (Graphviz shape names).
_SHAPE = {
    NodeKind.WORKFLOW.value: "box",
    NodeKind.SKILL.value: "box",
    NodeKind.TOOL.value: "parallelogram",
    NodeKind.SCHEDULER.value: "doublecircle",
    NodeKind.MEMORY_STORE.value: "cylinder",
    NodeKind.PROMPT.value: "note",
    NodeKind.SERVICE.value: "hexagon",
    NodeKind.ENV.value: "ellipse",
}

# Per-tier fill colors matching the Mermaid renderer.
_FILL = {
    PortabilityTier.PORTABLE.value: "#d4f7d4",
    PortabilityTier.PARTIAL.value: "#fff3c4",
    PortabilityTier.NEEDS_REVIEW.value: "#ffd9b3",
    PortabilityTier.UNSUPPORTED.value: "#f7c2c2",
}

_STROKE = {
    PortabilityTier.PORTABLE.value: "#1a7f1a",
    PortabilityTier.PARTIAL.value: "#a87900",
    PortabilityTier.NEEDS_REVIEW.value: "#a55a00",
    PortabilityTier.UNSUPPORTED.value: "#8a1a1a",
}

_EDGE_STYLE = {
    EdgeKind.CONTROL.value: "",
    EdgeKind.DATA.value: 'label="data"',
    EdgeKind.TRIGGER.value: "penwidth=2",
    EdgeKind.DEPENDENCY.value: "style=dashed",
    EdgeKind.READS.value: 'style=dashed, label="reads"',
    EdgeKind.WRITES.value: 'style=dashed, label="writes"',
}


def render_dot_graph(ir: IRGraph) -> str:
    """Render the IR as a Graphviz DOT document.

    Suitable for `dot -Tsvg > arch.svg` or `dot -Tpng > arch.png`. Env-var nodes
    are omitted from the graph (they clutter without adding insight), matching
    the Mermaid renderer's behavior.
    """
    lines = [
        "digraph praxis {",
        "    rankdir=LR;",
        '    node [fontname="Helvetica", fontsize=10];',
        '    edge [fontname="Helvetica", fontsize=9];',
        "",
    ]

    env_ids = {n.id for n in ir.nodes if _kind(n) == NodeKind.ENV.value}

    for node in ir.nodes:
        kind = _kind(node)
        if kind == NodeKind.ENV.value:
            continue  # env vars clutter the graph; surfaced in report instead
        tier = _tier(node)
        shape = _SHAPE.get(kind, "box")
        fill = _FILL.get(tier, "#ffffff")
        stroke = _STROKE.get(tier, "#000000")
        label = f"{kind}: {node.name}".replace('"', '\\"')
        lines.append(
            f'    "{node.id}" [shape={shape}, style=filled, '
            f'fillcolor="{fill}", color="{stroke}", label="{label}"];'
        )

    lines.append("")

    for edge in ir.edges:
        if edge.from_ in env_ids or edge.to in env_ids:
            continue
        kind = edge.kind if isinstance(edge.kind, str) else edge.kind.value
        attrs = _EDGE_STYLE.get(kind, "")
        if attrs:
            lines.append(f'    "{edge.from_}" -> "{edge.to}" [{attrs}];')
        else:
            lines.append(f'    "{edge.from_}" -> "{edge.to}";')

    lines.append("}")
    return "\n".join(lines)


def _kind(node: Node) -> str:
    return node.kind if isinstance(node.kind, str) else node.kind.value


def _tier(node: Node) -> str:
    if not node.portability:
        return ""
    t = node.portability.tier
    return t if isinstance(t, str) else t.value
