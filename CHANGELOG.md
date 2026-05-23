# Changelog

All notable changes to Praxis are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-05-23

### Added
- **`praxis skills extract`** — clusters prompts by token-bigram Jaccard similarity (single-link, configurable threshold) and emits a Markdown report with tiered suggestions (loose family ≥ threshold / strong overlap ≥ 0.60 / near-duplicate ≥ 0.85). Pure rule-based, no LLM. See [`docs/skills-extract.md`](docs/skills-extract.md).
- **`praxis doctor`** — sanity checks the local install: praxis import, IR schema discoverability, required dependencies, baseline fixture readability.
- **`praxis --version`** — prints CLI version and IR schema version.
- **Golden-file regression suite** under `tools/fixtures/baseline/` — locks the full migration output (`ir.json` + `architecture.mmd` + `hermes/` tree) of the baseline fixture. Diffs against live output on every `pytest` run.
- **Three demo prompt families** in `examples/openclaw-sample/prompts/` — `summarize_weekly.j2` and `classify_email.j2` (cluster with their originals at 0.6 and 0.5 respectively) and `extract_entities.j2`/`extract_entities_v2.j2` (cluster at 0.90) — exercise all three suggestion tiers.
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

[Unreleased]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ikatyal2110/openclaw-to-hermes/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ikatyal2110/openclaw-to-hermes/releases/tag/v0.1.0
