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

## Try it live

**[Live code-generation demo](https://bkumars22.github.io/AIautomation/)** —
a static page (`webshowcase/`), no install, generates real code for all 5
targets from either an intermediate JSON definition or plain-English
steps (via a rule-based, no-AI parser that runs entirely in your
browser — see [Live demo details](#live-demo-webshowcasegithub-pages)
below for exactly what it can and can't do, and how to embed it on your
own site).

## Quick start (full local install — live "Run" + reports)

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

## Live demo (`webshowcase/`, GitHub Pages)

A fully static site — no backend, no build step — that ports the 5
adapters' code-generation logic to JavaScript (`webshowcase/adapters.js`,
mirroring `adapters/*.py` line-for-line in template shape) so it runs
entirely client-side:

- **Two input modes.** *Plain English*: type steps like a manual test
  case (`Go to /login.` / `Enter "x" into the email field.` / `Verify
  that the confirmation banner is visible.`), and a rule-based parser
  (`webshowcase/parser.js` — **pattern matching, not an LLM**, no API
  key involved anywhere) converts recognized sentences into the
  intermediate format. *Intermediate JSON*: paste/edit the format
  directly, same as the local UI. Every fixture example, including the
  real SCIP one, can be loaded in either mode.
- **What it's honest about not doing.** No "Run" button and no real
  pass/fail results — executing generated Selenium/Playwright/Cypress
  code means launching a real browser, which is server-side work GitHub
  Pages architecturally can't do. Unrecognized plain-English lines are
  reported, never silently dropped or guessed at.
- **Embedding on your own site:** it's self-contained static files with
  no external dependencies, so either `<iframe src="https://bkumars22.github.io/AIautomation/">`
  it directly, or copy the `webshowcase/` folder onto your own host —
  nothing in it assumes a particular domain.
- **Deploying it yourself:** `.github/workflows/pages.yml` deploys
  `webshowcase/` on every push to `main` via the official
  `actions/deploy-pages` action. The one manual step GitHub requires:
  repo Settings → Pages → Build and deployment → Source → **GitHub
  Actions** (can't be done from a workflow file itself).

## Scope, honestly

Real and tested: Playwright, Selenium, Cypress, TestNG+Java, Cucumber,
the LangGraph-based requirements→intermediate-format generation
pipeline (needs `ANTHROPIC_API_KEY`, less battle-tested than the rest —
see `docs/getting_started.md`), CSV/Excel export, the FastAPI+JS UI, and
the static GitHub Pages showcase (`webshowcase/`) including its
rule-based plain-English parser — verified by round-tripping every
fixture (including the real SCIP one) from generated manual-case text
back through the parser with zero unrecognized lines.

Documented as a pattern but **not implemented**: .NET/NUnit/SpecFlow,
JUnit, Robot Framework, Behave, and any other framework not listed
above. An enterprise-grade UI redesign was also explicitly out of scope
for this project. See [`docs/adding_a_new_language.md`](docs/adding_a_new_language.md).
