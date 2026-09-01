"""
UnifiedTestResult — the one shape every tool-specific parser converges
results into, and a small formatter for printing a combined report
across tools.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UnifiedTestResult:
    test_name: str
    tool_used: str  # "selenium" | "playwright" | "cypress"
    status: str  # "passed" | "failed" | "skipped"
    duration_ms: int
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None


def format_unified_report(results: list[UnifiedTestResult]) -> str:
    if not results:
        return "No results to report."

    name_width = max(len(r.test_name) for r in results) + 2
    lines = [f'{"Test":<{name_width}}{"Tool":<12}{"Status":<9}{"Duration":>10}']
    lines.append("-" * (name_width + 31))
    for r in results:
        lines.append(f"{r.test_name:<{name_width}}{r.tool_used:<12}{r.status:<9}{r.duration_ms:>8}ms")
        if r.error_message:
            first_line = r.error_message.strip().splitlines()[0]
            lines.append(f"    -> {first_line}")

    passed = sum(1 for r in results if r.status == "passed")
    tools = sorted({r.tool_used for r in results})
    lines.append("")
    lines.append(f"{passed}/{len(results)} passed across {len(tools)} tool(s): {', '.join(tools)}")
    return "\n".join(lines)
