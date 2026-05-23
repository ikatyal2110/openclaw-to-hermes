# OpenClaw format (assumed by this MVP)

Praxis v0.1's analyzer reads the YAML convention documented here. If your OpenClaw project uses a different dialect, fork the analyzer modules under `packages/core-py/praxis_core/analyzers/openclaw/` — the IR is the stable interface; analyzers are intentionally swappable.

## Project layout

```
my-openclaw-project/
├── openclaw.yaml             # project metadata
├── workflows/                # one YAML per workflow
├── plugins/                  # one YAML per plugin
├── prompts/                  # *.j2 or *.txt prompt templates
├── memory/stores.yaml        # memory store declarations
├── services/services.yaml    # external dependencies (DBs, MCP, APIs)  [optional]
└── .env.example              # declared environment variables
```

## `openclaw.yaml`

```yaml
name: my-project
version: 1.2.0
description: "Optional human description."
env:
  - RSS_URL
  - SLACK_CHANNEL
  - OPENAI_API_KEY
```

## Workflows

```yaml
# workflows/daily_digest.yaml
name: daily_digest
description: "Daily RSS summary posted to Slack."   # optional
triggers:
  - kind: cron
    spec: "0 9 * * *"
steps:
  - id: fetch
    plugin: fetch_articles
    with:
      source: "${env.RSS_URL}"
  - id: summarize
    plugin: llm_summarize
    with:
      prompt: summarize
      input: "${steps.fetch.output}"
  - id: notify
    plugin: slack_post
    with:
      channel: "${env.SLACK_CHANNEL}"
      body: "${steps.summarize.output}"
```

Supported `triggers[].kind`: `cron`, `webhook`, `manual`.
Supported step references: `${env.VAR}`, `${steps.<id>.output}`, `${prev.output}` (shorthand for the immediately preceding step).

## Plugins

```yaml
# plugins/fetch_articles.yaml
name: fetch_articles
kind: tool                # tool | router | sink
runtime: http             # http | python | subprocess
config:
  method: GET
  url_template: "${source}"
inputs:
  - {name: source, type: string, required: true}
outputs:
  - {name: articles, type: list<object>}
```

Runtime semantics:
- `http` → portable. Maps to a Hermes HTTP tool.
- `python` → portable iff the entrypoint is a pure function. Otherwise `needs_review`.
- `subprocess` → `needs_review`. Hermes has no native subprocess primitive.

`kind: router` → `needs_review`. Routing in OpenClaw is autonomous decomposition in Hermes — the migration suggests collapsing the router into the calling skill.

## Prompts

Plain text or Jinja2 templates under `prompts/`. The filename (without extension) is the prompt name referenced from workflow steps.

## Memory

```yaml
# memory/stores.yaml
stores:
  seen_articles:
    kind: kv
    key_type: string
    value_type: object
    ttl_seconds: 604800
  ticket_history:
    kind: vector
    dim: 1536
    metric: cosine
```

`kind: kv` translates cleanly. `kind: vector` translates with a caveat (embedding model must be specified on the Hermes side). `kind: sql` → `needs_review` in MVP.

## Services

```yaml
# services/services.yaml
services:
  jira:
    kind: api
    base_url: "${env.JIRA_BASE_URL}"
  postgres:
    kind: database
    dsn: "${env.DATABASE_URL}"
```

Services are surfaced in the report as external dependencies. They do not translate directly — the Hermes side must declare them in its own format (or the corresponding tools must encapsulate them).

## What's deliberately out of scope for v0.1

- Inline Python plugin source — Praxis parses YAML manifests, not arbitrary Python entrypoints. Add a `kind: python` plugin's source under `plugins/<name>.py` and the analyzer will note it but not introspect.
- Conditional workflow branches (`when:` clauses) — flagged `needs_review`. Hermes-side decomposition is the recommended pattern.
- Loops over collections — flagged `needs_review` for the same reason.
- Multi-tenant configuration — Praxis assumes one project per repo root.
