"""
Tests the Playwright adapter two ways:

1. Codegen unit tests — every action type produces the expected call
   shape, for all three fixtures. Fast, no browser needed.
2. Real execution tests — each fixture's generated script is actually run
   (as a subprocess, exactly like a user would run it) against the real
   demo site in tests/demo_site/. This is the proof the prompt this
   project was built from explicitly demanded: "actually-runnable code
   against a real test page", not just plausible-looking generated text.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from adapters.playwright_adapter import PlaywrightAdapter  # noqa: E402
from tests.demo_site.server import DemoSiteServer  # noqa: E402

FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def adapter() -> PlaywrightAdapter:
    return PlaywrightAdapter()


class TestCodegen:
    """Every action type this format defines must produce a correct call."""

    def test_navigate(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert 'page.goto(BASE_URL + "/login")' in code

    def test_fill(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert '"field_description"' in code and '.fill("test@example.com")' in code

    def test_click(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert ".click()" in code and '"Sign In"' in code

    def test_assert_visible(self, adapter):
        code = adapter.generate(_load_fixture("login.json"))
        assert "to_be_visible()" in code

    def test_select(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert '.select_option(label="Sales")' in code

    def test_check(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert ".check()" in code

    def test_assert_text_with_hint(self, adapter):
        code = adapter.generate(_load_fixture("form_submission.json"))
        assert '"hint": {"test_id": "confirmation-banner"}' in code
        assert "to_contain_text(" in code

    def test_link_text_distinct_from_button_text(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert '"type": "link_text"' in code

    def test_assert_url(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert "expect(page).to_have_url(re.compile(re.escape(" in code
        assert '"/pricing"' in code

    def test_element_role_target(self, adapter):
        code = adapter.generate(_load_fixture("navigation.json"))
        assert '"role": "heading"' in code and '"name": "Simple, transparent pricing"' in code

    def test_generated_file_is_valid_python(self, adapter):
        for fixture_name in ["login.json", "form_submission.json", "navigation.json"]:
            code = adapter.generate(_load_fixture(fixture_name))
            compile(code, f"<generated:{fixture_name}>", "exec")  # raises SyntaxError if malformed


class TestRealExecutionAgainstDemoSite:
    """The actual proof: generated code runs and passes against a real page."""

    @pytest.fixture(scope="class")
    def demo_site_url(self):
        with DemoSiteServer() as base_url:
            yield base_url

    def _run_fixture(self, adapter: PlaywrightAdapter, fixture_name: str, base_url: str, tmp_path: Path):
        test_def = _load_fixture(fixture_name)
        code = adapter.generate(test_def)
        script_path = tmp_path / adapter.generate_filename(test_def)
        script_path.write_text(code, encoding="utf-8")

        import os
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT),
            env={**os.environ, "TEST_BASE_URL": base_url},
            capture_output=True, text=True, timeout=30,
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
