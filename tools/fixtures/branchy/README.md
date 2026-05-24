# branchy fixture

A deliberately non-trivial OpenClaw project that exercises every conditional/loop/retry path Praxis preserves:

| Construct | Where | Expected behavior |
|---|---|---|
| `when:` clause | `workflows/incident_response.yaml` `page` step | Survives as `_praxis_when` + TODO |
| `for_each` clause | `workflows/incident_response.yaml` `notify` step | Survives as `_praxis_for_each` + TODO |
| `retry:` block | `page` and `notify` steps | Survives as `_praxis_retry` + TODO |
| Webhook trigger | `workflows/incident_response.yaml` | Emits a `partial` scheduler |
| Secret env var | `PAGERDUTY_TOKEN` | Flagged 🔐 in the report |
| Config env var | `PAGERDUTY_URL` | Plain config in the report |
| Pure Python plugin | `parse_alert`, `classify_severity` | Tier `portable` |
| HTTP plugin | `pagerduty_create`, `send_email` | Tier `portable` |
| KV memory | `recent_incidents` | Tier `portable` |

Locked by `tools/fixtures/branchy/expected/` and `packages/core-py/tests/test_fixtures_branchy.py`.

## Regenerating

```bash
praxis migrate tools/fixtures/branchy/source --out /tmp/branchy-refresh
# Then refresh tools/fixtures/branchy/expected/ from /tmp/branchy-refresh,
# normalizing project.analyzed_at and project.source_root in ir.json to "NORMALIZED".
```
