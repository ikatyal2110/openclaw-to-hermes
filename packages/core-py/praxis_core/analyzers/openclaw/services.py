"""Reads services/services.yaml — declared external dependencies."""

from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Capability, Node, NodeKind, Provenance, make_node_id


class ServicesAnalyzer(Analyzer):
    name = "openclaw.services"

    def analyze(self, root: Path) -> IRGraph:
        ir = IRGraph()
        data = self.safe_load_yaml(root / "services" / "services.yaml")
        if not isinstance(data, dict):
            return ir
        for service_name, spec in (data.get("services") or {}).items():
            if not isinstance(spec, dict):
                continue
            ir.nodes.append(
                Node(
                    id=make_node_id("openclaw", NodeKind.SERVICE, service_name),
                    kind=NodeKind.SERVICE,
                    name=service_name,
                    capabilities=[Capability.EXTERNAL_DEPENDENCY],
                    provenance=Provenance(
                        framework="openclaw",
                        source_file="services/services.yaml",
                        original_kind=f"service/{spec.get('kind', 'unknown')}",
                    ),
                    metadata={"spec": spec},
                )
            )
        return ir
