# Adding a New Language / Framework

This project genuinely implements 5 targets (Playwright, Selenium,
Cypress, TestNG+Java, Cucumber — see `docs/adapters.md`). It does
**not** implement .NET/NUnit/SpecFlow, JUnit, Robot Framework, Behave,
or anything else. This doc describes the pattern those would follow if
someone builds them — it's a design guide, not a claim that they exist.
Don't let a name in this doc get mistaken for a shipped feature.

## The two pieces every new target needs

**1. An adapter** (`adapters/base_adapter.py`'s `BaseAdapter`):
`generate(test_def) -> str`, `file_extension`, `generate_filename()`.
Its only job is translating each intermediate-format action
(`docs/intermediate_format.md`) into that language/tool's real API
calls, embedding values safely (see `docs/troubleshooting.md`'s
string-literal entry — use a proper escaper, never naive
interpolation or `repr()`-equivalents).

**2. A locator resolver**, IF the target framework has no built-in
semantic element lookup (most don't — Playwright is the outlier here).
This is genuinely the hard part, and it's per-language by nature (see
`docs/architecture.md`'s "why locator resolution is a separate layer"
section) — you're re-implementing the *design* already proven in
Python (`locator_resolution/strategies/accessibility_tree.py`), JS
(`cypress/support/commands.js`), and Java
(`runners/testng-selenium/src/main/java/com/utf/locator/AccessibilityTreeStrategies.java`),
not sharing code across them:

- `hint.test_id` / `hint.css` tried first
- per-target-type chain of: aria-label, `<label>` association
  (`for` attribute AND nested-input), placeholder, visible text
  content, role attribute (with an implicit-role-to-tag map for
  `button`/`link`/`heading`/`checkbox`/`textbox` etc.)
- visual fallback (`hint.reference_image`) last, if you want full
  parity — Java's runner deliberately skips this (see
  `docs/adapters.md`), so "no visual fallback" is an accepted, honest
  scope boundary for a new language too, not a blocker.

## Worked example: .NET (NUnit or SpecFlow) + Selenium

This is the concrete case actually discussed while building this
project, kept here as the clearest illustration of the pattern:

1. **Locator resolver** (`UtfLocator/SeleniumResolver.cs`): port
   `AccessibilityTreeStrategies.java`'s five strategies to C# using
   Selenium's .NET bindings (`OpenQA.Selenium`). The XPath/CSS
   expressions themselves translate almost directly; the port work is
   language plumbing (interfaces, LINQ vs. streams), not new logic.
2. **Adapter** (`adapters/nunit_selenium_adapter.py` or
   `adapters/specflow_adapter.py`): generate a `[Test]`-attributed NUnit
   class (mirroring `TestNGSeleniumAdapter`'s shape almost 1:1 — TestNG
   and NUnit attributes map closely), or, for SpecFlow, a `.feature`
   file + reusable `[Binding]` step class (mirroring the Cucumber
   adapter's split instead).
3. **`assert_url`**: use NUnit's/Selenium .NET's own polling wait
   (`WebDriverWait` exists in the .NET bindings too) — see
   `docs/troubleshooting.md`'s SPA-navigation entry for why a one-shot
   `driver.Url` check would reintroduce the exact bug already fixed in
   every other adapter.
4. **Runner scaffold**: a `runners/nunit-selenium/` .NET project
   (`dotnet new nunit`), analogous to `runners/testng-selenium/`'s
   Maven project — checked-in project file, no separately-installed
   .NET SDK version pinning beyond what the project file specifies.
5. **Reporting**: NUnit's own `--result` TRX/XML output needs one more
   parser in `reporting/result_parsers/`, converging into the same
   `UnifiedTestResult` (`reporting/unified_report.py`) every other tool
   already does.

## Other frameworks, briefly

- **JUnit 5 + Selenium (Java)**: closest port of all — same JVM, same
  `com.utf.locator.SeleniumResolver` already exists and needs zero
  changes; only the adapter's generated annotations
  (`@Test`/`@BeforeEach` instead of TestNG's `@Test`/`@BeforeMethod`)
  and the Maven Surefire config differ.
- **Robot Framework**: no native project-file/attribute translation
  step like the above — Robot's keyword-driven `.robot` files are
  closer in spirit to Cucumber's Gherkin than to TestNG's imperative
  Java, so a `RobotFrameworkAdapter` would likely follow the Cucumber
  split (generated `.robot` test cases + a hand-written Python keyword
  library using the existing Selenium resolver) rather than the
  self-contained-script shape.
- **Behave (Python + Gherkin)**: nearly identical shape to the Cucumber
  adapter, just emitting Behave's slightly different Gherkin dialect
  and step-matching syntax, backed by a Python step library reusing
  `locator_resolution/selenium_resolver.py` or
  `locator_resolution/playwright_resolver.py` directly (no port needed
  at all, since it's already Python).
