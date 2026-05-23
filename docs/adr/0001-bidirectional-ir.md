# ADR 0001: Bidirectional IR, scoped to two frameworks

- **Status:** Accepted (v0.1)
- **Date:** 2026-05-17

## Context

The original brief asked for a "universal agent workflow IR" that could support OpenClaw, Hermes, and future frameworks via plugins. Every prior attempt at a universal agent IR (LangChain LCEL, Semantic Kernel's planner, AutoGen's GraphFlow) ended up either lowest-common-denominator (useless for any specific framework) or coupled to whichever framework dominated at design time (not actually universal).

## Decision

Praxis v0.1 ships a **bidirectional** IR scoped to exactly OpenClaw and Hermes.

- Every node kind, capability, and edge type is justified by appearing in at least one of those two frameworks.
- The IR must round-trip through both: OpenClaw → IR → OpenClaw and Hermes → IR → Hermes (modulo whitespace and key ordering).
- A third backend will not be added to the IR until v0.4. When it is added, the third backend implementation is allowed (expected, even) to force breaking changes to the IR — that's how we learn what's actually general.

## Consequences

**Positive:**
- The IR is grounded in real primitives, not speculative ones.
- Round-trip tests catch lossy translations early.
- We retain the option to generalize later, informed by data.

**Negative:**
- Early contributors who want to add LangGraph/n8n/etc. before v0.4 will be told "not yet." This is on purpose.
- The IR schema will likely break at v0.4. Pinning is required.

## Alternatives considered

- **Universal IR from day one.** Rejected for the reasons above.
- **No IR; direct translation.** Rejected because it forecloses the report, the graph visualization, and replayability.
- **IR scoped to OpenClaw only (one-way).** Rejected because we lose round-trip validation, which is the single best mechanism for catching lossy translators.
