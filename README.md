# Praxis

> **Migrate an agent system from OpenClaw to Hermes** — workflows, plugins, prompts, memory, schedules, secrets, and the structural decisions behind them. Not a config converter; an architecture-aware translator.

Praxis reads your OpenClaw project, builds a typed intermediate representation, and emits a Hermes project plus a Markdown **migration playbook** — a checklist of what was auto-translated and what needs your judgment. The playbook is the product.

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

**v0.5 — beta.** Production-quality CLI with `scan` / `graph` / `report` / `migrate` / `check` / `explain` / `skills extract` / `stats` / `doctor` / `init`. IR schema `0.1`, locked by a golden-file regression suite. 130+ tests, strict mypy in CI. Hybrid runtime and additional backends are deferred — see [Roadmap](#roadmap) and [`CHANGELOG.md`](CHANGELOG.md).

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

### What you get from `praxis migrate`

```
out/
├── MIGRATION_REPORT.md     ← your playbook (checklist + tier table + TODOs)
├── architecture.mmd        ← Mermaid graph (paste into mermaid.live)
├── ir.json                 ← portable IR (diff between runs, validate)
└── hermes/
    ├── skills/             ← one YAML per workflow
    ├── tools/              ← one YAML per plugin
    ├── schedules/          ← one YAML per cron trigger
    ├── memory/             ← one YAML per store
    └── prompts/            ← prompts copied verbatim
```

The CLI prints a one-line summary so you know what was emitted:

```
Migrated → ./out
  files : {'skills': 3, 'tools': 6, 'schedules': 2, 'memory': 2, 'prompts': 6}
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

`praxis skills extract` surfaces two kinds of candidate Hermes-side consolidations:

**1. Prompt clusters** — prompts that share enough structure (Jaccard ≥ threshold on token bigrams) to suggest they should be one parameterized skill rather than several near-duplicate templates. Tiered actions:

| Min similarity | Suggested action |
|---|---|
| ≥ 0.85 | Near-duplicate — merge into one skill and parameterize the differing variables |
| ≥ 0.60 | Strong structural overlap — likely one skill with two prose variants |
| ≥ threshold | Loose family resemblance — review before merging |

**2. Repeated tool sequences** — *maximal* tool chains (length ≥ 2) that appear verbatim in ≥ 2 workflows. Strong candidates for factoring into a single named skill rather than inlining the same chain in every workflow. The detector reports only the longest distinct chains, not their sub-windows.

See [`docs/skills-extract.md`](docs/skills-extract.md).

## Assumptions about OpenClaw and Hermes

This release assumes specific YAML conventions for both frameworks, documented in [`docs/openclaw-format.md`](docs/openclaw-format.md) and [`docs/hermes-format.md`](docs/hermes-format.md). **If your flavor differs, customize the analyzers** under `packages/core-py/praxis_core/analyzers/openclaw/` and emitters under `packages/core-py/praxis_core/emitters/hermes.py`. The IR is the stable interface — adapt the edges to match your reality.

This is by design. A migration tool that pretends to handle every dialect of every framework lies. A tool that exposes its assumptions and gives you the IR contract is honest infrastructure.

## CLI reference

```
# Discovery
praxis --version                              Print version + IR schema version
praxis doctor                                 Sanity-check the local install
praxis init <path>                            Scaffold a starter OpenClaw project
praxis stats <path> [--json]                  At-a-glance project analytics

# Read-only analysis
praxis scan <path> [--emit-ir FILE] [--json]  Walk repo, summary table or JSON
praxis graph <path> --format mermaid          Architecture graph
praxis report <path>                          Migration playbook (Markdown)
praxis explain <path> <node> [--json]         Drill into one node
praxis skills extract <path> [--threshold N] [--report FILE]
                                              Prompt clusters + tool-sequence repeats
praxis check <path> [-W] [--json]             CI-friendly validator (exit 1 on errors)
praxis roundtrip <path> [--json]              Forward+back migration; reports lossy nodes

# Translation
praxis migrate <path> --target hermes --out <dir> [--dry-run]
                                              Emit Hermes project + report + graph + IR
                                              --dry-run prints the manifest without writing files

# IR utilities
praxis ir validate <file>                     Lint IR against schema
praxis ir diff <a> <b>                        Structural diff between two IRs
praxis ir to-mermaid <file>                   Render Mermaid graph from a saved IR
```

For a step-by-step first-day walkthrough on a real project, see [`docs/migrating-real-projects.md`](docs/migrating-real-projects.md).

## Roadmap

- **v0.1.** scan / graph / report / migrate / ir validate / ir diff, OpenClaw → Hermes, rule-based.
- **v0.2.** Prompt clustering & tool-sequence repetition detection (`praxis skills extract`). Golden-file fixture lock. `doctor` and `--version`. Strict mypy in CI.
- **v0.3.** `praxis explain <node>` for drilling into classifications. Robust analyzer error handling (broken YAML → diagnostic, not crash). Secrets classifier on env vars (🔐 in the report). Real-project walkthrough doc.
- **v0.4.** Migration checklist in the report (actionable playbook, not just a diagnostic). `praxis init` scaffolder. `--json` output for scan + explain.
- **v0.5.** `praxis check` (CI-friendly pre-flight validator). `when:` clause preservation through translation (auto-emitted as `_praxis_when` with a TODO for verification).
- **v0.6.** `for_each` loop preservation (mirrors `when:` pattern). `praxis stats` for at-a-glance analytics. README + CLI reference polish.
- **v0.7.** `retry:` block preservation (completes the `when:`/`for_each`/`retry:` trio). `praxis migrate --dry-run`. Second golden fixture (`branchy`) exercising all three constructs.
- **v0.8.** Expanded memory store classifier (Redis/Memcached portable, SQL/Postgres/MySQL partial via wrapper tool, SQLite/DynamoDB/S3 needs_review). Richer rule-based intent inference.
- **v0.9.** Expanded plugin runtime classifier (20+ runtimes including docker/lambda/grpc/graphql/shell/multi-language). `praxis ir to-mermaid` for offline graph rendering.
- **v0.10.** Cleaner Hermes emission — `_praxis` metadata block dropped on portable, high-confidence skills so they look hand-written.
- **v0.11 (current).** Hermes → IR analyzer (round-trip!). `praxis roundtrip` command for validating which nodes survive forward→back. `praxis check --json` for CI.
- **v0.12.** LLM-assisted intent inference with content-addressed caching.
- **v0.13.** Hybrid bridge, read-only (Hermes introspects OpenClaw tools).
- **v0.14.** Hybrid bridge, read-write. LangGraph as a third target — first chance to break the IR.
- **v0.15.** VS Code extension surfacing the migration report as inline annotations.
- **v1.0.** Stable IR. Backend authoring guide. Public benchmark fixture suite. PyPI release.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The fastest way to make Praxis better is to add a fixture project to `tools/fixtures/` representing a real-world OpenClaw pattern that doesn't round-trip yet.

Good first issues:
- Add a `--format dot` option to `praxis graph` (currently only mermaid + json).
- Extend the prompt tokenizer to recognize Hermes prompt placeholders.
- Add support for OpenClaw retry/backoff blocks in `workflows.py`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
