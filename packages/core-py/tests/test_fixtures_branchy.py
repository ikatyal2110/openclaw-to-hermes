"""Golden-file regression test for the branchy fixture.

Locks the `when:` / `for_each` / `retry:` preservation paths against the
`tools/fixtures/branchy/expected/` tree. Mirrors test_fixtures.py for the
baseline fixture, but with its own source/+expected/ pair.

To refresh the golden when output legitimately changes:

    praxis migrate tools/fixtures/branchy/source --out /tmp/branchy-refresh
    # Then refresh tools/fixtures/branchy/expected/ from /tmp/branchy-refresh,
    # normalizing project.analyzed_at and project.source_root in ir.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from praxis_core.pipeline import migrate


@pytest.fixture(scope="module")
def branchy_fixture_dir(repo_root: Path) -> Path:
    return repo_root / "tools" / "fixtures" / "branchy"


@pytest.fixture(scope="module")
def branchy_actual(branchy_fixture_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("branchy-actual")
    migrate(branchy_fixture_dir / "source", out)
    return out


def _normalize_ir(raw: str) -> dict:
    d = json.loads(raw)
    d["project"]["analyzed_at"] = "NORMALIZED"
    d["project"]["source_root"] = "NORMALIZED"
    return d


def test_branchy_ir_matches_golden(branchy_actual: Path, branchy_fixture_dir: Path) -> None:
    actual = _normalize_ir((branchy_actual / "ir.json").read_text())
    expected = json.loads((branchy_fixture_dir / "expected" / "ir.json").read_text())
    assert actual == expected


def test_branchy_mmd_matches_golden(branchy_actual: Path, branchy_fixture_dir: Path) -> None:
    actual = (branchy_actual / "architecture.mmd").read_text()
    expected = (branchy_fixture_dir / "expected" / "architecture.mmd").read_text()
    assert actual == expected


def test_branchy_hermes_tree_matches_golden(
    branchy_actual: Path, branchy_fixture_dir: Path
) -> None:
    expected_root = branchy_fixture_dir / "expected" / "hermes"
    actual_root = branchy_actual / "hermes"
    expected_files = sorted(
        p.relative_to(expected_root) for p in expected_root.rglob("*") if p.is_file()
    )
    actual_files = sorted(p.relative_to(actual_root) for p in actual_root.rglob("*") if p.is_file())
    assert actual_files == expected_files
    for rel in expected_files:
        assert (actual_root / rel).read_text() == (expected_root / rel).read_text(), (
            f"Content mismatch in hermes/{rel}"
        )


def test_branchy_skill_carries_all_three_preservation_keys(
    branchy_fixture_dir: Path,
) -> None:
    """Sanity check that the locked output actually exercises all three constructs."""
    skill_yaml = (
        branchy_fixture_dir / "expected" / "hermes" / "skills" / "incident_response.yaml"
    ).read_text()
    assert "_praxis_when" in skill_yaml
    assert "_praxis_for_each" in skill_yaml
    assert "_praxis_retry" in skill_yaml
