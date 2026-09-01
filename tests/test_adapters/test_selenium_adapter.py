"""
Tests the Selenium adapter the same two ways as the Playwright adapter:
codegen correctness, then real execution of each generated script against
the same real demo site — proof that identical intermediate definitions
produce correct, runnable code across tools, not just for Playwright.
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

from adapters.selenium_adapter import SeleniumAdapter  # noqa: E402
from tests.demo_site.server import DemoSiteServer  # noqa: E402

FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def adapter() -> SeleniumAdapter:
    return SeleniumAdapter()


class TestCodegen:
    def test_navigate(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert 'driver.get(BASE_URL + "/login")' in code

    def test_fill(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert '.send_keys("test@example.com")' in code

    def test_click(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert ".click()" in code

    def test_select_uses_select_by_visible_text(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert "Select(resolve(driver," in code
        assert '.select_by_visible_text("Sales")' in code

    def test_check_only_clicks_if_not_already_selected(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert "if not _el.is_selected(): _el.click()" in code

    def test_assert_url(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert "EC.url_contains(" in code
        assert '"/pricing"' in code

    def test_generated_file_is_valid_python(self, adapter):
        for fixture_name in ["login.json", "form_submission.json", "navigation.json"]:
            code = adapter.generate(_load_fixture(fixture_name))
            compile(code, f"<generated:{fixture_name}>", "exec")


class TestRealExecutionAgainstDemoSite:
    """
    Proves the accessibility-tree resolution strategies (aria-label,
    label-association, role/text matching) actually work against real
    DOM elements — the whole point of building them instead of hand-
    waving the "hard problem" the design brief called out.
    """

    @pytest.fixture(scope="class")
    def demo_site_url(self):
        with DemoSiteServer() as base_url:
            yield base_url

    def _run_fixture(self, adapter: SeleniumAdapter, fixture_name: str, base_url: str, tmp_path: Path):
        test_def = _load_fixture(fixture_name)
        code = adapter.generate(test_def)
        script_path = tmp_path / adapter.generate_filename(test_def)
        script_path.write_text(code, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT),
            env={**os.environ, "TEST_BASE_URL": base_url},
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"{fixture_name} failed against the real demo site:\n{result.stdout}\n{result.stderr}"
        )

    def test_login_scenario_passes_for_real(self, adapter, demo_site_url, tmp_path):
        self._run_fixture(adapter, "login.json", demo_site_url, tmp_path)

    def test_form_submission_scenario_passes_for_real(self, adapter, demo_site_url, tmp_path):
        self._run_fixture(adapter, "form_submission.json", demo_site_url, tmp_path)

    def test_navigation_scenario_passes_for_real(self, adapter, demo_site_url, tmp_path):
        self._run_fixture(adapter, "navigation.json", demo_site_url, tmp_path)
