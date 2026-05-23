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

[![CI](https://github.com/ikatyal2110/openclaw-to-hermes/actions/workflows/ci.yml/badge.svg)](https://github.com/ikatyal2110/openclaw-to-hermes/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](packages/core-py/pyproject.toml)

## Status

**v0.2 — beta.** Analyzer, rule-based migration, and prompt-clustering skill extraction for OpenClaw → Hermes. IR schema is `0.1` and locked behind a golden-file regression suite. Hybrid runtime, LLM-assisted intent inference, and additional backends are deferred — see [Roadmap](#roadmap) and [`CHANGELOG.md`](CHANGELOG.md).

## What Praxis is and isn't

**Is:**
- A scanner that builds a typed architecture graph of an OpenClaw project.
- A translator that converts ~30–50% of common patterns deterministically.
- A report generator that, for the rest, produces specific, reviewable TODOs.
- A prompt-clustering tool that surfaces candidate skills to consolidate.
- An intermediate representation (IR) you can inspect, diff, and re-emit.

**Isn't:**
- A drop-in autopilot. The report is the product. The generated Hermes files are a head start, not a final answer.
- A general-purpose agent framework converter. v0.2 supports exactly one source and one target.

## Quick start

Praxis ships as a Python package with a CLI. (A TypeScript wrapper lives in `packages/cli` and shells out — same surface area, optional.)

```bash
# Install from a clone (PyPI release coming with v1.0)
git clone https://github.com/ikatyal2110/openclaw-to-hermes
cd openclaw-to-hermes
pip install -e packages/core-py

# Sanity-check the install
praxis doctor

# Scan a project — print a summary table
praxis scan examples/openclaw-sample

# Generate a Mermaid graph of the architecture
praxis graph examples/openclaw-sample --format mermaid > arch.mmd

# Produce a Markdown migration feasibility report
praxis report examples/openclaw-sample > REPORT.md

# Materialize a Hermes project
praxis migrate examples/openclaw-sample --target hermes --out ./out

# Cluster prompts to surface candidate skills
praxis skills extract examples/openclaw-sample --report extract.md

# Inspect the IR directly
praxis scan examples/openclaw-sample --emit-ir ir.json
praxis ir validate ir.json
```

### Sample output — `praxis migrate`

```
Migrated → ./out
  report: ./out/MIGRATION_REPORT.md
  graph : ./out/architecture.mmd
  ir    : ./out/ir.json
  files : {'skills': 2, 'tools': 6, 'schedules': 1, 'memory': 2, 'prompts': 6}
```

### Sample output — `praxis skills extract`

```
                    Prompt clusters (threshold=0.40)
┃ # ┃ Size ┃ Min sim ┃ Max sim ┃ Members
│ 1 │    2 │    0.54 │    0.54 │ classify, classify_email          ← loose family
│ 2 │    2 │    0.90 │    0.90 │ extract_entities, extract_entities_v2  ← near-duplicate
│ 3 │    2 │    0.63 │    0.63 │ summarize, summarize_weekly       ← strong overlap
6 prompt(s) scanned, 3 cluster(s).
```

## Repository layout

```
praxis/
├── schemas/praxis-ir.schema.json    # The IR — the public contract
├── docs/                            # Architecture, IR spec, ADRs, user guides
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

The IR is versioned in [`schemas/praxis-ir.schema.json`](schemas/praxis-ir.schema.json). Internal code can change; the IR can't break without a version bump. See [`docs/ir-spec.md`](docs/ir-spec.md).

## How translation works

Four portability tiers; the classifier stamps every node with one:

| Tier | What it means | Action |
|---|---|---|
| `portable` | Deterministic one-to-one mapping exists | Emitted directly, no review needed |
| `partial` | Translatable with a documented caveat | Emitted with a TODO in the report |
| `needs_review` | Translatable but requires a human decision | Emitted as a skeleton; report explains why |
| `unsupported` | No Hermes primitive | Not emitted; report lists alternatives |

The classifier is rule-based and will remain so — opaque LLM gating kills the debuggability the tool depends on. See [`docs/migration-model.md`](docs/migration-model.md) for the full mapping table.

## Skill extraction (v0.2)

`praxis skills extract` clusters prompts by token-bigram Jaccard similarity (single-link, configurable threshold) and emits a Markdown report with tiered suggestions:

| Min similarity | Suggested action |
|---|---|
| ≥ 0.85 | Near-duplicate — merge into one skill and parameterize the differing variables |
| ≥ 0.60 | Strong structural overlap — likely one skill with two prose variants |
| ≥ threshold | Loose family resemblance — review before merging |

See [`docs/skills-extract.md`](docs/skills-extract.md).

## Assumptions about OpenClaw and Hermes

This release assumes specific YAML conventions for both frameworks, documented in [`docs/openclaw-format.md`](docs/openclaw-format.md) and [`docs/hermes-format.md`](docs/hermes-format.md). **If your flavor differs, customize the analyzers** under `packages/core-py/praxis_core/analyzers/openclaw/` and emitters under `packages/core-py/praxis_core/emitters/hermes.py`. The IR is the stable interface — adapt the edges to match your reality.

This is by design. A migration tool that pretends to handle every dialect of every framework lies. A tool that exposes its assumptions and gives you the IR contract is honest infrastructure.

## CLI reference

```
praxis --version                        Print version and IR schema version
praxis doctor                           Run install sanity checks
praxis scan <path>                      Walk repo, emit IR + summary table
praxis graph <path> --format mermaid    Architecture graph (mermaid | json)
praxis report <path>                    Migration feasibility report (Markdown)
praxis migrate <path> --target hermes --out <dir>
                                        Translate + emit Hermes project + report + graph + IR
praxis ir validate <file>               Lint an IR file against the JSON Schema
praxis ir diff <a> <b>                  Structural diff between two IRs
praxis skills extract <path> [--threshold N] [--report FILE]
                                        Cluster prompts; surface candidate skill extractions
```

## Roadmap

- **v0.1.** scan / graph / report / migrate / ir validate / ir diff, OpenClaw → Hermes, rule-based.
- **v0.2 (current).** Prompt clustering & skill extraction. Golden-file fixture lock. `doctor` and `--version`. Strict mypy in CI.
- **v0.3.** Tool-sequence repetition (the other half of skill extraction). LLM-assisted intent inference with content-addressed caching. Memory schema beyond KV/vector.
- **v0.4.** Hybrid bridge, read-only (Hermes introspects OpenClaw tools).
- **v0.5.** Hybrid bridge, read-write. LangGraph as a third target — first chance to break the IR.
- **v0.6.** VS Code extension surfacing the migration report as inline annotations.
- **v1.0.** Stable IR. Backend authoring guide. Public benchmark fixture suite. PyPI release.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The fastest way to make Praxis better is to add a fixture project to `tools/fixtures/` representing a real-world OpenClaw pattern that doesn't round-trip yet.

Good first issues:
- Add a `--format dot` option to `praxis graph` (currently only mermaid + json).
- Extend the prompt tokenizer to recognize Hermes prompt placeholders.
- Add support for OpenClaw retry/backoff blocks in `workflows.py`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
