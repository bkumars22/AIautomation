"""
Step 3 of the document-upload feature: for each extracted scenario,
generate a manual test case and automated code for one chosen framework.

Deliberately reuses the EXISTING generation building blocks unchanged --
generation.intermediate_generator.generate_intermediate_definition,
generation.manual_case_generator.generate_manual_test_case, and the same
5 adapters backend/main.py already exposes -- rather than introducing a
parallel generation path. The only new logic here is turning one
extracted scenario dict into the plain-text requirement string that
generate_intermediate_definition already expects.
"""
from __future__ import annotations

from typing import Any

from adapters.cucumber_adapter import CucumberAdapter
from adapters.cypress_adapter import CypressAdapter
from adapters.playwright_adapter import PlaywrightAdapter
from adapters.selenium_adapter import SeleniumAdapter
from adapters.testng_selenium_adapter import TestNGSeleniumAdapter
from generation.intermediate_generator import generate_intermediate_definition
from generation.manual_case_generator import generate_manual_test_case

# Mirrors backend/main.py's _ADAPTERS exactly -- same 5 targets, same names.
_ADAPTERS = {
    "playwright": PlaywrightAdapter(),
    "selenium": SeleniumAdapter(),
    "cypress": CypressAdapter(),
    "testng-selenium": TestNGSeleniumAdapter(),
    "cucumber": CucumberAdapter(),
}


def _scenario_to_requirement_text(scenario: dict[str, Any]) -> str:
    return (
        f"{scenario['scenario_name']}\n\n"
        f"{scenario['description']}\n\n"
        f"Acceptance criteria: {scenario['acceptance_criteria']}"
    )


def generate_full_test_suite(scenarios: list[dict[str, Any]], framework: str) -> list[dict[str, Any]]:
    """One extracted scenario in, one manual+automated test pair out, per scenario.
    An empty `scenarios` list returns an empty list -- callers (the API layer)
    are responsible for messaging a document with zero identifiable scenarios,
    not this function fabricating something to generate."""
    if framework not in _ADAPTERS:
        raise ValueError(f"Unknown framework: {framework!r}. Must be one of {sorted(_ADAPTERS)}")

    adapter = _ADAPTERS[framework]
    results = []
    for scenario in scenarios:
        requirement_text = _scenario_to_requirement_text(scenario)
        intermediate = generate_intermediate_definition(requirement_text)
        manual_case = generate_manual_test_case(intermediate)
        automated_code = adapter.generate(intermediate)

        results.append({
            "scenario_name": scenario["scenario_name"],
            "manual_test_case": manual_case,
            "automated_code": automated_code,
            "framework": framework,
            "intermediate_json": intermediate,
        })
    return results
