"""
Shared parsing for pytest-json-report output — a real discovery made
while building this module, not an assumption: Playwright (via
pytest-playwright's `page` fixture) and Selenium (via this framework's
own `driver` fixture, see root conftest.py) both converge on running
generated scripts as ordinary pytest tests to get structured results,
since neither raw sync-API Playwright scripts nor raw Selenium scripts
have a built-in structured reporter of their own. Only Cypress has a
genuinely different native format (see cypress_parser.py) — verified by
actually running `pytest --json-report` against both and comparing the
schemas, not assumed.
"""
from __future__ import annotations

from typing import Any

from reporting.unified_report import UnifiedTestResult

_OUTCOME_MAP = {"passed": "passed", "failed": "failed", "skipped": "skipped"}


def parse_pytest_json_report(report: dict[str, Any], tool_used: str) -> list[UnifiedTestResult]:
    results = []
    for test in report.get("tests", []):
        # nodeid looks like "generated/test_x.py::test_x[chromium]" (Playwright
        # parametrizes by browser) or "...::test_x" (Selenium, unparametrized) --
        # strip both the file prefix and any [param] suffix for a clean name.
        raw_name = test["nodeid"].split("::")[-1]
        test_name = raw_name.split("[")[0]

        call = test.get("call", {})
        status = _OUTCOME_MAP.get(test["outcome"], test["outcome"])
        error_message = call.get("longrepr") if status != "passed" else None

        results.append(UnifiedTestResult(
            test_name=test_name,
            tool_used=tool_used,
            status=status,
            duration_ms=round(call.get("duration", 0) * 1000),
            error_message=str(error_message) if error_message else None,
        ))
    return results
