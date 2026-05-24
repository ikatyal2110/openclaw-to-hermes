# Contributing to Praxis

Thanks for taking the time. Praxis is small and opinionated by design — the bar for new features is "does this make a concrete migration cheaper or more trustworthy?"

## Getting set up

```bash
# Python core
cd packages/core-py
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# TypeScript packages (optional, only if you're touching the CLI wrapper or IR types)
pnpm install
pnpm -r build
```

Sanity-check the install:

```bash
praxis doctor
```

Run the canonical fixture end-to-end:

```bash
praxis migrate examples/openclaw-sample --out /tmp/praxis-out
```

You should see `MIGRATION_REPORT.md`, `architecture.mmd`, `ir.json`, and a `hermes/` tree under `/tmp/praxis-out`.

## Running tests, lint, types

These four commands match exactly what CI runs. Everything must pass before a PR merges.

```bash
cd packages/core-py
ruff check .
ruff format --check .
mypy praxis_core              # strict mode — no continue-on-error
pytest -q                     # 84+ tests, including the golden-file regression
```

For a tighter loop while developing: `pytest -q -x --ff` (stop on first failure, run failures first).

## The fastest way to help

Add a fixture. `tools/fixtures/` is where we want to grow a public benchmark suite of real-ish OpenClaw projects. Each fixture is a directory with:

- The OpenClaw source (`openclaw.yaml`, `workflows/`, etc.).
- An expected `ir.json` (the result of `praxis scan ... --emit-ir`).
- An expected `hermes/` tree + `architecture.mmd` (the result of `praxis migrate ...`).
- A short `README.md` explaining what's interesting about it.

When a fixture fails to round-trip, that's the bug we want.

See [`tools/fixtures/README.md`](tools/fixtures/README.md) for the layout. The `baseline/` fixture is an exception (it reuses `examples/openclaw-sample/` as its source); future fixtures follow the standard `source/`+`expected/` pattern.

## Regenerating the baseline golden fixture

If you've made an intentional change to the analyzer/translator/emitter that affects the baseline output:

```bash
praxis migrate examples/openclaw-sample --out /tmp/baseline-refresh
# Then refresh tools/fixtures/baseline/expected/ from /tmp/baseline-refresh,
# normalizing project.analyzed_at and project.source_root in ir.json to the
# literal string "NORMALIZED" (the regression test normalizes the same fields).
```

The test in `packages/core-py/tests/test_fixtures.py` will fail until the golden is refreshed. Mention the regeneration in your PR description.

## Code organization

- `packages/core-py/praxis_core/analyzers/` — read a framework, emit partial IR.
- `packages/core-py/praxis_core/resolver.py` — link references, drop orphans, dedupe.
- `packages/core-py/praxis_core/scoring/` — rule-based portability classifier. **Do not LLM-ify this without strong reason.**
- `packages/core-py/praxis_core/translators/` — IR → IR (per `source × target × node-kind`).
- `packages/core-py/praxis_core/emitters/` — IR → files on disk.
- `packages/core-py/praxis_core/reports/` — Markdown + Mermaid rendering.
- `packages/core-py/praxis_core/extract/` — prompt clustering for `praxis skills extract`.
- `packages/ir/` — TypeScript mirror of the IR types.
- `packages/cli/` — thin TS shell around the Python CLI.

## Style

- Python: `ruff` (lint + format) and `mypy --strict`. CI will reject otherwise.
- TypeScript: strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
- Default to writing no comments. If a comment is needed, explain *why*, not what.
- Test the unit you wrote — every public function should have at least one test, and every classifier rule has its own test (see `tests/test_classifier.py`).

## IR changes

The IR is the public contract. Changing it touches everything downstream.

- **Additive change** (new optional field) → MINOR bump in `praxis_ir_version`. Update the JSON Schema, the Pydantic model, and the TS zod schema in the same PR.
- **Breaking change** (removed/renamed field) → MAJOR bump, and an ADR under `docs/adr/`. New ADRs are numbered sequentially.

## Decisions that need an ADR

Anything that:
- Adds a node `kind` or `capability`.
- Adds an extension point or plugin interface.
- Changes the portability classifier's tier definitions.
- Adds a new source or target framework.
- Introduces a new external dependency.

See `docs/adr/` for examples. ADRs are short (one page is fine) and have the format: Context / Decision / Consequences.

## Filing issues

Three issue templates are the most useful:

- **"Praxis ate my workflow"** — paste a minimal OpenClaw repro + expected Hermes output. We turn these into fixtures.
- **"This translation is wrong"** — paste the IR node, the emitter output, and a one-paragraph explanation of why it's wrong. Be specific about *which* tier the node should be in.
- **Feature request** — open a discussion first if it's nontrivial. The bar is concrete user pain.

## Commit & PR conventions

- One logical change per commit. The CI runs on every push.
- Commit messages: imperative mood ("add X", "fix Y"), one-line summary under 70 chars, optional body explaining *why*.
- PRs: include the local verification you ran (`ruff check`, `mypy`, `pytest`) and any baseline-regeneration notes.
- All public-facing changes (new commands, new flags, schema bumps) need a `CHANGELOG.md` entry under `## [Unreleased]`.

## Release process

We use semantic versioning. The release helper at [`scripts/release.sh`](scripts/release.sh) automates the boring parts.

### Pre-release checklist

1. Move the `## [Unreleased]` section in `CHANGELOG.md` under a new `## [X.Y.Z] — YYYY-MM-DD` heading.
2. Update README's roadmap section if the release closes a roadmap item.
3. Confirm the local gate is clean (`scripts/release.sh` will re-check, but failing early saves time):
   ```bash
   cd packages/core-py
   ruff check . && ruff format --check . && mypy praxis_core && pytest -q
   ```

### Cutting the release

```bash
# Dry — bumps version, runs gate, builds artifacts, commits, tags, pushes.
scripts/release.sh 0.12.0

# Same plus PyPI upload (requires PYPI_TOKEN or ~/.pypirc).
scripts/release.sh 0.12.0 --pypi
```

### After the script finishes

Create the GitHub release with the CHANGELOG entry as the body. The script prints the exact `gh` command to run.

### PyPI publishing (when ready)

The package is **not yet on PyPI** as of v0.11 — install is still from-clone. The first PyPI publish needs:

1. A PyPI account and a token scoped to the `praxis-core` project name.
2. The token set as `PYPI_TOKEN` in your environment or in `~/.pypirc`.
3. Reserve the name on TestPyPI first to verify the package metadata renders correctly:
   ```bash
   cd packages/core-py
   python3 -m build
   python3 -m twine upload --repository testpypi dist/*
   pip install --index-url https://test.pypi.org/simple/ praxis-core
   ```
4. Once that round-trips, `scripts/release.sh <version> --pypi` does the real upload.

Until the first publish lands, install instructions in the README direct users to clone the repo and run `pip install -e packages/core-py`.

## Code of conduct

See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Short version: be specific, be kind, and assume the other person has read more of the code than you have.
