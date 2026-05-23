"""Analyzer contract.

An Analyzer takes a project root and emits a partial IRGraph: nodes and edges
that originate from a specific domain (workflows, plugins, prompts, ...).
References to other domains are emitted as edges keyed by *intended* node IDs;
the resolver stitches them later.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from praxis_core.ir import IRGraph


class Analyzer(ABC):
    """Subclass and implement analyze(). Name must be unique per source framework."""

    name: str = ""

    @abstractmethod
    def analyze(self, root: Path) -> IRGraph:
        """Read the project at `root` and return a partial IRGraph."""

    @staticmethod
    def safe_load_yaml(path: Path) -> dict | list | None:
        import yaml

        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
