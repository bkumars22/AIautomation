"""
Visual (OpenCV template-matching) fallback strategy — the last resort
when ID/label/role/text semantic matching all fail (e.g. an icon-only
button with no text, label, or aria-label).

Directly reuses the technique playwright-modular-locator-framework's
VisualMatchStrategy already proved out (grayscale cv2.matchTemplate,
same 0.8 default confidence threshold) rather than inventing a new
approach. The one real difference: Selenium has no direct "element at
these pixel coordinates" API, so this converts the matched region's
center point to a live element via `document.elementFromPoint()` — the
standard way to bridge a screen coordinate back to a DOM node.

Only activates when the target carries a `hint.reference_image` (a path
to a cropped screenshot of just the element) — see docs/locator_hints.md
for when a real element actually needs this instead of the cheaper
semantic strategies.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import cv2

from locator_resolution.base import LocatorStrategy


def match_template(screenshot_path: str, reference_image_path: str, confidence_threshold: float = 0.8) -> dict[str, Any] | None:
    """
    Core OpenCV template-matching logic, factored out so both
    VisualFallbackStrategy (Selenium, in-process) and
    scripts/visual_match_cli.py (shelled out to from the Cypress adapter's
    Node task — see cypress.config.js — since Node has no OpenCV binding
    as simple/mature as Python's) call the exact same matching code
    instead of two parallel reimplementations.

    Returns the matched region's center point + confidence, or None if
    nothing matched above the threshold.
    """
    full_page = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
    reference = cv2.imread(reference_image_path, cv2.IMREAD_GRAYSCALE)
    if full_page is None or reference is None:
        return None

    result = cv2.matchTemplate(full_page, reference, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence_threshold:
        return None

    ref_height, ref_width = reference.shape
    return {
        "center_x": max_loc[0] + ref_width // 2,
        "center_y": max_loc[1] + ref_height // 2,
        "confidence": round(float(max_val), 4),
    }


class VisualFallbackStrategy(LocatorStrategy):
    name = "visual_fallback"

    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def find(self, driver, target: dict):
        hint = target.get("hint") or {}
        reference_image_path = hint.get("reference_image")
        if not reference_image_path:
            return None  # this strategy only ever activates when explicitly hinted

        with tempfile.TemporaryDirectory() as tmp:
            screenshot_path = str(Path(tmp) / "full_page.png")
            driver.save_screenshot(screenshot_path)

            match = match_template(screenshot_path, reference_image_path, self.confidence_threshold)
            if match is None:
                return None

            return driver.execute_script(
                "return document.elementFromPoint(arguments[0], arguments[1]);",
                match["center_x"], match["center_y"],
            )
