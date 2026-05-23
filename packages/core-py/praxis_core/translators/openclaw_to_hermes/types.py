"""In-memory shape of a Hermes project, produced by the translator and consumed by the emitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HermesSkill:
    name: str
    description: str
    when_to_use: list[str] = field(default_factory=list)
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    procedure: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    todos: list[str] = field(default_factory=list)


@dataclass
class HermesTool:
    name: str
    description: str
    runtime: str
    spec: dict[str, Any] = field(default_factory=dict)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class HermesSchedule:
    name: str
    cron: str
    invoke_skill: str


@dataclass
class HermesMemory:
    name: str
    kind: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class HermesPrompt:
    name: str
    body: str
    format: str = "j2"


@dataclass
class HermesProject:
    skills: list[HermesSkill] = field(default_factory=list)
    tools: list[HermesTool] = field(default_factory=list)
    schedules: list[HermesSchedule] = field(default_factory=list)
    memories: list[HermesMemory] = field(default_factory=list)
    prompts: list[HermesPrompt] = field(default_factory=list)
