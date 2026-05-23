# IR Specification (v0.1)

The Praxis Intermediate Representation is the only public contract of this project. Internal code may change freely; the IR cannot break without a version bump.

The canonical JSON Schema is [`schemas/praxis-ir.schema.json`](../schemas/praxis-ir.schema.json). This document explains the *why* behind the schema.

## Design principles

1. **Framework-neutral node fields, framework-tagged provenance.** A node's primary fields don't mention OpenClaw or Hermes. Provenance does.
2. **Capabilities, not class hierarchies.** Translators look for `capabilities: ["scheduled", "sequenceable"]`, not `kind === "Cron"`. Capabilities compose; class trees don't.
3. **Intent is first-class.** `intent.description` carries the natural-language summary; `intent.confidence` quantifies how sure we are; `intent.evidence` cites what we relied on.
4. **Round-trippability.** Every emitter must be paired with an analyzer for that same framework. Hermes → IR → Hermes must converge (modulo whitespace).
5. **Determinism.** Node IDs are content-derived. Arrays are sorted before serialization.

## Top-level shape

```json
{
  "praxis_ir_version": "0.1",
  "project": { "name": "...", "source_framework": "openclaw", "source_root": "...", "analyzed_at": "..." },
  "nodes": [ ... ],
  "edges": [ ... ],
  "diagnostics": [ ... ]
}
```

## Node kinds

| Kind | Meaning |
|---|---|
| `tool` | A leaf capability the agent can invoke (HTTP call, function, native plugin). |
| `skill` | A reusable, intent-bearing routine. Output of translation. |
| `workflow` | A chained set of steps in the source framework. Typically input only. |
| `prompt` | A prompt template or system prompt. |
| `memory_store` | A schema for persistent state (KV, vector, structured). |
| `scheduler` | A trigger (cron, event, webhook). |
| `service` | An external dependency declared by the project (DB, API, MCP server). |
| `secret` | A declared secret reference. Never the value. |
| `env` | An environment variable input. |

## Capabilities

Capabilities are the lingua franca translators consume. The MVP set:

| Capability | Meaning |
|---|---|
| `sequenceable` | This node belongs in a linear procedure. |
| `branchable` | This node introduces conditional flow. |
| `retriable` | Can be safely re-invoked on failure. |
| `scheduled` | Driven by a time or event trigger. |
| `stateful` | Reads or writes persistent state. |
| `side_effecting` | Has observable effects outside the agent. |
| `llm_invoking` | Calls a language model. |
| `http_callable` | Reaches an HTTP endpoint. |
| `memory_reading` | Reads from a `memory_store`. |
| `memory_writing` | Writes to a `memory_store`. |
| `user_facing` | Produces output the user sees directly. |
| `external_dependency` | Requires an external service to function. |

A `Cron-triggered RSS-to-Slack workflow` node would carry:
`["sequenceable", "scheduled", "side_effecting", "external_dependency"]`.

## Edges

| Edge kind | Meaning |
|---|---|
| `control` | Sequencing — execution follows from A to B. |
| `data` | A's output flows as B's input. |
| `dependency` | B requires A to exist (e.g., a workflow depends on a plugin). |
| `trigger` | A causes B to start (cron, webhook). |
| `reads` / `writes` | A reads from / writes to memory store B. |

Edges are typed for a reason: the translator decides differently for control vs data flow.

## Intent and confidence

```json
{
  "intent": {
    "description": "Daily RSS summary posted to Slack",
    "confidence": 0.92,
    "evidence": [
      "cron 0 9 * * * trigger",
      "step 1: fetch_articles plugin",
      "step 3: slack_post sink"
    ],
    "source": "static"
  }
}
```

- `source: "static"` — derived purely from the source code/config.
- `source: "llm"` — produced by an LLM call (cached, content-addressable).
- `source: "human"` — overridden by a developer in an `.praxis.yaml` annotation file.

The Hermes emitter uses `intent.description` to seed the skill's natural-language description. If `confidence < 0.6`, the report flags the skill for human review even when the structure translates cleanly.

## Portability

Stamped by the scoring stage:

```json
{
  "portability": {
    "score": 0.8,
    "tier": "portable",
    "rationale": "All steps map to known Hermes tool patterns.",
    "blockers": []
  }
}
```

Tiers:
- `portable` — translator emits clean output, no human review required.
- `partial` — translator emits output with non-blocking gaps (e.g., unconverted prose).
- `needs_review` — translator emits a stub plus a TODO with specific questions.
- `unsupported` — no translator applies. Node is preserved in the report but not emitted.

## Diagnostics

```json
{
  "level": "warn",
  "code": "PRX014",
  "message": "Plugin 'custom_pdf_parser' uses runtime: subprocess. Hermes has no native subprocess primitive — wire this as an HTTP tool or skip.",
  "node_id": "plugin:custom_pdf_parser",
  "hint": "See docs/migration-model.md#subprocess-plugins"
}
```

Codes start with `PRX` and are stable. Users grep them in CI. Don't reuse codes; deprecate and add new ones.

## Versioning

`praxis_ir_version` is `MAJOR.MINOR`. MINOR bumps add optional fields. MAJOR bumps may remove or restructure fields. Praxis tooling pins the IR version it understands; mismatches are an error, not a warning.
