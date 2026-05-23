"""Tool-sequence repetition detector — the structural half of skill extraction.

A "tool sequence" is the ordered list of plugin calls in a workflow's `raw_steps`.
When the same subsequence appears in two or more workflows, it's a candidate for
factoring into a shared Hermes skill: same tool chain → same operation, named
inconsistently across workflows.

We report only *maximal* repeated subsequences. A subsequence is maximal if
extending it by one token on either side (within any workflow's full sequence)
drops the occurrence count below the threshold. This avoids drowning the report
in every sub-window of a long shared chain.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind


def extract_tool_sequences(ir: IRGraph) -> dict[str, list[str]]:
    """Return workflow_name → ordered list of plugin names called by its steps."""
    seqs: dict[str, list[str]] = {}
    for n in ir.nodes:
        kind = n.kind.value if hasattr(n.kind, "value") else n.kind
        if kind != NodeKind.WORKFLOW.value:
            continue
        raw_steps = (n.metadata or {}).get("raw_steps") or []
        plugins = [
            s["plugin"]
            for s in raw_steps
            if isinstance(s, dict) and isinstance(s.get("plugin"), str)
        ]
        if plugins:
            seqs[n.name] = plugins
    return seqs


@dataclass
class RepeatedSequence:
    """A subsequence of tool names that recurs in ≥ min_occurrences workflows."""

    tools: tuple[str, ...]
    workflows: list[str] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.tools)

    @property
    def occurrences(self) -> int:
        return len(self.workflows)


def find_repeated_subsequences(
    sequences: dict[str, list[str]],
    min_length: int = 2,
    min_occurrences: int = 2,
) -> list[RepeatedSequence]:
    """Find maximal subsequences of length ≥ min_length that appear in
    ≥ min_occurrences distinct workflows.

    Returns clusters sorted by (length desc, occurrences desc, tools asc) for
    deterministic output.
    """
    if not sequences:
        return []

    # Tally every subsequence of length ≥ min_length across all workflows. A
    # workflow that contains the same subseq multiple times is still counted
    # once toward min_occurrences (we care about cross-workflow recurrence).
    occurrences: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for wf_name, seq in sequences.items():
        if len(seq) < min_length:
            continue
        for length in range(min_length, len(seq) + 1):
            for start in range(len(seq) - length + 1):
                sub = tuple(seq[start : start + length])
                occurrences[sub].add(wf_name)

    # Only keep subsequences hitting the cross-workflow threshold.
    candidates: dict[tuple[str, ...], set[str]] = {
        sub: wfs for sub, wfs in occurrences.items() if len(wfs) >= min_occurrences
    }

    # Maximality filter: drop any subseq that is a contiguous slice of a longer
    # candidate with the *same* workflow set. The longer one dominates.
    by_workflows: dict[frozenset[str], list[tuple[str, ...]]] = defaultdict(list)
    for sub, wfs in candidates.items():
        by_workflows[frozenset(wfs)].append(sub)

    maximal: dict[tuple[str, ...], set[str]] = {}
    for wfs_key, subs in by_workflows.items():
        subs_sorted = sorted(subs, key=lambda s: -len(s))
        kept: list[tuple[str, ...]] = []
        for sub in subs_sorted:
            if any(_is_contiguous_slice_of(sub, longer) for longer in kept):
                continue
            kept.append(sub)
            maximal[sub] = set(wfs_key)

    results = [RepeatedSequence(tools=sub, workflows=sorted(wfs)) for sub, wfs in maximal.items()]
    results.sort(key=lambda r: (-r.length, -r.occurrences, r.tools))
    return results


def _is_contiguous_slice_of(short: tuple[str, ...], long: tuple[str, ...]) -> bool:
    if len(short) >= len(long):
        return False
    for start in range(len(long) - len(short) + 1):
        if long[start : start + len(short)] == short:
            return True
    return False


def extract_repeated_sequences(
    ir: IRGraph,
    min_length: int = 2,
    min_occurrences: int = 2,
) -> list[RepeatedSequence]:
    """Convenience wrapper: extract sequences from IR and find repeats."""
    return find_repeated_subsequences(
        extract_tool_sequences(ir),
        min_length=min_length,
        min_occurrences=min_occurrences,
    )
