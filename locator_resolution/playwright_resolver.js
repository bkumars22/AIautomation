/**
 * JS port of locator_resolution/playwright_resolver.py, for the
 * Cucumber+Playwright runner (cucumber/). Same reasoning as the Python
 * version: Playwright's own getByRole/getByLabel/getByText already do
 * accessibility-tree-based semantic lookup, so this only adds the same
 * small per-type fallback chain on top, not a from-scratch resolver.
 */

class LocatorResolutionError extends Error {}

function hintCandidates(page, hint) {
  const candidates = [];
  if (hint.test_id) candidates.push(["hint_test_id", () => page.getByTestId(hint.test_id)]);
  if (hint.css) candidates.push(["hint_css", () => page.locator(hint.css)]);
  return candidates;
}

function semanticCandidates(page, target) {
  const { type, value } = target;
  if (type === "element_role") {
    return [["role", () => page.getByRole(target.role, { name: target.name })]];
  }
  if (["field_description", "checkbox_description", "dropdown_description"].includes(type)) {
    return [
      ["label", () => page.getByLabel(value)],
      ["placeholder", () => page.getByPlaceholder(value)],
      ["text", () => page.getByText(value)],
    ];
  }
  if (type === "button_text") {
    return [
      ["role_button", () => page.getByRole("button", { name: value })],
      ["text", () => page.getByText(value)],
    ];
  }
  if (type === "link_text") {
    return [
      ["role_link", () => page.getByRole("link", { name: value })],
      ["text", () => page.getByText(value)],
    ];
  }
  if (type === "page_text") {
    return [["text", () => page.getByText(value)]];
  }
  throw new LocatorResolutionError(`Unknown target type: ${type}`);
}

async function resolve(page, target) {
  const candidates = [...hintCandidates(page, target.hint || {}), ...semanticCandidates(page, target)];
  const tried = [];
  for (const [name, makeLocator] of candidates) {
    const locator = makeLocator();
    try {
      if ((await locator.count()) > 0) return locator.first();
    } catch (e) {
      tried.push(`${name} (error: ${e.message})`);
      continue;
    }
    tried.push(name);
  }
  throw new LocatorResolutionError(
    `No locator strategy matched target ${JSON.stringify(target)}. Tried: ${tried}. See docs/locator_hints.md.`
  );
}

module.exports = { resolve, LocatorResolutionError };
