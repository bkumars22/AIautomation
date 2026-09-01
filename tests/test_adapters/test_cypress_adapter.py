"""
Tests the Cypress adapter the same two ways as the other two: codegen
correctness, then real execution of each generated spec (via `npx cypress
run`) against the same real demo site — the third and final proof that
one identical intermediate definition produces correct, runnable code
across all three tools, not just Playwright and Selenium.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from adapters.cypress_adapter import CypressAdapter  # noqa: E402
from tests.demo_site.server import DemoSiteServer  # noqa: E402

FIXTURES_DIR = ROOT / "tests" / "fixtures"
GENERATED_DIR = ROOT / "generated"  # Cypress's specPattern (cypress.config.js) requires this exact location


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def adapter() -> CypressAdapter:
    return CypressAdapter()


class TestCodegen:
    def test_navigate(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert 'cy.visit("/login")' in code

    def test_fill(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert '.clear().type("test@example.com")' in code

    def test_click(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert ".click()" in code

    def test_select(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert '.select("Sales")' in code

    def test_check(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert ".check()" in code

    def test_assert_text_with_hint(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert '"hint":{"test_id":"confirmation-banner"}' in code.replace(" ", "").replace("\n", "")
        assert 'should("contain.text"' in code

    def test_assert_url(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert 'cy.url().should("include", "/pricing")' in code

    def test_element_role_target(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert '"role":"heading"' in code.replace(" ", "")
        assert "Simple, transparent pricing" in code


class TestRealExecutionAgainstDemoSite:
    """Proves cy.resolveTarget()'s fallback chain actually resolves real elements, same fixtures as the other two adapters."""

    @pytest.fixture(scope="class")
    def demo_site_url(self):
        with DemoSiteServer() as base_url:
            yield base_url

    def _run_fixture(self, adapter: CypressAdapter, fixture_name: str, base_url: str):
        test_def = _load_fixture(fixture_name)
        code = adapter.generate(test_def)
        GENERATED_DIR.mkdir(exist_ok=True)
        spec_path = GENERATED_DIR / adapter.generate_filename(test_def)
        spec_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "cypress", "run", "--spec", str(spec_path.relative_to(ROOT)).replace("\\", "/"),
                 "--config", f"baseUrl={base_url}"],
                cwd=str(ROOT), capture_output=True, encoding="utf-8", errors="replace",
                shell=True, timeout=90,
            )
            assert result.returncode == 0, (
                f"{fixture_name} failed against the real demo site:\n{result.stdout[-3000:]}\n{result.stderr[-1000:]}"
            )
        finally:
            spec_path.unlink(missing_ok=True)

    def test_login_scenario_passes_for_real(self, adapter, demo_site_url):
        self._run_fixture(adapter, "login.json", demo_site_url)

    def test_form_submission_scenario_passes_for_real(self, adapter, demo_site_url):
        self._run_fixture(adapter, "form_submission.json", demo_site_url)

    def test_navigation_scenario_passes_for_real(self, adapter, demo_site_url):
        self._run_fixture(adapter, "navigation.json", demo_site_url)
