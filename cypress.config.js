const { defineConfig } = require("cypress");
const { matchTemplate } = require("./locator_resolution/visual_match_task");

module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.TEST_BASE_URL || "http://localhost:8000",
    specPattern: "generated/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
    setupNodeEvents(on, _config) {
      // Visual fallback shells out to the SAME OpenCV logic the Selenium
      // adapter uses (locator_resolution/strategies/visual_fallback.py) via
      // a Cypress "task" — Node has no first-class OpenCV binding as
      // mature/simple as Python's, and reusing the already-proven Python
      // implementation is more honest than a from-scratch reimplementation
      // in JS. See locator_resolution/visual_match_task.js's docstring.
      on("task", { matchTemplate });
    },
  },
});
