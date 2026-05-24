"""Reads hermes/schedules/*.yaml — emits one SCHEDULER node per file and a
TRIGGER edge into the referenced skill."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    Provenance,
    make_node_id,
)


class HermesSchedulesAnalyzer(Analyzer):
    name = "hermes.schedules"

    def analyze(self, hermes_root: Path) -> IRGraph:
        ir = IRGraph()
        sched_dir = hermes_root / "schedules"
        if not sched_dir.exists():
            return ir
        for path in sorted(sched_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                continue
            self._emit_schedule(ir, path, data)
        return ir

    def _emit_schedule(self, ir: IRGraph, path: Path, data: dict[str, Any]) -> None:
        name = data.get("name") or path.stem
        cron = data.get("cron")
        invoke = data.get("invoke_skill")
        sched_id = make_node_id("hermes", NodeKind.SCHEDULER, name)
        ir.nodes.append(
            Node(
                id=sched_id,
                kind=NodeKind.SCHEDULER,
                name=name,
                capabilities=[Capability.SCHEDULED],
                provenance=Provenance(
                    framework="hermes",
                    source_file=str(path.relative_to(path.parents[1])),
                    original_kind="schedule",
                ),
                metadata={"trigger_kind": "cron" if cron else "unknown", "spec": cron},
            )
        )
        if isinstance(invoke, str):
            ir.edges.append(
                Edge(
                    **{"from": sched_id},
                    to=make_node_id("hermes", NodeKind.SKILL, invoke),
                    kind=EdgeKind.TRIGGER,
                    label=cron if isinstance(cron, str) else None,
                )
            )
