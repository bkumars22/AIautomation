"""
Tests the LangGraph wiring end-to-end with generate_intermediate_definition
mocked (no LLM/API key needed) — this is testing the GRAPH's routing and
node sequencing, which is independent of whether the LLM call inside one
node is real or mocked. Real, unmocked LLM generation quality is a
separate, environment-dependent concern (needs ANTHROPIC_API_KEY) covered
by generation/intermediate_generator.py's own tests instead.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from graph.generation_graph import generate_test  # noqa: E402

_FAKE_INTERMEDIATE_DEF = {
    "test_name": "User can log in",
    "steps": [
        {"action": "navigate", "target": {"type": "url", "value": "/login"}},
        {"action": "click", "target": {"type": "button_text", "value": "Sign In"}},
    ],
}


def _mock_generate_intermediate(_requirement_text):
    return _FAKE_INTERMEDIATE_DEF


class TestGenerationGraphRouting:
    def test_routes_to_playwright(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=_mock_generate_intermediate):
            result = generate_test("User can log in", target_tool="playwright")
        assert result["error"] == ""
        assert "page.goto" in result["generated_code"]
        assert "Playwright" in result["generated_code"] or "playwright" in result["generated_code"]

    def test_routes_to_selenium(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=_mock_generate_intermediate):
            result = generate_test("User can log in", target_tool="selenium")
        assert result["error"] == ""
        assert "driver.get" in result["generated_code"]

    def test_routes_to_cypress(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=_mock_generate_intermediate):
            result = generate_test("User can log in", target_tool="cypress")
        assert result["error"] == ""
        assert "cy.visit" in result["generated_code"]

    def test_manual_case_generated_before_routing(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=_mock_generate_intermediate):
            result = generate_test("User can log in", target_tool="playwright")
        assert "Test Case: User can log in" in result["manual_test_case"]
        assert "Sign In" in result["manual_test_case"]

    def test_unknown_tool_routes_to_error(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=_mock_generate_intermediate):
            result = generate_test("User can log in", target_tool="nonexistent_tool")
        assert result["error"] != ""
        assert result["generated_code"] == ""

    def test_empty_requirement_short_circuits_before_llm_call(self):
        with patch("graph.generation_graph.generate_intermediate_definition") as mock_gen:
            result = generate_test("   ", target_tool="playwright")
        mock_gen.assert_not_called()
        assert "empty" in result["error"]

    def test_llm_failure_propagates_as_error_not_exception(self):
        with patch("graph.generation_graph.generate_intermediate_definition", side_effect=RuntimeError("no API key")):
            result = generate_test("User can log in", target_tool="playwright")
        assert "no API key" in result["error"]
        assert result["generated_code"] == ""
