"""Tests for the env-var secret classifier and its report rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from praxis_core.analyzers.openclaw import analyze_openclaw_project
from praxis_core.analyzers.openclaw.env import is_likely_secret
from praxis_core.ir.models import NodeKind
from praxis_core.pipeline import build_ir
from praxis_core.reports import render_migration_report


@pytest.mark.parametrize(
    "name",
    [
        "OPENAI_API_KEY",
        "JIRA_TOKEN",
        "DATABASE_PASSWORD",
        "AUTH_SECRET",
        "SESSION_COOKIE",
        "PRIVATE_KEY",
        "STRIPE_BEARER",
    ],
)
def test_secret_names_are_classified(name: str) -> None:
    assert is_likely_secret(name)


@pytest.mark.parametrize(
    "name",
    [
        "RSS_URL",
        "JIRA_BASE_URL",
        "SLACK_CHANNEL",
        "API_URL",
        "POSTGRES_HOST",
        "PORT",
        "KEYWORD",  # contains "KEY" but not as a whole segment
        "MONKEY_BUSINESS",
    ],
)
def test_config_names_are_not_classified_as_secret(name: str) -> None:
    assert not is_likely_secret(name)


def test_analyzer_stamps_secret_metadata(sample_root: Path) -> None:
    ir = analyze_openclaw_project(sample_root)
    envs = {
        n.name: n
        for n in ir.nodes
        if (n.kind.value if hasattr(n.kind, "value") else n.kind) == NodeKind.ENV.value
    }
    assert envs["OPENAI_API_KEY"].metadata["secret"] is True
    assert envs["JIRA_TOKEN"].metadata["secret"] is True
    assert envs["RSS_URL"].metadata["secret"] is False
    assert envs["SLACK_CHANNEL"].metadata["secret"] is False
    assert envs["OPENAI_API_KEY"].metadata["classification"] == "secret"
    assert envs["RSS_URL"].metadata["classification"] == "config"


def test_report_separates_secrets_from_config(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    body = render_migration_report(ir)
    assert "### Secrets (credential-like names" in body
    assert "🔐 `OPENAI_API_KEY`" in body
    assert "🔐 `JIRA_TOKEN`" in body
    assert "### Configuration" in body
    # RSS_URL is config and should appear in the configuration list, not the secrets list.
    assert "- `RSS_URL`" in body
