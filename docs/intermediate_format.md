# Intermediate Test Definition Format — v1 design

This is the ONE tool-agnostic JSON shape the AI generation step produces.
Every adapter (Selenium, Playwright, Cypress) translates from this same
shape — the AI never sees Selenium/Playwright/Cypress syntax.

Validated against three real scenarios below: login, a form submission
with a dropdown and checkbox, and site navigation with a URL assertion.

## Top-level shape

```json
{
  "test_name": "string, required",
  "description": "string, optional — used by manual case generation",
  "steps": [ /* Step, in execution order */ ]
}
```

## Step shape

```json
{
  "action": "navigate | fill | click | select | check | uncheck | assert_visible | assert_text | assert_url",
  "target": { "type": "...", "value": "...", "role": "...", "name": "...", "hint": { } },
  "value": "string, required for: fill, select, assert_text, assert_url"
}
```

`target` is required on every action except `assert_url` (which only needs `value`).

## `target.type` — the semantic vocabulary

| type | meaning | used by |
|---|---|---|
| `url` | a relative or absolute URL | `navigate` |
| `field_description` | plain-English label of an input, e.g. "email input field" | `fill` |
| `button_text` | visible text on a button | `click` |
| `link_text` | visible text of a link | `click` |
| `checkbox_description` | plain-English label of a checkbox | `check`, `uncheck` |
| `dropdown_description` | plain-English label of a `<select>` | `select` |
| `element_role` | accessibility role + accessible name (most robust when known) | any interactive action |
| `page_text` | arbitrary visible text anywhere on the page | `assert_visible`, `assert_text` |

`element_role` shape: `{"type": "element_role", "role": "button", "name": "Sign In"}` — maps
directly to Playwright's `get_by_role`, and is what the accessibility-tree
locator strategy resolves toward for Selenium/Cypress too. Prefer this
type when the generator can confidently infer a role; the plain
`*_description`/`*_text` types exist for the more common case where it
can't and a human-readable description is all that's available.

## The `hint` escape hatch

Every `target` may optionally carry a `hint` object to help locator
resolution when semantic matching is genuinely ambiguous (see
`docs/locator_hints.md`, written once real failure cases exist from
adapter testing):

```json
{ "type": "button_text", "value": "Submit", "hint": { "css": "#checkout-submit-btn" } }
```

`hint` keys are resolver-specific (`css`, `xpath`, `test_id`, ...) and are
tried BEFORE the semantic fallback chain, never instead of it — a stale
hint degrades gracefully to normal resolution rather than hard-failing.

## Validation: three real scenarios

### 1. Login (`tests/fixtures/login.json`)
navigate → fill × 2 → click → assert_visible. Exercises the base case
from the original design sketch unchanged.

### 2. Form submission (`tests/fixtures/form_submission.json`)
navigate → fill × 2 → select → check → click → assert_text. Exercises
`select` and `check`, and asserting specific text (not just visibility)
after submit — the dropdown/checkbox actions the login scenario alone
doesn't cover.

### 3. Navigation (`tests/fixtures/navigation.json`)
navigate → click (`link_text`) → assert_url → assert_visible
(`element_role`). Exercises `link_text` as distinct from `button_text`,
`assert_url`, and the `element_role` target type end-to-end.

All three validate that every action/target-type combination needed for
common web-app testing round-trips through one identical schema with no
scenario-specific special-casing required.
