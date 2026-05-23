# Handoff — Praxis v0.1 MVP

**One-line:** Praxis is an OpenClaw → Hermes migration engine. Architecture analyzer + semantic translator, not a config converter. See `README.md` for the user-facing pitch and `docs/architecture.md` for the six-stage pipeline.

## Current status (as of this handoff)

- **v0.1 MVP scaffolded and committed to disk.** All files exist under `/Users/ishaankatyal/Desktop/openclaw-to-hermes/`.
- **UNVERIFIED end-to-end.** The previous session's shell could not initialize (the harness booted from a stale CWD), so `python -m praxis_core scan examples/openclaw-sample` was never executed. File-by-file static review was done; the test suite is comprehensive but was not run.
- **Next user action:** open a fresh terminal, `pip install -e packages/core-py`, run `pytest -q` from `packages/core-py/`. Fix whatever the test suite surfaces first.

## What the project is (and isn't)

**Is:**
- A scanner that builds a typed architecture graph of an OpenClaw project (workflows, plugins, prompts, memory, services, env).
- A rule-based translator that converts ~30–50% of common patterns deterministically to Hermes.
- A report generator that, for the rest, produces specific reviewable TODOs.
- A versioned IR (JSON Schema) you can inspect, diff, and re-emit.

**Isn't:**
- A drop-in autopilot.
- A general agent-framework converter (v0.1 supports exactly OpenClaw → Hermes).
- An LLM-heavy semantic engine (LLM intent inference is v0.2).
- A hybrid runtime (deferred to v0.3+).

## Architectural decisions already made (don't relitigate without ADR)

| Decision | Where |
|---|---|
| Name = **Praxis**, CLI binary = `praxis` (not `claw*` — survives a rebrand) | README |
| Apache-2.0 license | LICENSE |
| **Bidirectional IR scoped to OpenClaw ↔ Hermes only in v0.1** — no "universal IR" until a third backend forces generality | `docs/adr/0001-bidirectional-ir.md` |
| **Analyzer reads YAML manifests only, not source code** | `docs/adr/0002-conservative-analyzer-scope.md` |
| **Rule-based classifier, no LLM in scoring** | `docs/migration-model.md`, `packages/core-py/praxis_core/scoring/classifier.py` |
| Python owns analysis/emission; TypeScript owns CLI wrapper + IR types for editor tooling; JSON over stdio at the boundary | `docs/architecture.md` |
| Dual-package, not Nx/Turbo monorepo | `pnpm-workspace.yaml` + `packages/core-py/pyproject.toml` |
| IR version = `0.1`. Bump rules in `CONTRIBUTING.md` | `schemas/praxis-ir.schema.json` |

## Repository layout

```
openclaw-to-hermes/
├── README.md                        # user-facing pitch
├── CHANGELOG.md                     # versioned release notes
├── LICENSE  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md
├── .gitignore  package.json  pnpm-workspace.yaml  tsconfig.base.json
├── .github/
│   ├── workflows/ci.yml             # Python 3.11/3.12 matrix + ajv + pnpm
│   ├── ISSUE_TEMPLATE/{config,praxis-ate-my-workflow,wrong-translation}.yml
│   └── pull_request_template.md
├── schemas/
│   └── praxis-ir.schema.json        # IR — the public contract (v0.1)
├── docs/
│   ├── architecture.md              # six-stage pipeline
│   ├── ir-spec.md                   # IR field semantics
│   ├── migration-model.md           # tier × confidence rules
│   ├── openclaw-format.md           # assumed source YAML format
│   ├── hermes-format.md             # emitted YAML format
│   └── adr/{0001-bidirectional-ir,0002-conservative-analyzer-scope}.md
├── examples/openclaw-sample/        # the fixture; exercises every code path
│   ├── openclaw.yaml  .env.example
│   ├── workflows/{daily_digest,support_triage}.yaml
│   ├── plugins/{fetch_articles,dedupe_seen,llm_summarize,
│   │           slack_post,classify_ticket,ticket_router}.yaml
│   ├── plugins/{dedupe_seen,ticket_router}.py   # reference impls, not introspected
│   ├── prompts/{summarize,classify}.j2
│   ├── memory/stores.yaml
│   └── services/services.yaml
├── packages/
│   ├── core-py/                     # Python — canonical implementation
│   │   ├── pyproject.toml           # hatchling, pydantic, typer, ruff, mypy, pytest
│   │   ├── praxis_core/
│   │   │   ├── __init__.py  __main__.py  cli.py  pipeline.py  resolver.py
│   │   │   ├── ir/{__init__,models}.py
│   │   │   ├── analyzers/{base.py, openclaw/*}.py    # driver + 6 analyzers
│   │   │   ├── scoring/{__init__,classifier}.py
│   │   │   ├── translators/openclaw_to_hermes/      # 5 translators + driver + types
│   │   │   ├── emitters/{__init__,hermes}.py
│   │   │   └── reports/{__init__,markdown,mermaid}.py
│   │   └── tests/                   # 7 files, ~65 tests
│   │       ├── conftest.py
│   │       ├── test_ir_models.py
│   │       ├── test_analyzers_openclaw.py
│   │       ├── test_resolver.py
│   │       ├── test_classifier.py
│   │       ├── test_translators.py
│   │       ├── test_pipeline.py
│   │       └── test_cli.py
│   ├── ir/                          # TS types + zod schema mirroring the JSON Schema
│   ├── cli/                         # TS shim that subprocesses `python -m praxis_core`
│   └── bridge/                      # placeholder for v0.3+ hybrid runtime
└── tools/fixtures/                  # golden-file regression suite (empty in v0.1)
```

## The fixture, and what it exercises

`examples/openclaw-sample/` is intentionally rich:

| Construct | Where | Expected portability tier |
|---|---|---|
| cron-triggered linear workflow | `workflows/daily_digest.yaml` | portable |
| webhook-triggered workflow | `workflows/support_triage.yaml` | portable (skill-only; no schedule emitted) |
| HTTP plugin | `plugins/fetch_articles.yaml` | portable |
| Impure Python plugin | `plugins/dedupe_seen.yaml` | **needs_review** (no `pure: true`) |
| LLM-invoking HTTP plugin | `plugins/llm_summarize.yaml` | portable |
| Router plugin | `plugins/ticket_router.yaml` | **partial** (router → autonomous decomposition advisory) |
| KV memory store | `memory/stores.yaml` `seen_articles` | portable |
| Vector memory store | `memory/stores.yaml` `ticket_history` | **needs_review** (embedding model not declared) |
| External services | `services/services.yaml` | partial (surfaced in report only) |

A correct run produces: 2 skills, 6 tools, 1 schedule (daily_digest only), 2 memory entries, 2 prompts, plus `MIGRATION_REPORT.md`, `architecture.mmd`, and `ir.json`.

## Likely bug paths (look here first if tests fail)

1. **Pydantic alias handling on `Edge.from_`.** Set via `Field(alias="from")` + `populate_by_name=True`. Constructed throughout the codebase as `Edge(**{"from": ...}, to=..., kind=...)`. If `test_edge_accepts_from_alias_via_dict` fails, every analyzer that creates edges is affected.
2. **Enum-vs-string comparisons in `scoring/classifier.py`.** With `use_enum_values=True`, field values are strings at runtime. Defensive `isinstance(x, str) else x.value` patterns exist everywhere; if one was missed, classification quietly returns `None`-equivalent results.
3. **Regex rewriting in `translators/openclaw_to_hermes/workflow_to_skill.py:_rewrite_with`.** Handles `${env.X}`, `${steps.id.output}`, `${prev.output}` only as full-string matches. Mid-string interpolation is deliberately out of scope.
4. **Mermaid `_safe(node_id)` substitution.** Node IDs contain dots; we replace `.` with `_` for Mermaid identifiers. If a node ID contains another disallowed char, Mermaid will reject silently.
5. **CLI schema-discovery walk in `cli.py:_find_schema`.** Walks up from CWD then from the installed package path. Fails confusingly if neither tree contains `schemas/praxis-ir.schema.json`.

## Roadmap (don't lose sight)

- **v0.1 (this MVP).** scan / graph / report / migrate / ir validate / ir diff. OpenClaw → Hermes only, rule-based, no LLM.
- **v0.2.** Prompt clustering & skill extraction (`praxis skills extract`). Memory schema beyond KV/vector. Round-trip tests (Hermes → IR → Hermes). LLM-assisted intent inference with content-addressed caching.
- **v0.3.** Hybrid bridge, read-only (Hermes introspects OpenClaw tools).
- **v0.4.** Hybrid bridge, read-write. LangGraph as third target — first chance to break the IR.
- **v0.5.** VS Code extension surfacing the migration report inline.
- **v1.0.** Stable IR. Backend authoring guide. Public benchmark fixture suite under `tools/fixtures/`.

## Open work — what to do next, in priority order

1. **Run `pytest -q` and make it pass.** Most likely blockers: pydantic alias paths, missing test deps (`jsonschema`, `pyyaml`), or my CWD-relative schema lookup in `cli._find_schema`.
2. **Manually run `praxis migrate examples/openclaw-sample --out /tmp/out`** and inspect the generated `MIGRATION_REPORT.md`, `architecture.mmd`, and `ir.json`. Verify the per-node tier matches the expectations table above.
3. **Lock the fixture as a golden test.** Move `examples/openclaw-sample/` to `tools/fixtures/baseline/source/` and commit `tools/fixtures/baseline/expected/` containing the verified IR + emitted Hermes tree. Add a `test_fixtures.py` that diffs current output against expected.
4. **Tighten mypy.** CI currently has `continue-on-error: true` on the mypy step — remove that once the strict-mode gaps are closed.
5. **Decide on the next feature.** Probably `praxis skills extract` (prompt clustering) — it's the single highest-value v0.2 capability because it surfaces structure the user can't find by hand.

## Things NOT to do without a stronger signal

- Don't start the hybrid bridge. Defer until at least one external user has migrated a real project end-to-end and asked for it.
- Don't generalize the IR. v0.1 is scoped to two frameworks on purpose (see ADR-0001).
- Don't LLM-ify the portability classifier. Rules are debuggable; opaque scores kill the trust the tool depends on.
- Don't add a third backend in v0.1–v0.3. v0.4 is the gate.

## CLI cheat sheet

```bash
cd /Users/ishaankatyal/Desktop/openclaw-to-hermes
pip install -e packages/core-py
pytest -q -c packages/core-py/pyproject.toml --rootdir packages/core-py

praxis scan examples/openclaw-sample
praxis graph examples/openclaw-sample --format mermaid > arch.mmd
praxis report examples/openclaw-sample > REPORT.md
praxis migrate examples/openclaw-sample --target hermes --out /tmp/praxis-out
praxis ir validate /tmp/praxis-out/ir.json
```

## Context the next session won't have

- The original requestor described OpenClaw as "orchestration-heavy" and Hermes as "cognition-heavy" — the project's whole framing depends on that contrast. If the names get challenged again, the answer is: yes, I noted in the pre-design critique that neither framework is one I could independently verify; the codebase therefore treats both as YAML-conventions documented under `docs/openclaw-format.md` and `docs/hermes-format.md`, and the analyzer/emitter are deliberately swappable. The IR is the stable seam.
- The earlier critical analysis (delivered before any code was written) recommended deleting two things from the original spec: "universal agent workflow IR" (replaced with bidirectional, ADR-0001) and "hybrid mode in MVP" (deferred to v0.3). If those resurface as "missing features," they are deliberate cuts, not oversights.
