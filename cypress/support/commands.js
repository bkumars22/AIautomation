/**
 * cy.resolveTarget(target) — Cypress's version of the semantic locator
 * fallback chain. Cypress, like Selenium, has no built-in semantic-
 * label-to-selector translation (that's Playwright's own get_by_*
 * primitives, see locator_resolution/playwright_resolver.py's docstring
 * for why this is genuinely harder here), so this mirrors the exact same
 * strategies as locator_resolution/strategies/accessibility_tree.py,
 * reimplemented in JS since Cypress specs run in the browser/Node
 * boundary Cypress itself controls.
 */

function ciIncludes(haystack, needle) {
  return (haystack || "").toLowerCase().includes((needle || "").toLowerCase());
}

function ownText($el) {
  return $el.clone().children().remove().end().text().trim();
}

function findByAriaLabel(value) {
  return Cypress.$("[aria-label]").filter((_, el) => ciIncludes(Cypress.$(el).attr("aria-label"), value));
}

function findByLabelAssociation(value) {
  const labels = Cypress.$("label").filter((_, el) => ciIncludes(Cypress.$(el).text(), value));
  let result = Cypress.$();
  labels.each((_, label) => {
    const $label = Cypress.$(label);
    const forId = $label.attr("for");
    if (forId) {
      const byId = Cypress.$(`#${forId}`);
      if (byId.length) {
        result = byId;
        return false;
      }
    }
    const nested = $label.find("input, select, textarea");
    if (nested.length) {
      result = nested.first();
      return false;
    }
  });
  return result;
}

function findByPlaceholder(value) {
  return Cypress.$("[placeholder]").filter((_, el) => ciIncludes(Cypress.$(el).attr("placeholder"), value));
}

function findByTextContent(value) {
  return Cypress.$("*")
    .filter((_, el) => ciIncludes(ownText(Cypress.$(el)), value))
    .first();
}

const IMPLICIT_ROLE_SELECTORS = {
  button: 'button, input[type="button"], input[type="submit"]',
  link: "a",
  heading: "h1, h2, h3, h4, h5, h6",
  checkbox: 'input[type="checkbox"]',
  textbox: 'input[type="text"], input[type="email"], textarea',
};

function findByRole(role, name) {
  const selector = IMPLICIT_ROLE_SELECTORS[role] || `[role="${role}"]`;
  return Cypress.$(selector).filter((_, el) => {
    const $el = Cypress.$(el);
    return ciIncludes($el.attr("aria-label"), name) || ciIncludes($el.text(), name);
  });
}

// Chains, not unions: tried IN ORDER, first non-empty match wins. jQuery's
// .add() merges sets in DOCUMENT order rather than call order, which
// silently breaks strategy priority whenever two DIFFERENT elements match
// two DIFFERENT strategies (a real bug found while testing this adapter:
// .add()-ing every strategy together and taking .first() picked whichever
// matching element happened to sit first in the DOM, not the one the
// highest-priority strategy found).
const SEMANTIC_STRATEGY_CHAINS_BY_TYPE = {
  field_description: [findByAriaLabel, findByLabelAssociation, findByPlaceholder, findByTextContent],
  checkbox_description: [findByAriaLabel, findByLabelAssociation],
  dropdown_description: [findByAriaLabel, findByLabelAssociation],
  button_text: [findByTextContent, findByAriaLabel],
  link_text: [findByTextContent, findByAriaLabel],
  page_text: [findByTextContent],
};

function resolveSemanticChain(target) {
  if (target.type === "element_role") {
    return findByRole(target.role, target.name);
  }
  const chain = SEMANTIC_STRATEGY_CHAINS_BY_TYPE[target.type] || [];
  for (const strategyFn of chain) {
    const found = strategyFn(target.value);
    if (found && found.length) return found;
  }
  return Cypress.$();
}

Cypress.Commands.add("resolveTarget", (target) => {
  const hint = target.hint || {};

  if (hint.test_id) {
    const byTestId = Cypress.$(`[data-testid="${hint.test_id}"]`);
    if (byTestId.length) return cy.wrap(byTestId.first());
  }
  if (hint.css) {
    const byCss = Cypress.$(hint.css);
    if (byCss.length) return cy.wrap(byCss.first());
  }

  const found = resolveSemanticChain(target);
  if (found && found.length) {
    return cy.wrap(found.first());
  }

  if (hint.reference_image) {
    const screenshotName = "__visual_fallback_tmp";
    return cy.screenshot(screenshotName, { capture: "fullPage" }).then(() => {
      const screenshotPath = `cypress/screenshots/${Cypress.spec.name}/${screenshotName}.png`;
      return cy
        .task("matchTemplate", { screenshotPath, referenceImagePath: hint.reference_image })
        .then((match) => {
          if (!match) {
            throw new Error(`No locator strategy matched target ${JSON.stringify(target)} (visual fallback found nothing above threshold either)`);
          }
          return cy.document().then((doc) => {
            const el = doc.elementFromPoint(match.center_x, match.center_y);
            if (!el) throw new Error("Visual match resolved to a point with no element");
            return cy.wrap(Cypress.$(el));
          });
        });
    });
  }

  throw new Error(
    `No locator strategy matched target ${JSON.stringify(target)}. See docs/locator_hints.md for how to add a hint for ambiguous elements.`
  );
});
