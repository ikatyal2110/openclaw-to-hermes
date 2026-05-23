<!-- Praxis PR template. Keep it tight. -->

## What this changes

<!-- One paragraph. The user-visible behavior change, not the implementation. -->

## Why

<!-- Link the issue, or describe the migration scenario this unblocks. -->

## IR impact

- [ ] No IR change.
- [ ] IR additive change (new optional field). `praxis_ir_version` bumped to: <!-- e.g. 0.2 -->
- [ ] IR breaking change. ADR linked: <!-- docs/adr/NNNN-*.md -->

## Tests

- [ ] New/changed analyzer or translator has unit tests under `packages/core-py/tests/`.
- [ ] If this affects emitted output, the pipeline test asserts the new shape.
- [ ] If this adds a fixture, `tools/fixtures/<name>/expected/` is committed.

## Reviewer notes

<!-- Anything that won't be obvious from the diff: trade-offs, follow-up issues, scope cuts. -->
