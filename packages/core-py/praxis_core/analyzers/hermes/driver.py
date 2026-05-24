"""Drives all Hermes analyzers in order and returns one merged IRGraph.

Mirrors `analyzers/openclaw/driver.py`. The same error-wrapping pattern (PRX001
for YAML, PRX002 for everything else) so a broken Hermes file surfaces as a
diagnostic, not a stack trace.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from praxis_core.analyzers.base import Analyzer
from praxis_core.analyzers.hermes.memory import HermesMemoryAnalyzer
from praxis_core.analyzers.hermes.prompts import HermesPromptsAnalyzer
from praxis_core.analyzers.hermes.schedules import HermesSchedulesAnalyzer
from praxis_core.analyzers.hermes.skills import HermesSkillsAnalyzer
from praxis_core.analyzers.hermes.tools import HermesToolsAnalyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Diagnostic, Project


def analyze_hermes_project(root: Path) -> IRGraph:
    """Run every Hermes analyzer and merge into a single IR (pre-resolve).

    Accepts either a path containing `hermes/` (which is the directory layout
    `praxis migrate` writes) OR the inner `hermes/` directory itself.
    """
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Project root not found: {root}")

    hermes_root = root / "hermes" if (root / "hermes").is_dir() else root

    analyzers: list[Analyzer] = [
        HermesSkillsAnalyzer(),
        HermesToolsAnalyzer(),
        HermesMemoryAnalyzer(),
        HermesSchedulesAnalyzer(),
        HermesPromptsAnalyzer(),
    ]

    merged = IRGraph(
        project=Project(
            name=root.name,
            source_framework="hermes",
            source_root=str(root.resolve()),
            analyzed_at=datetime.now(UTC),
        )
    )

    for analyzer in analyzers:
        try:
            partial = analyzer.analyze(hermes_root)
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


# Re-export for typing.
_ = Any
