"""
Step 2 of the document-upload feature -- the genuinely hard part: a
requirements document usually describes several distinct testable
behaviors, not one, so this must split them apart BEFORE anything
downstream (manual case / automated code generation) runs on them.

Mirrors generation/intermediate_generator.py's shape exactly: a single,
thin, real network-calling function (_call_llm) that every test mocks,
plus separate, independently-unit-testable parsing/validation functions
around it -- same reasoning, same file laid out the same way, so anyone
who already understands that module understands this one.
"""
from __future__ import annotations

import json
import os
import re

_SYSTEM_PROMPT = """You read a requirements document (a Jira export, a business \
requirements doc, or general free-form requirements) and identify every \
distinct testable scenario in it -- a specific user action and its expected \
outcome.

Only include genuinely distinct, testable behaviors. Do not split one \
behavior into artificial fragments. If the document describes background, \
glossary terms, or non-functional notes with no specific user-facing action \
and outcome, do not invent a scenario for them.

If the document contains NO identifiable testable scenario at all, return \
an empty JSON list: []

Respond with ONLY a JSON list, no prose, no markdown code fences. Each item: \
{"scenario_name": "short imperative name", "description": "1-2 sentence description", \
"acceptance_criteria": "the specific, checkable condition(s) that make this pass"}"""


class ScenarioExtractionError(Exception):
    """Raised when the LLM's response isn't usable -- never silently downgraded to a fabricated scenario."""


def _call_llm(document_text: str) -> str:
    """The only function that makes a real network call -- mocked in all unit tests."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set -- extract_test_scenarios() needs a real LLM to find "
            "distinct testable scenarios in an uploaded document. Set the env var to use this feature."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": document_text}],
    )
    return response.content[0].text


def _extract_json_list(llm_output: str) -> list:
    """Same fenced-code-block tolerance as intermediate_generator.py's _extract_json."""
    stripped = llm_output.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ScenarioExtractionError(f"LLM did not return valid JSON: {exc}. Raw output: {llm_output[:500]!r}") from exc
    return parsed


def validate_scenarios(scenarios: list) -> None:
    """Raises ScenarioExtractionError with a specific, actionable message on the first structural problem found."""
    if not isinstance(scenarios, list):
        raise ScenarioExtractionError(f"Expected a JSON list of scenarios, got {type(scenarios).__name__}")

    required_keys = {"scenario_name", "description", "acceptance_criteria"}
    for i, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ScenarioExtractionError(f"Scenario {i} is not an object: {scenario!r}")
        missing = required_keys - scenario.keys()
        if missing:
            raise ScenarioExtractionError(f"Scenario {i} is missing required field(s): {sorted(missing)}")
        if not scenario["scenario_name"].strip():
            raise ScenarioExtractionError(f"Scenario {i} has an empty scenario_name")


def extract_test_scenarios(document_text: str) -> list[dict]:
    """
    Document text in, a validated list of distinct testable scenarios out.
    Returns an empty list (never a fabricated scenario) when the document
    genuinely has no identifiable testable behavior -- callers must handle
    that explicitly rather than assuming at least one scenario always comes back.
    """
    llm_output = _call_llm(document_text)
    scenarios = _extract_json_list(llm_output)
    validate_scenarios(scenarios)
    return scenarios
