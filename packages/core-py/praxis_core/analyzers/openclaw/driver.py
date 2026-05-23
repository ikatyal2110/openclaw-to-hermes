"""Drives all OpenClaw analyzers in order and returns one merged IRGraph."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from praxis_core.analyzers.base import Analyzer
from praxis_core.analyzers.openclaw.env import EnvAnalyzer
from praxis_core.analyzers.openclaw.memory import MemoryAnalyzer
from praxis_core.analyzers.openclaw.plugins import PluginsAnalyzer
from praxis_core.analyzers.openclaw.project import ProjectAnalyzer
from praxis_core.analyzers.openclaw.prompts import PromptsAnalyzer
from praxis_core.analyzers.openclaw.services import ServicesAnalyzer
from praxis_core.analyzers.openclaw.workflows import WorkflowsAnalyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Diagnostic, Project


def analyze_openclaw_project(root: Path) -> IRGraph:
    """Run every OpenClaw analyzer and merge into a single IR (pre-resolve).

    Analyzers that raise are caught and converted to PRX001 diagnostics with
    file:line context where available. A broken YAML file should never crash
    Praxis — it should surface in the report as a fixable error.
    """
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Project root not found: {root}")

    project_meta: dict[str, Any] | None = None
    project_diagnostics: list[Diagnostic] = []
    try:
        project_meta = ProjectAnalyzer().read(root)
    except yaml.YAMLError as exc:
        project_diagnostics.append(_yaml_diagnostic("openclaw.project", exc))
    except Exception as exc:  # noqa: BLE001 — boundary collection
        project_diagnostics.append(_generic_diagnostic("openclaw.project", exc))

    analyzers: list[Analyzer] = [
        EnvAnalyzer(),
        WorkflowsAnalyzer(),
        PluginsAnalyzer(),
        PromptsAnalyzer(),
        MemoryAnalyzer(),
        ServicesAnalyzer(),
    ]

    merged = IRGraph(
        project=Project(
            name=(project_meta or {}).get("name") if project_meta else root.name,
            source_framework="openclaw",
            source_root=str(root.resolve()),
            analyzed_at=datetime.now(UTC),
        )
    )
    merged.diagnostics.extend(project_diagnostics)

    for analyzer in analyzers:
        try:
            partial = analyzer.analyze(root)
        except yaml.YAMLError as exc:
            merged.diagnostics.append(_yaml_diagnostic(analyzer.name, exc))
            continue
        except Exception as exc:  # noqa: BLE001 — boundary collection
            merged.diagnostics.append(_generic_diagnostic(analyzer.name, exc))
            continue
        merged.nodes.extend(partial.nodes)
        merged.edges.extend(partial.edges)
        merged.diagnostics.extend(partial.diagnostics)

    return merged


def _yaml_diagnostic(analyzer_name: str, exc: yaml.YAMLError) -> Diagnostic:
    where = ""
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        where = f" in {mark.name}, line {mark.line + 1}, column {mark.column + 1}"
    return Diagnostic(
        level="error",
        code="PRX001",
        message=f"{analyzer_name}: YAML parse error{where}: {exc!s}",
        hint="Open the file in your editor; the YAML linter usually points at the same line.",
    )


def _generic_diagnostic(analyzer_name: str, exc: Exception) -> Diagnostic:
    return Diagnostic(
        level="error",
        code="PRX002",
        message=f"{analyzer_name}: {type(exc).__name__}: {exc!s}",
        hint=(
            "Open an issue with the failing project minimally reduced; this likely indicates "
            "either a malformed manifest or a Praxis bug."
        ),
    )
