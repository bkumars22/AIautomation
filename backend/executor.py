"""
Runs one piece of generated code against a real target URL and returns a
single UnifiedTestResult — the same execution mechanisms already proven
in tests/test_adapters/*.py (pytest+json-report for Playwright/Selenium,
`cypress run --reporter json` for Cypress), consolidated here so the
backend API doesn't duplicate that plumbing a third time.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from reporting.result_parsers.cypress_parser import parse_cypress_results
from reporting.result_parsers.playwright_parser import parse_playwright_results
from reporting.result_parsers.selenium_parser import parse_selenium_results
from reporting.unified_report import UnifiedTestResult

ROOT = Path(__file__).parent.parent
_EXECUTION_TIMEOUT_SECONDS = 90


def _no_result(tool: str, reason: str) -> UnifiedTestResult:
    return UnifiedTestResult(test_name="(unknown)", tool_used=tool, status="failed", duration_ms=0, error_message=reason)


def _run_python_via_pytest(tool: str, code: str, base_url: str) -> UnifiedTestResult:
    with tempfile.TemporaryDirectory(dir=str(ROOT / "generated")) as tmp:
        script_path = Path(tmp) / "test_generated.py"
        script_path.write_text(code, encoding="utf-8")
        report_path = Path(tmp) / "report.json"

        subprocess.run(
            [sys.executable, "-m", "pytest", str(script_path),
             "--json-report", f"--json-report-file={report_path}", "-q"],
            cwd=str(ROOT), env={**os.environ, "TEST_BASE_URL": base_url},
            capture_output=True, encoding="utf-8", errors="replace", timeout=_EXECUTION_TIMEOUT_SECONDS,
        )

        if not report_path.exists():
            return _no_result(tool, "pytest produced no report — the generated code likely failed to even collect (syntax error?)")

        report = json.loads(report_path.read_text(encoding="utf-8"))

    parser = parse_playwright_results if tool == "playwright" else parse_selenium_results
    results = parser(report)
    return results[0] if results else _no_result(tool, "No test was collected from the generated code")


def _run_cypress(code: str, base_url: str) -> UnifiedTestResult:
    generated_dir = ROOT / "generated"
    generated_dir.mkdir(exist_ok=True)
    spec_path = generated_dir / f"test_ui_generated_{uuid.uuid4().hex[:8]}.cy.js"
    spec_path.write_text(code, encoding="utf-8")

    try:
        result = subprocess.run(
            ["npx", "cypress", "run", "--spec", str(spec_path.relative_to(ROOT)).replace("\\", "/"),
             "--config", f"baseUrl={base_url}", "--reporter", "json"],
            cwd=str(ROOT), capture_output=True, encoding="utf-8", errors="replace",
            shell=True, timeout=_EXECUTION_TIMEOUT_SECONDS,
        )
        try:
            results = parse_cypress_results(result.stdout)
        except ValueError:
            return _no_result("cypress", f"Cypress produced no parseable report:\n{result.stdout[-1000:]}\n{result.stderr[-500:]}")
        return results[0] if results else _no_result("cypress", "No test was collected from the generated spec")
    finally:
        spec_path.unlink(missing_ok=True)


def run_generated_test(tool: str, code: str, base_url: str) -> UnifiedTestResult:
    if tool in ("playwright", "selenium"):
        return _run_python_via_pytest(tool, code, base_url)
    if tool == "cypress":
        return _run_cypress(code, base_url)
    raise ValueError(f"Unknown tool: {tool!r}")
