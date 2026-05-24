"""Reads hermes/prompts/*.{j2,txt} — emits one PROMPT node per file (verbatim
copy of the OpenClaw prompts analyzer, with `hermes` provenance)."""

from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Node, NodeKind, Provenance, make_node_id


class HermesPromptsAnalyzer(Analyzer):
    name = "hermes.prompts"

    def analyze(self, hermes_root: Path) -> IRGraph:
        ir = IRGraph()
        prompt_dir = hermes_root / "prompts"
        if not prompt_dir.exists():
            return ir
        for path in sorted(list(prompt_dir.glob("*.j2")) + list(prompt_dir.glob("*.txt"))):
            name = path.stem
            body = path.read_text(encoding="utf-8")
            ir.nodes.append(
                Node(
                    id=make_node_id("hermes", NodeKind.PROMPT, name),
                    kind=NodeKind.PROMPT,
                    name=name,
                    description=body.strip().splitlines()[0][:160] if body.strip() else None,
                    provenance=Provenance(
                        framework="hermes",
                        source_file=str(path.relative_to(path.parents[1])),
                        original_kind="prompt_template",
                    ),
                    metadata={"body": body, "format": path.suffix.lstrip(".")},
                )
            )
        return ir
