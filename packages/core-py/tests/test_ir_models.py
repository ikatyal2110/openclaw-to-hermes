"""IR model invariants. Catches the subtle pydantic-alias bug class."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from praxis_core import IR_VERSION
from praxis_core.ir import IRGraph
from praxis_core.ir.models import (
    Capability,
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    Portability,
    PortabilityTier,
    Provenance,
    make_node_id,
)


def test_node_id_is_deterministic() -> None:
    a = make_node_id("openclaw", NodeKind.WORKFLOW, "daily_digest")
    b = make_node_id("openclaw", NodeKind.WORKFLOW, "daily_digest")
    assert a == b
    assert a != make_node_id("openclaw", NodeKind.WORKFLOW, "other")


def test_edge_accepts_from_alias_via_dict() -> None:
    """Edge.from_ is aliased to 'from'. Pydantic must accept either."""
    e = Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL)
    assert e.from_ == "a"
    assert e.to == "b"


def test_edge_accepts_from_alias_by_field_name() -> None:
    """populate_by_name=True allows from_ as a kwarg too."""
    e = Edge(from_="a", to="b", kind=EdgeKind.CONTROL)
    assert e.from_ == "a"


def test_edge_serializes_with_alias() -> None:
    e = Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL)
    dumped = e.model_dump(mode="json", by_alias=True)
    assert dumped["from"] == "a"
    assert "from_" not in dumped


def test_irgraph_sort_is_deterministic() -> None:
    ir = IRGraph()
    ir.nodes.append(_node("z"))
    ir.nodes.append(_node("a"))
    ir.nodes.append(_node("m"))
    ir.edges.append(Edge(**{"from": "z"}, to="a", kind=EdgeKind.CONTROL))
    ir.edges.append(Edge(**{"from": "a"}, to="m", kind=EdgeKind.CONTROL))
    ir.sort()
    ids = [n.id for n in ir.nodes]
    assert ids == sorted(ids)
    pairs = [(e.from_, e.to) for e in ir.edges]
    assert pairs == sorted(pairs)


def test_irgraph_round_trip_validates_against_schema(repo_root: Path) -> None:
    schema = json.loads((repo_root / "schemas" / "praxis-ir.schema.json").read_text())
    ir = IRGraph(praxis_ir_version=IR_VERSION)
    ir.nodes.append(_node("a"))
    ir.nodes.append(_node("b"))
    ir.edges.append(Edge(**{"from": "a"}, to="b", kind=EdgeKind.CONTROL))
    payload = ir.to_json_dict()
    jsonschema.validate(payload, schema)


def test_capabilities_use_string_values_after_model_dump() -> None:
    n = _node("x", capabilities=[Capability.SCHEDULED, Capability.SIDE_EFFECTING])
    dumped = n.model_dump(mode="json", by_alias=True)
    assert dumped["capabilities"] == ["scheduled", "side_effecting"]


def test_portability_tier_serializes_as_string() -> None:
    n = _node("x")
    n.portability = Portability(score=0.95, tier=PortabilityTier.PORTABLE)
    dumped = n.model_dump(mode="json", by_alias=True)
    assert dumped["portability"]["tier"] == "portable"


def test_unknown_kind_rejected() -> None:
    with pytest.raises(Exception):
        Node(
            id="x",
            kind="nope",  # type: ignore[arg-type]
            name="x",
            provenance=Provenance(framework="openclaw"),
        )


def _node(node_id: str, **kwargs) -> Node:  # noqa: ANN003
    return Node(
        id=node_id,
        kind=kwargs.pop("kind", NodeKind.TOOL),
        name=kwargs.pop("name", node_id),
        capabilities=kwargs.pop("capabilities", []),
        provenance=Provenance(framework="openclaw"),
        **kwargs,
    )
