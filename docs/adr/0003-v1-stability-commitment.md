# ADR-0003: v1.0 stability commitment

## Status

Accepted (2026-05-24, with v1.0.0 release).

## Context

Praxis shipped 13 minor releases from v0.1 to v0.13. Across them the IR schema, CLI surface, and Python API have all stabilized:

- The IR schema has been frozen at `praxis_ir_version: 0.1` since v0.1 — no nodes/fields renamed, none removed.
- The CLI command surface has grown additively (scan → graph → report → migrate → explain → init → doctor → check → stats → bench → skills extract → roundtrip → ir validate/diff/to-mermaid). No command has been removed or had its arguments reshaped after introduction.
- The `praxis_core` Python package's public surface (analyzers, translators, emitters, IR models, classifier) has been stable.

Several "breaking" changes happened during 0.x but in the safety direction (e.g., `runtime: subprocess` reclassified from `unsupported` to `partial`; `kind: sql` memory similarly). Those were tier shifts, not schema changes — downstream IR consumers still parse the same fields.

Real users beginning to adopt Praxis need to know what they can build against without risk of yanked rugs.

## Decision

With v1.0.0 we make the following stability commitments. They apply within the 1.x major line.

### Stable (additive-only changes)

- **IR JSON schema** (`schemas/praxis-ir.schema.json`). New optional fields can be added; existing fields cannot be renamed, removed, or have their type narrowed.
- **`praxis_ir_version`** is bumped to `1.0`. Stays at `1.x` for the life of the 1.x line; consumers may check `>=1.0,<2.0`.
- **CLI command names and primary arguments.** New commands and new flags may be added; existing ones may not be removed or have their meaning changed.
- **Python public API**: `praxis_core.{__version__, IR_VERSION, ir, analyzers, translators, emitters, scoring, reports, pipeline, extract}` modules. Imports from these paths are stable.
- **Diagnostic codes** (`PRX001`, `PRX002`, `PRX010`, `PRX011`, `PRX030`). Once assigned, they don't get reused for a different meaning.

### Not stable (may change in any minor release)

- **Classifier tier assignments for specific runtimes/memory kinds.** A runtime currently classified as `partial` may move to `portable` (or vice versa) as we learn more. The tier system itself (`portable` / `partial` / `needs_review` / `unsupported`) is stable; specific verdicts are not.
- **Inferred intent text and confidence numbers.** Heuristics evolve. Tests asserting exact intent strings will break.
- **Translation output's prose fields** (`description`, `when_to_use`). The structural fields are stable; the prose is best-effort.
- **The `_praxis*` metadata block in emitted Hermes skills.** Its presence and shape may change as the translator gets cleverer.
- **Mermaid / DOT graph renderer output.** Visual choices may change; the data is in the IR.

### Out of scope of 1.x

The roadmap items past v1.0 (LLM-assisted intent inference, hybrid bridge, third-target backends) are 1.x feature additions. None require breaking changes to deliver, by design. If one does, it gates v2.0.

## Consequences

- Downstream consumers can `pin praxis-core~=1.0` and trust additive growth.
- A v2.0 cut is reserved for "we genuinely got the IR shape wrong" — not for cosmetic or feature work.
- Each minor release continues to ship with a CHANGELOG entry, golden-fixture re-baseline (when needed), and tag.
- Migration from `praxis_ir_version: 0.1` → `1.0` is a one-time event handled inside the v1.0.0 release. No deprecation window — there are no 0.1 IR files in the wild that aren't ours.

## Alternatives considered

- **Stay on 0.x indefinitely.** The 0.x convention says "API may change" — but ours hasn't, materially, in 13 minor releases. Continuing to claim instability would understate the actual contract.
- **Use a separate IR version unrelated to the package version.** This is what Praxis did pre-v1.0 (package was 0.13, IR was 0.1). Going forward, both share the major version because the IR schema is the package's primary surface and they should rev together at breaking-change boundaries.
