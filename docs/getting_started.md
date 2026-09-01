# Getting Started

This framework generates runnable test automation code — Playwright,
Selenium, Cypress, TestNG (Java), or Cucumber (Gherkin) — from one
tool-agnostic intermediate test definition. This doc gets you from a
fresh checkout to your first passing generated test.

**Read this framing first:** each generated script embeds an absolute
path back to this checkout (`_FRAMEWORK_ROOT` in the Python adapters,
`sys.path.insert`) so it can import the shared locator resolver. That
means moving or renaming this checkout breaks every previously-generated
script until you regenerate it. If you outgrow that, `pip install -e .`
this project (not currently packaged that way — see
`docs/architecture.md`) and drop the path-injection instead. This is a
one-time setup decision per real project, not a framework limitation.

## 1. Install

```bash
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium

npm install   # Cypress + Cucumber-js + the Node Playwright package
```

## 2. Try it via the CLI (fastest way to see the shape)

```python
import json
from adapters.playwright_adapter import PlaywrightAdapter

test_def = json.load(open("tests/fixtures/login.json"))
print(PlaywrightAdapter().generate(test_def))
```

Swap `PlaywrightAdapter` for `SeleniumAdapter`, `CypressAdapter`,
`TestNGSeleniumAdapter`, or `CucumberAdapter` — same `test_def` in, a
different real script out. That's the whole point of the intermediate
format: see `docs/intermediate_format.md`.

## 3. Try it via the UI

```bash
uvicorn backend.main:app --reload
```

Open `http://localhost:8000`. It auto-starts a small bundled demo site
(see `tests/demo_site/`) so there's something to point generated code
at with zero configuration. Pick an example fixture, pick a framework,
generate, and — for Playwright/Selenium/Cypress — click **Run** to
execute it for real and see PASS/FAIL. Every run is added to a
session-scoped report you can download as CSV or Excel from the
**Reports** section.

**TestNG and Cucumber generate but don't "Run" in the UI** — they're
real, independently-verified runners, but each needs its own
project-level toolchain (Maven; `cucumber-js`) rather than a single
self-contained script, so wiring live execution into a shared backend
process is a materially different (and riskier — concurrent requests
writing into the same Maven source tree) engineering problem than the
in-process script runner the other three use. Run them as shown below
instead.

## 4. Run each tool for real, against the bundled demo site

Start the demo site once (or let the UI's own instance run — pick one):

```python
from tests.demo_site.server import DemoSiteServer
with DemoSiteServer(port=8199) as base_url:
    ...  # keep this process alive while you run tests below
```

**Playwright / Selenium** — generated scripts are standalone AND
pytest-compatible:

```bash
TEST_BASE_URL=http://127.0.0.1:8199 python generated/test_user_can_log_in_with_valid_credentials.py
# or, for a structured report:
TEST_BASE_URL=http://127.0.0.1:8199 pytest generated/ --json-report
```

**Cypress**:

```bash
npx cypress run --spec "generated/*.cy.js" --config baseUrl=http://127.0.0.1:8199
```

**TestNG (Java)** — generated classes live in
`runners/testng-selenium/src/test/java/com/utf/generated/`:

```bash
cd runners/testng-selenium
TEST_BASE_URL=http://127.0.0.1:8199 ./mvnw test
```

**Cucumber** — generated `.feature` files go in `generated/`, and are
run against the hand-written step library in `cucumber/`:

```bash
TEST_BASE_URL=http://127.0.0.1:8199 npx cucumber-js
```

## 5. Point it at your own app

Set `TEST_BASE_URL` (or the UI's base-URL field) to your app instead of
the demo site. Write your own intermediate JSON (see
`docs/intermediate_format.md`) describing the flow you want tested. If
semantic resolution can't find an element (see
`docs/locator_hints.md` for when that happens and how to fix it with a
`hint`), the resolver's error message tells you exactly which
strategies it tried, in order.

## 6. Generating from plain-English requirements (optional)

`generation/intermediate_generator.py` calls an LLM (Anthropic) to turn
free-text requirements into an intermediate definition, wired through
`graph/generation_graph.py` (LangGraph). This needs `ANTHROPIC_API_KEY`
set — it was not exercised end-to-end in this project's own testing
(no key was available in the dev environment it was built in), so treat
it as less battle-tested than everything else in this doc, which was.
