"""Cron scheduler nodes → Hermes schedules pointing at the triggered skill."""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.ir.models import EdgeKind, Node, NodeKind
from praxis_core.translators.openclaw_to_hermes.types import HermesProject, HermesSchedule


def translate_schedules(ir: IRGraph, project: HermesProject) -> None:
    workflow_by_id = {n.id: n for n in ir.nodes if _kind(n) == NodeKind.WORKFLOW.value}
    for node in ir.nodes:
        if _kind(node) != NodeKind.SCHEDULER.value:
            continue
        meta = node.metadata or {}
        if meta.get("trigger_kind") != "cron":
            continue
        triggered = _trigger_target(ir, node.id)
        if not triggered or triggered not in workflow_by_id:
            continue
        skill_name = workflow_by_id[triggered].name
        project.schedules.append(
            HermesSchedule(
                name=skill_name,
                cron=str(meta.get("spec", "")),
                invoke_skill=skill_name,
            )
        )


def _trigger_target(ir: IRGraph, scheduler_id: str) -> str | None:
    for e in ir.edges:
        kind = e.kind if isinstance(e.kind, str) else e.kind.value
        if e.from_ == scheduler_id and kind == EdgeKind.TRIGGER.value:
            return e.to
    return None


def _kind(node: Node) -> str:
    return node.kind if isinstance(node.kind, str) else node.kind.value
