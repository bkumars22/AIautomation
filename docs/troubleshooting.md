# Troubleshooting

Every entry here is a real bug hit and fixed during this project's own
development — kept as a record because each one generalizes to
something you're likely to hit too.

## "No locator strategy matched target ..."

The resolver's error message (all 5 languages produce an equivalent
one) lists every strategy it tried, in order, before giving up. Start
there: it tells you exactly which mechanisms (label, placeholder,
aria-label, text, role) were checked and found nothing. Usually the fix
is either a hint (`docs/locator_hints.md`) or noticing the description
in your intermediate JSON doesn't match the page's actual text/label —
the two real cases in `docs/locator_hints.md` are exactly this.

## `assert_url` failing right after a real navigation happened

**Symptom:** the browser visibly reaches the right URL, but the
generated assertion still fails with "Expected URL to contain X, got
[the old URL]".

**Cause:** a Single Page App doesn't navigate synchronously with the
triggering click when the route change happens after an async call
resolves (e.g. `await apiLogin(...)` then `navigate('/dashboard')` in a
React app). The original `assert_url` codegen checked `page.url` /
`driver.current_url` exactly once, immediately after the click — a race
that a static/server-rendered page never exposes (its navigation is
part of the click itself), which is exactly why this stayed hidden
until this framework was pointed at a real SPA (the SCIP demonstration,
`examples/scip_login.json`) instead of just its own bundled demo site.

**Fix (already applied, all adapters):** every `assert_url` now uses
each tool's native polling assertion — Playwright's
`expect(page).to_have_url(...)`, Selenium/TestNG's `WebDriverWait` +
`EC.url_contains`/`ExpectedConditions.urlContains`, Cucumber's
`page.waitForURL(...)`. Cypress already used `cy.url().should(...)`,
which retries by design, so it was never affected.

If you hit an analogous one-shot-check race somewhere else (e.g. a
custom assertion you add), the fix is the same shape: reach for the
tool's built-in polling/retry primitive instead of a synchronous
snapshot check.

## Generated code has a broken string literal

**Symptom:** a `SyntaxError`/compile error in generated code, only for
specific input values (an apostrophe, an embedded quote).

**Cause:** naively embedding a Python value with `repr()` (or manual
string concatenation in JS/Java) picks a quote character based on the
value's own content — `repr("we'll")` uses double quotes because the
value contains a single quote, which breaks the moment that gets nested
inside an f-string that's *itself* using double quotes.

**Fix:** every adapter embeds values via a `json.dumps()`-based helper
in Python (`_py()`), a proper escaper in Java (`_java_str()`), or
Cucumber Expression string capture in JS — never raw interpolation or
`repr()`. If you extend an adapter, keep using its existing helper.

## Cypress: strategies matching in the wrong priority order

**Cause:** jQuery's `.add()` unions two element sets in *document
order*, not call order — so building a fallback chain with
`.add(labelMatch).add(placeholderMatch)` does not mean "try label
first, then placeholder"; it means "whichever appears first in the
DOM wins," silently breaking intended priority.

**Fix:** `cypress/support/commands.js`'s
`SEMANTIC_STRATEGY_CHAINS_BY_TYPE` explicitly short-circuits through
the chain in order instead of unioning.

## Cypress JSON report mixed into stdout

`cypress run --reporter json` doesn't print a clean JSON document — the
JSON is embedded in otherwise-normal CLI output. Naive `json.loads()`
on the full stdout fails. `reporting/result_parsers/cypress_parser.py`
uses `json.JSONDecoder().raw_decode()` to pull out just the JSON object
starting wherever it begins in the string, ignoring everything else.

## Maven: invalid XML comment

An early `pom.xml` comment's text happened to contain `--`, which is
invalid inside an XML comment (XML forbids `--` anywhere in a comment
body, not just at the boundaries) and fails the build with a parse
error, not a helpful message pointing at the comment. If a Maven build
fails with a raw XML parse error, check comments for a stray `--`
before anything else.

## Maven offline mode failing on a fresh dependency

`./mvnw -o test` (offline) fails the first time a new dependency
(Selenium, TestNG, a specific plugin version) isn't already cached
locally — the error looks like a missing-artifact problem, not an
"offline flag" problem. Drop `-o` for the first run after adding a new
dependency so Maven can actually resolve it; `-o` is fine again once
it's cached.

## Java: a role-tag lookup produces a malformed XPath like `////input...`

**Cause:** `AccessibilityTreeStrategies.IMPLICIT_ROLE_TAGS` originally
stored map values that already included a `//` prefix (e.g.
`"button | //input[@type='button']"`), and the code building the final
XPath *also* prepended `//` per segment — for any multi-segment role
this doubled up into `////`, an invalid path that silently matched
nothing.

**Fix:** map values are plain tag segments with no `//` of their own;
exactly one `//` is prepended per segment by the loop, consistently.

## Java: checkbox/dropdown resolving too loosely

An early version of `SeleniumResolver`'s per-type strategy chains gave
`checkbox_description` and `dropdown_description` the same broad chain
as `field_description` (4 strategies including a text-content
fallback), which is looser than intended and can match an unrelated
element that merely contains matching text. Fixed to the narrower
`[AriaLabel, LabelAssociation]` chain those two target types actually
need, matching the other languages' resolvers.

## `charset=utf-8` missing from a Content-Type header

`http.server.SimpleHTTPRequestHandler`'s default `guess_type()` doesn't
include `charset=utf-8` in the Content-Type it serves, so a browser can
misdecode non-ASCII bytes (an em-dash, in this project's case) even
though the file on disk is valid UTF-8. `tests/demo_site/server.py`
overrides `guess_type()` to force the charset. If you see mojibake
served from a plain Python HTTP server, check this first.
