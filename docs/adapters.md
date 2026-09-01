# Adapters and Runners

Five targets, one intermediate test definition (`docs/intermediate_format.md`).
All five are real, generated code — none is a stub. Four of the five
(everything but Cucumber) generate a complete, self-contained script per
test; Cucumber generates a business-readable scenario against a shared,
hand-written step library, because that's the idiomatic shape for that
tool (see its own section below).

| Adapter | Language | File | Runs via |
|---|---|---|---|
| Playwright | Python | `adapters/playwright_adapter.py` | standalone script, or pytest |
| Selenium | Python | `adapters/selenium_adapter.py` | standalone script, or pytest |
| Cypress | JavaScript | `adapters/cypress_adapter.py` | `cypress run` |
| TestNG + Selenium | Java | `adapters/testng_selenium_adapter.py` | Maven (`./mvnw test`) |
| Cucumber + Playwright | Gherkin | `adapters/cucumber_adapter.py` | `cucumber-js` |

## Playwright (Python)

The "easy case." Playwright's `get_by_role` / `get_by_label` /
`get_by_text` already query the browser's accessibility tree, so
`locator_resolution/playwright_resolver.py` only adds a small
per-target-type fallback chain on top (e.g. `field_description` tries
label, then placeholder, then plain text) — see that file's docstring.
Generated function signature `test_{slug}(page)` is both directly
runnable (`if __name__ == "__main__"` block launches its own browser)
and pytest/`pytest-playwright`-compatible (accepts the `page` fixture).

`assert_url` uses `expect(page).to_have_url(re.compile(...))`, which
polls — see `docs/troubleshooting.md`'s SPA-navigation entry for why a
one-shot `page.url` check is a real bug, not a style choice.

## Selenium (Python)

Selenium has no built-in semantic-label-to-selector translation, so
`locator_resolution/selenium_resolver.py` +
`locator_resolution/strategies/accessibility_tree.py` do the actual
work: `AriaLabelStrategy`, `LabelAssociationStrategy` (`<label for=...>`
or a nested `<input>`), `PlaceholderStrategy`, `TextContentStrategy`,
`RoleAttributeStrategy`. `locator_resolution/strategies/visual_fallback.py`
is the last resort — OpenCV template matching against a
`hint.reference_image`, only activates when explicitly hinted (see
`docs/locator_hints.md`). Generated function `test_{slug}(driver)`
mirrors the Playwright adapter's dual-purpose shape, backed by the
`driver` fixture in the project root's `conftest.py`.

`assert_url` uses `WebDriverWait(driver, 5).until(EC.url_contains(...))`
— same polling reasoning as Playwright's `expect`.

## Cypress (JavaScript)

Generates a `.cy.js` spec calling a custom `cy.resolveTarget()` command
(`cypress/support/commands.js`), which runs the same accessibility-tree
strategy chains as Selenium's, ported to jQuery-based DOM queries run
inside the Cypress command chain (`SEMANTIC_STRATEGY_CHAINS_BY_TYPE` —
note this is NOT `.add()`-based; see `docs/troubleshooting.md` for why
that matters). Visual fallback shells out to
`scripts/visual_match_cli.py` via a Cypress Node task
(`cypress.config.js`) rather than reimplementing OpenCV matching in JS.

`assert_url` uses `cy.url().should("include", ...)`, which already
retries by Cypress's own design — nothing needed changing here for the
SPA-timing issue that affected the other four adapters.

## TestNG + Selenium (Java)

Proves the intermediate format targets a JVM toolchain, not just
Python/JS. Generated classes live in
`runners/testng-selenium/src/test/java/com/utf/generated/` and import
`com.utf.locator.SeleniumResolver` (`runners/testng-selenium/src/main/java/com/utf/locator/`),
this language's own port of the accessibility-tree strategies. **Known,
intentional scope gap: no visual fallback for Java** — porting OpenCV
matching a third time wasn't worth it for this project; if you need it,
see `docs/adding_a_new_language.md`'s pattern.

`assert_url` uses `new WebDriverWait(driver, Duration.ofSeconds(5)).until(ExpectedConditions.urlContains(...))`.

Run with `./mvnw test` from `runners/testng-selenium/` (the wrapper is
checked in — see `.mvn/wrapper/maven-wrapper.properties` — so a working
JDK is all you need, no separately-installed Maven).

## Cucumber + Playwright (Gherkin)

Structurally different from the other four on purpose: Cucumber's whole
value proposition is a business-readable spec backed by a REUSABLE step
library, not per-test generated glue code. `CucumberAdapter.generate()`
produces ONLY a `.feature` file — no step definitions are ever
generated. The hand-written, generic step library lives in
`cucumber/step_definitions/steps.js` and covers every action/target-type
phrasing the adapter can produce, resolving elements via
`locator_resolution/playwright_resolver.js` (a JS port of the Python
Playwright resolver). `cucumber/support/world.js` gives each scenario
its own real Playwright browser/page.

Step phrasing is deliberately literal about a hint-based lookup (e.g.
`the element with test id "confirmation-banner" should show "..."`)
rather than reading identically to a description-based assertion — for
a spec meant to be read by non-engineers, hiding *how* an element was
found seemed less honest than a slightly more mechanical sentence.

`assert_url` uses `page.waitForURL(...)`, matching the other three
Selenium/Playwright-family fixes.

## What's real vs. what's documented-only

All five above are generated, run, and verified against both the
bundled demo site (`tests/demo_site/`) and a real, independently-built
app (see `examples/scip_login.json` and
`docs/troubleshooting.md`'s SPA-navigation entry, found via that real
run). TestNG and Cucumber additionally get a demonstration of the
underlying idea for other languages/runners (.NET/NUnit, JUnit, Robot
Framework, Behave) — see `docs/adding_a_new_language.md` for that
pattern, explicitly NOT implemented in this project.
