"""Rule-based portability classifier. Stamps every node with a Portability block.

Resist LLM-ifying this. Opaque scoring kills the trust this tool depends on.
"""

from __future__ import annotations

from typing import Any

from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Node,
    NodeKind,
    Portability,
    PortabilityTier,
    SideEffectKind,
)


def score_portability(ir: IRGraph) -> IRGraph:
    for node in ir.nodes:
        node.portability = _classify(node)
    return ir


def _classify(node: Node) -> Portability:
    kind = node.kind.value if hasattr(node.kind, "value") else str(node.kind)
    meta = node.metadata or {}

    if kind == NodeKind.WORKFLOW.value:
        return _classify_workflow(node, meta)
    if kind == NodeKind.TOOL.value:
        return _classify_tool(node, meta)
    if kind == NodeKind.MEMORY_STORE.value:
        return _classify_memory(node, meta)
    if kind == NodeKind.SCHEDULER.value:
        return _classify_scheduler(node, meta)
    if kind == NodeKind.PROMPT.value:
        return Portability(
            score=1.0, tier=PortabilityTier.PORTABLE, rationale="Prompt copied verbatim."
        )
    if kind == NodeKind.ENV.value:
        return Portability(
            score=1.0,
            tier=PortabilityTier.PORTABLE,
            rationale="Environment variable, passed through.",
        )
    if kind == NodeKind.SERVICE.value:
        return Portability(
            score=0.5,
            tier=PortabilityTier.PARTIAL,
            rationale="Surfaced in report; Hermes side declares its own services.",
        )
    return Portability(
        score=0.0, tier=PortabilityTier.NEEDS_REVIEW, rationale=f"No classifier for kind={kind}."
    )


def _classify_workflow(node: Node, meta: dict[str, Any]) -> Portability:
    blockers: list[str] = []
    if meta.get("has_branches"):
        blockers.append("Conditional branches (`when:` clauses) — split into multiple skills.")
    raw_steps = meta.get("raw_steps") or []
    for s in raw_steps:
        if isinstance(s, dict) and ("for_each" in s or "loop" in s):
            blockers.append("Loop step — recommend a single tool that handles the collection.")
            break
    if blockers:
        return Portability(
            score=0.4,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale="Workflow has constructs without a one-to-one Hermes mapping.",
            blockers=blockers,
        )
    intent_conf = node.intent.confidence if node.intent else 0.0
    if intent_conf < 0.6:
        return Portability(
            score=0.7,
            tier=PortabilityTier.PARTIAL,
            rationale="Structurally portable; intent confidence below threshold — verify `when_to_use` prose.",
        )
    return Portability(
        score=0.95, tier=PortabilityTier.PORTABLE, rationale="Linear sequenceable workflow."
    )


def _classify_tool(node: Node, meta: dict[str, Any]) -> Portability:
    runtime = (meta.get("runtime") or "").lower()
    kind_field = (meta.get("kind") or "").lower()

    if kind_field == "router":
        return Portability(
            score=0.5,
            tier=PortabilityTier.PARTIAL,
            rationale="Router plugin — collapse into autonomous decomposition on the Hermes side.",
            blockers=[
                "Router has no one-to-one Hermes mapping; review the generated skill's `when_to_use`."
            ],
        )
    if runtime == "http":
        return Portability(
            score=1.0, tier=PortabilityTier.PORTABLE, rationale="HTTP tool — direct map."
        )
    if runtime == "python":
        if meta.get("pure"):
            return Portability(
                score=0.8,
                tier=PortabilityTier.PORTABLE,
                rationale="Pure Python function — map to Hermes tool with a stub.",
            )
        return Portability(
            score=0.4,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale="Impure Python plugin — review side effects before porting.",
            blockers=["Confirm side-effect surface; either declare `pure: true` or wrap as HTTP."],
        )
    if runtime == "subprocess":
        return Portability(
            score=0.0,
            tier=PortabilityTier.UNSUPPORTED,
            rationale="Subprocess plugins have no native Hermes primitive.",
            blockers=["Wrap as HTTP service or eliminate."],
        )
    if any(
        se.kind == SideEffectKind.UNKNOWN.value or se.kind == SideEffectKind.UNKNOWN
        for se in node.side_effects
    ):
        return Portability(
            score=0.3, tier=PortabilityTier.NEEDS_REVIEW, rationale="Unknown side-effect surface."
        )
    return Portability(
        score=0.5, tier=PortabilityTier.PARTIAL, rationale=f"Runtime {runtime!r} not recognized."
    )


def _classify_memory(node: Node, meta: dict[str, Any]) -> Portability:
    spec = meta.get("spec") or {}
    kind = (spec.get("kind") or "").lower()

    # KV-equivalent backends — direct or near-direct map to Hermes' kv primitive.
    if kind in ("kv", "redis", "memcached"):
        rationale = {
            "kv": "KV store — direct map.",
            "redis": "Redis used as a KV store — direct map; declare TTL semantics on the Hermes side.",
            "memcached": "Memcached used as a KV store — direct map; evictions differ from Hermes default.",
        }[kind]
        return Portability(score=1.0, tier=PortabilityTier.PORTABLE, rationale=rationale)

    if kind == "vector":
        return Portability(
            score=0.6,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale="Vector store — embedding model not declared in source; specify on the Hermes side.",
            blockers=["Which embedding model produced these vectors?"],
        )

    # Relational backends — translatable but require a wrapper tool on the Hermes side.
    if kind in ("sql", "postgres", "postgresql", "mysql", "mariadb"):
        return Portability(
            score=0.4,
            tier=PortabilityTier.PARTIAL,
            rationale=(
                f"Relational store ({kind}) — Hermes has no SQL primitive. Expose the table "
                "as an HTTP/RPC tool whose handler runs the query, and treat the tool as the "
                "memory surface."
            ),
            blockers=[
                "Define a wrapper tool that performs the read/write query.",
                "Confirm transaction/isolation guarantees still hold under the tool boundary.",
            ],
        )

    # Embedded/file-based stores — common in dev, awkward in production migration.
    if kind in ("sqlite", "file", "json"):
        return Portability(
            score=0.5,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale=(
                f"{kind.capitalize()} store — host-local state doesn't transfer cleanly to a "
                "distributed Hermes deployment. Move the data to a shared backend (KV or DB) or "
                "wrap as a tool."
            ),
            blockers=[
                "Plan the data migration: dump current state, import into target backend.",
                "Decide between KV (if K→V semantics fit) and a wrapper tool over the original file.",
            ],
        )

    # Document/wide-column NoSQL stores.
    if kind in ("dynamodb", "cosmos", "firestore", "mongodb"):
        return Portability(
            score=0.5,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale=(
                f"{kind} — NoSQL semantics (consistency, secondary indexes, TTL) vary by "
                "vendor. Map the document model into Hermes either as a KV store (if access "
                "is point-lookup) or as a wrapper tool (if queries are richer)."
            ),
            blockers=[
                "Audit the access patterns: point-lookup vs. query vs. scan.",
                "Decide KV-mapping vs. wrapper-tool based on query complexity.",
            ],
        )

    # Object storage.
    if kind in ("s3", "gcs", "blob", "azure_blob"):
        return Portability(
            score=0.5,
            tier=PortabilityTier.NEEDS_REVIEW,
            rationale=(
                f"{kind} object storage — Hermes treats blob storage as an external service, "
                "not a memory primitive. Wire as a tool that reads/writes the bucket; bring "
                "credentials in via the secrets store."
            ),
            blockers=[
                "Define a tool that wraps the bucket operations the workflows need.",
                "Confirm encryption-at-rest and access-control requirements on the Hermes side.",
            ],
        )

    return Portability(
        score=0.3,
        tier=PortabilityTier.NEEDS_REVIEW,
        rationale=f"Unknown memory kind {kind!r} — Praxis doesn't recognize this backend.",
        blockers=[
            "Declare the backend explicitly so a Hermes-side equivalent can be chosen.",
            "If this is a common backend Praxis should support, open an issue.",
        ],
    )


def _classify_scheduler(node: Node, meta: dict[str, Any]) -> Portability:
    if meta.get("trigger_kind") == "cron":
        return Portability(
            score=1.0, tier=PortabilityTier.PORTABLE, rationale="Cron — passes through."
        )
    if meta.get("trigger_kind") == "webhook":
        return Portability(
            score=0.5,
            tier=PortabilityTier.PARTIAL,
            rationale="Webhook — Hermes side must wire its own HTTP listener; surfaced as a skill, not a schedule.",
        )
    return Portability(
        score=0.4, tier=PortabilityTier.NEEDS_REVIEW, rationale="Unrecognized trigger kind."
    )


# Re-export Capability so callers don't need a separate import for type hints.
_ = Capability
