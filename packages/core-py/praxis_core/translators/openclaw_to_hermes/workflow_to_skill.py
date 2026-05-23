"""OpenClaw workflow → Hermes skill.

Skills are the highest-leverage translation: workflow steps become a `procedure`,
intent becomes `description`, and inferred triggers become `when_to_use` entries.
Confidence interacts with portability — see docs/migration-model.md.
"""
from __future__ import annotations

import re
from typing import Any

from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind, PortabilityTier
from praxis_core.translators.openclaw_to_hermes.types import HermesProject, HermesSkill

ENV_REF = re.compile(r"\$\{env\.([A-Z0-9_]+)\}")
STEP_REF = re.compile(r"\$\{steps\.([a-zA-Z0-9_]+)\.output\}")
PREV_REF = re.compile(r"\$\{prev\.output\}")


def translate_skills(ir: IRGraph, project: HermesProject) -> None:
    for node in ir.nodes:
        kind = node.kind if isinstance(node.kind, str) else node.kind.value
        if kind != NodeKind.WORKFLOW.value:
            continue
        skill = _build_skill(ir, node)
        project.skills.append(skill)


def _build_skill(ir: IRGraph, wf) -> HermesSkill:  # noqa: ANN001
    meta = wf.metadata or {}
    raw_steps: list[dict[str, Any]] = meta.get("raw_steps") or []
    triggers: list[dict[str, Any]] = meta.get("triggers") or []

    desc = (wf.intent.description if wf.intent else None) or wf.description or wf.name
    confidence = wf.intent.confidence if wf.intent else 0.5

    when_to_use = _derive_when_to_use(wf.name, triggers, raw_steps)

    inputs: dict[str, dict[str, Any]] = {}
    procedure: list[dict[str, Any]] = []
    prev_alias = "prev"

    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        plugin = step.get("plugin")
        if not plugin:
            continue
        step_id = step.get("id") or plugin
        with_block = step.get("with", {}) or {}
        rewritten, step_inputs = _rewrite_with(with_block, prev_alias)
        for input_name, env_var in step_inputs.items():
            inputs.setdefault(_input_key(env_var), {"type": "string", "env": env_var})
            rewritten[input_name] = "${" + _input_key(env_var) + "}"
        procedure.append({"tool": plugin, "with": rewritten, "as": step_id})
        prev_alias = step_id

    todos: list[str] = []
    if wf.portability and wf.portability.tier in (
        PortabilityTier.NEEDS_REVIEW.value,
        PortabilityTier.PARTIAL.value,
    ):
        todos.extend(wf.portability.blockers or [])
        if wf.portability.tier == PortabilityTier.PARTIAL.value and confidence < 0.6:
            todos.append(
                f"Intent confidence is {confidence:.2f} (< 0.6). Review the description and `when_to_use`."
            )

    # Reflect webhook triggers in when_to_use
    for t in triggers:
        if isinstance(t, dict) and t.get("kind") == "webhook":
            when_to_use.append(f"HTTP request arrives at webhook path {t.get('path')!r}")

    return HermesSkill(
        name=wf.name,
        description=desc,
        when_to_use=when_to_use,
        inputs=inputs,
        procedure=procedure,
        confidence=confidence,
        todos=todos,
    )


def _derive_when_to_use(name: str, triggers: list, steps: list) -> list[str]:  # noqa: ANN001
    out: list[str] = []
    for t in triggers:
        if not isinstance(t, dict):
            continue
        if t.get("kind") == "cron":
            out.append(f"Scheduled trigger fires (cron: {t.get('spec')})")
        elif t.get("kind") == "manual":
            out.append(f"User explicitly invokes `{name}`")
    if not out:
        plugin_names = [s.get("plugin") for s in steps if isinstance(s, dict)]
        if plugin_names:
            out.append(f"Equivalent task is requested ({' → '.join(p for p in plugin_names if p)})")
    return out


def _rewrite_with(block: dict[str, Any], prev_alias: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Translate OpenClaw `${env.X}` and `${steps.id.output}` into Hermes interpolation,
    and surface env-derived inputs.
    """
    rewritten: dict[str, Any] = {}
    discovered_envs: dict[str, str] = {}

    for k, v in block.items():
        if isinstance(v, str):
            env_match = ENV_REF.fullmatch(v) or ENV_REF.search(v)
            step_match = STEP_REF.search(v)
            if env_match and ENV_REF.fullmatch(v):
                env_var = env_match.group(1)
                discovered_envs[k] = env_var
                rewritten[k] = v  # placeholder, the caller rewrites it
            elif step_match and STEP_REF.fullmatch(v):
                rewritten[k] = "${" + step_match.group(1) + "}"
            elif PREV_REF.fullmatch(v):
                rewritten[k] = "${" + prev_alias + "}"
            else:
                rewritten[k] = v
        else:
            rewritten[k] = v
    return rewritten, discovered_envs


def _input_key(env_var: str) -> str:
    return env_var.lower()
