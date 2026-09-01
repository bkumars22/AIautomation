"""
Shared Strategy-pattern contract for locator resolution — ported from
playwright-modular-locator-framework's ModularLocatorEngine, generalized
so any tool's strategies can plug into the same fallback-chain engine.

Playwright doesn't need this (see locator_resolution/playwright_resolver.py's
docstring for why) — this is for Selenium and Cypress, which have no
built-in semantic-label-to-selector translation and need real,
tool-specific resolution logic: an accessibility-tree-informed pass first
(ARIA attributes, label association, role/text), then OpenCV visual
template matching as the last resort, exactly the fallback order the
Locator Framework project already proved out.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LocatorStrategy(ABC):
    """Every locator strategy module implements `find()`; the engine only ever calls that."""

    name: str

    @abstractmethod
    def find(self, context: Any, target: dict) -> Any | None:
        """Return a tool-specific element handle, or None if this strategy found nothing."""
        raise NotImplementedError


class LocatorResolutionError(Exception):
    """Raised when every strategy in the chain — including visual fallback — found nothing."""


class LocatorEngine:
    """
    Runs strategies in order, returns the first match. This class itself
    never changes when strategies are added/removed/reordered — that's
    the entire point of the pattern (see ModularLocatorEngine, the
    original version of this class, for the from-scratch demo of why).
    """

    def __init__(self, strategies: list[LocatorStrategy]):
        self.strategies = strategies

    def find_element(self, context: Any, target: dict) -> dict:
        report = {"target": target, "strategy_used": None, "element": None, "tried": []}
        for strategy in self.strategies:
            element = strategy.find(context, target)
            report["tried"].append(strategy.name)
            if element is not None:
                report["strategy_used"] = strategy.name
                report["element"] = element
                report["healed"] = len(report["tried"]) > 1
                return report

        raise LocatorResolutionError(
            f"No strategy matched target {target!r}. Tried, in order: {report['tried']}. "
            f"See docs/locator_hints.md for how to add a hint for ambiguous elements."
        )
