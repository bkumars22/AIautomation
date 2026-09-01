"""
LangGraph orchestration: requirement text in, generated tool-specific
code + a human-readable manual test case out.

Node order here is parse_requirements -> generate_intermediate ->
generate_manual_cases -> route_to_adapter -> {tool}_adapter, which is the
correct dependency order (generate_manual_test_case's signature takes the
intermediate definition as input — see generation/manual_case_generator.py
— so it cannot run before generate_intermediate produces one). The
original build prompt's own sketch listed generate_manual_cases BEFORE
generate_intermediate; that ordering is inconsistent with the function
signature it also specifies, so this fixes it rather than reproducing
the inconsistency.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from adapters.cypress_adapter import CypressAdapter
from adapters.playwright_adapter import PlaywrightAdapter
from adapters.selenium_adapter import SeleniumAdapter
from generation.intermediate_generator import generate_intermediate_definition
from generation.manual_case_generator import generate_manual_test_case
from generation.requirements_parser import parse_requirements

_ADAPTERS = {
    "playwright": PlaywrightAdapter(),
    "selenium": SeleniumAdapter(),
    "cypress": CypressAdapter(),
}


class TestGenState(TypedDict):
    requirement_text: str
    target_tool: str  # "playwright" | "selenium" | "cypress"
    intermediate_def: dict[str, Any]
    manual_test_case: str
    generated_code: str
    error: str


def parse_requirements_node(state: TestGenState) -> TestGenState:
    try:
        text = parse_requirements(state.get("requirement_text", ""))
        return {**state, "requirement_text": text}
    except ValueError as exc:
        return {**state, "error": str(exc)}


def generate_intermediate_definition_node(state: TestGenState) -> TestGenState:
    if state.get("error"):
        return state
    try:
        intermediate_def = generate_intermediate_definition(state["requirement_text"])
        return {**state, "intermediate_def": intermediate_def}
    except Exception as exc:
        return {**state, "error": f"generate_intermediate_definition: {exc}"}


def generate_manual_cases_node(state: TestGenState) -> TestGenState:
    if state.get("error"):
        return state
    manual_case = generate_manual_test_case(state["intermediate_def"])
    return {**state, "manual_test_case": manual_case}


def route_to_adapter_node(state: TestGenState) -> str:
    if state.get("error"):
        return "error"
    if state.get("target_tool") not in _ADAPTERS:
        return "error"
    return state["target_tool"]


def _make_adapter_node(tool_name: str):
    def node(state: TestGenState) -> TestGenState:
        code = _ADAPTERS[tool_name].generate(state["intermediate_def"])
        return {**state, "generated_code": code}
    return node


def error_node(state: TestGenState) -> TestGenState:
    return {**state, "error": state.get("error") or f"Unknown target_tool: {state.get('target_tool')!r}"}


def build_generation_graph():
    graph = StateGraph(TestGenState)
    graph.add_node("parse_requirements", parse_requirements_node)
    graph.add_node("generate_intermediate", generate_intermediate_definition_node)
    graph.add_node("generate_manual_cases", generate_manual_cases_node)
    graph.add_node("playwright", _make_adapter_node("playwright"))
    graph.add_node("selenium", _make_adapter_node("selenium"))
    graph.add_node("cypress", _make_adapter_node("cypress"))
    graph.add_node("error", error_node)

    graph.set_entry_point("parse_requirements")
    graph.add_edge("parse_requirements", "generate_intermediate")
    graph.add_edge("generate_intermediate", "generate_manual_cases")
    graph.add_conditional_edges("generate_manual_cases", route_to_adapter_node, {
        "playwright": "playwright",
        "selenium": "selenium",
        "cypress": "cypress",
        "error": "error",
    })
    graph.add_edge("playwright", END)
    graph.add_edge("selenium", END)
    graph.add_edge("cypress", END)
    graph.add_edge("error", END)

    return graph.compile()


def generate_test(requirement_text: str, target_tool: str) -> TestGenState:
    """Entry point: requirement text + tool choice in, full pipeline state out."""
    graph = build_generation_graph()
    initial: TestGenState = {
        "requirement_text": requirement_text,
        "target_tool": target_tool,
        "intermediate_def": {},
        "manual_test_case": "",
        "generated_code": "",
        "error": "",
    }
    return graph.invoke(initial)
