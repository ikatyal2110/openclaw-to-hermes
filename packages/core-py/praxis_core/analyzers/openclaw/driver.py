"""Drives all OpenClaw analyzers in order and returns one merged IRGraph."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from praxis_core.analyzers.openclaw.env import EnvAnalyzer
from praxis_core.analyzers.openclaw.memory import MemoryAnalyzer
from praxis_core.analyzers.openclaw.plugins import PluginsAnalyzer
from praxis_core.analyzers.openclaw.project import ProjectAnalyzer
from praxis_core.analyzers.openclaw.prompts import PromptsAnalyzer
from praxis_core.analyzers.openclaw.services import ServicesAnalyzer
from praxis_core.analyzers.openclaw.workflows import WorkflowsAnalyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Project


def analyze_openclaw_project(root: Path) -> IRGraph:
    """Run every OpenClaw analyzer and merge into a single IR (pre-resolve)."""
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Project root not found: {root}")

    project_meta = ProjectAnalyzer().read(root)
    analyzers = [
        EnvAnalyzer(),
        WorkflowsAnalyzer(),
        PluginsAnalyzer(),
        PromptsAnalyzer(),
        MemoryAnalyzer(),
        ServicesAnalyzer(),
    ]

    merged = IRGraph(
        project=Project(
            name=project_meta.get("name") if project_meta else root.name,
            source_framework="openclaw",
            source_root=str(root.resolve()),
            analyzed_at=datetime.now(timezone.utc),
        )
    )

    for analyzer in analyzers:
        partial = analyzer.analyze(root)
        merged.nodes.extend(partial.nodes)
        merged.edges.extend(partial.edges)
        merged.diagnostics.extend(partial.diagnostics)

    return merged
