# Locator Hints — when semantic resolution isn't enough

Every adapter resolves elements through a fallback chain of semantic
strategies first (label, placeholder, aria-label, text content, role —
see `docs/adapters.md` for the per-tool list). That covers most real
markup. `hint` is the escape hatch for the cases it doesn't.

## Supported hint keys

| key | works in | meaning |
|---|---|---|
| `test_id` | all 5 adapters | matches `data-testid="..."` |
| `css` | Playwright, Selenium, Cypress | a raw CSS selector, tried before semantic resolution |
| `reference_image` | Selenium, Cypress | path to a cropped screenshot; triggers OpenCV template matching as the absolute last resort |

A hint is always tried FIRST, never INSTEAD of semantic resolution — if
a hint goes stale (element removed, `data-testid` renamed), resolution
falls through to the normal chain instead of hard-failing. This is
deliberate: a hint should make resolution more reliable, never more
brittle.

```json
{ "type": "button_text", "value": "Submit", "hint": { "css": "#checkout-submit-btn" } }
```

## Two real cases that needed a hint (found during this project's own testing, not hypothetical)

**1. An assertion whose describing text isn't the asserted text.**
`tests/fixtures/form_submission.json`'s final step asserts a
confirmation banner's content, but the banner is *described* as
"confirmation banner" while it actually *displays* "Thanks — we'll be
in touch shortly." Semantic `page_text` resolution would search for an
element whose text IS "confirmation banner" — which doesn't exist. Fix:

```json
{
  "action": "assert_text",
  "target": { "type": "page_text", "value": "confirmation banner", "hint": { "test_id": "confirmation-banner" } },
  "value": "Thanks - we'll be in touch shortly."
}
```

The Cucumber adapter goes further here and phrases this step
differently in the generated `.feature` file
(`the element with test id "confirmation-banner" should show "..."`)
specifically so a hint-based lookup is visible in the readable spec,
not hidden behind a sentence that reads identically either way.

**2. A label with no `for` attribute and no wrapping `<label>`.**
The real Supply Chain Intelligence Platform app's login page
(`examples/scip_login.json`) renders its Username field as a plain
sibling `<label>Username</label>` next to the `<input>` — no `for`
attribute, no nesting. `LabelAssociationStrategy` (which looks for
exactly that association) can't find it. It still resolved correctly
*without* a hint here, because the input also has
`placeholder="Enter username"` and `PlaceholderStrategy` is next in the
`field_description` chain — but if that placeholder hadn't existed,
`hint.css` would have been the fix. This is the general shape of "when
you'll need a hint": an element with no accessible name reachable by
any of aria-label / `<label>` association / placeholder / visible text.

## Visual fallback: when even a CSS hint isn't enough

For an icon-only button or canvas-drawn control with no accessible name
or stable selector at all, `hint.reference_image` (a cropped screenshot
of just that element) triggers OpenCV grayscale template matching
(`cv2.matchTemplate`, 0.8 confidence threshold) against a full-page
screenshot, then resolves the matched region's center point back to a
live DOM element. This only exists for Selenium (Python) and Cypress
(JS, via a Node task shelling out to the same Python matching code) —
see `docs/adapters.md` for why TestNG/Java doesn't have it. It's a real
last resort, not the first thing to reach for: every strategy before it
is cheaper and more robust to minor visual changes (a re-theme, a
slightly different screenshot resolution) than a pixel match is.
