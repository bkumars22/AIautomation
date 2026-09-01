"""
Unit tests for document_upload/scenario_extractor.py. _call_llm (the one
function that makes a real network call) is always mocked here, exactly
like tests/test_generation/test_intermediate_generator.py -- verifies the
prompt-independent logic (JSON-list extraction, fenced-code tolerance,
structural validation, the zero-scenarios case) without needing a real
API key. See docs/document_upload.md for the separate, real-document
verification that DOES need a key.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from document_upload.scenario_extractor import (
    ScenarioExtractionError,
    extract_test_scenarios,
    validate_scenarios,
)

_VALID_SCENARIOS = [
    {
        "scenario_name": "Apply a valid promo code",
        "description": "Shopper enters a valid promo code and the total updates.",
        "acceptance_criteria": "Total reflects the discount; a confirmation message appears.",
    },
    {
        "scenario_name": "Reject an invalid promo code",
        "description": "Shopper enters an invalid promo code.",
        "acceptance_criteria": "Inline error shown; total unchanged.",
    },
]


class TestExtractTestScenarios:
    def test_parses_plain_json_response(self):
        with patch("document_upload.scenario_extractor._call_llm", return_value=json.dumps(_VALID_SCENARIOS)):
            result = extract_test_scenarios("Some document text")
        assert result == _VALID_SCENARIOS

    def test_strips_markdown_code_fence(self):
        fenced = f"```json\n{json.dumps(_VALID_SCENARIOS)}\n```"
        with patch("document_upload.scenario_extractor._call_llm", return_value=fenced):
            result = extract_test_scenarios("Some document text")
        assert result == _VALID_SCENARIOS

    def test_empty_list_for_document_with_no_scenarios(self):
        """The explicit, named requirement: a document with nothing testable
        must come back as an empty list, never a fabricated scenario."""
        with patch("document_upload.scenario_extractor._call_llm", return_value="[]"):
            result = extract_test_scenarios("A glossary of terms with no user actions.")
        assert result == []

    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from document_upload.scenario_extractor import _call_llm
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            _call_llm("Some document text")

    def test_non_json_response_raises_not_silently_swallowed(self):
        with patch("document_upload.scenario_extractor._call_llm", return_value="Sure, here are the scenarios:\n- one\n- two"):
            with pytest.raises(ScenarioExtractionError, match="valid JSON"):
                extract_test_scenarios("Some document text")

    def test_malformed_scenario_raises_not_silently_swallowed(self):
        bad = [{"scenario_name": "Missing fields"}]
        with patch("document_upload.scenario_extractor._call_llm", return_value=json.dumps(bad)):
            with pytest.raises(ScenarioExtractionError, match="missing required field"):
                extract_test_scenarios("Some document text")


class TestValidateScenarios:
    def test_valid_list_passes(self):
        validate_scenarios(_VALID_SCENARIOS)  # must not raise

    def test_empty_list_passes(self):
        validate_scenarios([])  # must not raise -- a legitimate "no scenarios" result

    def test_not_a_list_raises(self):
        with pytest.raises(ScenarioExtractionError, match="Expected a JSON list"):
            validate_scenarios({"scenario_name": "x"})

    def test_non_object_item_raises(self):
        with pytest.raises(ScenarioExtractionError, match="not an object"):
            validate_scenarios(["just a string"])

    def test_empty_scenario_name_raises(self):
        bad = [{"scenario_name": "  ", "description": "x", "acceptance_criteria": "y"}]
        with pytest.raises(ScenarioExtractionError, match="empty scenario_name"):
            validate_scenarios(bad)
