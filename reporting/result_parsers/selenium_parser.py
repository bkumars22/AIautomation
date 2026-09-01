"""
Parses pytest-json-report output from running generated Selenium scripts
under pytest — Selenium has no reporter of its own, so this project's
root conftest.py provides the `driver` fixture generated scripts already
expect (the standard way real Selenium+pytest projects work), and gets
the exact same structured-report format as the Playwright parser for
free (see _pytest_json_report.py's docstring for how that was verified).
"""
from __future__ import annotations

from typing import Any

from reporting.result_parsers._pytest_json_report import parse_pytest_json_report
from reporting.unified_report import UnifiedTestResult


def parse_selenium_results(report: dict[str, Any]) -> list[UnifiedTestResult]:
    return parse_pytest_json_report(report, tool_used="selenium")
