"""Tests for the JSON extraction/repair + validation layer (M4)."""

import pytest

from app.enrichment.parse import (
    EnrichmentParseError,
    extract_json,
    parse_classify,
    parse_graph,
)
from app.schemas.enrichment import normalise_entity_name


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_code_fence():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_finds_object_in_prose():
    text = 'Sure! Here is the result:\n{"a": 1, "b": {"c": 2}}\nHope that helps.'
    assert extract_json(text) == {"a": 1, "b": {"c": 2}}


def test_extract_json_handles_braces_inside_strings():
    assert extract_json('{"note": "a } brace in a string"}') == {"note": "a } brace in a string"}


def test_extract_json_raises_on_garbage():
    with pytest.raises(EnrichmentParseError):
        extract_json("no json here at all")


def test_parse_classify_rejects_out_of_range_score():
    bad = '{"category": "x", "tags": [], "scores": {"relevance": 9, "novelty": 1, ' \
          '"actionability": 1, "strategic_potential": 1, "hype": 1}}'
    with pytest.raises(EnrichmentParseError):
        parse_classify(bad)


def test_parse_graph_drops_unknown_entity_type():
    # An invalid entity type fails validation → parse error (caller degrades).
    with pytest.raises(EnrichmentParseError):
        parse_graph('{"entities": [{"name": "X", "type": "alien"}], "relationships": []}')


def test_parse_graph_ok():
    g = parse_graph('{"entities": [{"name": "OpenAI", "type": "org"}], "relationships": []}')
    assert g.entities[0].name == "OpenAI"


def test_normalise_entity_name():
    assert normalise_entity_name("  OpenAI ") == "openai"
    assert normalise_entity_name("Open   AI") == "open ai"
