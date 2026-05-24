# Authoring a backend

This guide explains how to add support for a **third framework** to Praxis — either as a new *source* (read the framework's projects into the IR) or a new *target* (emit projects from the IR), or both. The architecture was designed for this from day one; see [ADR-0001](adr/0001-bidirectional-ir.md).

Concrete example: you want Praxis to be able to migrate an OpenClaw project to **LangGraph**, or to read an existing **AutoGen** project into the IR for analysis.

## The contract

A backend is *just* an analyzer (source) and/or an emitter (target). They both speak the IR — nothing else. The IR is the contract; if your code preserves it, the rest of the pipeline works unchanged.

```
                ┌─────────────┐                ┌─────────────┐
   <framework>  │  analyzer   │   IRGraph      │  emitter    │  <framework>
    project    →│ (source)    │───────────────→│ (target)    │→  project
                └─────────────┘                └─────────────┘

                Translators run between analyzer and emitter to remap
                node kinds, capabilities, and constructs to the target's idioms.
```

You don't need to write both an analyzer and an emitter — pick the direction you care about. A source-only backend lets users `praxis scan` and `praxis migrate <my-framework> <other-framework>`. A target-only backend lets them `praxis migrate <other-framework> <my-framework>`.

## Where things live

```
packages/core-py/praxis_core/
├── analyzers/
│   ├── openclaw/        # reference: source analyzer (7 sub-analyzers)
│   └── hermes/          # reference: source analyzer (5 sub-analyzers)
├── translators/
│   └── openclaw_to_hermes/   # reference: per-kind translators + types
└── emitters/
    └── hermes.py        # reference: target emitter
```

To add a backend called `langgraph`, you'd create:

```
packages/core-py/praxis_core/
├── analyzers/langgraph/          # if reading LangGraph projects
└── emitters/langgraph.py         # if writing LangGraph projects
```

And at least one translator if you're emitting:

```
packages/core-py/praxis_core/translators/openclaw_to_langgraph/
```

## Step-by-step: a source analyzer

1. **Make a directory** `praxis_core/analyzers/<name>/`.
2. **Add `__init__.py`** that re-exports a top-level `analyze_<name>_project(root: Path) -> IRGraph`.
3. **Add a `driver.py`** mirroring [`analyzers/hermes/driver.py`](../packages/core-py/praxis_core/analyzers/hermes/driver.py) — wraps each sub-analyzer in `try`/`except` so YAML errors become PRX001 diagnostics instead of stack traces.
4. **For each file kind** the framework has (workflows, plugins, prompts, memory, …), add a per-kind analyzer module mirroring the OpenClaw pattern:

    ```python
    class MyKindAnalyzer(Analyzer):
        name = "<framework>.<kind>"

        def analyze(self, root: Path) -> IRGraph:
            ir = IRGraph()
            for path in sorted((root / "<subdir>").glob("*.yaml")):
                data = self.safe_load_yaml(path)
                if not isinstance(data, dict):
                    continue
                ir.nodes.append(Node(
                    id=make_node_id("<framework>", NodeKind.XXX, data.get("name")),
                    kind=NodeKind.XXX,
                    name=data.get("name"),
                    provenance=Provenance(
                        framework="<framework>",
                        source_file=str(path.relative_to(path.parents[1])),
                    ),
                    metadata={...},   # everything the classifier or translator will need
                ))
            return ir
    ```

5. **Pick the right `NodeKind`** for what you're emitting. The current kinds are:

    | NodeKind | Use for |
    |---|---|
    | `WORKFLOW` | Ordered procedures (OpenClaw workflows, LangGraph graphs) |
    | `SKILL` | Hermes-style invokable units; declarative `when_to_use` |
    | `TOOL` | Single-purpose callable (HTTP endpoint, function, container) |
    | `PROMPT` | Template body |
    | `MEMORY_STORE` | Stateful backend |
    | `SCHEDULER` | Cron, webhook, or event trigger |
    | `SERVICE` | External system (DB, third-party API) declared in config |
    | `SECRET` | Reserved (currently env nodes carry `metadata.secret`) |
    | `ENV` | Environment variable reference |

    If your framework has a concept that doesn't fit any of these, **don't add a new kind silently** — write an ADR (see [ADR-0001](adr/0001-bidirectional-ir.md)) and discuss in an issue first. Every new kind has ripple effects: classifier, translator, report, mermaid renderer, JSON Schema, TS zod schema.

6. **Wire it in.** Add your driver call wherever the CLI looks up source frameworks (currently `praxis_core/pipeline.py`'s `build_ir` is hard-coded to OpenClaw; a follow-up PR can make it dispatch on `Project.source_framework`, but for now you can wire a parallel function `build_ir_langgraph`).

7. **Write tests.** Each analyzer module gets a test file under `tests/test_analyzers_<framework>.py`. The bar is: every file kind produces the expected node shape from a representative input, and a broken-YAML input produces a PRX001 diagnostic instead of a crash.

## Step-by-step: a target emitter

1. **Add `praxis_core/emitters/<name>.py`** with one top-level function `emit_<name>_project(project: <NameProject>, out_root: Path) -> dict[str, list[str]]`.
2. **Define a project shape** under `praxis_core/translators/openclaw_to_<name>/types.py` (mirroring `openclaw_to_hermes/types.py`). These are dataclasses or pydantic models that describe what's about to be written — they're the type-safe handoff between the translator and the emitter.
3. **Translate** per node kind. Mirror `openclaw_to_hermes/workflow_to_skill.py` etc. — each translator file owns one IR-kind → one target-kind translation.
4. **Write the emitter** — flat file-per-node, sorted-keys YAML, deterministic output.
5. **Preserve non-trivial constructs as `_praxis_<construct>`** in the output. Praxis does this for `when:`, `for_each:`, `retry:` in the Hermes emitter — the prefixed key makes the auto-generation visible to a human reviewer, and they rename it to the target's actual key once they've verified the syntax.
6. **Drop metadata for the happy path.** If the skill emerged with confidence ≥ 0.9 AND no TODOs, the `_praxis` metadata block should be omitted — otherwise the output looks more auto-generated than it needs to. See [`praxis_core/emitters/hermes.py:_skill_dict`](../packages/core-py/praxis_core/emitters/hermes.py).
7. **Lock the output with a fixture.** Add `tools/fixtures/<name>/` with `source/` (an example OpenClaw project) and `expected/` (the emitter's deterministic output). A regression test diffs the actual against the expected — see `tests/test_fixtures.py` for the pattern.

## Step-by-step: a translator (when emitter and analyzer kinds differ)

OpenClaw has `WORKFLOW`; Hermes has `SKILL`. The translator owns that remapping. Create:

```
praxis_core/translators/openclaw_to_<name>/
├── __init__.py             # re-exports translate_openclaw_to_<name>
├── driver.py               # iterates IR.nodes, dispatches per kind
├── types.py                # target shape (dataclasses / pydantic)
├── workflow_to_skill.py    # one per IR-kind → target-kind transform
├── plugin_to_tool.py
├── prompts.py
└── memory_schema.py
```

The driver pattern is straightforward — see [`openclaw_to_hermes/driver.py`](../packages/core-py/praxis_core/translators/openclaw_to_hermes/driver.py) for the reference.

## Step-by-step: extending the portability classifier

When you add a new source framework, the classifier may need new rules to know how that framework's constructs map to portability tiers. The classifier rules live in [`praxis_core/scoring/classifier.py`](../packages/core-py/praxis_core/scoring/classifier.py).

The rule: classification is **always rule-based**. No LLM-in-the-classifier. Opaque scoring kills the trust the report depends on. If you need fuzzy matching, do it in intent-inference or skills-extract, not the classifier.

## Don't forget

- **Update [`schemas/praxis-ir.schema.json`](../schemas/praxis-ir.schema.json)** if you add an IR field. The schema is the public contract; analyzers and emitters in other languages depend on it. Bump `praxis_ir_version` and add an ADR for non-additive changes.
- **Update [`docs/<framework>-format.md`](.)** documenting the YAML conventions your analyzer assumes. Praxis is honest about the dialects it supports — undocumented assumptions are bugs in waiting.
- **Add a CI matrix entry** if your backend needs additional system deps (Node tooling, a specific Python lib, …).
- **Add at least one good-first-issue** in the README pointing at your backend's open gaps.

## Testing the round trip

If your backend supports both directions, you get round-trip testing for free:

```python
def test_my_backend_round_trips(tmp_path):
    forward = build_ir(openclaw_path)
    out = tmp_path / "out"
    migrate(openclaw_path, out, target="<name>")
    back = analyze_<name>_project(out)
    # Common nodes survive (some loss is expected for env/services/etc.)
    fwd = {(n.kind, n.name) for n in forward.nodes}
    bk = {(n.kind, n.name) for n in back.nodes}
    assert len(fwd & bk) >= 0.5 * len(fwd)  # majority round-trip
```

`praxis roundtrip <openclaw-path>` does this end-to-end against Hermes today. Extending it for a new target is one line.

## A short rant about IR stability

The IR is currently `v0.1` and explicitly unstable. Any change you make to the schema during early development is fine. **Once Praxis v1.0 ships, the IR is frozen** — additive-only without a major bump.

This means: if you're adding a backend pre-v1.0, lobby for the IR shape you need now. Post-v1.0, you'll have to live with what's there or fork the schema.

## Examples to read in order

1. [`praxis_core/analyzers/openclaw/prompts.py`](../packages/core-py/praxis_core/analyzers/openclaw/prompts.py) — the simplest analyzer (one file per node, no edges).
2. [`praxis_core/analyzers/openclaw/workflows.py`](../packages/core-py/praxis_core/analyzers/openclaw/workflows.py) — the most complex (intent inference, edges to plugins, scheduler emission).
3. [`praxis_core/analyzers/hermes/driver.py`](../packages/core-py/praxis_core/analyzers/hermes/driver.py) — the error-wrapping pattern.
4. [`praxis_core/translators/openclaw_to_hermes/workflow_to_skill.py`](../packages/core-py/praxis_core/translators/openclaw_to_hermes/workflow_to_skill.py) — the construct-preservation pattern (`_praxis_when` / `_praxis_for_each` / `_praxis_retry`).
5. [`praxis_core/emitters/hermes.py`](../packages/core-py/praxis_core/emitters/hermes.py) — the emitter doing the cleanest happy-path output.

## Opening the PR

See [CONTRIBUTING.md § "Decisions that need an ADR"](../CONTRIBUTING.md#decisions-that-need-an-adr). Adding a new source or target framework requires an ADR — short, one page, format: Context / Decision / Consequences.

Once merged, your backend appears in `praxis doctor`'s output and in the README's CLI reference. The community thanks you.
