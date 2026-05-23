"""OpenClaw memory store → Hermes memory schema."""
from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind, PortabilityTier
from praxis_core.translators.openclaw_to_hermes.types import HermesMemory, HermesProject


def translate_memory(ir: IRGraph, project: HermesProject) -> None:
    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind != NodeKind.MEMORY_STORE.value:
            continue
        if node.portability and node.portability.tier == PortabilityTier.UNSUPPORTED.value:
            continue
        spec = (node.metadata or {}).get("spec") or {}
        store_kind = spec.get("kind", "kv")
        fields = {k: v for k, v in spec.items() if k != "kind"}
        project.memories.append(HermesMemory(name=node.name, kind=store_kind, fields=fields))
