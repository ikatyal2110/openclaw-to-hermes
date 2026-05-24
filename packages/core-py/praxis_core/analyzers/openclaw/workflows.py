"""Reads workflows/*.yaml. Emits one workflow node + one scheduler per cron trigger,
plus control/data edges between workflow steps and the referenced plugins.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Diagnostic,
    Edge,
    EdgeKind,
    Intent,
    Node,
    NodeKind,
    Provenance,
    make_node_id,
)

ENV_REF = re.compile(r"\$\{env\.([A-Z0-9_]+)\}")
STEP_REF = re.compile(r"\$\{steps\.([a-zA-Z0-9_]+)\.")
PREV_REF = re.compile(r"\$\{prev\.")


class WorkflowsAnalyzer(Analyzer):
    name = "openclaw.workflows"

    def analyze(self, root: Path) -> IRGraph:
        ir = IRGraph()
        workflow_dir = root / "workflows"
        if not workflow_dir.exists():
            return ir

        for path in sorted(workflow_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                ir.diagnostics.append(
                    Diagnostic(
                        level="warn",
                        code="PRX010",
                        message=f"Workflow file {path.name} is empty or malformed.",
                    )
                )
                continue
            self._emit_workflow(ir, path, data)

        return ir

    def _emit_workflow(self, ir: IRGraph, path: Path, data: dict[str, Any]) -> None:
        name = data.get("name") or path.stem
        wf_id = make_node_id("openclaw", NodeKind.WORKFLOW, name)
        triggers = data.get("triggers") or []
        steps = data.get("steps") or []

        capabilities: list[Capability] = [Capability.SEQUENCEABLE, Capability.SIDE_EFFECTING]
        if any(t.get("kind") == "cron" for t in triggers if isinstance(t, dict)):
            capabilities.append(Capability.SCHEDULED)

        has_branches = any(isinstance(s, dict) and "when" in s for s in steps)
        if has_branches:
            capabilities.append(Capability.BRANCHABLE)

        intent = self._infer_intent(name, data, triggers, steps)

        ir.nodes.append(
            Node(
                id=wf_id,
                kind=NodeKind.WORKFLOW,
                name=name,
                description=data.get("description"),
                capabilities=capabilities,
                intent=intent,
                provenance=Provenance(
                    framework="openclaw",
                    source_file=str(path.relative_to(path.parents[1])),
                    original_kind="workflow",
                ),
                metadata={
                    "raw_steps": steps,
                    "triggers": triggers,
                    "has_branches": has_branches,
                },
            )
        )

        # Schedulers
        for idx, trig in enumerate(triggers):
            if not isinstance(trig, dict):
                continue
            kind = trig.get("kind")
            if kind == "cron":
                sched_name = f"{name}__cron_{idx}"
                sched_id = make_node_id("openclaw", NodeKind.SCHEDULER, sched_name)
                ir.nodes.append(
                    Node(
                        id=sched_id,
                        kind=NodeKind.SCHEDULER,
                        name=sched_name,
                        capabilities=[Capability.SCHEDULED],
                        provenance=Provenance(
                            framework="openclaw",
                            source_file=str(path.relative_to(path.parents[1])),
                            original_kind=f"trigger/{kind}",
                        ),
                        metadata={"trigger_kind": "cron", "spec": trig.get("spec")},
                    )
                )
                ir.edges.append(
                    Edge(
                        **{"from": sched_id},
                        to=wf_id,
                        kind=EdgeKind.TRIGGER,
                        label=trig.get("spec"),
                    )
                )
            elif kind == "webhook":
                sched_name = f"{name}__webhook_{idx}"
                sched_id = make_node_id("openclaw", NodeKind.SCHEDULER, sched_name)
                ir.nodes.append(
                    Node(
                        id=sched_id,
                        kind=NodeKind.SCHEDULER,
                        name=sched_name,
                        capabilities=[Capability.USER_FACING],
                        provenance=Provenance(
                            framework="openclaw",
                            source_file=str(path.relative_to(path.parents[1])),
                            original_kind=f"trigger/{kind}",
                        ),
                        metadata={"trigger_kind": "webhook", "path": trig.get("path")},
                    )
                )
                ir.edges.append(
                    Edge(
                        **{"from": sched_id},
                        to=wf_id,
                        kind=EdgeKind.TRIGGER,
                        label=trig.get("path"),
                    )
                )

        # Steps → control edges
        prev_plugin_id: str | None = None
        for step in steps:
            if not isinstance(step, dict):
                continue
            plugin_name = step.get("plugin")
            if not plugin_name:
                ir.diagnostics.append(
                    Diagnostic(
                        level="warn",
                        code="PRX011",
                        message=f"Workflow {name} has a step without a plugin field.",
                        node_id=wf_id,
                    )
                )
                continue
            plugin_id = make_node_id("openclaw", NodeKind.TOOL, plugin_name)
            ir.edges.append(
                Edge(**{"from": wf_id}, to=plugin_id, kind=EdgeKind.CONTROL, label=step.get("id"))
            )
            if prev_plugin_id is not None:
                ir.edges.append(Edge(**{"from": prev_plugin_id}, to=plugin_id, kind=EdgeKind.DATA))
            with_block = repr(step.get("with", {}))
            for env_var in set(ENV_REF.findall(with_block)):
                ir.edges.append(
                    Edge(
                        **{"from": make_node_id("openclaw", NodeKind.ENV, env_var)},
                        to=plugin_id,
                        kind=EdgeKind.DEPENDENCY,
                        label=f"env:{env_var}",
                    )
                )
            prompt_ref = (step.get("with") or {}).get("prompt")
            if isinstance(prompt_ref, str):
                ir.edges.append(
                    Edge(
                        **{"from": make_node_id("openclaw", NodeKind.PROMPT, prompt_ref)},
                        to=plugin_id,
                        kind=EdgeKind.DEPENDENCY,
                        label=f"prompt:{prompt_ref}",
                    )
                )
            prev_plugin_id = plugin_id

    @staticmethod
    def _infer_intent(
        name: str,
        data: dict[str, Any],
        triggers: list[dict[str, Any]],
        steps: list[dict[str, Any]],
    ) -> Intent | None:
        """Static, rule-based intent. The LLM-assisted pass (v0.8+) refines this.

        Heuristics, in order of contribution:
          1. Explicit `description:` field — highest confidence.
          2. Cron/webhook trigger metadata — adds 'scheduled' / 'webhook-driven'.
          3. Step plugin chain — shows the procedure.
          4. Workflow name pattern (daily_*, weekly_*, monthly_*) — schedule hint.
          5. Plugin-name verbs (fetch_*, classify_*, summarize_*, notify_*) — action verbs.
        """
        evidence: list[str] = []

        desc = (data.get("description") or "").strip()
        if desc:
            # Lower confidence for placeholder/non-descriptive content.
            conf = 0.95
            evidence.append("description field present")
            if len(desc) < 20 or desc.lower() in ("todo", "tbd", "wip", "fixme"):
                conf = 0.5
                evidence.append("description is short/placeholder — confidence reduced")
            return Intent(description=desc, confidence=conf, evidence=evidence, source="static")

        bits: list[str] = []

        # Trigger-based hints.
        cron_specs = [
            t.get("spec") for t in triggers if isinstance(t, dict) and t.get("kind") == "cron"
        ]
        for spec in cron_specs:
            evidence.append(f"cron trigger {spec}")
            bits.append("scheduled")
        webhook_paths = [
            t.get("path") for t in triggers if isinstance(t, dict) and t.get("kind") == "webhook"
        ]
        for p in webhook_paths:
            evidence.append(f"webhook {p}")
            bits.append("webhook-driven")

        # Workflow-name pattern.
        lower = name.lower()
        for cadence in ("daily", "weekly", "monthly", "hourly", "nightly"):
            if (
                lower.startswith(cadence)
                or f"_{cadence}_" in lower
                or lower.endswith(f"_{cadence}")
            ):
                evidence.append(f"name suggests {cadence} cadence")
                bits.append(f"{cadence} task")
                break

        # Plugin-name verb extraction.
        plugin_names = [s.get("plugin") for s in steps if isinstance(s, dict) and s.get("plugin")]
        action_verbs = _verbs_from_plugins(plugin_names)
        if action_verbs:
            evidence.append(f"action verbs: {', '.join(action_verbs)}")
            bits.append(" → ".join(action_verbs))
        elif plugin_names:
            evidence.extend(f"step: {p}" for p in plugin_names)
            bits.append(" → ".join(str(p) for p in plugin_names))

        if not bits:
            return None

        # Confidence: webhook-driven and verb-rich → 0.7; just plugin chain → 0.5.
        confidence = 0.5
        if "webhook-driven" in bits or any("scheduled" in b for b in bits):
            confidence += 0.1
        if action_verbs:
            confidence += 0.1

        return Intent(
            description=f"{name}: {'; '.join(bits)}",
            confidence=min(confidence, 0.95),
            evidence=evidence,
            source="static",
        )


_PLUGIN_VERB_PREFIXES = (
    "fetch",
    "get",
    "list",
    "load",
    "read",
    "classify",
    "score",
    "rank",
    "filter",
    "dedupe",
    "summarize",
    "translate",
    "transform",
    "extract",
    "parse",
    "store",
    "save",
    "write",
    "send",
    "notify",
    "post",
    "publish",
    "page",
    "page_oncall",
    "create",
    "delete",
    "update",
    "render",
)


def _verbs_from_plugins(plugin_names: list[str | None]) -> list[str]:
    """Extract the leading verb from each plugin name when it matches a known verb.

    `fetch_articles` → 'fetch', `classify_ticket` → 'classify', `slack_post` → 'post'.
    Returns a deduplicated, order-preserving list of verbs.
    """
    seen: set[str] = set()
    verbs: list[str] = []
    for raw in plugin_names:
        if not raw:
            continue
        parts = raw.lower().split("_")
        for token in (parts[0], parts[-1]):  # check first AND last segment
            if token in _PLUGIN_VERB_PREFIXES and token not in seen:
                verbs.append(token)
                seen.add(token)
                break
    return verbs
