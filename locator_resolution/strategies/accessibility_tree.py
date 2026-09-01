"""
Selenium locator strategies — the real engineering the design brief calls
out: Selenium has no get_by_label/get_by_role, so semantic descriptions
have to be resolved via accessibility-tree-adjacent heuristics (ARIA
attributes, <label> association, role semantics) instead of one of
Playwright's built-in primitives.

Each strategy is deliberately narrow (mirrors playwright-modular-locator-
framework's ExactIdStrategy/VisibleTextStrategy/etc. — one matching
mechanism per class, composed into an ordered chain from outside).
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from locator_resolution.base import LocatorStrategy

# Implicit ARIA roles for common tags Selenium/HTML don't require an
# explicit role="..." attribute for — used by RoleAttributeStrategy so
# {"role": "button", ...} also matches a plain <button>, not only
# role="button".
_IMPLICIT_ROLE_TAGS = {
    "button": ["button", "input[@type='button']", "input[@type='submit']"],
    "link": ["a"],
    "heading": ["h1", "h2", "h3", "h4", "h5", "h6"],
    "checkbox": ["input[@type='checkbox']"],
    "textbox": ["input[@type='text']", "input[@type='email']", "textarea"],
}


def _ci_contains(attr_or_text: str, value: str) -> str:
    """XPath fragment: case-insensitive `contains()` for an attribute or text() expression."""
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lower = "abcdefghijklmnopqrstuvwxyz"
    return f"contains(translate({attr_or_text}, '{upper}', '{lower}'), '{value.lower()}')"


def _first_or_none(driver: WebDriver, xpath: str) -> WebElement | None:
    elements = driver.find_elements(By.XPATH, xpath)
    for el in elements:
        if el.is_displayed():
            return el
    return None


class AriaLabelStrategy(LocatorStrategy):
    """Matches any element whose aria-label attribute contains the description."""
    name = "aria_label"

    def find(self, driver: WebDriver, target: dict) -> WebElement | None:
        value = target.get("value")
        if not value:
            return None
        xpath = f"//*[@aria-label and {_ci_contains('@aria-label', value)}]"
        return _first_or_none(driver, xpath)


class LabelAssociationStrategy(LocatorStrategy):
    """
    Matches a <label> containing the description, then resolves to the
    input it labels — via the label's `for` attribute, or an input
    nested inside the label (both real, standard label-association
    patterns).
    """
    name = "label_association"

    def find(self, driver: WebDriver, target: dict) -> WebElement | None:
        value = target.get("value")
        if not value:
            return None

        label_xpath = f"//label[{_ci_contains('.', value)}]"
        for label in driver.find_elements(By.XPATH, label_xpath):
            for_id = label.get_attribute("for")
            if for_id:
                inputs = driver.find_elements(By.XPATH, f"//*[@id='{for_id}']")
                if inputs and inputs[0].is_displayed():
                    return inputs[0]
            nested = label.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            if nested and nested[0].is_displayed():
                return nested[0]
        return None


class PlaceholderStrategy(LocatorStrategy):
    name = "placeholder"

    def find(self, driver: WebDriver, target: dict) -> WebElement | None:
        value = target.get("value")
        if not value:
            return None
        xpath = f"//*[@placeholder and {_ci_contains('@placeholder', value)}]"
        return _first_or_none(driver, xpath)


class TextContentStrategy(LocatorStrategy):
    """Matches any element whose own visible text contains the description — the broadest, last-resort semantic match."""
    name = "text_content"

    def find(self, driver: WebDriver, target: dict) -> WebElement | None:
        value = target.get("value")
        if not value:
            return None
        xpath = f"//*[{_ci_contains('normalize-space(text())', value)}]"
        return _first_or_none(driver, xpath)


class RoleAttributeStrategy(LocatorStrategy):
    """
    Matches by ARIA role (explicit role="..." attribute or the tag's
    implicit role) plus accessible name (aria-label or visible text) —
    for the `element_role` target type.
    """
    name = "role_attribute"

    def find(self, driver: WebDriver, target: dict) -> WebElement | None:
        role = target.get("role")
        accessible_name = target.get("name")
        if not role or not accessible_name:
            return None

        tag_alternatives = _IMPLICIT_ROLE_TAGS.get(role, [])
        tag_predicate = " | ".join(f"//{t}" for t in tag_alternatives) or f"//*[@role='{role}']"
        name_predicate = (
            f"[{_ci_contains('@aria-label', accessible_name)} or "
            f"{_ci_contains('normalize-space(.)', accessible_name)}]"
        )

        candidates = tag_predicate.replace("//", f"//") if "|" not in tag_predicate else tag_predicate
        parts = [p.strip() for p in candidates.split("|")]
        xpath = " | ".join(f"{p}{name_predicate}" for p in parts)
        return _first_or_none(driver, xpath)
