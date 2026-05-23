"""End-to-end pipeline orchestration.

Each function here corresponds to a CLI subcommand's heavy lifting and is the
unit subcommand handlers test against.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from praxis_core.analyzers.openclaw import analyze_openclaw_project
from praxis_core.emitters import emit_hermes_project
from praxis_core.ir import IRGraph
from praxis_core.reports import render_mermaid_graph, render_migration_report
from praxis_core.resolver import resolve
from praxis_core.scoring import score_portability
from praxis_core.translators import translate_openclaw_to_hermes


def build_ir(source_root: Path) -> IRGraph:
    """Stages 1–4: scan → analyze → resolve → score."""
    ir = analyze_openclaw_project(source_root)
    resolve(ir)
    score_portability(ir)
    ir.sort()
    return ir


def ir_to_json(ir: IRGraph) -> str:
    return json.dumps(ir.to_json_dict(), indent=2, sort_keys=True)


def migrate(source_root: Path, out_root: Path) -> dict[str, Any]:
    """Stages 1–6: build IR, translate to Hermes, emit project + report + graph + ir.json."""
    ir = build_ir(source_root)
    project = translate_openclaw_to_hermes(ir)

    out_root.mkdir(parents=True, exist_ok=True)
    written = emit_hermes_project(project, out_root)

    (out_root / "MIGRATION_REPORT.md").write_text(render_migration_report(ir), encoding="utf-8")
    (out_root / "architecture.mmd").write_text(render_mermaid_graph(ir), encoding="utf-8")
    (out_root / "ir.json").write_text(ir_to_json(ir), encoding="utf-8")

    return {
        "ir_path": str(out_root / "ir.json"),
        "report_path": str(out_root / "MIGRATION_REPORT.md"),
        "graph_path": str(out_root / "architecture.mmd"),
        "written": written,
    }
