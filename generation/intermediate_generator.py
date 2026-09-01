"""
The core AI generation step: turns free-text requirements into ONE
tool-agnostic intermediate test definition (see docs/intermediate_format.md).

The LLM call itself is a single, thin, mockable function
(`_call_llm`) so the prompt-construction and response-parsing logic
(the part that actually needs testing) can be unit tested without a real
API call or key — see tests/test_generation/test_intermediate_generator.py.
Needs ANTHROPIC_API_KEY set to actually run generate_intermediate_definition()
for real; ImportError/missing-key failures are raised clearly, not silently
swallowed, since a bad generation must never produce a wrong test silently.
"""
from __future__ import annotations

import json
import os
import re

_SYSTEM_PROMPT = """You translate a plain-English UI test requirement into ONE JSON test \
definition in a fixed, tool-agnostic intermediate format. You do not know or mention \
Selenium, Playwright, or Cypress syntax — only this format.

Format:
{
  "test_name": "string",
  "description": "string, optional",
  "steps": [
    {"action": "navigate", "target": {"type": "url", "value": "/path"}},
    {"action": "fill", "target": {"type": "field_description", "value": "plain-English label"}, "value": "text to type"},
    {"action": "click", "target": {"type": "button_text", "value": "visible button text"}},
    {"action": "click", "target": {"type": "link_text", "value": "visible link text"}},
    {"action": "select", "target": {"type": "dropdown_description", "value": "plain-English label"}, "value": "option text"},
    {"action": "check", "target": {"type": "checkbox_description", "value": "plain-English label"}},
    {"action": "uncheck", "target": {"type": "checkbox_description", "value": "plain-English label"}},
    {"action": "assert_visible", "target": {"type": "page_text", "value": "plain-English description"}},
    {"action": "assert_text", "target": {"type": "page_text", "value": "plain-English description"}, "value": "exact expected text"},
    {"action": "assert_url", "value": "/expected-path"}
  ]
}

Prefer {"type": "element_role", "role": "button|link|heading|checkbox|textbox", "name": "accessible name"} \
over button_text/link_text when you're confident of the ARIA role.

Respond with ONLY the JSON object, no prose, no markdown code fences."""


def _call_llm(requirement_text: str) -> str:
    """The only function that makes a real network call — mocked in all unit tests."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — generate_intermediate_definition() needs a real "
            "LLM to turn free text into the intermediate format. Set the env var, or use the "
            "existing intermediate JSON fixtures directly (they need no LLM at all)."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": requirement_text}],
    )
    return response.content[0].text


def _extract_json(llm_output: str) -> dict:
    """
    LLMs occasionally wrap JSON in ```json fences despite being told not
    to — strip those before parsing rather than failing on a cosmetic
    formatting choice the system prompt didn't fully prevent.
    """
    stripped = llm_output.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    return json.loads(stripped)


def validate_intermediate_definition(test_def: dict) -> None:
    """Raises ValueError with a specific, actionable message on the first structural problem found."""
    if "test_name" not in test_def or not test_def["test_name"]:
        raise ValueError("Intermediate definition is missing a non-empty 'test_name'")
    if "steps" not in test_def or not isinstance(test_def["steps"], list) or not test_def["steps"]:
        raise ValueError("Intermediate definition must have a non-empty 'steps' list")

    valid_actions = {
        "navigate", "fill", "click", "select", "check", "uncheck",
        "assert_visible", "assert_text", "assert_url",
    }
    for i, step in enumerate(test_def["steps"]):
        if step.get("action") not in valid_actions:
            raise ValueError(f"Step {i}: unknown action {step.get('action')!r}")
        if step["action"] != "assert_url" and "target" not in step:
            raise ValueError(f"Step {i} ({step['action']}): missing required 'target'")


def generate_intermediate_definition(requirement_text: str) -> dict:
    """Requirement text in, a validated intermediate test definition out."""
    llm_output = _call_llm(requirement_text)
    test_def = _extract_json(llm_output)
    validate_intermediate_definition(test_def)
    return test_def
