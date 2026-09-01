"""
Translates one intermediate test definition into a real Gherkin .feature
file -- the idiomatic Cucumber pattern: a REUSABLE, hand-written step
library (cucumber/step_definitions/steps.js) implements each phrase
once, and generation only ever produces the business-readable scenario
itself, never throwaway step definitions per test. This is a genuinely
different shape from the other 3 adapters (which each generate a
complete, self-contained script) -- Cucumber's whole value proposition
is exactly this separation.

Step phrasing is deliberately literal about HOW an element is found
(e.g. "the element with test id X") when a hint is present, rather than
hiding that in an assertion that reads identically either way -- for a
business-readable spec, being explicit about a hint-based lookup is more
honest than the reader having no way to tell it apart from a
description-based one.
"""
from __future__ import annotations

from typing import Any

from adapters.base_adapter import BaseAdapter


def _escape(text: str) -> str:
    return text.replace('"', '\\"')


class CucumberAdapter(BaseAdapter):
    name = "cucumber"
    file_extension = ".feature"

    def generate(self, test_def: dict[str, Any]) -> str:
        lines = [f'Feature: {test_def["test_name"]}']
        if test_def.get("description"):
            lines.append(f'  {test_def["description"]}')
        lines.append("")
        lines.append("  Scenario: runs")

        for i, step in enumerate(test_def["steps"]):
            keyword = self._keyword(step, is_first=(i == 0))
            lines.append(f"    {keyword} {self._step_text(step)}")

        lines.append("")
        return "\n".join(lines)

    def _is_action(self, step: dict[str, Any]) -> bool:
        return not step["action"].startswith("assert")

    def _keyword(self, step: dict[str, Any], is_first: bool) -> str:
        if is_first:
            return "Given"
        return "When" if self._is_action(step) else "Then"

    def _step_text(self, step: dict[str, Any]) -> str:
        action = step["action"]
        target = step.get("target") or {}
        value = step.get("value")
        target_type = target.get("type")
        hint = target.get("hint") or {}

        if action == "navigate":
            return f'the user navigates to "{_escape(target["value"])}"'

        if action == "fill":
            return f'the user enters "{_escape(value)}" into the "{_escape(target["value"])}" field'

        if action == "click":
            if target_type == "element_role":
                return f'the user clicks the {target["role"]} named "{_escape(target["name"])}"'
            noun = "button" if target_type == "button_text" else "link"
            return f'the user clicks the "{_escape(target["value"])}" {noun}'

        if action == "select":
            return f'the user selects "{_escape(value)}" from the "{_escape(target["value"])}" dropdown'

        if action == "check":
            return f'the user checks the "{_escape(target["value"])}" checkbox'

        if action == "uncheck":
            return f'the user unchecks the "{_escape(target["value"])}" checkbox'

        if action == "assert_visible":
            if target_type == "element_role":
                return f'the user should see the {target["role"]} named "{_escape(target["name"])}"'
            return f'the user should see "{_escape(target["value"])}"'

        if action == "assert_text":
            if "test_id" in hint:
                return f'the element with test id "{_escape(hint["test_id"])}" should show "{_escape(value)}"'
            return f'the "{_escape(target["value"])}" should show "{_escape(value)}"'

        if action == "assert_url":
            return f'the URL should contain "{_escape(value)}"'

        raise ValueError(f"CucumberAdapter: unsupported action {action!r}")
