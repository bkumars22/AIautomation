"""
Assembles the right strategy chain per target type and runs it through
LocatorEngine — the single entry point generated Selenium code calls.
Hints (test_id, css) are always tried first; the OpenCV visual fallback
is always last, and only ever activates when a target carries a
hint.reference_image (see visual_fallback.py's docstring).
"""
from __future__ import annotations

from typing import Any

from selenium.webdriver.common.by import By

from locator_resolution.base import LocatorEngine, LocatorResolutionError, LocatorStrategy
from locator_resolution.strategies.accessibility_tree import (
    AriaLabelStrategy,
    LabelAssociationStrategy,
    PlaceholderStrategy,
    RoleAttributeStrategy,
    TextContentStrategy,
)
from locator_resolution.strategies.visual_fallback import VisualFallbackStrategy

__all__ = ["resolve", "LocatorResolutionError"]


class _HintTestIdStrategy(LocatorStrategy):
    name = "hint_test_id"

    def find(self, driver, target: dict) -> Any | None:
        test_id = (target.get("hint") or {}).get("test_id")
        if not test_id:
            return None
        elements = driver.find_elements(By.CSS_SELECTOR, f'[data-testid="{test_id}"]')
        return elements[0] if elements else None


class _HintCssStrategy(LocatorStrategy):
    name = "hint_css"

    def find(self, driver, target: dict) -> Any | None:
        css = (target.get("hint") or {}).get("css")
        if not css:
            return None
        elements = driver.find_elements(By.CSS_SELECTOR, css)
        return elements[0] if elements else None


_SEMANTIC_STRATEGIES_BY_TYPE: dict[str, list[LocatorStrategy]] = {
    "field_description": [AriaLabelStrategy(), LabelAssociationStrategy(), PlaceholderStrategy(), TextContentStrategy()],
    "checkbox_description": [AriaLabelStrategy(), LabelAssociationStrategy(), TextContentStrategy()],
    "dropdown_description": [AriaLabelStrategy(), LabelAssociationStrategy(), PlaceholderStrategy()],
    "button_text": [TextContentStrategy(), AriaLabelStrategy()],
    "link_text": [TextContentStrategy(), AriaLabelStrategy()],
    "element_role": [RoleAttributeStrategy()],
    "page_text": [TextContentStrategy()],
}


def resolve(driver, target: dict):
    semantic = _SEMANTIC_STRATEGIES_BY_TYPE.get(target["type"], [])
    chain = [_HintTestIdStrategy(), _HintCssStrategy(), *semantic, VisualFallbackStrategy()]
    report = LocatorEngine(chain).find_element(driver, target)
    return report["element"]
