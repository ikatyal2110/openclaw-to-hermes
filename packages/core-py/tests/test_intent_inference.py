"""Tests for the static intent-inference heuristics in WorkflowsAnalyzer."""

from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.openclaw import analyze_openclaw_project


def _project(tmp_path: Path, name: str, workflow_yaml: str) -> Path:
    project = tmp_path / name
    (project / "workflows").mkdir(parents=True)
    (project / "workflows" / f"{name}.yaml").write_text(workflow_yaml)
    return project


def _intent(tmp_path: Path, name: str, workflow_yaml: str):
    ir = analyze_openclaw_project(_project(tmp_path, name, workflow_yaml))
    wf = next(n for n in ir.nodes if n.name == name)
    return wf.intent


def test_explicit_long_description_is_high_confidence(tmp_path: Path) -> None:
    intent = _intent(
        tmp_path,
        "wf_one",
        "name: wf_one\ndescription: A clear sentence about what this workflow does in production.\n",
    )
    assert intent is not None
    assert intent.confidence == 0.95


def test_placeholder_description_reduces_confidence(tmp_path: Path) -> None:
    intent = _intent(tmp_path, "wf_two", "name: wf_two\ndescription: TODO\n")
    assert intent is not None
    assert intent.confidence == 0.5
    assert any("placeholder" in e.lower() for e in intent.evidence)


def test_short_description_reduces_confidence(tmp_path: Path) -> None:
    intent = _intent(tmp_path, "wf_three", "name: wf_three\ndescription: do thing\n")
    assert intent is not None
    assert intent.confidence == 0.5


def test_cron_trigger_inferred_when_no_description(tmp_path: Path) -> None:
    intent = _intent(
        tmp_path,
        "nightly_etl",
        "name: nightly_etl\ntriggers:\n  - kind: cron\n    spec: '0 2 * * *'\n",
    )
    assert intent is not None
    assert "scheduled" in intent.description or "nightly" in intent.description
    assert intent.confidence >= 0.5


def test_name_cadence_pattern_picked_up(tmp_path: Path) -> None:
    intent = _intent(
        tmp_path,
        "daily_report",
        "name: daily_report\nsteps:\n  - id: a\n    plugin: build_report\n",
    )
    assert intent is not None
    assert "daily" in intent.description.lower()


def test_plugin_verbs_extracted(tmp_path: Path) -> None:
    intent = _intent(
        tmp_path,
        "pipeline",
        """name: pipeline
steps:
  - id: a
    plugin: fetch_articles
  - id: b
    plugin: classify_topic
  - id: c
    plugin: slack_post
""",
    )
    assert intent is not None
    # Each plugin-name verb should appear in the description.
    assert "fetch" in intent.description
    assert "classify" in intent.description
    assert "post" in intent.description


def test_webhook_triggers_raise_confidence(tmp_path: Path) -> None:
    intent = _intent(
        tmp_path,
        "incoming",
        """name: incoming
triggers:
  - kind: webhook
    path: /hook
steps:
  - id: a
    plugin: fetch_data
""",
    )
    assert intent is not None
    assert intent.confidence > 0.5
