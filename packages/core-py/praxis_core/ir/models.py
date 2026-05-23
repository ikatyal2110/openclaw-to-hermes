"""Pydantic models mirroring schemas/praxis-ir.schema.json.

The JSON Schema is authoritative; these models must stay in sync.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from praxis_core import IR_VERSION


class NodeKind(str, Enum):
    TOOL = "tool"
    SKILL = "skill"
    WORKFLOW = "workflow"
    PROMPT = "prompt"
    MEMORY_STORE = "memory_store"
    SCHEDULER = "scheduler"
    SERVICE = "service"
    SECRET = "secret"
    ENV = "env"


class Capability(str, Enum):
    SEQUENCEABLE = "sequenceable"
    BRANCHABLE = "branchable"
    RETRIABLE = "retriable"
    SCHEDULED = "scheduled"
    STATEFUL = "stateful"
    SIDE_EFFECTING = "side_effecting"
    LLM_INVOKING = "llm_invoking"
    HTTP_CALLABLE = "http_callable"
    MEMORY_READING = "memory_reading"
    MEMORY_WRITING = "memory_writing"
    USER_FACING = "user_facing"
    EXTERNAL_DEPENDENCY = "external_dependency"


class EdgeKind(str, Enum):
    DATA = "data"
    CONTROL = "control"
    DEPENDENCY = "dependency"
    TRIGGER = "trigger"
    READS = "reads"
    WRITES = "writes"


class SideEffectKind(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    SUBPROCESS = "subprocess"
    DATABASE = "database"
    MESSAGING = "messaging"
    SECRET_ACCESS = "secret_access"
    UNKNOWN = "unknown"


class PortabilityTier(str, Enum):
    PORTABLE = "portable"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    UNSUPPORTED = "unsupported"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class PortSpec(StrictModel):
    name: str
    type: str | None = None
    required: bool = True
    default: Any | None = None
    env: str | None = None
    description: str | None = None


class SideEffect(StrictModel):
    kind: SideEffectKind
    target: str | None = None
    description: str | None = None


class Intent(StrictModel):
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    source: str = "static"


class SourceSpan(StrictModel):
    start_line: int | None = None
    end_line: int | None = None


class Provenance(StrictModel):
    framework: str
    source_file: str | None = None
    source_span: SourceSpan | None = None
    original_kind: str | None = None


class Portability(StrictModel):
    score: float = Field(ge=0.0, le=1.0)
    tier: PortabilityTier
    rationale: str | None = None
    blockers: list[str] = Field(default_factory=list)


class Node(StrictModel):
    id: str
    kind: NodeKind
    name: str
    description: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    inputs: list[PortSpec] = Field(default_factory=list)
    outputs: list[PortSpec] = Field(default_factory=list)
    side_effects: list[SideEffect] = Field(default_factory=list)
    intent: Intent | None = None
    provenance: Provenance
    portability: Portability | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(StrictModel):
    from_: str = Field(alias="from")
    to: str
    kind: EdgeKind
    condition: str | None = None
    label: str | None = None

    model_config = ConfigDict(extra="forbid", use_enum_values=True, populate_by_name=True)


class Diagnostic(StrictModel):
    level: str
    message: str
    node_id: str | None = None
    code: str | None = None
    hint: str | None = None


class Project(StrictModel):
    name: str | None = None
    source_framework: str | None = None
    source_root: str | None = None
    analyzed_at: datetime | None = None


class IRGraph(StrictModel):
    praxis_ir_version: str = IR_VERSION
    project: Project | None = None
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    def sort(self) -> None:
        """Deterministic ordering — nodes by id, edges by (from, to, kind), diagnostics by code+message."""
        self.nodes.sort(key=lambda n: n.id)
        self.edges.sort(key=lambda e: (e.from_, e.to, str(e.kind)))
        self.diagnostics.sort(key=lambda d: (d.code or "", d.message))

    def node_by_id(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def to_json_dict(self) -> dict[str, Any]:
        self.sort()
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def make_node_id(framework: str, kind: NodeKind | str, name: str) -> str:
    """Deterministic, content-addressed node id. Stable across runs given the same inputs."""
    kind_str = kind.value if isinstance(kind, NodeKind) else str(kind)
    raw = f"{framework}:{kind_str}:{name}".lower()
    digest = hashlib.sha1(raw.encode()).hexdigest()[:8]
    safe_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    return f"{kind_str}.{safe_name}.{digest}"
