# Migration model

How Praxis decides what's portable, what needs review, and what isn't supported.

## The three tiers, restated

| Tier | What it means |
|---|---|
| `portable` | Rule-based translator produces output the developer can use directly. |
| `partial` | Output is correct in shape, but prose (descriptions, `when_to_use`) needs sharpening. |
| `needs_review` | Translator emits a stub with specific questions in the report. The developer must intervene. |
| `unsupported` | No translator applies. Preserved in the report as a documented gap. |

## Specific OpenClaw → Hermes mappings

### Workflow → Skill

A workflow with linear steps and an inferable single-sentence intent becomes a Hermes skill. The skill's `procedure` mirrors the workflow's `steps`; `when_to_use` is seeded from `intent.description`.

Caveats:
- Workflows with conditional branches (`when:` clauses) → `needs_review`. Recommended Hermes pattern: split into multiple skills; let the planner choose.
- Workflows with loops → `needs_review`. Recommended pattern: a single tool that handles the collection.

### Cron trigger → Schedule

`triggers[].kind: cron` becomes a Hermes schedule pointing to the generated skill. Cron expressions pass through verbatim. `webhook` and `manual` triggers do not produce schedules — they imply a different invocation path on the Hermes side, flagged in the report.

### Plugin → Tool

`plugin.runtime: http` translates cleanly to `hermes/tools/<name>.yaml` with the same input/output shapes.

`plugin.runtime: python` translates only if the entrypoint is declared as `pure: true` in the plugin manifest. Otherwise the report includes a stub and a question: "Does this plugin have side effects beyond its declared inputs?"

`plugin.runtime: subprocess` is unsupported. Diagnostic `PRX040`: "Hermes has no native subprocess primitive. Wrap as an HTTP service or remove."

### Router plugin → Autonomous decomposition

`plugin.kind: router` does not translate one-to-one. In OpenClaw, a router dispatches to one of N downstream plugins. In Hermes, that decision is the planner's job. Praxis collapses routers: the workflow containing the router becomes a single skill whose `when_to_use` enumerates the router's branches as separate triggering conditions.

This is the highest-value migration — it converts mechanical routing into autonomous decomposition — and also the lowest-confidence one. v0.1 always marks router migrations as `partial` with a `confidence` cap of 0.7. The developer reviews.

### Memory: KV → KV

`stores[].kind: kv` translates verbatim. Type tags pass through unchanged.

### Memory: vector → vector

Translates with an explicit `needs_review` flag because the embedding model isn't specified on the OpenClaw side. The report asks: "Which embedding model produced these vectors?"

### Memory: sql → unsupported (v0.1)

Praxis v0.2 will introduce a SQL-memory translator. v0.1 surfaces the store in the report with `tier: unsupported` and the diagnostic "Custom schema; recommend continuing to access via a tool that wraps the database."

### Prompts

Prompts under `prompts/` are extracted verbatim into `hermes/prompts/`. They are also linked into the IR as `prompt` nodes so future skill-clustering (v0.2) can find duplicates.

### Services

`services/services.yaml` entries become `service` nodes in the IR with capability `external_dependency`. They are not emitted on the Hermes side — they are surfaced in the report as required environment.

### Environment variables

Each entry in `.env.example` becomes an `env` node. Workflow/plugin references to `${env.X}` create edges. The report has a dedicated "Required environment" section.

## What we deliberately don't do

- **We don't generate tests.** Tests against migrated skills need ground truth Praxis doesn't have.
- **We don't preserve OpenClaw-specific runtime details** like retry policies — the Hermes runtime has its own. The report notes which retry policies were declared in OpenClaw and asks the developer to translate.
- **We don't reach into source code.** Plugin manifests are read; the Python/JS implementations of those plugins are not introspected in v0.1. (v0.2 adds `libcst`-based introspection for pure-Python plugins.)

## Confidence and review

A node's `intent.confidence` and its `portability.tier` interact as follows:

| confidence | tier | Outcome |
|---|---|---|
| ≥ 0.8 | `portable` | Emit; no flag. |
| 0.6–0.8 | `portable` | Emit; flag in report under "Verify intent". |
| < 0.6 | any | Always flag, even if structurally portable. |
| any | `needs_review` | Emit stub + TODO with questions. |
| any | `unsupported` | Do not emit; document in report. |

This combination is intentional: a structurally clean translation with a fuzzy intent is the most dangerous failure mode — it looks right and is wrong. Better to flag aggressively at low confidence than to ship a plausible lie.
