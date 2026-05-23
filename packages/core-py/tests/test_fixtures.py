"""Golden-file regression test for the baseline fixture.

Locks the IR + emitted Hermes tree + Mermaid graph against
`tools/fixtures/baseline/expected/`. Two fields in `ir.json` —
`project.analyzed_at` and `project.source_root` — are normalized before
comparison because they vary across runs and checkouts.

When the snapshot legitimately needs to change, regenerate with:

    praxis migrate examples/openclaw-sample --out /tmp/golden
    # then refresh tools/fixtures/baseline/expected/ from /tmp/golden,
    # normalizing project.analyzed_at and project.source_root in ir.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from praxis_core.pipeline import migrate


@pytest.fixture(scope="module")
def baseline_dir(repo_root: Path) -> Path:
    return repo_root / "tools" / "fixtures" / "baseline"


@pytest.fixture(scope="module")
def actual_out(sample_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("baseline-actual")
    migrate(sample_root, out)
    return out


def _normalize_ir(raw: str) -> dict:
    d = json.loads(raw)
    d["project"]["analyzed_at"] = "NORMALIZED"
    d["project"]["source_root"] = "NORMALIZED"
    return d


def test_ir_matches_golden(actual_out: Path, baseline_dir: Path) -> None:
    actual = _normalize_ir((actual_out / "ir.json").read_text())
    expected = json.loads((baseline_dir / "expected" / "ir.json").read_text())
    assert actual == expected


def test_architecture_mmd_matches_golden(actual_out: Path, baseline_dir: Path) -> None:
    actual = (actual_out / "architecture.mmd").read_text()
    expected = (baseline_dir / "expected" / "architecture.mmd").read_text()
    assert actual == expected


def test_hermes_tree_matches_golden(actual_out: Path, baseline_dir: Path) -> None:
    expected_root = baseline_dir / "expected" / "hermes"
    actual_root = actual_out / "hermes"

    expected_files = sorted(p.relative_to(expected_root) for p in expected_root.rglob("*") if p.is_file())
    actual_files = sorted(p.relative_to(actual_root) for p in actual_root.rglob("*") if p.is_file())
    assert actual_files == expected_files, "Hermes file set diverged from golden."

    for rel in expected_files:
        assert (actual_root / rel).read_text() == (expected_root / rel).read_text(), (
            f"Content mismatch in hermes/{rel}"
        )
