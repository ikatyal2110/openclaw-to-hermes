"""Smoke tests for the user-facing CLI. Catches argv wiring and exit-code regressions."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from praxis_core.cli import app

runner = CliRunner()


def test_cli_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "praxis" in result.output.lower()


def test_cli_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "praxis" in result.output
    assert "IR schema" in result.output


def test_cli_version_short_flag() -> None:
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0


def test_cli_doctor_passes() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output
    assert "praxis-core" in result.output
    assert "IR JSON schema" in result.output


def test_cli_init_creates_scannable_project(tmp_path: Path) -> None:
    target = tmp_path / "init-test"
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 0
    # Required directories exist
    for sub in ("workflows", "plugins", "prompts", "memory"):
        assert (target / sub).is_dir()
    # openclaw.yaml has the right name
    body = (target / "openclaw.yaml").read_text()
    assert "name: my-agent" in body
    # And the scaffold actually scans cleanly
    scan = runner.invoke(app, ["scan", str(target)])
    assert scan.exit_code == 0
    assert "hello" in scan.output
    assert "1 error(s)" not in scan.output


def test_cli_init_refuses_existing_dir_without_force(tmp_path: Path) -> None:
    target = tmp_path / "preexisting"
    target.mkdir()
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_cli_scan_json_output(sample_root: Path) -> None:
    result = runner.invoke(app, ["scan", str(sample_root), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["node_count"] > 0
    assert "tier_counts" in payload
    assert "nodes" in payload and isinstance(payload["nodes"], list)


def test_cli_explain_json_output(sample_root: Path) -> None:
    result = runner.invoke(app, ["explain", str(sample_root), "dedupe_seen", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["node"]["name"] == "dedupe_seen"
    assert payload["edges_in"]
    assert payload["edges_out"]


def test_cli_init_force_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "preexisting"
    target.mkdir()
    result = runner.invoke(app, ["init", str(target), "--force", "--name", "forced"])
    assert result.exit_code == 0
    assert "name: forced" in (target / "openclaw.yaml").read_text()


def test_cli_explain_by_name(sample_root: Path) -> None:
    result = runner.invoke(app, ["explain", str(sample_root), "dedupe_seen"])
    assert result.exit_code == 0
    assert "tool.dedupe_seen" in result.output
    assert "portability:" in result.output
    assert "needs_review" in result.output
    assert "edges:" in result.output


def test_cli_explain_unknown_node_returns_nonzero(sample_root: Path) -> None:
    result = runner.invoke(app, ["explain", str(sample_root), "nonexistent_thing"])
    assert result.exit_code == 1
    assert "No node matches" in result.output


def test_cli_explain_by_full_id(sample_root: Path) -> None:
    # First scan to discover an ID, then explain by it.
    scan_result = runner.invoke(app, ["scan", str(sample_root), "--emit-ir", "/tmp/_pxe.json"])
    assert scan_result.exit_code == 0
    payload = json.loads(Path("/tmp/_pxe.json").read_text())
    tool_node = next(n for n in payload["nodes"] if n["kind"] == "tool")
    result = runner.invoke(app, ["explain", str(sample_root), tool_node["id"]])
    assert result.exit_code == 0
    assert tool_node["id"] in result.output


def test_cli_scan_prints_summary(sample_root: Path) -> None:
    result = runner.invoke(app, ["scan", str(sample_root)])
    assert result.exit_code == 0
    assert "daily_digest" in result.output
    assert "fetch_articles" in result.output


def test_cli_scan_emits_ir(sample_root: Path, tmp_path: Path) -> None:
    ir_path = tmp_path / "ir.json"
    result = runner.invoke(app, ["scan", str(sample_root), "--emit-ir", str(ir_path)])
    assert result.exit_code == 0
    payload = json.loads(ir_path.read_text())
    assert payload["praxis_ir_version"] == "0.1"
    assert len(payload["nodes"]) > 0


def test_cli_graph_mermaid_format(sample_root: Path) -> None:
    result = runner.invoke(app, ["graph", str(sample_root), "--format", "mermaid"])
    assert result.exit_code == 0
    assert result.output.startswith("flowchart LR")


def test_cli_graph_unknown_format_exits_nonzero(sample_root: Path) -> None:
    result = runner.invoke(app, ["graph", str(sample_root), "--format", "bogus"])
    assert result.exit_code != 0


def test_cli_report_prints_markdown(sample_root: Path) -> None:
    result = runner.invoke(app, ["report", str(sample_root)])
    assert result.exit_code == 0
    assert "# Migration report" in result.output


def test_cli_migrate_writes_output_tree(sample_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["migrate", str(sample_root), "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "MIGRATION_REPORT.md").exists()
    assert (out / "hermes" / "skills" / "daily_digest.yaml").exists()


def test_cli_migrate_unknown_target_exits_nonzero(sample_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["migrate", str(sample_root), "--target", "langgraph", "--out", str(out)]
    )
    assert result.exit_code != 0


def test_cli_ir_validate_passes_for_generated_ir(sample_root: Path, tmp_path: Path) -> None:
    ir_path = tmp_path / "ir.json"
    runner.invoke(app, ["scan", str(sample_root), "--emit-ir", str(ir_path)])
    result = runner.invoke(app, ["ir", "validate", str(ir_path)])
    assert result.exit_code == 0


def test_cli_ir_diff_detects_no_change(sample_root: Path, tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    runner.invoke(app, ["scan", str(sample_root), "--emit-ir", str(a)])
    runner.invoke(app, ["scan", str(sample_root), "--emit-ir", str(b)])
    result = runner.invoke(app, ["ir", "diff", str(a), str(b)])
    assert result.exit_code == 0
    assert "No differences" in result.output


def test_cli_skills_extract_default_threshold(sample_root: Path) -> None:
    result = runner.invoke(app, ["skills", "extract", str(sample_root)])
    assert result.exit_code == 0
    assert "6 prompt(s) scanned" in result.output
    assert "3 cluster(s)" in result.output
    assert "summarize_weekly" in result.output
    assert "classify_email" in result.output
    assert "extract_entities_v2" in result.output
    # Tool-sequence section: daily_digest and weekly_digest share the full 4-step chain.
    assert "3 workflow(s) scanned" in result.output
    assert "1 repeated sequence(s)" in result.output
    assert "fetch_articles" in result.output and "slack_post" in result.output


def test_cli_skills_extract_high_threshold_collapses(sample_root: Path) -> None:
    result = runner.invoke(app, ["skills", "extract", str(sample_root), "--threshold", "0.95"])
    assert result.exit_code == 0
    assert "0 cluster(s)" in result.output


def test_cli_skills_extract_writes_report(sample_root: Path, tmp_path: Path) -> None:
    report_path = tmp_path / "extract.md"
    result = runner.invoke(
        app, ["skills", "extract", str(sample_root), "--report", str(report_path)]
    )
    assert result.exit_code == 0
    assert report_path.exists()
    body = report_path.read_text()
    assert "# Skills extract report" in body
    assert "Prompts scanned:** 6" in body
    assert "Workflows scanned:** 3" in body
    assert all(f"### Cluster {i}" in body for i in (1, 2, 3))
    # The extract_entities pair (~0.90) should trigger the near-duplicate suggestion tier.
    assert "Near-duplicate prompts" in body
    # The summarize pair (~0.63) hits the strong-overlap tier.
    assert "Strong structural overlap" in body
    # The classify pair (~0.54) hits the loose-family tier.
    assert "Loose family resemblance" in body
    # Tool sequence section: daily_digest/weekly_digest share the full chain.
    assert "## Repeated tool sequences" in body
    assert "### Sequence 1" in body
    assert "Strong factor-out candidate" in body
