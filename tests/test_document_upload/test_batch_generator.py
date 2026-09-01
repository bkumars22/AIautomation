"""
Unit tests for document_upload/batch_generator.py's orchestration logic.
generate_intermediate_definition is mocked (its own LLM-calling internals
are already covered by tests/test_generation/test_intermediate_generator.py)
so these tests verify per-scenario wiring and adapter routing without a
real API key.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from document_upload.batch_generator import generate_full_test_suite

_INTERMEDIATE_DEF = {
    "test_name": "Apply a valid promo code",
    "steps": [
        {"action": "navigate", "target": {"type": "url", "value": "/checkout"}},
        {"action": "assert_url", "value": "/checkout"},
    ],
}

_SCENARIOS = [
    {"scenario_name": "Apply a valid promo code", "description": "d1", "acceptance_criteria": "a1"},
    {"scenario_name": "Reject an invalid promo code", "description": "d2", "acceptance_criteria": "a2"},
]


def test_generates_one_result_per_scenario():
    with patch("document_upload.batch_generator.generate_intermediate_definition", return_value=_INTERMEDIATE_DEF):
        results = generate_full_test_suite(_SCENARIOS, "playwright")

    assert len(results) == 2
    assert results[0]["scenario_name"] == "Apply a valid promo code"
    assert results[0]["framework"] == "playwright"
    assert "def test_" in results[0]["automated_code"]
    assert "Test Case:" in results[0]["manual_test_case"]
    assert results[0]["intermediate_json"] == _INTERMEDIATE_DEF


def test_empty_scenarios_returns_empty_results():
    with patch("document_upload.batch_generator.generate_intermediate_definition", return_value=_INTERMEDIATE_DEF):
        results = generate_full_test_suite([], "playwright")
    assert results == []


def test_routes_to_the_chosen_adapter():
    with patch("document_upload.batch_generator.generate_intermediate_definition", return_value=_INTERMEDIATE_DEF):
        results = generate_full_test_suite(_SCENARIOS[:1], "cucumber")
    assert results[0]["framework"] == "cucumber"
    assert "Feature:" in results[0]["automated_code"]


def test_unknown_framework_raises():
    with pytest.raises(ValueError, match="Unknown framework"):
        generate_full_test_suite(_SCENARIOS, "dotnet-nunit")


def test_requirement_text_includes_all_scenario_fields():
    captured = {}

    def fake_generate(requirement_text):
        captured["text"] = requirement_text
        return _INTERMEDIATE_DEF

    with patch("document_upload.batch_generator.generate_intermediate_definition", side_effect=fake_generate):
        generate_full_test_suite(_SCENARIOS[:1], "selenium")

    assert "Apply a valid promo code" in captured["text"]
    assert "d1" in captured["text"]
    assert "a1" in captured["text"]
