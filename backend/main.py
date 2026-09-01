"""
FastAPI backend for the framework's UI — generate code for any of the 3
tools from an intermediate definition (or from free-text requirements,
if ANTHROPIC_API_KEY is set), and actually run generated code against a
real target URL, returning a UnifiedTestResult.

The bundled demo site (tests/demo_site/) starts automatically so the UI
has something to point at with zero configuration for a first try — see
docs/getting_started.md for why that's explicitly a demo convenience,
not how real projects are meant to use this.
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from adapters.cucumber_adapter import CucumberAdapter
from adapters.cypress_adapter import CypressAdapter
from adapters.playwright_adapter import PlaywrightAdapter
from adapters.selenium_adapter import SeleniumAdapter
from adapters.testng_selenium_adapter import TestNGSeleniumAdapter
from backend.executor import run_generated_test
from generation.intermediate_generator import validate_intermediate_definition
from generation.manual_case_generator import generate_manual_test_case
from graph.generation_graph import generate_test
from reporting.exporters import export_to_csv, export_to_excel
from tests.demo_site.server import DemoSiteServer

logger = logging.getLogger("universal_test_framework.backend")

ROOT = Path(__file__).parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures"
FRONTEND_DIR = ROOT / "frontend"

# Tools this backend can execute live, in-process, against the demo site.
_RUNNABLE_ADAPTERS = {
    "playwright": PlaywrightAdapter(),
    "selenium": SeleniumAdapter(),
    "cypress": CypressAdapter(),
}

# All tools this backend can GENERATE code for. TestNG and Cucumber are
# real, independently-verified runners (see runners/testng-selenium and
# cucumber/) but each needs its own project-level toolchain (Maven,
# cucumber-js) rather than a single self-contained script, so the API
# only offers code preview for them, not live "Run" -- see
# docs/getting_started.md for how to actually run them.
_ADAPTERS = {
    **_RUNNABLE_ADAPTERS,
    "testng-selenium": TestNGSeleniumAdapter(),
    "cucumber": CucumberAdapter(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    demo_site = DemoSiteServer()
    app.state.demo_site_url = demo_site.__enter__()
    app.state.run_history = []
    logger.info("Demo site running at %s", app.state.demo_site_url)
    yield
    demo_site.__exit__(None, None, None)


app = FastAPI(title="Universal Test Framework", lifespan=lifespan)


class GenerateFromDefRequest(BaseModel):
    intermediate_def: dict[str, Any]
    target_tool: str


class GenerateFromRequirementsRequest(BaseModel):
    requirement_text: str
    target_tool: str


class RunRequest(BaseModel):
    tool: str
    code: str
    base_url: Optional[str] = None


@app.get("/api/fixtures")
def list_fixtures():
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        fixtures.append({"name": path.stem, "intermediate_def": json.loads(path.read_text(encoding="utf-8"))})
    return {"fixtures": fixtures}


@app.get("/api/demo-site-url")
def demo_site_url():
    return {"base_url": app.state.demo_site_url}


@app.post("/api/generate")
def generate_from_definition(payload: GenerateFromDefRequest):
    if payload.target_tool not in _ADAPTERS:
        raise HTTPException(422, f"target_tool must be one of {list(_ADAPTERS)}")
    try:
        validate_intermediate_definition(payload.intermediate_def)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    code = _ADAPTERS[payload.target_tool].generate(payload.intermediate_def)
    manual_case = generate_manual_test_case(payload.intermediate_def)
    return {"generated_code": code, "manual_test_case": manual_case}


@app.post("/api/generate-from-requirements")
def generate_from_requirements(payload: GenerateFromRequirementsRequest):
    """Runs the full LangGraph pipeline — needs ANTHROPIC_API_KEY set on the backend process."""
    result = generate_test(payload.requirement_text, payload.target_tool)
    if result["error"]:
        raise HTTPException(422, result["error"])
    return {
        "intermediate_def": result["intermediate_def"],
        "manual_test_case": result["manual_test_case"],
        "generated_code": result["generated_code"],
    }


@app.post("/api/run")
def run(payload: RunRequest):
    if payload.tool not in _RUNNABLE_ADAPTERS:
        raise HTTPException(
            422,
            f"tool must be one of {list(_RUNNABLE_ADAPTERS)} -- "
            f"{payload.tool} is generated but run via its own toolchain "
            "(see docs/getting_started.md), not this in-process runner.",
        )
    base_url = payload.base_url or app.state.demo_site_url
    result = run_generated_test(payload.tool, payload.code, base_url)
    app.state.run_history.append(result)
    return {
        "test_name": result.test_name,
        "tool_used": result.tool_used,
        "status": result.status,
        "duration_ms": result.duration_ms,
        "error_message": result.error_message,
    }


@app.get("/api/history")
def history():
    return {
        "results": [
            {
                "test_name": r.test_name,
                "tool_used": r.tool_used,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
            }
            for r in app.state.run_history
        ]
    }


@app.post("/api/history/clear")
def clear_history():
    app.state.run_history = []
    return {"status": "ok"}


@app.get("/api/export/csv")
def export_csv():
    if not app.state.run_history:
        raise HTTPException(404, "No test runs yet -- run at least one test before exporting.")
    csv_text = export_to_csv(app.state.run_history)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=test_report.csv"},
    )


@app.get("/api/export/excel")
def export_excel():
    if not app.state.run_history:
        raise HTTPException(404, "No test runs yet -- run at least one test before exporting.")
    xlsx_bytes = export_to_excel(app.state.run_history)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_report.xlsx"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
