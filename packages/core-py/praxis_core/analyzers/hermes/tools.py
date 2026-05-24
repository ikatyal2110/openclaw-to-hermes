"""Reads hermes/tools/*.yaml — emits one TOOL node per file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Node,
    NodeKind,
    PortSpec,
    Provenance,
    make_node_id,
)


class HermesToolsAnalyzer(Analyzer):
    name = "hermes.tools"

    def analyze(self, hermes_root: Path) -> IRGraph:
        ir = IRGraph()
        tools_dir = hermes_root / "tools"
        if not tools_dir.exists():
            return ir
        for path in sorted(tools_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                continue
            self._emit_tool(ir, path, data)
        return ir

    def _emit_tool(self, ir: IRGraph, path: Path, data: dict[str, Any]) -> None:
        name = data.get("name") or path.stem
        runtime = (data.get("runtime") or "").lower()
        capabilities: list[Capability] = []
        if runtime == "http":
            capabilities.append(Capability.HTTP_CALLABLE)
        if runtime == "python":
            capabilities.append(Capability.SIDE_EFFECTING)
        inputs = [_port(p) for p in (data.get("inputs") or []) if isinstance(p, dict)]
        outputs = [_port(p) for p in (data.get("outputs") or []) if isinstance(p, dict)]
        ir.nodes.append(
            Node(
                id=make_node_id("hermes", NodeKind.TOOL, name),
                kind=NodeKind.TOOL,
                name=name,
                description=data.get("description"),
                capabilities=capabilities,
                inputs=inputs,
                outputs=outputs,
                provenance=Provenance(
                    framework="hermes",
                    source_file=str(path.relative_to(path.parents[1])),
                    original_kind="tool",
                ),
                metadata={
                    "runtime": runtime,
                    "spec": data.get("spec") or {},
                },
            )
        )


def _port(p: dict[str, Any]) -> PortSpec:
    return PortSpec(
        name=str(p.get("name") or ""),
        type=p.get("type"),
        required=bool(p.get("required", True)),
        default=p.get("default"),
        description=p.get("description"),
    )
