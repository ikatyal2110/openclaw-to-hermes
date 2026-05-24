"""Hermes analyzer — reads an emitted Hermes project back into the IR.

Same contract as the OpenClaw analyzers: walk the on-disk layout documented in
docs/hermes-format.md, emit a partial IRGraph per file kind, and the driver
merges them. The pair of analyzers (openclaw → IR, hermes → IR) is what makes
round-trip migration testable.
"""

from praxis_core.analyzers.hermes.driver import analyze_hermes_project

__all__ = ["analyze_hermes_project"]
