"""Shared test fixtures. The OpenClaw sample under examples/ is the canonical input
for all integration tests; unit tests build smaller fixtures inline.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Walk up from this file until we find the repo root (the directory containing schemas/)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "schemas" / "praxis-ir.schema.json").exists():
            return parent
    raise RuntimeError("Could not locate repo root from test file.")


@pytest.fixture(scope="session")
def sample_root(repo_root: Path) -> Path:
    return repo_root / "examples" / "openclaw-sample"


@pytest.fixture()
def tmp_out(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    return out
