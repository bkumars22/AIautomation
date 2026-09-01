"""
Generates Playwright scripts from all three fixture intermediate
definitions, writes them to generated/, starts the real demo site, and
actually executes each generated script against it — the real proof that
codegen + locator resolution work end to end, not just that the generated
text looks plausible.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from adapters.playwright_adapter import PlaywrightAdapter  # noqa: E402
from tests.demo_site.server import DemoSiteServer  # noqa: E402

FIXTURES = ["login.json", "form_submission.json", "navigation.json"]


def main() -> int:
    adapter = PlaywrightAdapter()
    generated_dir = ROOT / "generated"
    generated_dir.mkdir(exist_ok=True)

    generated_files = []
    for fixture_name in FIXTURES:
        test_def = json.loads((ROOT / "tests" / "fixtures" / fixture_name).read_text())
        code = adapter.generate(test_def)
        out_path = generated_dir / adapter.generate_filename(test_def)
        out_path.write_text(code, encoding="utf-8")
        generated_files.append(out_path)
        print(f"Generated: {out_path.relative_to(ROOT)}")

    print()
    all_passed = True
    with DemoSiteServer() as base_url:
        print(f"Demo site running at {base_url}\n")
        for path in generated_files:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(ROOT),
                env={**__import__("os").environ, "TEST_BASE_URL": base_url},
                capture_output=True, text=True,
            )
            ok = result.returncode == 0
            all_passed = all_passed and ok
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {path.name}")
            if not ok:
                print(result.stdout)
                print(result.stderr)

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
