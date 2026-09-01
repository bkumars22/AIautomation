import { ADAPTERS, generateManualCase } from "./adapters.js";
import { FIXTURES } from "./fixtures.js";
import { parsePlainEnglish, SUPPORTED_PHRASINGS } from "./parser.js";

const fixtureSelect = document.getElementById("fixture-select");
const loadFixtureBtn = document.getElementById("load-fixture-btn");
const inputText = document.getElementById("input-text");
const generateBtn = document.getElementById("generate-btn");
const downloadBtn = document.getElementById("download-btn");
const generateStatus = document.getElementById("generate-status");
const outputPanel = document.getElementById("output-panel");
const manualCaseEl = document.getElementById("manual-case");
const generatedCodeEl = document.getElementById("generated-code");
const plainHint = document.getElementById("plain-hint");
const jsonHint = document.getElementById("json-hint");
const showPhrasingsBtn = document.getElementById("show-phrasings-btn");
const phrasingsList = document.getElementById("phrasings-list");
const parsePreview = document.getElementById("parse-preview");
const parsedJsonEl = document.getElementById("parsed-json");
const skippedLinesEl = document.getElementById("skipped-lines");

let lastGenerated = null; // { code, filename }

for (const fixture of FIXTURES) {
  const option = document.createElement("option");
  option.value = fixture.name;
  option.textContent = fixture.label;
  fixtureSelect.appendChild(option);
}

for (const phrasing of SUPPORTED_PHRASINGS) {
  const li = document.createElement("li");
  li.textContent = phrasing;
  phrasingsList.appendChild(li);
}

showPhrasingsBtn.addEventListener("click", () => {
  phrasingsList.hidden = !phrasingsList.hidden;
});

function inputMode() {
  return document.querySelector('input[name="input-mode"]:checked').value;
}

function loadFixture(name) {
  const fixture = FIXTURES.find((f) => f.name === name) || FIXTURES[0];
  inputText.value = inputMode() === "json"
    ? JSON.stringify(fixture.def, null, 2)
    : generateManualCase(fixture.def);
}

document.querySelectorAll('input[name="input-mode"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const isJson = inputMode() === "json";
    jsonHint.hidden = !isJson;
    plainHint.hidden = isJson;
    phrasingsList.hidden = true;
    loadFixture(fixtureSelect.value || FIXTURES[0].name);
  });
});

loadFixtureBtn.addEventListener("click", () => loadFixture(fixtureSelect.value));

function selectedTool() {
  return document.querySelector('input[name="tool"]:checked').value;
}

function resolveTestDef() {
  if (inputMode() === "json") {
    parsePreview.hidden = true;
    return JSON.parse(inputText.value);
  }

  const { testDef, skipped } = parsePlainEnglish(inputText.value);
  parsePreview.hidden = false;
  parsedJsonEl.textContent = JSON.stringify(testDef, null, 2);
  if (skipped.length > 0) {
    skippedLinesEl.hidden = false;
    skippedLinesEl.className = "no-run-note warning";
    skippedLinesEl.innerHTML =
      `<strong>${skipped.length} line(s) not recognized</strong> — skipped, not guessed at:<br>` +
      skipped.map((s) => `&bull; "${escapeHtml(s.line)}" — ${escapeHtml(s.reason)}`).join("<br>");
  } else {
    skippedLinesEl.hidden = true;
  }
  return testDef;
}

generateBtn.addEventListener("click", () => {
  outputPanel.hidden = true;
  downloadBtn.hidden = true;

  let testDef;
  try {
    testDef = resolveTestDef();
  } catch (e) {
    generateStatus.textContent = "Error: " + e.message;
    return;
  }

  const tool = selectedTool();
  const adapter = ADAPTERS[tool];
  try {
    const code = adapter.generate(testDef);
    const filename = adapter.filename(testDef);
    manualCaseEl.textContent = generateManualCase(testDef);
    generatedCodeEl.textContent = code;
    outputPanel.hidden = false;
    generateStatus.textContent = "Done.";
    lastGenerated = { code, filename };
    downloadBtn.hidden = false;
  } catch (e) {
    generateStatus.textContent = "Error: " + e.message;
  }
});

downloadBtn.addEventListener("click", () => {
  if (!lastGenerated) return;
  const blob = new Blob([lastGenerated.code], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = lastGenerated.filename;
  a.click();
  URL.revokeObjectURL(url);
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

loadFixture(FIXTURES[0].name);
