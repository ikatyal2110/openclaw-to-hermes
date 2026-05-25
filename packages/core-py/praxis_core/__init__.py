"""Praxis core: OpenClaw → Hermes migration engine."""

__version__ = "1.0.0"

# IR_VERSION is the schema version stamped into every emitted ir.json. From v1.0
# onward, this is a stability commitment: the schema shape is additive-only
# within the 1.x line. Removing or renaming a field requires bumping to 2.0 and
# an ADR. See docs/adr/0003-v1-stability-commitment.md.
IR_VERSION = "1.0"
