"""Reads memory/stores.yaml — emits one memory_store node per declared store."""
from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Capability, Node, NodeKind, Provenance, make_node_id


class MemoryAnalyzer(Analyzer):
    name = "openclaw.memory"

    def analyze(self, root: Path) -> IRGraph:
        ir = IRGraph()
        data = self.safe_load_yaml(root / "memory" / "stores.yaml")
        if not isinstance(data, dict):
            return ir

        for store_name, spec in (data.get("stores") or {}).items():
            if not isinstance(spec, dict):
                continue
            ir.nodes.append(
                Node(
                    id=make_node_id("openclaw", NodeKind.MEMORY_STORE, store_name),
                    kind=NodeKind.MEMORY_STORE,
                    name=store_name,
                    capabilities=[Capability.STATEFUL],
                    provenance=Provenance(
                        framework="openclaw",
                        source_file="memory/stores.yaml",
                        original_kind=f"memory_store/{spec.get('kind', 'unknown')}",
                    ),
                    metadata={"spec": spec},
                )
            )
        return ir
