"""Unit tests for praxis_core.extract.prompts — tokenizer, similarity, clustering."""
from __future__ import annotations

from praxis_core.extract.prompts import (
    cluster_prompts,
    jaccard_bigrams,
    tokenize_prompt,
)


def test_tokenize_lowercases_and_splits() -> None:
    toks = tokenize_prompt("Hello, World!  Foo-bar.")
    assert toks == ["hello", "world", "foo", "bar"]


def test_tokenize_normalizes_jinja_interpolation() -> None:
    a = tokenize_prompt("Summarize {{ articles }} in bullets.")
    b = tokenize_prompt("Summarize {{ tickets }} in bullets.")
    assert a == b
    assert "__var__" in a


def test_tokenize_normalizes_jinja_block() -> None:
    toks = tokenize_prompt("Header. {% if x %}body{% endif %} footer")
    assert "__var__" in toks
    assert "header" in toks and "footer" in toks


def test_jaccard_identical_is_one() -> None:
    s = "Classify the ticket as bug or billing."
    assert jaccard_bigrams(s, s) == 1.0


def test_jaccard_disjoint_is_zero() -> None:
    assert jaccard_bigrams("alpha beta gamma", "xray yankee zulu") == 0.0


def test_jaccard_jinja_vars_dont_break_match() -> None:
    a = "You are a classifier. Input: {{ ticket }}"
    b = "You are a classifier. Input: {{ message }}"
    assert jaccard_bigrams(a, b) == 1.0


def test_jaccard_short_inputs_return_zero() -> None:
    assert jaccard_bigrams("hi", "hi") == 0.0  # only 1 token → no bigrams


def test_cluster_empty_input() -> None:
    assert cluster_prompts({}) == []


def test_cluster_below_threshold_yields_none() -> None:
    prompts = {
        "a": "totally unrelated content about cats sleeping",
        "b": "quantum physics involves wave equations and superposition",
    }
    assert cluster_prompts(prompts, threshold=0.4) == []


def test_cluster_merges_similar_prompts() -> None:
    prompts = {
        "summarize_news": "Summarize the articles into bullet points. Input: {{ x }}",
        "summarize_blog": "Summarize the articles into bullet points. Input: {{ y }}",
        "classify": "Classify the support ticket as bug or billing or feedback.",
    }
    clusters = cluster_prompts(prompts, threshold=0.5)
    assert len(clusters) == 1
    assert clusters[0].members == ["summarize_blog", "summarize_news"]
    assert clusters[0].size == 2
    assert clusters[0].min_similarity == 1.0


def test_cluster_single_link_chains_transitively() -> None:
    # a~b high, b~c high, a~c low. Single-link should still merge all three.
    prompts = {
        "a": "alpha beta gamma delta epsilon",
        "b": "alpha beta gamma zeta eta",
        "c": "zeta eta theta iota kappa",
    }
    clusters = cluster_prompts(prompts, threshold=0.1)
    assert len(clusters) == 1
    assert sorted(clusters[0].members) == ["a", "b", "c"]


def test_cluster_threshold_is_inclusive() -> None:
    prompts = {"a": "x y z", "b": "x y w"}
    score = jaccard_bigrams(prompts["a"], prompts["b"])
    assert score > 0
    clusters = cluster_prompts(prompts, threshold=score)
    assert len(clusters) == 1


def test_cluster_output_is_deterministic() -> None:
    prompts = {
        "z_prompt": "shared common preamble text for testing",
        "a_prompt": "shared common preamble text for testing",
        "m_prompt": "shared common preamble text for testing",
    }
    clusters = cluster_prompts(prompts, threshold=0.5)
    assert len(clusters) == 1
    assert clusters[0].members == ["a_prompt", "m_prompt", "z_prompt"]
