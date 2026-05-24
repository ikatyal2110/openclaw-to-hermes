"""Reads hermes/skills/*.yaml — emits one SKILL node per file, plus DEPENDENCY
edges from each procedure step's tool reference into the tool node."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Edge,
    EdgeKind,
    Intent,
    Node,
    NodeKind,
    Provenance,
    make_node_id,
)


class HermesSkillsAnalyzer(Analyzer):
    name = "hermes.skills"

    def analyze(self, hermes_root: Path) -> IRGraph:
        ir = IRGraph()
        skills_dir = hermes_root / "skills"
        if not skills_dir.exists():
            return ir
        for path in sorted(skills_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                continue
            self._emit_skill(ir, path, data)
        return ir

    def _emit_skill(self, ir: IRGraph, path: Path, data: dict[str, Any]) -> None:
        name = data.get("name") or path.stem
        skill_id = make_node_id("hermes", NodeKind.SKILL, name)
        description = data.get("description")
        when_to_use = data.get("when_to_use") or []
        procedure = data.get("procedure") or []

        capabilities: list[Capability] = [Capability.SEQUENCEABLE]
        if any(isinstance(s, dict) and "_praxis_when" in s for s in procedure):
            capabilities.append(Capability.BRANCHABLE)

        # Skills carry their description verbatim as intent — Hermes treats it as
        # the canonical "what this is for" statement, so confidence is high.
        intent = None
        if description:
            intent = Intent(
                description=description,
                confidence=0.95,
                evidence=["description field present in Hermes skill"],
                source="static",
            )

        # Round-trip metadata: confidence from the original `_praxis` block if present.
        praxis_meta = data.get("_praxis") or {}
        if isinstance(praxis_meta, dict) and isinstance(praxis_meta.get("confidence"), int | float):
            intent = Intent(
                description=description or name,
                confidence=float(praxis_meta["confidence"]),
                evidence=["_praxis.confidence in source"],
                source="static",
            )

        ir.nodes.append(
            Node(
                id=skill_id,
                kind=NodeKind.SKILL,
                name=name,
                description=description,
                capabilities=capabilities,
                intent=intent,
                provenance=Provenance(
                    framework="hermes",
                    source_file=str(path.relative_to(path.parents[1])),
                    original_kind="skill",
                ),
                metadata={
                    "procedure": procedure,
                    "when_to_use": when_to_use,
                    "inputs": data.get("inputs") or {},
                },
            )
        )

        # Edges to tools used in the procedure.
        for step in procedure:
            if not isinstance(step, dict):
                continue
            tool_name = step.get("tool")
            if not isinstance(tool_name, str):
                continue
            ir.edges.append(
                Edge(
                    **{"from": skill_id},
                    to=make_node_id("hermes", NodeKind.TOOL, tool_name),
                    kind=EdgeKind.CONTROL,
                    label=step.get("as"),
                )
            )
