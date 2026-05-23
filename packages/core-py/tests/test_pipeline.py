"""End-to-end: scan → migrate. The single best regression net for the project."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from praxis_core.pipeline import build_ir, migrate
from praxis_core.reports import render_mermaid_graph, render_migration_report


def test_migrate_writes_expected_files(sample_root: Path, tmp_out: Path) -> None:
    result = migrate(sample_root, tmp_out)
    assert Path(result["report_path"]).exists()
    assert Path(result["graph_path"]).exists()
    assert Path(result["ir_path"]).exists()
    assert (tmp_out / "hermes" / "skills" / "daily_digest.yaml").exists()
    assert (tmp_out / "hermes" / "skills" / "support_triage.yaml").exists()
    assert (tmp_out / "hermes" / "schedules" / "daily_digest.yaml").exists()
    assert (tmp_out / "hermes" / "memory" / "seen_articles.yaml").exists()
    assert (tmp_out / "hermes" / "prompts" / "summarize.j2").exists()


def test_ir_json_validates_against_schema(repo_root: Path, sample_root: Path, tmp_out: Path) -> None:
    migrate(sample_root, tmp_out)
    schema = json.loads((repo_root / "schemas" / "praxis-ir.schema.json").read_text())
    ir_payload = json.loads((tmp_out / "ir.json").read_text())
    jsonschema.validate(ir_payload, schema)


def test_emitted_skill_yaml_is_well_formed(sample_root: Path, tmp_out: Path) -> None:
    migrate(sample_root, tmp_out)
    skill = yaml.safe_load((tmp_out / "hermes" / "skills" / "daily_digest.yaml").read_text())
    assert skill["name"] == "daily_digest"
    assert isinstance(skill["procedure"], list)
    assert skill["procedure"][0]["tool"] == "fetch_articles"


def test_emitted_schedule_points_to_skill(sample_root: Path, tmp_out: Path) -> None:
    migrate(sample_root, tmp_out)
    sched = yaml.safe_load((tmp_out / "hermes" / "schedules" / "daily_digest.yaml").read_text())
    assert sched["invoke_skill"] == "daily_digest"
    assert sched["cron"] == "0 9 * * *"


def test_emitted_tool_yaml_is_well_formed(sample_root: Path, tmp_out: Path) -> None:
    migrate(sample_root, tmp_out)
    tool = yaml.safe_load((tmp_out / "hermes" / "tools" / "fetch_articles.yaml").read_text())
    assert tool["name"] == "fetch_articles"
    assert tool["runtime"] == "http"


def test_report_contains_summary_and_todos(sample_root: Path, tmp_out: Path) -> None:
    migrate(sample_root, tmp_out)
    report = (tmp_out / "MIGRATION_REPORT.md").read_text()
    assert "# Migration report" in report
    assert "## Summary" in report
    assert "## TODOs" in report


def test_pipeline_is_deterministic(sample_root: Path, tmp_path: Path) -> None:
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    out1.mkdir()
    out2.mkdir()
    migrate(sample_root, out1)
    migrate(sample_root, out2)
    ir1 = json.loads((out1 / "ir.json").read_text())
    ir2 = json.loads((out2 / "ir.json").read_text())
    # analyzed_at differs; everything else must be identical.
    for ir in (ir1, ir2):
        ir.get("project", {}).pop("analyzed_at", None)
    assert ir1 == ir2


def test_mermaid_render_is_a_flowchart(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    mermaid = render_mermaid_graph(ir)
    assert mermaid.splitlines()[0] == "flowchart LR"


def test_report_render_does_not_crash_on_empty_ir() -> None:
    from praxis_core.ir import IRGraph

    out = render_migration_report(IRGraph())
    assert "# Migration report" in out
