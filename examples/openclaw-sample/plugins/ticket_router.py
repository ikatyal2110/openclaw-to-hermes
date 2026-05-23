"""Reference implementation for the `ticket_router` plugin.

Praxis v0.1 does NOT introspect this file — see plugins/ticket_router.yaml.
"""
from __future__ import annotations

from typing import Any

ROUTES = {
    "bug": "jira_create",
    "billing": "stripe_dispute_open",
    "feedback": "slack_post",
}


def route(ticket: dict[str, Any], category: str, *, invoke) -> dict[str, Any]:  # noqa: ANN001
    target = ROUTES.get(category)
    if not target:
        raise ValueError(f"No route for category: {category}")
    return invoke(target, ticket=ticket)
