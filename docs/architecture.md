# Architecture Overview

```
requirements (free text, optional)
        |
        v  generation/requirements_parser.py
        v  generation/intermediate_generator.py (LLM, via graph/generation_graph.py's LangGraph pipeline)
        v
intermediate test definition (JSON) ---- generation/manual_case_generator.py --> plain-English manual test case
        |
        v  one of 5 adapters (adapters/*.py)
        v
generated code (Playwright / Selenium / Cypress / TestNG-Java / Cucumber .feature)
        |
        v  each adapter's generated code imports a shared locator resolver
        v  (locator_resolution/*, one implementation per language)
        v
runs against a real browser/app
        |
        v  native test-tool output (pytest-json-report / Cypress JSON / TestNG XML)
        v  reporting/result_parsers/*.py --> UnifiedTestResult (reporting/unified_report.py)
        v
reporting/exporters.py --> CSV / Excel
```

## Why an intermediate format at all

The alternative is an LLM (or a human) writing Selenium/Playwright/etc.
code directly per target tool — N tools means N generation paths, each
with its own chance to get an action or locator strategy subtly wrong.
One JSON shape (`docs/intermediate_format.md`) that every adapter
translates identically means the "what should happen" step (parsing
requirements, choosing actions and target descriptions) is written and
validated exactly once, and adding a 6th tool is "write one more
adapter for the format," not "re-solve test generation from scratch."

## Why locator resolution is a separate layer per language, not shared

Playwright ships real accessibility-tree queries
(`get_by_role`/`get_by_label`/`get_by_text`) — Selenium, Cypress, and
plain Java/Selenium do not. That's the actual hard problem this project
set out to solve (see each resolver's own docstring in
`locator_resolution/`), and it's inherently per-language: a DOM query
strategy is expressed in Python, JS, or Java DOM/WebDriver APIs, so
there is no way to write it once and share the implementation across
languages — only the *design* (try aria-label, then label association,
then placeholder, then text content, then role, with a hint escape
hatch before all of them and a visual fallback after) is shared, and
each language's resolver re-implements that same design against its own
APIs. `docs/adapters.md` documents each one; `docs/adding_a_new_language.md`
documents the pattern for porting it to a 4th language.

## Why Cucumber is structured differently from the other four

Playwright/Selenium/Cypress/TestNG adapters each generate one complete,
self-contained script per test — regenerate the test definition,
regenerate the script, nothing else to maintain. Cucumber's actual
value proposition is the opposite: a business-readable `.feature` file
backed by a small, reusable, hand-written step library. Generating
throwaway step definitions per test would defeat that entirely, so
`CucumberAdapter` only ever emits the `.feature` file, and
`cucumber/step_definitions/steps.js` is written once, by hand, to cover
every phrasing the adapter can produce (see `docs/adapters.md`).

## Reporting: converging genuinely different native formats

Playwright and Selenium (Python) share pytest's own JSON report schema,
consumed by one shared parser
(`reporting/result_parsers/_pytest_json_report.py`) since a custom
`driver` pytest fixture (`conftest.py`) makes Selenium collectible by
pytest too. Cypress's `--reporter json` embeds a JSON object inside
otherwise-normal CLI text, requiring `json.JSONDecoder().raw_decode()`
to extract (see `docs/troubleshooting.md`). Both converge into the same
`UnifiedTestResult` dataclass (`reporting/unified_report.py`), which is
what `reporting/exporters.py` and the backend API report on — the
reporting layer doesn't need to know which tool produced a result once
it's in that shape.

## Backend + UI

`backend/main.py` (FastAPI) exposes code generation for all 5 adapters
and live in-process execution for the 3 self-contained-script tools
(`backend/executor.py` reuses the exact same pytest/Cypress invocation
mechanisms proven in `tests/test_adapters/`, not a separate
implementation). `frontend/` is plain HTML/JS with no build step —
deliberately, since the UI's job here is to prove the API end-to-end,
not to be a production console.

## What this project deliberately does not do

- Package itself as an installable library (`pip install -e .` /
  npm package) — generated scripts embed an absolute path back to this
  checkout instead (see `docs/getting_started.md`'s opening note).
- Implement visual fallback for Java (`docs/adapters.md`).
- Genuinely support any language/framework beyond the 5 above — see
  `docs/adding_a_new_language.md` for how the pattern extends, without
  claiming those extensions are built.
- Ship an enterprise-grade UI redesign; the current frontend is
  functional, not polished, by explicit scope decision.
