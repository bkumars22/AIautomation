"""
Generates a human-readable manual test case from an intermediate test
definition — tool-independent, produced once before any adapter routing.

Must be genuinely useful standalone: readable by a non-technical
stakeholder, not a comment-ified version of the automation code. So this
describes WHAT a person would do/see, in plain English, never mentioning
locators, selectors, or any of the intermediate format's field names.
"""
from __future__ import annotations

from typing import Any

_TARGET_PHRASE = {
    "field_description": lambda t: t["value"],
    "checkbox_description": lambda t: f'the "{t["value"]}" checkbox',
    "dropdown_description": lambda t: f'the "{t["value"]}" dropdown',
    "button_text": lambda t: f'the "{t["value"]}" button',
    "link_text": lambda t: f'the "{t["value"]}" link',
    "element_role": lambda t: f'the {t["role"]} named "{t["name"]}"',
    "page_text": lambda t: t["value"],
}


def _describe_target(target: dict[str, Any]) -> str:
    phrase_fn = _TARGET_PHRASE.get(target["type"])
    return phrase_fn(target) if phrase_fn else target.get("value", "the element")


def describe_step_in_plain_english(step: dict[str, Any]) -> str:
    action = step["action"]
    target = step.get("target")
    value = step.get("value")

    if action == "navigate":
        return f'Go to {target["value"]}.'
    if action == "fill":
        return f'Enter "{value}" into {_describe_target(target)}.'
    if action == "click":
        return f'Click {_describe_target(target)}.'
    if action == "select":
        return f'Choose "{value}" from {_describe_target(target)}.'
    if action == "check":
        return f'Check {_describe_target(target)}.'
    if action == "uncheck":
        return f'Uncheck {_describe_target(target)}.'
    if action == "assert_visible":
        return f'Verify that {_describe_target(target)} is visible.'
    if action == "assert_text":
        return f'Verify that {_describe_target(target)} shows "{value}".'
    if action == "assert_url":
        return f'Verify the page URL contains "{value}".'
    return f"Unrecognized step: {step}"


def generate_manual_test_case(intermediate_def: dict[str, Any]) -> str:
    lines = [f"Test Case: {intermediate_def['test_name']}"]
    if intermediate_def.get("description"):
        lines.append(intermediate_def["description"])
    lines.append("")
    lines.append("Steps:")
    for i, step in enumerate(intermediate_def["steps"], 1):
        lines.append(f"{i}. {describe_step_in_plain_english(step)}")
    return "\n".join(lines)
