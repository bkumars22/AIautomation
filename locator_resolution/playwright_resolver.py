"""
Semantic locator resolution for the Playwright adapter.

Playwright's own get_by_role/get_by_label/get_by_text already query the
browser's accessibility tree — this is genuinely "the easy case" the
framework's design doc calls out: no custom accessibility-tree walking or
visual fallback is needed here (that's Selenium/Cypress's problem, since
they have no built-in semantic-label-to-selector translation).

What this module DOES add on top of Playwright's primitives: a small,
explicit fallback chain per target type (e.g. field_description tries
get_by_label, then get_by_placeholder, then get_by_text), because a
generator-produced semantic description won't always land on the exact
mechanism (label vs. placeholder vs. plain visible text) a given page
actually used for that element. This mirrors the same fallback-chain
philosophy as playwright-modular-locator-framework's ModularLocatorEngine,
adapted to Playwright's own lazy Locator objects instead of a raw DOM list.

A `hint` on the target (e.g. {"test_id": "..."} or {"css": "..."}) is
always tried FIRST — see docs/locator_hints.md for real cases (found
during this project's own adapter testing) where semantic resolution
alone genuinely cannot work, most notably: an assert_text target whose
identifying description is not the same string as the text being
asserted (a confirmation banner described as "confirmation banner" but
displaying "Thanks — we'll be in touch shortly.").
"""
from __future__ import annotations

from typing import Any


class LocatorResolutionError(Exception):
    """Raised when every strategy in the fallback chain found zero matches."""


def _hint_candidates(page, hint: dict[str, Any]) -> list[tuple[str, Any]]:
    candidates = []
    if "test_id" in hint:
        candidates.append(("hint_test_id", lambda: page.get_by_test_id(hint["test_id"])))
    if "css" in hint:
        candidates.append(("hint_css", lambda: page.locator(hint["css"])))
    return candidates


def _semantic_candidates(page, target: dict[str, Any]) -> list[tuple[str, Any]]:
    target_type = target["type"]
    value = target.get("value")

    if target_type == "element_role":
        return [("role", lambda: page.get_by_role(target["role"], name=target["name"]))]

    if target_type in ("field_description", "checkbox_description", "dropdown_description"):
        return [
            ("label", lambda: page.get_by_label(value)),
            ("placeholder", lambda: page.get_by_placeholder(value)),
            ("text", lambda: page.get_by_text(value)),
        ]

    if target_type == "button_text":
        return [
            ("role_button", lambda: page.get_by_role("button", name=value)),
            ("text", lambda: page.get_by_text(value)),
        ]

    if target_type == "link_text":
        return [
            ("role_link", lambda: page.get_by_role("link", name=value)),
            ("text", lambda: page.get_by_text(value)),
        ]

    if target_type == "page_text":
        return [("text", lambda: page.get_by_text(value))]

    raise LocatorResolutionError(f"Unknown target type: {target_type!r}")


def resolve(page, target: dict[str, Any]):
    """
    Return a Playwright Locator for one intermediate-format `target`,
    trying each candidate strategy (hints first, then the semantic
    fallback chain for that target type) until one matches at least one
    real element on the current page.

    Raises LocatorResolutionError if every strategy matched zero elements
    — this is deliberate: surfacing "no strategy found this element" here
    is far more debuggable than returning a locator that will just time
    out later with a generic Playwright error.
    """
    candidates = _hint_candidates(page, target.get("hint") or {}) + _semantic_candidates(page, target)

    tried = []
    for name, make_locator in candidates:
        locator = make_locator()
        try:
            count = locator.count()
        except Exception as exc:
            tried.append(f"{name} (error: {exc})")
            continue
        if count > 0:
            return locator.first
        tried.append(name)

    raise LocatorResolutionError(
        f"No locator strategy matched target {target!r}. Tried, in order: {tried}. "
        f"See docs/locator_hints.md for how to add a hint for ambiguous elements."
    )
