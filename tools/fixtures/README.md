# Fixtures

Golden-file regression projects for Praxis. Each subdirectory is a complete OpenClaw project plus the expected migration output.

Standard layout:

```
tools/fixtures/<name>/
├── README.md            # what's interesting about this fixture
├── source/              # OpenClaw input
└── expected/
    ├── ir.json
    ├── architecture.mmd
    └── hermes/
```

To add one:

```bash
praxis scan tools/fixtures/<name>/source --emit-ir tools/fixtures/<name>/expected/ir.json
praxis migrate tools/fixtures/<name>/source --out tools/fixtures/<name>/expected
```

## Baseline (exception)

`tools/fixtures/baseline/` has no `source/` directory — it reuses `examples/openclaw-sample/` as its source so the example stays discoverable as a user-facing demo. The locking test (`packages/core-py/tests/test_fixtures.py`) points at `examples/openclaw-sample/` and diffs the live output against `tools/fixtures/baseline/expected/`.

To regenerate the baseline after an intentional change:

```bash
praxis migrate examples/openclaw-sample --out /tmp/baseline-refresh
# Then refresh tools/fixtures/baseline/expected/ from /tmp/baseline-refresh,
# normalizing project.analyzed_at and project.source_root in ir.json to the
# literal string "NORMALIZED" (the test normalizes the same fields).
```

Future fixtures should follow the standard `source/`+`expected/` layout.
