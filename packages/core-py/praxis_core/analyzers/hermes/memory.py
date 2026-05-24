"""Reads hermes/memory/*.yaml — emits one MEMORY_STORE node per file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Capability, Node, NodeKind, Provenance, make_node_id


class HermesMemoryAnalyzer(Analyzer):
    name = "hermes.memory"

    def analyze(self, hermes_root: Path) -> IRGraph:
        ir = IRGraph()
        memory_dir = hermes_root / "memory"
        if not memory_dir.exists():
            return ir
        for path in sorted(memory_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                continue
            name = data.get("name") or path.stem
            kind = (data.get("kind") or "").lower()
            # Pull out kind+name; the rest of the schema fields go into spec for
            # the classifier and report.
            spec: dict[str, Any] = {k: v for k, v in data.items() if k not in ("name",)}
            ir.nodes.append(
                Node(
                    id=make_node_id("hermes", NodeKind.MEMORY_STORE, name),
                    kind=NodeKind.MEMORY_STORE,
                    name=name,
                    capabilities=[Capability.STATEFUL],
                    provenance=Provenance(
                        framework="hermes",
                        source_file=str(path.relative_to(path.parents[1])),
                        original_kind="memory_store",
                    ),
                    metadata={"spec": spec, "kind": kind},
                )
            )
        return ir
