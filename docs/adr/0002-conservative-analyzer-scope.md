# ADR 0002: v0.1 analyzer reads manifests, not source code

- **Status:** Accepted (v0.1)
- **Date:** 2026-05-17

## Context

OpenClaw plugins frequently ship as a YAML manifest plus a Python (or JavaScript) entrypoint that implements the actual behavior. A maximally helpful analyzer would `libcst`-parse the Python and report:
- What the plugin actually does (HTTP calls, DB reads, file I/O).
- Whether it's pure.
- What side effects to flag.

We chose not to do this in v0.1.

## Decision

The v0.1 analyzer reads YAML manifests only. Plugin source files (`.py`, `.js`, etc.) are noted in the IR as `metadata.source_present: true` but not parsed.

Pure vs. impure status is determined solely from the `pure: bool` flag in the plugin manifest. If a manifest declares `pure: true` and the implementation isn't, that's the developer's responsibility.

## Consequences

**Positive:**
- The analyzer has one input format (YAML), one parser dependency (pyyaml).
- Adversarial Python source can't crash the analyzer.
- The classification logic is fully explainable from declared metadata, which builds trust.
- The MVP ships.

**Negative:**
- Some plugins that *should* be classified `portable` end up `needs_review` because their manifest doesn't declare `pure`.
- The "infer intent from code" promise is weaker than it could be — v0.1 infers intent from workflow shape and explicit descriptions, not from what the plugin actually does.

## Path forward (v0.2)

Add a `libcst`-based introspection pass for plugins where `runtime: python` and a sibling `.py` file exists. The pass produces a `metadata.inferred_purity` field with confidence. It supplements (never replaces) the manifest's `pure` declaration. If declared and inferred disagree, the classifier flags `needs_review` regardless of declared value, with a diagnostic explaining the mismatch.

## Alternatives considered

- **Parse Python source eagerly in v0.1.** Rejected. Doubles the analyzer's surface area before the IR has been validated by real users. We'd be optimizing the wrong thing.
- **Run the plugin in a sandbox to observe behavior.** Rejected. Out of scope for a build-time tool; brings in container/sandbox dependencies; surfaces "works on my machine" failures.
- **Trust the manifest entirely, no future plans to introspect.** Rejected because the moat *requires* understanding what the code does, eventually.
