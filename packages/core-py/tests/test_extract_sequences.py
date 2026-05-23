"""Unit tests for praxis_core.extract.sequences — tool-sequence repetition detector."""

from __future__ import annotations

from praxis_core.extract.sequences import (
    RepeatedSequence,
    find_repeated_subsequences,
)


def test_empty_input_returns_empty() -> None:
    assert find_repeated_subsequences({}) == []


def test_single_workflow_yields_no_repeats() -> None:
    assert find_repeated_subsequences({"only": ["a", "b", "c"]}) == []


def test_no_overlap_yields_no_repeats() -> None:
    seqs = {"alpha": ["a", "b", "c"], "beta": ["x", "y", "z"]}
    assert find_repeated_subsequences(seqs) == []


def test_shared_prefix_is_detected_and_maximal() -> None:
    seqs = {
        "alpha": ["fetch", "parse", "send"],
        "beta": ["fetch", "parse", "store"],
    }
    repeats = find_repeated_subsequences(seqs)
    assert len(repeats) == 1
    r = repeats[0]
    assert r.tools == ("fetch", "parse")
    assert sorted(r.workflows) == ["alpha", "beta"]


def test_shared_full_chain_dominates_sub_windows() -> None:
    seqs = {
        "alpha": ["fetch", "parse", "send"],
        "beta": ["fetch", "parse", "send"],
    }
    repeats = find_repeated_subsequences(seqs)
    # Maximality: only the length-3 chain is reported, not its 2-grams.
    assert len(repeats) == 1
    assert repeats[0].tools == ("fetch", "parse", "send")


def test_three_workflows_with_shared_middle() -> None:
    seqs = {
        "a": ["start", "X", "Y", "end_a"],
        "b": ["init", "X", "Y", "end_b"],
        "c": ["boot", "X", "Y", "end_c"],
    }
    repeats = find_repeated_subsequences(seqs)
    assert len(repeats) == 1
    assert repeats[0].tools == ("X", "Y")
    assert repeats[0].occurrences == 3


def test_min_length_threshold_excludes_shorter() -> None:
    seqs = {"alpha": ["a", "b"], "beta": ["a", "b"]}
    assert find_repeated_subsequences(seqs, min_length=3) == []
    assert find_repeated_subsequences(seqs, min_length=2) != []


def test_min_occurrences_threshold() -> None:
    seqs = {
        "a": ["x", "y"],
        "b": ["x", "y"],
        "c": ["unrelated"],
    }
    assert find_repeated_subsequences(seqs, min_occurrences=2) != []
    assert find_repeated_subsequences(seqs, min_occurrences=3) == []


def test_intra_workflow_repetition_does_not_inflate_count() -> None:
    seqs = {
        "alpha": ["a", "b", "c", "a", "b"],
        "beta": ["a", "b"],
    }
    repeats = find_repeated_subsequences(seqs, min_occurrences=2)
    by_chain = {r.tools: r for r in repeats}
    assert ("a", "b") in by_chain
    assert by_chain[("a", "b")].occurrences == 2


def test_output_is_deterministic() -> None:
    seqs = {
        "wf3": ["m", "n", "o"],
        "wf1": ["m", "n", "o"],
        "wf2": ["p", "q"],
        "wf4": ["p", "q"],
    }
    repeats = find_repeated_subsequences(seqs)
    assert [r.length for r in repeats] == sorted([r.length for r in repeats], reverse=True)
    for r in repeats:
        assert r.workflows == sorted(r.workflows)


def test_dataclass_properties() -> None:
    r = RepeatedSequence(tools=("a", "b", "c"), workflows=["x", "y"])
    assert r.length == 3
    assert r.occurrences == 2
