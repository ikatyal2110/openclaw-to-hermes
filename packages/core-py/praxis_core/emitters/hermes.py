"""Writes a HermesProject to disk in the on-disk convention documented in docs/hermes-format.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from praxis_core.translators.openclaw_to_hermes.types import (
    HermesMemory,
    HermesProject,
    HermesSchedule,
    HermesSkill,
    HermesTool,
)


def emit_hermes_project(project: HermesProject, out_root: Path) -> dict[str, list[str]]:
    """Materialize the project under `out_root/hermes/`. Returns a manifest of written paths."""
    hermes_root = out_root / "hermes"
    (hermes_root / "skills").mkdir(parents=True, exist_ok=True)
    (hermes_root / "tools").mkdir(parents=True, exist_ok=True)
    (hermes_root / "schedules").mkdir(parents=True, exist_ok=True)
    (hermes_root / "memory").mkdir(parents=True, exist_ok=True)
    (hermes_root / "prompts").mkdir(parents=True, exist_ok=True)

    written: dict[str, list[str]] = {
        "skills": [],
        "tools": [],
        "schedules": [],
        "memory": [],
        "prompts": [],
    }

    for skill in project.skills:
        path = hermes_root / "skills" / f"{skill.name}.yaml"
        path.write_text(_dump(_skill_dict(skill)), encoding="utf-8")
        written["skills"].append(str(path))

    for tool in project.tools:
        path = hermes_root / "tools" / f"{tool.name}.yaml"
        path.write_text(_dump(_tool_dict(tool)), encoding="utf-8")
        written["tools"].append(str(path))

    for sched in project.schedules:
        path = hermes_root / "schedules" / f"{sched.name}.yaml"
        path.write_text(_dump(_schedule_dict(sched)), encoding="utf-8")
        written["schedules"].append(str(path))

    for mem in project.memories:
        path = hermes_root / "memory" / f"{mem.name}.yaml"
        path.write_text(_dump(_memory_dict(mem)), encoding="utf-8")
        written["memory"].append(str(path))

    for prompt in project.prompts:
        path = hermes_root / "prompts" / f"{prompt.name}.{prompt.format}"
        path.write_text(prompt.body, encoding="utf-8")
        written["prompts"].append(str(path))

    return written


def _dump(obj: dict[str, Any]) -> str:
    return yaml.safe_dump(obj, sort_keys=False, default_flow_style=False, width=100)


def _skill_dict(s: HermesSkill) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": s.name,
        "description": s.description,
    }
    if s.when_to_use:
        out["when_to_use"] = s.when_to_use
    if s.inputs:
        out["inputs"] = s.inputs
    out["procedure"] = s.procedure
    # Only emit the Praxis metadata block when the user actually needs to see it:
    # either the intent is non-trivial (confidence < 0.9) or there are TODOs to act on.
    # A high-confidence, clean translation should look like a hand-written Hermes skill.
    if s.confidence < 0.9 or s.todos:
        out["_praxis"] = {"confidence": round(s.confidence, 2)}
        if s.todos:
            out["_praxis"]["todos"] = s.todos
    return out


def _tool_dict(t: HermesTool) -> dict[str, Any]:
    return {
        "name": t.name,
        "description": t.description,
        "runtime": t.runtime,
        "spec": t.spec,
        "inputs": t.inputs,
        "outputs": t.outputs,
    }


def _schedule_dict(s: HermesSchedule) -> dict[str, Any]:
    return {"cron": s.cron, "invoke_skill": s.invoke_skill}


def _memory_dict(m: HermesMemory) -> dict[str, Any]:
    out: dict[str, Any] = {"name": m.name, "kind": m.kind}
    out.update(m.fields)
    return out
