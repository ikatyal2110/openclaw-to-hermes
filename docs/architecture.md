# Architecture

Praxis is a six-stage pipeline. Each stage takes an IR document in and produces an enriched IR out. No stage mutates state it didn't own; every intermediate IR is serializable and replayable.

```
[Source repo]
  ↓ (1) Scan       file discovery, classification
  ↓ (2) Analyze    per-domain analyzers produce partial IR
  ↓ (3) Resolve    merge partials, link references, build graph
  ↓ (4) Score      portability classifier annotates nodes
  ↓ (5) Translate  IR → target framework's IR
  ↓ (6) Emit       write files + reports
[Hermes project + REPORT.md + ir.json]
```

## Stages

### 1. Scan
Walks the source root. Identifies which files belong to which analyzer (by path convention and a quick content sniff). Output: a manifest, not yet an IR.

### 2. Analyze
Each analyzer (`analyzers/openclaw/workflows.py`, `analyzers/openclaw/plugins.py`, …) reads its files and emits **partial** IR — nodes and edges with `provenance` set, but without cross-references resolved.

### 3. Resolve
Partials are merged. References by name (e.g. a workflow step says `plugin: fetch_articles`) are linked into IR edges. Diagnostics are emitted for unresolved references.

### 4. Score
The portability classifier walks the IR and stamps a `portability` block on every node. The classifier is rule-based by design — opaque LLM scoring is debt the project refuses to take on at MVP.

### 5. Translate
For each `(source_framework, target_framework, node_kind)` triple, a translator transforms IR nodes into target-shaped IR nodes. Translators may compose. Anything the classifier marked `needs_review` is wrapped with a stub plus an explicit diagnostic.

### 6. Emit
The target emitter writes files. The report emitter writes `MIGRATION_REPORT.md` and `architecture.mmd`. The raw IR is always written too — Praxis treats the IR as a first-class deliverable, not an internal detail.

## Why six stages, not three

Compressing analyze+resolve+score into one pass would be 30% less code and 10x harder to debug. The discipline of explicit stages buys two things:

1. **Replayability.** Cache the IR after Resolve; iterate on translators without re-parsing.
2. **Reviewability.** A failing migration can be inspected at any stage's output.

## Plugin model

Three extension points, all keyed by the IR shape:

| Slot | Signature | Example |
|---|---|---|
| Analyzer | `(source_path) → partial IR` | `analyzers/openclaw/workflows.py` |
| Translator | `(IRNode, context) → IRNode` | `translators/openclaw_to_hermes/workflow_to_skill.py` |
| Emitter | `IR → files on disk` | `emitters/hermes.py` |

Each is registered via a module-level decorator (`@analyzer("openclaw.workflows")`). New backends are new modules; no fork required.

## What lives in TypeScript vs Python

- **Python** owns analysis and emission. It needs `libcst` for code introspection, `pydantic` for typed IR, `networkx` for graph ops.
- **TypeScript** owns the user-facing CLI surface and IR types for editor tooling. The TS CLI is a thin wrapper that subprocesses to `python -m praxis_core`.
- **Boundary:** JSON over stdio. No FFI, no shared memory. Boring and reliable.

For the MVP, the Python CLI is the canonical entry point. The TS CLI is scaffolded but optional.

## Determinism

Praxis must produce the same output for the same input. Concretely:

- Node IDs are deterministic hashes of `(framework, kind, source_file, name)`.
- Node and edge arrays are sorted before serialization.
- LLM calls (post-v0.1) are cached by content hash of their input.

If `praxis migrate` produces different output on a re-run with no source changes, that is a bug.
