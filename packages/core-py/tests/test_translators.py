"""Translators turn the resolved-and-scored IR into a HermesProject."""

from __future__ import annotations

from pathlib import Path

from praxis_core.pipeline import build_ir
from praxis_core.translators import translate_openclaw_to_hermes


def test_translator_produces_one_skill_per_workflow(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    skill_names = sorted(s.name for s in project.skills)
    assert skill_names == ["daily_digest", "support_triage", "weekly_digest"]


def test_translator_emits_tools_for_each_plugin(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    names = {t.name for t in project.tools}
    for expected in [
        "fetch_articles",
        "dedupe_seen",
        "llm_summarize",
        "slack_post",
        "classify_ticket",
        "ticket_router",
    ]:
        assert expected in names


def test_cron_translates_to_schedule(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    schedules = [s for s in project.schedules if s.invoke_skill == "daily_digest"]
    assert len(schedules) == 1
    assert schedules[0].cron == "0 9 * * *"


def test_webhook_does_not_translate_to_schedule(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    assert not any(s.invoke_skill == "support_triage" for s in project.schedules)


def test_skill_procedure_preserves_step_order(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    daily = next(s for s in project.skills if s.name == "daily_digest")
    tools_in_order = [step["tool"] for step in daily.procedure]
    assert tools_in_order == ["fetch_articles", "dedupe_seen", "llm_summarize", "slack_post"]


def test_skill_inputs_derived_from_env_refs(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    daily = next(s for s in project.skills if s.name == "daily_digest")
    assert "rss_url" in daily.inputs
    assert daily.inputs["rss_url"]["env"] == "RSS_URL"
    assert "slack_channel" in daily.inputs


def test_skill_data_flow_uses_step_aliases(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    daily = next(s for s in project.skills if s.name == "daily_digest")
    dedupe_step = next(s for s in daily.procedure if s["tool"] == "dedupe_seen")
    assert dedupe_step["with"]["items"] == "${fetch}"


def test_memory_translates_kv_verbatim(sample_root: Path) -> None:
    ir = build_ir(sample_root)
    project = translate_openclaw_to_hermes(ir)
    seen = next(m for m in project.memories if m.name == "seen_articles")
    assert seen.kind == "kv"
    assert seen.fields.get("ttl_seconds") == 604800


def test_unsupported_memory_is_not_emitted() -> None:
    """SQL memory is unsupported and must not appear in the translated project."""
    from praxis_core.ir import IRGraph
    from praxis_core.ir.models import Node, NodeKind, Portability, PortabilityTier, Provenance
    from praxis_core.translators import translate_openclaw_to_hermes

    ir = IRGraph()
    n = Node(
        id="memory_store.x.aaaa",
        kind=NodeKind.MEMORY_STORE,
        name="x",
        provenance=Provenance(framework="openclaw"),
        metadata={"spec": {"kind": "sql"}},
        portability=Portability(score=0.0, tier=PortabilityTier.UNSUPPORTED, rationale="..."),
    )
    ir.nodes.append(n)
    project = translate_openclaw_to_hermes(ir)
    assert project.memories == []
