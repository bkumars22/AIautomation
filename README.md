# Universal Test Framework

A tool-agnostic AI test automation framework: describe a test flow once,
in one intermediate JSON format, and generate real, runnable code for
**Playwright, Selenium, Cypress, TestNG (Java), or Cucumber** — plus a
plain-English manual test case, a unified pass/fail report across every
tool, and CSV/Excel export.

Every one of those five targets is real, generated, and independently
verified — including against a real, separately-built application (see
[Real-world proof](#real-world-proof) below), not just this project's
own bundled demo site.

## Why

Testing the same user flow across multiple automation stacks normally
means writing (and maintaining) N separate implementations. This
project generates all of them from one source of truth instead — see
[`docs/architecture.md`](docs/architecture.md) for the full reasoning.

## Quick start

```bash
pip install -r requirements.txt && playwright install chromium
npm install
uvicorn backend.main:app --reload
```

Open `http://localhost:8000` — pick an example, pick a framework,
generate, run against the bundled demo site. Full walkthrough,
including how to run TestNG/Cucumber and point this at your own app:
[`docs/getting_started.md`](docs/getting_started.md).

## Documentation

| doc | what's in it |
|---|---|
| [`docs/getting_started.md`](docs/getting_started.md) | install, first generated test, running each of the 5 tools, the UI |
| [`docs/intermediate_format.md`](docs/intermediate_format.md) | the one JSON shape every adapter translates from |
| [`docs/adapters.md`](docs/adapters.md) | what each of the 5 adapters/runners does and how it resolves elements |
| [`docs/locator_hints.md`](docs/locator_hints.md) | the `hint` escape hatch, with two real cases that needed it |
| [`docs/architecture.md`](docs/architecture.md) | pipeline diagram and the reasoning behind the main design decisions |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | every real bug hit while building this, and its fix |
| [`docs/adding_a_new_language.md`](docs/adding_a_new_language.md) | the extension pattern for .NET, JUnit, Robot Framework, Behave — **documented, not built** |

## Real-world proof

Beyond the bundled demo site (`tests/demo_site/`), this framework was
pointed at a real, independently-built application (a separate Supply
Chain Intelligence Platform project) with no changes made to accommodate
it. That run surfaced a genuine bug — a race between `assert_url` and a
Single Page App's async, client-side navigation — which is now fixed
across every affected adapter. Full writeup in
[`docs/troubleshooting.md`](docs/troubleshooting.md#assert_url-failing-right-after-a-real-navigation-happened).
This is the kind of thing a demo against your own toy site can't catch,
and exactly why that proof was worth doing.

## Scope, honestly

Real and tested: Playwright, Selenium, Cypress, TestNG+Java, Cucumber,
the LangGraph-based requirements→intermediate-format generation
pipeline (needs `ANTHROPIC_API_KEY`, less battle-tested than the rest —
see `docs/getting_started.md`), CSV/Excel export, and the FastAPI+JS UI.

Documented as a pattern but **not implemented**: .NET/NUnit/SpecFlow,
JUnit, Robot Framework, Behave, and any other framework not listed
above. An enterprise-grade UI redesign was also explicitly out of scope
for this project. See [`docs/adding_a_new_language.md`](docs/adding_a_new_language.md).
