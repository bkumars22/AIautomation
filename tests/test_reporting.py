"""
Tests the 3 result parsers against REAL captured output from each tool
(tests/fixtures/reporting/) — not fabricated JSON shaped to match
whatever the parser expects. Each fixture file was produced by actually
running the corresponding adapter's generated script and capturing its
real stdout/report file; see reporting/result_parsers/*.py docstrings for
how the schemas were verified.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from reporting.result_parsers.cypress_parser import parse_cypress_results  # noqa: E402
from reporting.result_parsers.playwright_parser import parse_playwright_results  # noqa: E402
from reporting.result_parsers.selenium_parser import parse_selenium_results  # noqa: E402
from reporting.unified_report import UnifiedTestResult, format_unified_report  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "reporting"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestPlaywrightParser:
    def test_passed_result(self):
        results = parse_playwright_results(_load_json("playwright_passed.json"))
        assert len(results) == 1
        r = results[0]
        assert r.tool_used == "playwright"
        assert r.status == "passed"
        assert r.test_name == "test_user_can_log_in_with_valid_credentials"
        assert r.duration_ms > 0
        assert r.error_message is None

    def test_failed_result_has_error_message(self):
        results = parse_playwright_results(_load_json("playwright_failed.json"))
        r = results[0]
        assert r.status == "failed"
        assert r.error_message is not None
        assert "page.goto" in r.error_message


class TestSeleniumParser:
    def test_passed_result(self):
        results = parse_selenium_results(_load_json("selenium_passed.json"))
        r = results[0]
        assert r.tool_used == "selenium"
        assert r.status == "passed"
        assert r.error_message is None

    def test_failed_result_has_error_message(self):
        results = parse_selenium_results(_load_json("selenium_failed.json"))
        r = results[0]
        assert r.status == "failed"
        assert r.error_message is not None


class TestCypressParser:
    def test_extracts_json_from_mixed_cli_output(self):
        # This is the real bug this parser exists to handle: `cypress run
        # --reporter json` interleaves the JSON with box-drawing progress
        # text on the same stdout stream.
        raw = _load_text("cypress_passed_raw.txt")
        assert not raw.strip().startswith("{")  # confirms the fixture really is mixed output
        results = parse_cypress_results(raw)
        assert len(results) == 1

    def test_passed_result(self):
        results = parse_cypress_results(_load_text("cypress_passed_raw.txt"))
        r = results[0]
        assert r.tool_used == "cypress"
        assert r.status == "passed"
        assert r.test_name == "User can log in with valid credentials"
        assert r.duration_ms > 0
        assert r.error_message is None

    def test_failed_result_has_error_message(self):
        results = parse_cypress_results(_load_text("cypress_failed_raw.txt"))
        r = results[0]
        assert r.status == "failed"
        assert "cy.visit()" in r.error_message


class TestUnifiedReport:
    def test_combines_results_from_all_three_tools(self):
        pw = parse_playwright_results(_load_json("playwright_passed.json"))
        sel = parse_selenium_results(_load_json("selenium_passed.json"))
        cy = parse_cypress_results(_load_text("cypress_passed_raw.txt"))

        combined = pw + sel + cy
        assert len(combined) == 3
        assert {r.tool_used for r in combined} == {"playwright", "selenium", "cypress"}

        report_text = format_unified_report(combined)
        assert "3/3 passed across 3 tool(s)" in report_text
        for r in combined:
            assert r.test_name in report_text

    def test_report_surfaces_failure_reason(self):
        failed = UnifiedTestResult(
            test_name="something broke", tool_used="playwright", status="failed",
            duration_ms=100, error_message="AssertionError: expected 1 to equal 2\nmore detail",
        )
        report_text = format_unified_report([failed])
        assert "AssertionError: expected 1 to equal 2" in report_text
        assert "0/1 passed" in report_text

    def test_empty_results(self):
        assert format_unified_report([]) == "No results to report."
