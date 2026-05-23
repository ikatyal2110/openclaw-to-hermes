"""Reads plugins/*.yaml and emits one IR `tool` node per plugin manifest."""
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
    Node,
    NodeKind,
    PortSpec,
    Provenance,
    SideEffect,
    SideEffectKind,
    make_node_id,
)

ENV_REF = re.compile(r"\$\{env\.([A-Z0-9_]+)\}")


class PluginsAnalyzer(Analyzer):
    name = "openclaw.plugins"

    def analyze(self, root: Path) -> IRGraph:
        ir = IRGraph()
        plugin_dir = root / "plugins"
        if not plugin_dir.exists():
            return ir

        for path in sorted(plugin_dir.glob("*.yaml")):
            data = self.safe_load_yaml(path)
            if not isinstance(data, dict):
                ir.diagnostics.append(
                    Diagnostic(
                        level="warn",
                        code="PRX020",
                        message=f"Plugin file {path.name} is empty or malformed.",
                    )
                )
                continue
            self._emit_plugin(ir, path, data)

        return ir

    def _emit_plugin(self, ir: IRGraph, path: Path, data: dict[str, Any]) -> None:
        name = data.get("name") or path.stem
        node_id = make_node_id("openclaw", NodeKind.TOOL, name)
        runtime = (data.get("runtime") or "unknown").lower()
        kind = (data.get("kind") or "tool").lower()

        capabilities: list[Capability] = []
        side_effects: list[SideEffect] = []

        if runtime == "http":
            capabilities += [Capability.HTTP_CALLABLE, Capability.SIDE_EFFECTING]
            side_effects.append(SideEffect(kind=SideEffectKind.NETWORK, target=self._http_target(data)))
        elif runtime == "python":
            if not data.get("pure", False):
                capabilities.append(Capability.SIDE_EFFECTING)
                side_effects.append(SideEffect(kind=SideEffectKind.UNKNOWN))
        elif runtime == "subprocess":
            capabilities.append(Capability.SIDE_EFFECTING)
            side_effects.append(SideEffect(kind=SideEffectKind.SUBPROCESS))
        if "openai" in (self._http_target(data) or "") or "${env.OPENAI_API_KEY}" in (data.get("config", {}) or {}).get("auth", ""):
            capabilities.append(Capability.LLM_INVOKING)

        memory_store = (data.get("config") or {}).get("memory_store")
        if memory_store:
            capabilities += [Capability.STATEFUL, Capability.MEMORY_READING, Capability.MEMORY_WRITING]

        inputs = [self._port(p) for p in data.get("inputs", []) or []]
        outputs = [self._port(p) for p in data.get("outputs", []) or []]

        node = Node(
            id=node_id,
            kind=NodeKind.TOOL,
            name=name,
            description=data.get("description"),
            capabilities=capabilities,
            inputs=inputs,
            outputs=outputs,
            side_effects=side_effects,
            provenance=Provenance(
                framework="openclaw",
                source_file=str(path.relative_to(path.parents[1])),
                original_kind=f"plugin/{kind}",
            ),
            metadata={
                "runtime": runtime,
                "kind": kind,
                "config": data.get("config", {}),
                "pure": data.get("pure"),
            },
        )
        ir.nodes.append(node)

        # Edges for env references inside the plugin config.
        config_str = repr(data.get("config", {}))
        for env_var in set(ENV_REF.findall(config_str)):
            ir.edges.append(
                Edge(
                    **{"from": make_node_id("openclaw", NodeKind.ENV, env_var)},
                    to=node_id,
                    kind=EdgeKind.DEPENDENCY,
                    label=f"env:{env_var}",
                )
            )

        # Edge to memory store if declared.
        if memory_store:
            ir.edges.append(
                Edge(
                    **{"from": node_id},
                    to=make_node_id("openclaw", NodeKind.MEMORY_STORE, memory_store),
                    kind=EdgeKind.READS,
                    label=memory_store,
                )
            )
            ir.edges.append(
                Edge(
                    **{"from": node_id},
                    to=make_node_id("openclaw", NodeKind.MEMORY_STORE, memory_store),
                    kind=EdgeKind.WRITES,
                    label=memory_store,
                )
            )

    @staticmethod
    def _port(p: dict[str, Any]) -> PortSpec:
        return PortSpec(
            name=p["name"],
            type=p.get("type"),
            required=p.get("required", True),
            default=p.get("default"),
            description=p.get("description"),
        )

    @staticmethod
    def _http_target(data: dict[str, Any]) -> str | None:
        cfg = data.get("config") or {}
        return cfg.get("url_template")
