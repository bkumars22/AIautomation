"""
Unit tests for generation/intermediate_generator.py. _call_llm (the one
function that makes a real network call) is always mocked here — these
tests verify the prompt-independent logic: JSON extraction (including the
markdown-fence case real LLMs sometimes produce despite instructions not
to) and structural validation, none of which need a real API key.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from generation.intermediate_generator import (  # noqa: E402
    generate_intermediate_definition,
    validate_intermediate_definition,
)

_VALID_DEF = {
    "test_name": "Example",
    "steps": [
        {"action": "navigate", "target": {"type": "url", "value": "/login"}},
        {"action": "assert_url", "value": "/login"},
    ],
}


class TestGenerateIntermediateDefinition:
    def test_parses_plain_json_response(self):
        with patch("generation.intermediate_generator._call_llm", return_value=json.dumps(_VALID_DEF)):
            result = generate_intermediate_definition("Some requirement")
        assert result == _VALID_DEF

    def test_strips_markdown_code_fence(self):
        fenced = f"```json\n{json.dumps(_VALID_DEF)}\n```"
        with patch("generation.intermediate_generator._call_llm", return_value=fenced):
            result = generate_intermediate_definition("Some requirement")
        assert result == _VALID_DEF

    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from generation.intermediate_generator import _call_llm
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            _call_llm("Some requirement")

    def test_invalid_generated_json_raises_not_silently_swallowed(self):
        bad_def = {"test_name": "Missing steps"}
        with patch("generation.intermediate_generator._call_llm", return_value=json.dumps(bad_def)):
            with pytest.raises(ValueError, match="steps"):
                generate_intermediate_definition("Some requirement")


class TestValidateIntermediateDefinition:
    def test_valid_definition_passes(self):
        validate_intermediate_definition(_VALID_DEF)  # must not raise

    def test_missing_test_name(self):
        with pytest.raises(ValueError, match="test_name"):
            validate_intermediate_definition({"steps": _VALID_DEF["steps"]})

    def test_empty_steps(self):
        with pytest.raises(ValueError, match="steps"):
            validate_intermediate_definition({"test_name": "x", "steps": []})

    def test_unknown_action(self):
        bad = {"test_name": "x", "steps": [{"action": "teleport", "target": {}}]}
        with pytest.raises(ValueError, match="unknown action"):
            validate_intermediate_definition(bad)

    def test_missing_target_on_non_assert_url_step(self):
        bad = {"test_name": "x", "steps": [{"action": "click"}]}
        with pytest.raises(ValueError, match="target"):
            validate_intermediate_definition(bad)

    def test_assert_url_does_not_require_target(self):
        ok = {"test_name": "x", "steps": [{"action": "assert_url", "value": "/pricing"}]}
        validate_intermediate_definition(ok)  # must not raise
