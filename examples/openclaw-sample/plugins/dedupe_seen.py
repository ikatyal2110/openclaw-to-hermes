"""Reference implementation for the `dedupe_seen` plugin.

Praxis v0.1 does NOT introspect this file — only the YAML manifest at
plugins/dedupe_seen.yaml is consumed by the analyzer. This source is here so
the fixture is runnable end-to-end if/when an OpenClaw runtime is installed.
"""

from __future__ import annotations

from typing import Any


def run(items: list[dict[str, Any]], *, memory) -> list[dict[str, Any]]:  # noqa: ANN001
    store = memory.get("seen_articles")
    fresh: list[dict[str, Any]] = []
    for item in items:
        key = item.get("id") or item.get("url")
        if key and not store.has(key):
            store.set(key, item)
            fresh.append(item)
    return fresh
