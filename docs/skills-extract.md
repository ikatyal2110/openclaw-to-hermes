# `praxis skills extract` — prompt clustering & skill extraction

The skill-extract command surfaces *candidate consolidations* in a project's prompt library: prompts that probably should be one skill with parameterized inputs, but currently exist as two or more near-duplicate templates. It is intentionally **diagnostic, not destructive** — it never rewrites your prompts; it gives you a Markdown report you can act on.

## Why this exists

OpenClaw projects drift. A team adds `summarize.j2` for daily articles, then a quarter later adds `summarize_weekly.j2` for the weekly digest — same prompt, slightly different copy. Six months in, no one notices the duplication; both prompts get edited independently and quietly diverge. `praxis skills extract` finds that drift before you commit it to the Hermes side, where you really do want one skill, not two.

## Quick start

```bash
praxis skills extract examples/openclaw-sample
```

Prints a Rich table of clusters:

```
                    Prompt clusters (threshold=0.40)
┃ # ┃ Size ┃ Min sim ┃ Max sim ┃ Members
│ 1 │    2 │    0.54 │    0.54 │ classify, classify_email
│ 2 │    2 │    0.90 │    0.90 │ extract_entities, extract_entities_v2
│ 3 │    2 │    0.63 │    0.63 │ summarize, summarize_weekly
6 prompt(s) scanned, 3 cluster(s).
```

Write a Markdown report:

```bash
praxis skills extract examples/openclaw-sample --report extract.md
```

Tighten the threshold to only see near-duplicates:

```bash
praxis skills extract examples/openclaw-sample --threshold 0.85
```

## How the algorithm works

Three steps, all rule-based:

1. **Tokenize.** Each prompt is lowercased; Jinja interpolations (`{{ … }}`) and blocks (`{% … %}`) are normalized to a sentinel (`__var__`); the body is split into tokens on non-alphanumeric characters (underscores kept). This means two prompts that differ only in their interpolated variable names are treated as identical text.
2. **Score.** For every prompt pair, Jaccard similarity is computed over the *bigrams* (consecutive token pairs) of the two token streams: `|A ∩ B| / |A ∪ B|`. Bigrams (rather than unigrams) reward shared phrasing, not just shared vocabulary.
3. **Cluster.** Single-link union-find: pairs above the threshold are unioned; groups of size ≥ 2 emerge as clusters. Clusters are sorted by size descending, then alphabetically by first member.

The full implementation lives in `packages/core-py/praxis_core/extract/prompts.py` and is ~120 lines. It has no LLM dependency, no embedding model, no I/O during scoring — just a deterministic function on the IR. This is on purpose: opaque similarity scores would kill the explainability the report depends on.

## Tuning the threshold

| Threshold | What you'll see |
|---|---|
| 0.85 | Only true near-duplicates. Use this if you've already reviewed your prompts and want to find the last few. |
| **0.40 (default)** | A useful working range. Surfaces strong overlap without flooding the report with weak coincidences. |
| 0.20 | A wider net — useful for exploration ("what loosely-related prompts do we have?") but expect false positives. |
| 0.05 | Almost everything will cluster. Diagnostic only. |

If the default produces too many clusters, raise the threshold. If it produces zero on a project you *know* has duplicates, lower it and re-inspect.

## Suggested-action tiers

The report annotates each cluster with a tier based on its **minimum** pairwise similarity (the lowest score among all pairs in the cluster):

| Min similarity | Tier | Suggested action |
|---|---|---|
| ≥ 0.85 | **Near-duplicate** | Merge into one skill and parameterize the differing variables. Delete the redundant prompt files. |
| ≥ 0.60 | **Strong overlap** | Likely one skill with two prose variants. Consider extracting a common preamble; keep distinct task-specific tails. |
| ≥ threshold | **Loose family** | Review before merging. May share a common framing but serve genuinely different tasks. |

Tier is chosen by *min* similarity (not max or mean) because the relevant question is "is **every** pair in this cluster close enough that one skill would serve all of them?" — a cluster's weakest link sets the merger ceiling.

## Tool-sequence repetition

In addition to prompt clustering, `praxis skills extract` finds **repeated tool sequences** across workflows: ordered chains of plugin calls (length ≥ 2) that appear verbatim in ≥ 2 workflows.

Algorithm:

1. For each `workflow` node in the IR, read `metadata["raw_steps"]` and extract the ordered list of plugin names.
2. For every subsequence of length ≥ 2, tally which workflows it appears in (intra-workflow repeats don't inflate the count).
3. Keep only subsequences appearing in ≥ 2 distinct workflows.
4. Apply a **maximality filter**: a subsequence is suppressed if a longer one with the same workflow set already exists. This prevents the report from drowning in every sub-window of a long shared chain.

Output is sorted by length descending, then by occurrence count, then alphabetically.

Suggested actions:

| Heuristic | Suggested action |
|---|---|
| length ≥ 4 OR occurrences ≥ 3 | **Strong factor-out candidate** — define one Hermes skill and call it from each workflow |
| Otherwise | **Possible factor-out** — review whether the workflows share intent or just coincidentally call the same tools |

## Limitations

- **No semantic understanding.** Two prompts that say "summarize" and "TL;DR" in different vocabularies will not cluster. The tokenizer is purely syntactic.
- **Tokens are bag-based.** Bigrams capture local order; full-sentence order is not modeled.
- **Single-link is permissive** (prompts). A chain of moderate pairs can produce a single large cluster (A~B at 0.5, B~C at 0.5 → all three cluster). If you see surprising mergers, look at the pairwise table in the report; the chain is visible there.
- **Sequence matching is exact** (tools). Two workflows that both call `fetch` and `parse` but in different orders won't be detected as sharing a chain. Order matters.

## When to run

- **During a migration audit**, before `praxis migrate`. Cleaning up prompt duplication on the OpenClaw side gives a cleaner Hermes output.
- **After adding new prompts**, as a lightweight CI check (the command exits 0 even when clusters are found — it's diagnostic, not blocking).
- **Quarterly hygiene**, as a sanity check against drift.

## Programmatic use

The clustering is a pure function and can be called from Python:

```python
from praxis_core.extract import cluster_prompts, jaccard_bigrams

similarity = jaccard_bigrams(prompt_a, prompt_b)
clusters = cluster_prompts({"a": prompt_a, "b": prompt_b, "c": prompt_c}, threshold=0.4)
for c in clusters:
    print(c.members, c.min_similarity, c.max_similarity)
```

Or against an existing IR:

```python
from praxis_core.extract import extract_prompt_clusters
from praxis_core.pipeline import build_ir
from pathlib import Path

ir = build_ir(Path("examples/openclaw-sample"))
clusters = extract_prompt_clusters(ir, threshold=0.4)
```

## See also

- [`docs/migration-model.md`](migration-model.md) — how prompts are classified by the portability tier system.
- [`docs/architecture.md`](architecture.md) — where extraction fits in the six-stage pipeline (it operates on a built IR, like the report and graph commands).
