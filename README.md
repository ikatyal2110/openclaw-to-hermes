# Praxis

> Migration engine and semantic translator for moving agent systems from **OpenClaw** (orchestration-heavy) to **Hermes** (cognition-heavy).

Praxis is **not** a config converter. It is an architecture analyzer that extracts the *operational intent* behind your OpenClaw workflows, plugins, prompts, and memory stores, and reconstructs that intent as Hermes-native skills, schedules, tools, and memory schemas — flagging anything that can't be translated mechanically for human review.

```
┌─────────────────┐    Praxis IR    ┌─────────────────┐
│  OpenClaw repo  │ ─────────────▶  │  Hermes project │
│  (workflows,    │   analyze →     │  (skills,       │
│   plugins,      │   translate →   │   schedules,    │
│   prompts, …)   │   emit          │   tools, …)     │
└─────────────────┘                 └─────────────────┘
                       +
              MIGRATION_REPORT.md
              architecture.mmd (Mermaid)
              ir.json (replayable)
```

## Status

**v0.1 — MVP.** Analyzer + report + rule-based migration for OpenClaw → Hermes, on a fixed YAML convention for both frameworks (see [`docs/openclaw-format.md`](docs/openclaw-format.md) and [`docs/hermes-format.md`](docs/hermes-format.md)). Hybrid runtime, prompt clustering, and additional backends are deferred — see [Roadmap](#roadmap).

## What Praxis is and isn't

**Is:**
- A scanner that builds a typed architecture graph of an OpenClaw project.
- A translator that converts ~30–50% of common patterns deterministically.
- A report generator that, for the rest, produces specific, reviewable TODOs.
- An intermediate representation (IR) you can inspect, diff, and re-emit.

**Isn't:**
- A drop-in autopilot. The report is the product. The generated Hermes files are a head start, not a final answer.
- A general-purpose agent framework converter. v0.1 supports exactly one source and one target.

## Quick start

Praxis ships as a Python package with a CLI. (A TypeScript wrapper lives in `packages/cli` and shells out — same surface area, optional.)

```bash
# Install the core
pipx install ./packages/core-py     # or: pip install -e packages/core-py

# Scan a project
praxis scan examples/openclaw-sample

# Generate a Mermaid graph of the architecture
praxis graph examples/openclaw-sample --format mermaid > arch.mmd

# Produce a Markdown migration feasibility report
praxis report examples/openclaw-sample > REPORT.md

# Materialize a Hermes project
praxis migrate examples/openclaw-sample --target hermes --out ./out

# Inspect the IR directly
praxis scan examples/openclaw-sample --emit-ir ir.json
praxis ir validate ir.json
```

## Repository layout

```
praxis/
├── schemas/praxis-ir.schema.json    # The IR — the public contract
├── docs/                            # Architecture, IR spec, ADRs
├── examples/openclaw-sample/        # A realistic fixture project
├── packages/
│   ├── core-py/                     # Python: analyzers, translators, emitters
│   ├── ir/                          # TypeScript types + zod schema for IR
│   └── cli/                         # Thin TS CLI (shells to core-py)
└── tools/fixtures/                  # Golden migration fixtures (regression tests)
```

See [`docs/architecture.md`](docs/architecture.md) for the six-stage pipeline (scan → analyze → resolve → score → translate → emit) and how each stage exchanges IR.

## The intermediate representation

The IR is the single contract on which everything else hangs. It is:
- **Framework-neutral** in node fields (`tool`, `workflow`, `memory_store`, …).
- **Framework-tagged** in `provenance` (where this node came from).
- **Capability-based**, not class-based — translators look for capabilities, not types.
- **Intent-bearing** — every workflow may carry a `description`, `confidence`, and `evidence`.
- **Round-trippable** — every emitter has a partner analyzer; Hermes → IR → Hermes must converge.

The IR is versioned in [`schemas/praxis-ir.schema.json`](schemas/praxis-ir.schema.json). Internal code can change; the IR can't break without a version bump.

## How translation works

Three tiers, falling back in order:

| Tier | Coverage (target) | Mechanism |
|---|---|---|
| Deterministic | 30–50% | Rule-based pattern matchers in `translators/openclaw_to_hermes/` |
| Templated + LLM prose | ~30% | Skeleton from rules; LLM fills `description` and `when_to_use` from inferred intent |
| Human-in-the-loop | 20–40% | Classifier marks `requires_human`; report emits TODOs with code, candidates, and questions |

The portability classifier is the gate. It is rule-based and will remain so until rule coverage is exhausted — opaque LLM gating kills debuggability.

## Assumptions about OpenClaw and Hermes

This MVP assumes specific YAML conventions for both frameworks, documented in `docs/openclaw-format.md` and `docs/hermes-format.md`. **If your actual flavor differs, customize the analyzers** under `packages/core-py/praxis_core/analyzers/openclaw/` and emitters under `packages/core-py/praxis_core/emitters/hermes.py`. The IR is the stable interface — adapt the edges to match your reality.

This is by design. A migration tool that pretends to handle every dialect of every framework lies. A tool that exposes its assumptions and gives you the IR contract is honest infrastructure.

## CLI reference

```
praxis scan <path>                      Walk repo, emit IR + summary table
praxis graph <path> --format mermaid    Architecture graph (mermaid | dot | json)
praxis report <path>                    Migration feasibility report (Markdown)
praxis migrate <path> --target hermes --out <dir>
praxis ir validate <file>               Lint an IR file against the JSON Schema
praxis ir diff <a> <b>                  Structural diff between two IRs
```

Post-MVP:
```
praxis skills extract <path>            Cluster prompts into reusable skills
praxis memory convert <path>            Translate memory schemas in isolation
praxis bridge start --config <file>     Run a hybrid Hermes↔OpenClaw bridge
```

## Roadmap

- **v0.1 (this MVP).** scan / graph / report / migrate, OpenClaw → Hermes, rule-based.
- **v0.2.** Prompt clustering & skill extraction. Memory schema translation beyond KV. Round-trip tests (Hermes → IR → Hermes).
- **v0.3.** Hybrid bridge, read-only: Hermes introspects OpenClaw tools without invoking.
- **v0.4.** Hybrid bridge, read-write. LangGraph as a third target to force IR generalization.
- **v0.5.** VS Code extension surfacing the migration report as inline annotations.
- **v1.0.** Stable IR. Backend authoring guide. Public benchmark fixture suite.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The fastest way to make Praxis better is to add a fixture project to `tools/fixtures/` representing a real-world OpenClaw pattern that doesn't round-trip yet.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
