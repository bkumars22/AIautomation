"""
Parses pytest-json-report output from running generated Playwright
scripts under pytest (pytest-playwright's `page` fixture matches the
`page` parameter name the Playwright adapter already generates — no
change needed to the generated scripts themselves to get structured
reporting on top of standalone-runnable execution).
"""
from __future__ import annotations

from typing import Any

from reporting.result_parsers._pytest_json_report import parse_pytest_json_report
from reporting.unified_report import UnifiedTestResult


def parse_playwright_results(report: dict[str, Any]) -> list[UnifiedTestResult]:
    return parse_pytest_json_report(report, tool_used="playwright")
