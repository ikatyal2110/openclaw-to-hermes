# Migrating a real OpenClaw project

A practical walkthrough — what the first day with Praxis on a non-trivial OpenClaw repository actually looks like.

## Before you start

You need:

- A Python 3.11+ environment
- Read access to the OpenClaw project you want to migrate
- ~30 minutes for a small project; a half-day for one with 10+ workflows

Don't worry about getting it right the first time. Praxis is designed for iteration: `scan` and `migrate` are cheap, you can run them dozens of times while you clean things up.

## Step 0 — Install Praxis

```bash
git clone https://github.com/ikatyal2110/openclaw-to-hermes
cd openclaw-to-hermes
pip install -e packages/core-py
praxis doctor
```

If `praxis doctor` shows any red, fix that before going further. The most common issue is missing the `types-PyYAML` / `types-jsonschema` stubs when you've installed without the `[dev]` extras.

## Step 1 — Point it at your project

```bash
praxis scan ~/work/my-openclaw-project
```

You should see a Rich-formatted table of every node Praxis found, classified by portability tier:

```
         Praxis scan
┃ Kind          ┃ Name            ┃ Tier         ┃ Score
│ workflow      │ daily_digest    │ portable     │  0.95
│ tool          │ fetch_articles  │ portable     │  1.00
│ tool          │ dedupe_seen     │ needs_review │  0.40
│ memory_store  │ seen_articles   │ portable     │  1.00
│ ...
```

**If you see errors** (PRX001/PRX002 codes): your YAML probably doesn't quite match the conventions in [`docs/openclaw-format.md`](openclaw-format.md). Read the error — it'll tell you the file and line. Fix and re-run.

## Step 2 — Visualize the architecture

```bash
praxis graph ~/work/my-openclaw-project --format mermaid > arch.mmd
```

Paste the contents into [mermaid.live](https://mermaid.live) (or use a Mermaid VS Code preview). You'll see your workflows, tools, memory stores, and the edges between them. Color-coded by portability tier:

- 🟢 green — `portable`
- 🟡 yellow — `partial`
- 🟠 orange — `needs_review`
- 🔴 red — `unsupported`

This is usually the first moment a team sees their *whole* agent architecture in one picture. Take time with it.

## Step 3 — Read the report

```bash
praxis report ~/work/my-openclaw-project > REPORT.md
```

Open `REPORT.md`. The sections are ordered by what you'll act on first:

1. **Tier summary** — how much of the project is portable vs. needs work?
2. **Per-node tier table** — which specific things are flagged?
3. **TODOs** — each `partial` / `needs_review` node with its specific blocker
4. **Required environment** — split into 🔐 secrets vs. regular config
5. **External services** — Jira, OpenAI, etc. — wire equivalents on the Hermes side
6. **Diagnostics** — anything Praxis couldn't make sense of

Most projects have 60–80% portable nodes and a long tail of needs-review items, typically:
- Impure Python plugins (declare `pure: true` if they truly are, otherwise wrap as HTTP)
- Vector memory stores (embedding model isn't declared in OpenClaw)
- Router plugins (have no one-to-one Hermes mapping — fold into autonomous decomposition)
- Webhook-triggered workflows (you'll need to wire your own HTTP listener)

## Step 4 — Debug surprises with `praxis explain`

If a node is in a tier you didn't expect:

```bash
praxis explain ~/work/my-openclaw-project some_tool_name
```

You get the full picture for one node: kind, intent (with confidence), capabilities, side effects, portability tier + rationale + blockers, and all the edges in/out. The `rationale` line tells you *why* Praxis classified it the way it did — usually that's enough to either accept the classification or know what to change in your OpenClaw source.

## Step 5 — Find consolidation opportunities

```bash
praxis skills extract ~/work/my-openclaw-project --report extract.md
```

This finds two kinds of latent structure:

1. **Prompt clusters** — prompts that drift over time into near-duplicates. Merge them on the Hermes side as one parameterized skill.
2. **Repeated tool sequences** — tool chains that recur across workflows. Factor them out as one shared skill rather than re-inlining the chain.

Run this **before** the actual migration. Cleaning up OpenClaw-side duplication gives a cleaner Hermes output.

## Step 6 — Generate the Hermes project

```bash
praxis migrate ~/work/my-openclaw-project --out ./hermes-out
```

You get:

```
hermes-out/
├── MIGRATION_REPORT.md     ← read this
├── architecture.mmd        ← visualize this
├── ir.json                 ← inspect/diff this
└── hermes/
    ├── skills/             ← one YAML per workflow
    ├── tools/              ← one YAML per plugin
    ├── schedules/          ← one YAML per cron trigger
    ├── memory/             ← one YAML per store
    └── prompts/            ← prompts copied verbatim
```

Treat the `hermes/` tree as a **head start, not a final answer**. The report tells you what still needs human review.

## Step 7 — Iterate

The typical loop:

1. Read a TODO in `MIGRATION_REPORT.md`.
2. Fix it on the OpenClaw side (or note it for manual Hermes work).
3. Re-run `praxis migrate`.
4. Diff the new IR against the old: `praxis ir diff ./hermes-out/ir.json ./hermes-out.previous/ir.json`.

The IR diff is your changelog. If you accidentally regress a tier from `portable` back to `needs_review`, you'll see it.

## Step 8 — Manual cleanup on the Hermes side

The generated `hermes/skills/*.yaml` will have:

- `description` synthesized from inferred intent
- `when_to_use` derived from triggers and step structure
- `procedure` mirroring the OpenClaw step sequence
- `_praxis: confidence` for skills below 1.0 — review these first

Move them into your real Hermes project, polish the prose, and ship.

## What Praxis won't do for you

- **Translate custom Python plugin code.** It analyzes YAML manifests only. If your plugin lives in `plugins/foo.py`, Praxis sees the manifest's signature but doesn't read the source. You'll need to port the body manually.
- **Resolve cross-project secrets.** It flags 🔐 secret-named env vars but doesn't pull values from Vault/AWS Secrets Manager for you.
- **Migrate runtime state.** If your OpenClaw deployment has live state in memory stores, you need to plan that migration separately (the analyzer only reads the schemas).
- **Auto-translate router plugins.** Hermes uses autonomous decomposition instead of explicit routing — that's a model change, not a syntax change. Praxis flags routers as `partial` and gives you the structural skeleton to fill in.

## Getting help

- Check [`docs/openclaw-format.md`](openclaw-format.md) and [`docs/hermes-format.md`](hermes-format.md) for the assumed YAML conventions.
- File an issue with a minimal failing input — those become regression fixtures.
- Read [`CONTRIBUTING.md`](../CONTRIBUTING.md) for code organization if you want to extend the analyzers/translators.
