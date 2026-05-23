"""Prompt clustering — surface candidate skill extractions from similar prompts.

Rule-based on purpose (mirrors the classifier philosophy in scoring/classifier.py):
opaque embedding scores would obscure why two prompts cluster, and the value of
this command is the explainability of *which tokens overlap*, not raw recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind

_JINJA_INTERP = re.compile(r"\{\{\s*[^}]*\s*\}\}")
_JINJA_BLOCK = re.compile(r"\{%\s*[^%]*\s*%\}")
_TOKEN_SPLIT = re.compile(r"[^a-z0-9_]+")


def tokenize_prompt(body: str) -> list[str]:
    """Lowercase, normalize Jinja constructs to a sentinel, split on non-alphanum.

    Jinja interpolations and blocks collapse to `__var__` so that two prompts
    differing only in their variable names still match on shape.
    """
    body = _JINJA_INTERP.sub(" __var__ ", body)
    body = _JINJA_BLOCK.sub(" __var__ ", body)
    return [t for t in _TOKEN_SPLIT.split(body.lower()) if t]


def _bigrams(tokens: list[str]) -> set[tuple[str, str]]:
    return set(zip(tokens, tokens[1:], strict=False)) if len(tokens) >= 2 else set()


def jaccard_bigrams(a: str, b: str) -> float:
    """Jaccard similarity over token bigrams. Returns 0.0 if either side has <2 tokens."""
    ba, bb = _bigrams(tokenize_prompt(a)), _bigrams(tokenize_prompt(b))
    if not ba or not bb:
        return 0.0
    inter = len(ba & bb)
    union = len(ba | bb)
    return inter / union if union else 0.0


@dataclass
class PromptCluster:
    """A group of prompts whose pairwise similarity exceeds the threshold."""

    members: list[str]
    pairwise: dict[tuple[str, str], float] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def min_similarity(self) -> float:
        return min(self.pairwise.values()) if self.pairwise else 0.0

    @property
    def max_similarity(self) -> float:
        return max(self.pairwise.values()) if self.pairwise else 0.0


def cluster_prompts(
    prompts: dict[str, str],
    threshold: float = 0.4,
) -> list[PromptCluster]:
    """Single-link cluster prompts whose pairwise similarity ≥ threshold.

    `prompts` maps name → body. Returns clusters of size ≥ 2, sorted by size desc
    then alphabetically by first member for deterministic output.
    """
    names = sorted(prompts)
    parent: dict[str, str] = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    pair_scores: dict[tuple[str, str], float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            score = jaccard_bigrams(prompts[a], prompts[b])
            if score >= threshold:
                pair_scores[(a, b)] = score
                union(a, b)

    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)

    clusters: list[PromptCluster] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members_sorted = sorted(members)
        member_set = set(members_sorted)
        pairwise = {
            (a, b): s for (a, b), s in pair_scores.items() if a in member_set and b in member_set
        }
        clusters.append(PromptCluster(members=members_sorted, pairwise=pairwise))

    clusters.sort(key=lambda c: (-c.size, c.members[0]))
    return clusters


def extract_prompt_clusters(ir: IRGraph, threshold: float = 0.4) -> list[PromptCluster]:
    """Pull all prompt-kind nodes out of the IR and cluster them by body similarity."""
    bodies: dict[str, str] = {}
    for n in ir.nodes:
        kind = n.kind.value if hasattr(n.kind, "value") else n.kind
        if kind != NodeKind.PROMPT.value:
            continue
        body = (n.metadata or {}).get("body")
        if isinstance(body, str) and body.strip():
            bodies[n.name] = body
    return cluster_prompts(bodies, threshold=threshold)
