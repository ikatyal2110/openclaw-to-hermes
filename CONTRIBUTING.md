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

Run the canonical fixture end-to-end:

```bash
praxis migrate examples/openclaw-sample --out /tmp/praxis-out
```

You should see `MIGRATION_REPORT.md`, `architecture.mmd`, `ir.json`, and a `hermes/` tree under `/tmp/praxis-out`.

## The fastest way to help

Add a fixture. `tools/fixtures/` is where we want to grow a public benchmark suite of real-ish OpenClaw projects. Each fixture is a directory with:

- The OpenClaw source (`openclaw.yaml`, `workflows/`, etc.).
- An expected `ir.json` (the result of `praxis scan ... --emit-ir`).
- An expected `out/` tree (the result of `praxis migrate ...`).
- A short `README.md` explaining what's interesting about it.

When a fixture fails to round-trip, that's the bug we want.

## Code organization

- `packages/core-py/praxis_core/analyzers/` — read a framework, emit partial IR.
- `packages/core-py/praxis_core/resolver.py` — link references, drop orphans.
- `packages/core-py/praxis_core/scoring/` — rule-based portability classifier. **Do not LLM-ify this without strong reason.**
- `packages/core-py/praxis_core/translators/` — IR → IR (per `source × target × node-kind`).
- `packages/core-py/praxis_core/emitters/` — IR → files on disk.
- `packages/core-py/praxis_core/reports/` — Markdown + Mermaid rendering.
- `packages/ir/` — TypeScript mirror of the IR types.
- `packages/cli/` — thin TS shell around the Python CLI.

## Style

- Python: `ruff` and `mypy --strict`. CI will reject otherwise.
- TypeScript: strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
- Default to writing no comments. If a comment is needed, explain *why*, not what.

## IR changes

The IR is the public contract. Changing it touches everything downstream.

- **Additive change** (new optional field) → MINOR bump in `praxis_ir_version`. Update the JSON Schema, the Pydantic model, and the TS zod schema in the same PR.
- **Breaking change** (removed/renamed field) → MAJOR bump, and an ADR under `docs/adr/`. New ADRs are numbered sequentially.

## Decisions that need an ADR

Anything that:
- Adds a node `kind` or `capability`.
- Adds an extension point.
- Changes the portability classifier's tier definitions.
- Adds a new source or target framework.

## Filing issues

Two issue templates are the most useful:

- **"Praxis ate my workflow"** — paste a minimal OpenClaw repro + expected Hermes output. We turn these into fixtures.
- **"This translation is wrong"** — paste the IR node, the emitter output, and a one-paragraph explanation of why it's wrong. Be specific about *which* tier the node should be in.

## Code of conduct

See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Short version: be specific, be kind, and assume the other person has read more of the code than you have.
