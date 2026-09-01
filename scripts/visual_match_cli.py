"""
CLI wrapper around locator_resolution.strategies.visual_fallback.match_template
so non-Python callers (the Cypress adapter's Node task — see
locator_resolution/visual_match_task.js) can reuse the exact same OpenCV
matching code Selenium's VisualFallbackStrategy uses in-process.

Usage: python visual_match_cli.py <screenshot_path> <reference_image_path> [confidence_threshold]
Prints a JSON object (or `null`) to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from locator_resolution.strategies.visual_fallback import match_template  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: visual_match_cli.py <screenshot_path> <reference_image_path> [confidence_threshold]", file=sys.stderr)
        return 2

    screenshot_path, reference_image_path = sys.argv[1], sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8

    result = match_template(screenshot_path, reference_image_path, threshold)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
