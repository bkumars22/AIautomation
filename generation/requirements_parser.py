"""
parse_requirements — the first pipeline node. Deliberately thin: real
requirement understanding happens inside generate_intermediate_definition's
LLM call (generation/intermediate_generator.py); this step only does the
cheap, LLM-free validation that should short-circuit the pipeline before
spending an API call on obviously-empty input.
"""
from __future__ import annotations


def parse_requirements(requirement_text: str) -> str:
    """Returns the normalized requirement text, or raises ValueError if empty."""
    text = (requirement_text or "").strip()
    if not text:
        raise ValueError("requirement_text is empty")
    return text
