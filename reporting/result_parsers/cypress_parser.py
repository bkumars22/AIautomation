"""
Parses Cypress's own native `--reporter json` output (Mocha's built-in
json reporter) — genuinely Cypress's own format, unlike Playwright/
Selenium which both converge on pytest-json-report (see
_pytest_json_report.py's docstring).

`cypress run --reporter json` interleaves that JSON with the CLI's own
box-drawing progress output on the SAME stdout stream (verified by
actually running it and inspecting the raw output — `--reporter-options
output=<file>` does not cleanly redirect it away in this Cypress
version), so this must extract the JSON object from mixed text rather
than json.loads() the whole string directly.
"""
from __future__ import annotations

import json

from reporting.unified_report import UnifiedTestResult

_OUTCOME_MAP = {"passed": "passed", "failed": "failed", "pending": "skipped"}


def _extract_json_report(raw_output: str) -> dict:
    """Find the Mocha JSON report object embedded in Cypress's mixed CLI output."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw_output):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(raw_output, i)
        except json.JSONDecodeError:
            continue
        if "stats" in obj and "tests" in obj:
            return obj
    raise ValueError("No Cypress JSON report found in output — was --reporter json passed?")


def parse_cypress_results(raw_output: str) -> list[UnifiedTestResult]:
    report = _extract_json_report(raw_output)

    results = []
    for test in report.get("tests", []):
        # Every spec this adapter generates uses it("runs", ...) inside a
        # single describe(test_name) block, so fullTitle is always exactly
        # "{test_name} runs" -- stripping that fixed, adapter-controlled
        # suffix recovers the original test_name cleanly.
        test_name = test["fullTitle"]
        if test_name.endswith(" " + test["title"]):
            test_name = test_name[: -(len(test["title"]) + 1)]

        err = test.get("err") or {}
        status = "skipped" if test in report.get("pending", []) else ("failed" if err else "passed")

        results.append(UnifiedTestResult(
            test_name=test_name,
            tool_used="cypress",
            status=status,
            duration_ms=test.get("duration") or 0,
            error_message=err.get("message"),
        ))
    return results
