/**
 * Cucumber World: one real Playwright browser/page per scenario. BASE_URL
 * comes from TEST_BASE_URL (default http://localhost:8000), same
 * convention as every other generated runner in this framework.
 */
const { setWorldConstructor, Before, After } = require("@cucumber/cucumber");
const { chromium } = require("playwright");

const BASE_URL = process.env.TEST_BASE_URL || "http://localhost:8000";

class PlaywrightWorld {
  async init() {
    this.browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
    this.page = await this.browser.newPage();
  }

  async cleanup() {
    if (this.browser) await this.browser.close();
  }
}

setWorldConstructor(PlaywrightWorld);

Before(async function () {
  await this.init();
});

After(async function () {
  await this.cleanup();
});

module.exports = { BASE_URL };
