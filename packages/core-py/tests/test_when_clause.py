"""Verify that when: clauses in workflow steps survive translation."""

from __future__ import annotations

from pathlib import Path

from praxis_core.pipeline import build_ir
from praxis_core.translators import translate_openclaw_to_hermes


def _make_project_with_when_clause(tmp_path: Path) -> Path:
    project = tmp_path / "branchy"
    (project / "workflows").mkdir(parents=True)
    (project / "plugins").mkdir()
    (project / "workflows" / "branchy.yaml").write_text(
        """name: branchy
description: "Conditional triage."
steps:
  - id: classify
    plugin: classify_email
  - id: escalate
    plugin: page_oncall
    when: "${steps.classify.output.priority == 'high'}"
"""
    )
    (project / "plugins" / "classify_email.yaml").write_text(
        "name: classify_email\nruntime: http\nspec: {url: http://x}\n"
    )
    (project / "plugins" / "page_oncall.yaml").write_text(
        "name: page_oncall\nruntime: http\nspec: {url: http://y}\n"
    )
    return project


def test_when_clause_survives_into_procedure(tmp_path: Path) -> None:
    project = _make_project_with_when_clause(tmp_path)
    ir = build_ir(project)
    hermes = translate_openclaw_to_hermes(ir)
    skill = next(s for s in hermes.skills if s.name == "branchy")
    escalate = next(p for p in skill.procedure if p.get("as") == "escalate")
    assert "_praxis_when" in escalate
    assert "high" in escalate["_praxis_when"]


def test_when_clause_produces_todo(tmp_path: Path) -> None:
    project = _make_project_with_when_clause(tmp_path)
    ir = build_ir(project)
    hermes = translate_openclaw_to_hermes(ir)
    skill = next(s for s in hermes.skills if s.name == "branchy")
    assert any("_praxis_when" in todo for todo in skill.todos)


def test_step_without_when_clause_has_no_praxis_when(tmp_path: Path) -> None:
    project = _make_project_with_when_clause(tmp_path)
    ir = build_ir(project)
    hermes = translate_openclaw_to_hermes(ir)
    skill = next(s for s in hermes.skills if s.name == "branchy")
    classify = next(p for p in skill.procedure if p.get("as") == "classify")
    assert "_praxis_when" not in classify


def _make_project_with_for_each(tmp_path: Path) -> Path:
    project = tmp_path / "loopy"
    (project / "workflows").mkdir(parents=True)
    (project / "plugins").mkdir()
    (project / "workflows" / "loopy.yaml").write_text(
        """name: loopy
description: "Process each item in a list."
steps:
  - id: fetch
    plugin: fetch_articles
  - id: process
    plugin: process_one
    for_each: "${steps.fetch.output.items}"
"""
    )
    (project / "plugins" / "fetch_articles.yaml").write_text(
        "name: fetch_articles\nruntime: http\nspec: {url: http://x}\n"
    )
    (project / "plugins" / "process_one.yaml").write_text(
        "name: process_one\nruntime: http\nspec: {url: http://y}\n"
    )
    return project


def test_for_each_survives_into_procedure(tmp_path: Path) -> None:
    project = _make_project_with_for_each(tmp_path)
    ir = build_ir(project)
    hermes = translate_openclaw_to_hermes(ir)
    skill = next(s for s in hermes.skills if s.name == "loopy")
    process = next(p for p in skill.procedure if p.get("as") == "process")
    assert "_praxis_for_each" in process
    assert "items" in process["_praxis_for_each"]


def test_for_each_produces_todo(tmp_path: Path) -> None:
    project = _make_project_with_for_each(tmp_path)
    ir = build_ir(project)
    hermes = translate_openclaw_to_hermes(ir)
    skill = next(s for s in hermes.skills if s.name == "loopy")
    assert any("_praxis_for_each" in todo for todo in skill.todos)
