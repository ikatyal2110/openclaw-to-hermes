# Hermes format (emitted by this MVP)

Praxis v0.1 emits the YAML convention documented here. If your Hermes runtime uses a different on-disk format, replace the emitter at `packages/core-py/praxis_core/emitters/hermes.py` — the IR stays the same.

## Output layout

```
out/
├── hermes/
│   ├── skills/                   # one YAML per skill (from workflows)
│   ├── tools/                    # one YAML per tool (from plugins)
│   ├── schedules/                # one YAML per schedule (from cron triggers)
│   ├── memory/                   # memory schemas
│   └── prompts/                  # extracted prompt templates
├── ir.json                       # canonical IR (replayable)
├── architecture.mmd              # Mermaid graph
└── MIGRATION_REPORT.md           # per-node feasibility, blockers, TODOs
```

## Skill

```yaml
# hermes/skills/daily_digest.yaml
name: daily_digest
description: |
  Daily RSS summary posted to Slack. Fetches articles, summarizes each in 2
  sentences, and posts a digest to the configured channel.
when_to_use:
  - "scheduled daily briefing trigger fires"
  - "user requests a daily RSS digest"
inputs:
  rss_url: {type: string, env: RSS_URL}
  channel: {type: string, env: SLACK_CHANNEL}
procedure:
  - tool: fetch_articles
    with: {source: ${rss_url}}
    as: fetched
  - tool: llm_summarize
    with: {input: ${fetched}}
    as: summary
  - tool: slack_post
    with: {channel: ${channel}, body: ${summary}}
```

`when_to_use` is the slot most translators can't fill mechanically. The MVP seeds it from `intent.description` and the originating triggers; the report flags `confidence < 0.6` for human review.

## Tool

```yaml
# hermes/tools/fetch_articles.yaml
name: fetch_articles
description: "HTTP GET against an RSS source, returns parsed articles."
runtime: http
spec:
  method: GET
  url_template: "${source}"
inputs:
  - {name: source, type: string, required: true}
outputs:
  - {name: articles, type: list<object>}
```

## Schedule

```yaml
# hermes/schedules/daily_digest.yaml
cron: "0 9 * * *"
invoke_skill: daily_digest
```

## Memory schema

```yaml
# hermes/memory/seen_articles.yaml
name: seen_articles
kind: kv
key_type: string
value_type: object
ttl_seconds: 604800
```

## What Hermes-side users still need to do

The emitter does **not** generate:
- Hermes runtime configuration (model selection, API keys).
- Hermes orchestration glue (how the planner is bootstrapped).
- Tests of the migrated skills against your data.

Those are deliberately outside the migration scope. Praxis stops at the boundary of "this is a faithful translation of intent." The Hermes side has to be wired by the developer.
