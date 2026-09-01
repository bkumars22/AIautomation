/**
 * Generic, reusable step library -- the idiomatic Cucumber shape (see
 * adapters/cucumber_adapter.py's docstring). Every phrase here is
 * hand-written ONCE and matches generated .feature files via Cucumber
 * Expressions; generation never produces step definitions, only scenarios.
 */
const assert = require("assert");
const { Given, When, Then } = require("@cucumber/cucumber");
const { resolve } = require("../../locator_resolution/playwright_resolver");
const { BASE_URL } = require("../support/world");

Given("the user navigates to {string}", async function (path) {
  await this.page.goto(BASE_URL + path);
});

When("the user enters {string} into the {string} field", async function (value, description) {
  const locator = await resolve(this.page, { type: "field_description", value: description });
  await locator.fill(value);
});

When("the user clicks the {string} button", async function (text) {
  const locator = await resolve(this.page, { type: "button_text", value: text });
  await locator.click();
});

When("the user clicks the {string} link", async function (text) {
  const locator = await resolve(this.page, { type: "link_text", value: text });
  await locator.click();
});

When("the user clicks the {word} named {string}", async function (role, name) {
  const locator = await resolve(this.page, { type: "element_role", role, name });
  await locator.click();
});

When("the user selects {string} from the {string} dropdown", async function (option, description) {
  const locator = await resolve(this.page, { type: "dropdown_description", value: description });
  await locator.selectOption({ label: option });
});

When("the user checks the {string} checkbox", async function (description) {
  const locator = await resolve(this.page, { type: "checkbox_description", value: description });
  await locator.check();
});

When("the user unchecks the {string} checkbox", async function (description) {
  const locator = await resolve(this.page, { type: "checkbox_description", value: description });
  await locator.uncheck();
});

Then("the user should see {string}", async function (description) {
  const locator = await resolve(this.page, { type: "page_text", value: description });
  assert.ok(await locator.isVisible(), `Expected "${description}" to be visible`);
});

Then("the user should see the {word} named {string}", async function (role, name) {
  const locator = await resolve(this.page, { type: "element_role", role, name });
  assert.ok(await locator.isVisible(), `Expected ${role} "${name}" to be visible`);
});

Then("the {string} should show {string}", async function (description, expected) {
  const locator = await resolve(this.page, { type: "page_text", value: description });
  const actual = await locator.textContent();
  assert.ok(actual.includes(expected), `Expected text "${expected}", got: ${actual}`);
});

Then("the element with test id {string} should show {string}", async function (testId, expected) {
  const locator = await resolve(this.page, { type: "page_text", value: testId, hint: { test_id: testId } });
  const actual = await locator.textContent();
  assert.ok(actual.includes(expected), `Expected text "${expected}", got: ${actual}`);
});

Then("the URL should contain {string}", async function (path) {
  assert.ok(this.page.url().includes(path), `Expected URL to contain "${path}", got: ${this.page.url()}`);
});
