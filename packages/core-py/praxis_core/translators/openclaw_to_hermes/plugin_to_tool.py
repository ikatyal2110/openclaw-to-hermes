"""OpenClaw plugin → Hermes tool."""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import Node, NodeKind, PortabilityTier
from praxis_core.translators.openclaw_to_hermes.types import HermesProject, HermesTool


def translate_tools(ir: IRGraph, project: HermesProject) -> None:
    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind != NodeKind.TOOL.value:
            continue
        if node.portability and node.portability.tier == PortabilityTier.UNSUPPORTED.value:
            continue

        meta = node.metadata or {}
        runtime = meta.get("runtime", "unknown")
        cfg = meta.get("config", {}) or {}
        description = node.description or _describe(node, runtime)

        project.tools.append(
            HermesTool(
                name=node.name,
                description=description,
                runtime=runtime
                if runtime != "subprocess"
                else "http",  # subprocess shouldn't reach here
                spec={k: v for k, v in cfg.items() if k != "memory_store"},
                inputs=[
                    {"name": p.name, "type": p.type or "string", "required": p.required}
                    for p in node.inputs
                ],
                outputs=[{"name": p.name, "type": p.type or "string"} for p in node.outputs],
            )
        )


def _describe(node: Node, runtime: str) -> str:
    rationale = node.portability.rationale if node.portability else ""
    return f"{node.name} ({runtime}) — {rationale}".rstrip(" —")
