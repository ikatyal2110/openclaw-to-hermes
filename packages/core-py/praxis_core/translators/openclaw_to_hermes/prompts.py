"""Prompts pass through verbatim — content addressed by name."""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind
from praxis_core.translators.openclaw_to_hermes.types import HermesProject, HermesPrompt


def translate_prompts(ir: IRGraph, project: HermesProject) -> None:
    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind != NodeKind.PROMPT.value:
            continue
        meta = node.metadata or {}
        project.prompts.append(
            HermesPrompt(name=node.name, body=meta.get("body", ""), format=meta.get("format", "j2"))
        )
