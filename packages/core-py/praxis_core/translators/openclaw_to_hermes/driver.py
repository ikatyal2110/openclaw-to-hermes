"""Drives all OpenClaw→Hermes translators in order."""

from __future__ import annotations

from praxis_core.ir import IRGraph
from praxis_core.translators.openclaw_to_hermes.cron_to_schedule import translate_schedules
from praxis_core.translators.openclaw_to_hermes.memory_schema import translate_memory
from praxis_core.translators.openclaw_to_hermes.plugin_to_tool import translate_tools
from praxis_core.translators.openclaw_to_hermes.prompts import translate_prompts
from praxis_core.translators.openclaw_to_hermes.types import HermesProject
from praxis_core.translators.openclaw_to_hermes.workflow_to_skill import translate_skills


def translate_openclaw_to_hermes(ir: IRGraph) -> HermesProject:
    project = HermesProject()
    translate_tools(ir, project)
    translate_skills(ir, project)
    translate_schedules(ir, project)
    translate_memory(ir, project)
    translate_prompts(ir, project)
    return project
