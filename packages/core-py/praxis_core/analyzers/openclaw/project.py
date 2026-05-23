"""Reads openclaw.yaml — project metadata only. Other analyzers handle their own files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph


class ProjectAnalyzer(Analyzer):
    name = "openclaw.project"

    def read(self, root: Path) -> dict[str, Any] | None:
        loaded = self.safe_load_yaml(root / "openclaw.yaml")
        return loaded if isinstance(loaded, dict) else None

    def analyze(self, root: Path) -> IRGraph:
        return IRGraph()
