const fixtureSelect = document.getElementById("fixture-select");
const loadFixtureBtn = document.getElementById("load-fixture-btn");
const jsonTextarea = document.getElementById("intermediate-json");
const generateBtn = document.getElementById("generate-btn");
const generateStatus = document.getElementById("generate-status");
const outputPanel = document.getElementById("output-panel");
const manualCaseEl = document.getElementById("manual-case");
const generatedCodeEl = document.getElementById("generated-code");
const runBtn = document.getElementById("run-btn");
const runStatus = document.getElementById("run-status");
const runResultEl = document.getElementById("run-result");
const runUnsupportedEl = document.getElementById("run-unsupported");
const downloadCsvBtn = document.getElementById("download-csv-btn");
const downloadExcelBtn = document.getElementById("download-excel-btn");
const exportStatus = document.getElementById("export-status");

const RUNNABLE_TOOLS = new Set(["playwright", "selenium", "cypress"]);

let fixturesByName = {};

async function loadFixtureList() {
  const resp = await fetch("/api/fixtures");
  const data = await resp.json();
  for (const fixture of data.fixtures) {
    fixturesByName[fixture.name] = fixture.intermediate_def;
    const option = document.createElement("option");
    option.value = fixture.name;
    option.textContent = fixture.name;
    fixtureSelect.appendChild(option);
  }
}

loadFixtureBtn.addEventListener("click", () => {
  const name = fixtureSelect.value;
  if (!name) return;
  jsonTextarea.value = JSON.stringify(fixturesByName[name], null, 2);
});

function selectedTool() {
  return document.querySelector('input[name="tool"]:checked').value;
}

generateBtn.addEventListener("click", async () => {
  generateStatus.textContent = "Generating...";
  outputPanel.hidden = true;
  runResultEl.hidden = true;

  let intermediateDef;
  try {
    intermediateDef = JSON.parse(jsonTextarea.value);
  } catch (e) {
    generateStatus.textContent = "Invalid JSON: " + e.message;
    return;
  }

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intermediate_def: intermediateDef, target_tool: selectedTool() }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      generateStatus.textContent = "Error: " + (data.detail || resp.statusText);
      return;
    }
    manualCaseEl.textContent = data.manual_test_case;
    generatedCodeEl.textContent = data.generated_code;
    outputPanel.hidden = false;
    generateStatus.textContent = "Done.";

    const runnable = RUNNABLE_TOOLS.has(selectedTool());
    runBtn.hidden = !runnable;
    runUnsupportedEl.hidden = runnable;
  } catch (e) {
    generateStatus.textContent = "Request failed: " + e.message;
  }
});

runBtn.addEventListener("click", async () => {
  runStatus.textContent = "Running against the demo site (this launches a real browser, may take a few seconds)...";
  runResultEl.hidden = true;

  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool: selectedTool(), code: generatedCodeEl.textContent }),
    });
    const data = await resp.json();
    runStatus.textContent = "";
    runResultEl.hidden = false;
    runResultEl.className = "run-result " + (data.status === "passed" ? "passed" : "failed");
    runResultEl.innerHTML = `
      <strong>${data.status.toUpperCase()}</strong> — ${data.test_name} (${data.tool_used}, ${data.duration_ms}ms)
      ${data.error_message ? `<pre>${escapeHtml(data.error_message)}</pre>` : ""}
    `;
  } catch (e) {
    runStatus.textContent = "Request failed: " + e.message;
  }
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function downloadExport(path, filename) {
  exportStatus.textContent = "Preparing download...";
  try {
    const resp = await fetch(path);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      exportStatus.textContent = "Error: " + (data.detail || resp.statusText);
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    exportStatus.textContent = "Downloaded.";
  } catch (e) {
    exportStatus.textContent = "Request failed: " + e.message;
  }
}

downloadCsvBtn.addEventListener("click", () => downloadExport("/api/export/csv", "test_report.csv"));
downloadExcelBtn.addEventListener("click", () => downloadExport("/api/export/excel", "test_report.xlsx"));

loadFixtureList();

// ---------------------------------------------------------------------
// Document upload, batch generation, and audit history (/api/audit/*).
// ---------------------------------------------------------------------

const docUploadInput = document.getElementById("doc-upload-input");
const docUploadFramework = document.getElementById("doc-upload-framework");
const docUploadBtn = document.getElementById("doc-upload-btn");
const docUploadStatus = document.getElementById("doc-upload-status");
const docUploadResults = document.getElementById("doc-upload-results");
const scenarioListEl = document.getElementById("scenario-list");
const downloadAllManualBtn = document.getElementById("download-all-manual-btn");
const downloadAllAutomatedBtn = document.getElementById("download-all-automated-btn");
const refreshHistoryBtn = document.getElementById("refresh-history-btn");
const historyTableBody = document.querySelector("#audit-history-table tbody");

let currentSessionId = null;

docUploadBtn.addEventListener("click", async () => {
  const file = docUploadInput.files[0];
  if (!file) {
    docUploadStatus.textContent = "Choose a file first.";
    return;
  }

  docUploadStatus.textContent = "Uploading and generating (this calls an LLM, may take a while)...";
  docUploadResults.hidden = true;
  currentSessionId = null;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("framework", docUploadFramework.value);

  try {
    const resp = await fetch("/api/audit/upload", { method: "POST", body: formData });
    const data = await resp.json();
    if (!resp.ok) {
      docUploadStatus.textContent = "Error: " + (data.detail || resp.statusText);
      return;
    }

    currentSessionId = data.session_id;
    renderScenarioList(data.tests);
    docUploadResults.hidden = false;
    docUploadStatus.textContent = `Done — ${data.tests.length} scenario(s) found.`;
    loadAuditHistory();
  } catch (e) {
    docUploadStatus.textContent = "Request failed: " + e.message;
  }
});

function renderScenarioList(tests) {
  scenarioListEl.innerHTML = "";
  for (const test of tests) {
    const card = document.createElement("div");
    card.className = "scenario-card";
    card.innerHTML = `
      <h4>${escapeHtml(test.scenario_name)}</h4>
      <details>
        <summary>Manual test case</summary>
        <pre>${escapeHtml(test.manual_test_case)}</pre>
      </details>
      <details>
        <summary>Generated code (${escapeHtml(test.framework)})</summary>
        <pre>${escapeHtml(test.automated_code)}</pre>
      </details>
    `;
    scenarioListEl.appendChild(card);
  }
}

downloadAllManualBtn.addEventListener("click", () => {
  if (currentSessionId == null) return;
  downloadExport(`/api/audit/download/manual/${currentSessionId}`, "manual_test_cases.docx");
});

downloadAllAutomatedBtn.addEventListener("click", () => {
  if (currentSessionId == null) return;
  downloadExport(`/api/audit/download/automated/${currentSessionId}`, "automated_tests.zip");
});

async function loadAuditHistory() {
  try {
    const resp = await fetch("/api/audit/history");
    const data = await resp.json();
    historyTableBody.innerHTML = "";
    for (const session of data.sessions) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${escapeHtml(new Date(session.uploaded_at).toLocaleString())}</td>
        <td>${escapeHtml(session.uploaded_filename)}</td>
        <td>${escapeHtml(session.framework)}</td>
        <td>${session.scenario_count}</td>
        <td><button class="secondary" data-session-id="${session.id}" data-kind="manual">Manual</button>
            <button class="secondary" data-session-id="${session.id}" data-kind="automated">Automated</button></td>
      `;
      historyTableBody.appendChild(row);
    }
    historyTableBody.querySelectorAll("button[data-session-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-session-id");
        const kind = btn.getAttribute("data-kind");
        const filename = kind === "manual" ? "manual_test_cases.docx" : "automated_tests.zip";
        downloadExport(`/api/audit/download/${kind}/${id}`, filename);
      });
    });
  } catch (e) {
    docUploadStatus.textContent = "Failed to load audit history: " + e.message;
  }
}

refreshHistoryBtn.addEventListener("click", loadAuditHistory);

loadAuditHistory();
