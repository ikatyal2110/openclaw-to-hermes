# Changelog

All notable changes to Praxis are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] — 2026-05-24

### Changed
- **Cleaner Hermes emission for the portable happy path.** The emitter now drops the `_praxis: {confidence, todos}` metadata block when confidence ≥ 0.9 AND no TODOs exist. Portable, high-confidence skills now look indistinguishable from hand-written Hermes YAML. Skills with TODOs or sub-0.9 confidence still carry the block (the reviewer needs that signal).

### Tests
- 3 new tests for emitter behavior: portable skill drops `_praxis`, TODO-bearing skill keeps it, low-confidence skill keeps it.
- Re-baselined both golden fixtures for the cleaner output.
- Total: 166 tests passing.

## [0.9.0] — 2026-05-24

### Added
- **Expanded plugin runtime classifier.** Was 3 known runtimes (http/python/subprocess); now 20+:
  - **portable**: http, https, rest, plus pure functions in python/node/javascript/typescript/go/rust/java/ruby.
  - **partial**: docker/oci/container, lambda/cloud_function/faas, shell/bash/subprocess/exec/cli — each with hosting/wrapping blockers.
  - **needs_review**: impure compiled-language plugins, grpc/graphql/thrift — each with schema/protocol-bridging blockers.
- **`praxis ir to-mermaid <ir.json>`** — render a Mermaid graph directly from a saved IR file, no source project required. Useful for offline visualization and CI workflows that emit IR then render.

### Changed
- **BREAKING (classifier):** `runtime: subprocess` now classifies as `partial` (translatable via HTTP wrapper) instead of `unsupported`. Same change spirit as v0.8's SQL update.
- Re-baselined `tools/fixtures/baseline/` and `tools/fixtures/branchy/` for new intent-inference and classifier behavior.

### Tests
- 9 new tests (subprocess-now-partial, docker, lambda, grpc, graphql, https, pure-node-portable, impure-go-needs-review, ir to-mermaid).
- Total: 163 tests passing.

## [0.8.0] — 2026-05-24

### Added
- **Expanded memory store classifier.** SQL/Postgres/MySQL move from `unsupported` to `partial` (translatable via a wrapper tool, with actionable blockers). Redis and Memcached classify as `portable` (KV-equivalent). SQLite, file, and JSON stores classify as `needs_review` (state-migration question). DynamoDB, Cosmos, Firestore, and MongoDB classify as `needs_review` with access-pattern blockers. S3, GCS, and blob stores classify as `needs_review` as object storage. Unknown kinds give actionable blockers instead of an opaque message.
- **Richer rule-based intent inference.** Cadence patterns in workflow names (`daily_*`, `weekly_*`, `monthly_*`, `nightly_*`, `hourly_*`) contribute to inferred intent. Plugin-name verbs (`fetch_*`, `classify_*`, `summarize_*`, `slack_post`, etc.) extract into the description. Placeholder descriptions (`TODO`, `TBD`, single-word) downgrade confidence from 0.95 to 0.5. Webhook/scheduled triggers raise confidence on plugin-chain-derived intents.

### Changed
- **BREAKING (classifier):** `kind: sql` memory stores now classify as `partial` instead of `unsupported`. Existing reports and golden fixtures that asserted `unsupported` will need an update. (No IR schema change — only tier mapping.)

### Tests
- 13 new tests: 7 for memory store kinds (sql/postgres/redis/sqlite/dynamodb/s3/unknown), 6 for intent inference (long description, placeholder, short, cron-only, cadence name pattern, plugin verbs, webhook confidence).
- Total: 155 tests passing.

## [0.7.0] — 2026-05-24

### Added
- **`retry:` block preservation in translation** — completes the `when:` / `for_each` / `retry:` trio. Workflow steps with `retry:` policies now carry them through into the generated Hermes skill as `_praxis_retry`, with a TODO noting OpenClaw and Hermes retry keys may differ in name (max_attempts vs. retries, etc.).
- **`praxis migrate --dry-run`** — previews the file manifest (skills/tools/schedules/memory/prompts with correct extensions) without touching disk. Useful for review before committing the output, or for CI dry-runs.
- **`tools/fixtures/branchy/`** — second golden-file fixture, deliberately non-trivial. Exercises `when:`, `for_each`, `retry:`, webhook trigger, secret env var, and KV memory in one project. Locked by `tests/test_fixtures_branchy.py` with 4 regression assertions.

### Tests
- 7 new tests: 2 for `retry:` preservation, 1 for `--dry-run`, 4 for the branchy fixture.
- Total: 142 tests passing.

## [0.6.0] — 2026-05-23

### Added
- **`for_each` loop preservation in translation** — mirrors the `when:` clause pattern. Workflow steps with a `for_each` clause now carry the collection expression into the generated Hermes skill as `_praxis_for_each`, with a TODO suggesting the loop typically belongs *inside* the tool implementation on the Hermes side rather than in the skill procedure.
- **`praxis stats <path>`** — quick at-a-glance project analytics: node counts by kind, edge counts by kind, portability tier distribution, total prompt body characters, diagnostic count. `--json` for programmatic use. Useful for sizing a migration up front.

### Changed
- **README**: rewritten hero ("the playbook is the product"); CLI reference reorganized by purpose (Discovery / Read-only analysis / Translation / IR utilities); "What you get from praxis migrate" section shows the output tree; status bumped to reflect v0.5 features.

### Tests
- 4 new tests: 2 for `for_each` (preserved into procedure, generates TODO), 2 for `praxis stats` (table output, JSON output).
- Total: 135 tests passing.

## [0.5.0] — 2026-05-23

### Added
- **`praxis check <path>`** — pre-flight validator for CI. Runs the full pipeline through the resolver, groups diagnostics by level, and exits non-zero on errors. The `--warnings-as-errors` / `-W` flag escalates warnings too. Use as a merge gate.
- **`when:` clause preservation in translation** — workflow steps with `when:` conditions now carry their expression into the generated Hermes skill as `_praxis_when` (a deliberately-prefixed placeholder so reviewers can see it was auto-generated). A TODO is added pointing to the step IDs that need verification.

### Tests
- 6 new tests covering `praxis check` (clean project passes, broken YAML fails with exit 1, warnings-only passes by default and fails with `-W`) and `when:` clause translation (survives into procedure, generates TODO, doesn't pollute unrelated steps).
- Total: 131 tests passing.

## [0.4.0] — 2026-05-23

### Added
- **Migration checklist** — `MIGRATION_REPORT.md` now opens with a markdown checkbox playbook. Portable nodes roll up to a single "spot-check these N items" line; partial / needs_review / unsupported each get their own checkbox with the specific blocker inline. Turns the report from a diagnostic into a workflow.
- **`praxis init <path>`** — scaffolds a starter OpenClaw project (workflow + 2 plugins + prompt + KV memory + .env.example). Lowers first-touch friction; the scaffold scans cleanly with one realistic `needs_review` to demonstrate the classifier.
- **`praxis scan --json`** — prints `{project, node_count, edge_count, tier_counts, diagnostics, nodes[]}` for programmatic consumers (CI, dashboards).
- **`praxis explain --json`** — prints the full node (with edges in/out) as JSON.

### Tests
- 5 new tests covering `init` (creates scannable project, refuses existing dir without `--force`, `--force` overwrites) and `--json` modes on `scan` and `explain`.
- Total: 125 tests passing.

## [0.3.0] — 2026-05-23

### Added
- **`praxis explain <path> <node>`** — drill into a single IR node: kind, intent (with confidence + evidence), capabilities, side effects, portability tier with rationale + blockers, full edge inventory in/out, provenance. The debugging tool you reach for when a classification surprises you. Accepts either a node name or a full ID, with disambiguation prompts when a name is ambiguous and "did you mean" suggestions on misses.
- **Secrets classifier on env vars** — every env node is now stamped with `metadata["secret"]` and `metadata["classification"]` based on common naming conventions (TOKEN/KEY/SECRET/PASSWORD/etc. matched as whole underscore-segments). The migration report splits the environment section into 🔐 *Secrets* and *Configuration*, with explicit guidance to route secrets through Vault/AWS Secrets Manager rather than plaintext env.
- **`docs/migrating-real-projects.md`** — step-by-step walkthrough for the first day with Praxis on a real OpenClaw repo: install → scan → visualize → report → explain → extract → migrate → iterate.
- **`is_likely_secret(name)`** as a public helper in `praxis_core.analyzers.openclaw.env` so reports and downstream tooling can use the same classification.

### Changed
- **Analyzer error handling**: malformed YAML or unexpected exceptions inside an analyzer now produce structured `Diagnostic` entries (`PRX001` for YAML errors with file:line context, `PRX002` for everything else) instead of a Python traceback. The driver continues running the remaining analyzers so a single broken file doesn't blank out the whole scan.
- **`praxis scan` output** now prints up to 5 errors with hints, and a warning count, instead of a single opaque "N diagnostic(s)" line.
- **`_find_schema(quiet=True)`** added so `praxis doctor` can probe schema discoverability without aborting on failure.

### Tests
- 22 new tests: env classifier, broken-YAML diagnostic emission, `praxis explain` (by name, by full ID, on unknown), and end-to-end report rendering of the secrets split.
- Total: 120 tests passing.

## [0.2.0] — 2026-05-23

### Added
- **`praxis skills extract`** — surfaces two kinds of candidate skill consolidations:
  - **Prompt clusters**: token-bigram Jaccard similarity (single-link, configurable threshold) with tiered suggestions (loose family ≥ threshold / strong overlap ≥ 0.60 / near-duplicate ≥ 0.85).
  - **Repeated tool sequences**: maximal tool chains (length ≥ 2) that appear in ≥ 2 workflows, found via subsequence tally + maximality filter.
  - Pure rule-based, no LLM. See [`docs/skills-extract.md`](docs/skills-extract.md).
- **`praxis doctor`** — sanity checks the local install: praxis import, IR schema discoverability, required dependencies, baseline fixture readability.
- **`praxis --version`** — prints CLI version and IR schema version.
- **Golden-file regression suite** under `tools/fixtures/baseline/` — locks the full migration output (`ir.json` + `architecture.mmd` + `hermes/` tree) of the baseline fixture. Diffs against live output on every `pytest` run.
- **Three demo prompt families** in `examples/openclaw-sample/prompts/` — `summarize_weekly.j2` and `classify_email.j2` (cluster with their originals at 0.6 and 0.5 respectively) and `extract_entities.j2`/`extract_entities_v2.j2` (cluster at 0.90) — exercise all three suggestion tiers.
- **`weekly_digest` workflow** in the fixture — shares the full 4-tool chain (`fetch_articles → dedupe_seen → llm_summarize → slack_post`) with `daily_digest` to demonstrate sequence repetition detection.
- **`CHANGELOG.md`** and `docs/skills-extract.md` user guide.

### Changed
- **CI**: `mypy` strict mode is now load-bearing (no more `continue-on-error: true`). All 32 prior strict-mode warnings resolved.
- **CI**: ajv-cli now loads `ajv-formats` so `date-time` format validation passes against the draft-2020-12 schema.
- **Repo layout**: `HANDOFF.md` moved from repo root to `docs/internal/HANDOFF.md`; it's an internal collaborator handoff doc, not a user document.
- **README**: rewritten to reflect v0.2; added portability-tier table, skill-extract section, badges, `doctor` + `--version` in CLI ref, sample outputs, good-first-issues list.

### Fixed
- Pydantic enum naming collision in `tests/test_classifier.py` — the test helper's `kind` parameter shadowed metadata's own `kind` field, causing every TOOL-kind test to `TypeError`.

### Infrastructure
- `types-PyYAML` and `types-jsonschema` added as dev dependencies.
- Removed `cache: pnpm` from the typescript CI job (no committed lockfile by design).
- ruff: ignored `UP042` globally (the `(str, Enum)` pattern is intentional with Pydantic `use_enum_values=True`; `StrEnum` changes the 3.12 `str()` repr). Per-file-ignored `B008` in `cli.py` (typer's `Argument()`/`Option()` are deliberately function calls in defaults).

## [0.1.0] — 2026-05-22

Initial MVP. Analyzer, rule-based portability classifier, deterministic IR, Hermes emitter, Markdown + Mermaid reports.

### Added
- **Six-stage pipeline**: scan → analyze → resolve → score → translate → emit.
- **CLI**: `scan`, `graph`, `report`, `migrate`, `ir validate`, `ir diff`.
- **IR schema** `0.1` (JSON Schema draft 2020-12) — the public contract.
- **OpenClaw analyzers** for workflows, plugins, prompts, memory stores, schedulers, services, env, project metadata.
- **Hermes emitter** producing the canonical YAML layout for skills, tools, schedules, memory, prompts.
- **Portability classifier** with four tiers: `portable` / `partial` / `needs_review` / `unsupported`.
- **Markdown migration report** + **Mermaid architecture graph**.
- **Sample fixture** under `examples/openclaw-sample/` exercising every code path.
- **CI matrix** on Python 3.11/3.12 with ruff, mypy, pytest, ajv schema validation, and TypeScript typecheck.

### Decisions
- ADR-0001 — Bidirectional IR scoped to OpenClaw ↔ Hermes only; no "universal IR" until a third backend forces generality.
- ADR-0002 — Analyzer reads YAML manifests only, not source code.

[Unreleased]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ikatyal2110/openclaw-to-hermes/releases/tag/v0.1.0
