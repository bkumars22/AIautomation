# Document Upload, Batch Generation & Audit History

Upload a Jira story export, business requirements doc, or general
requirements document (PDF, DOCX, TXT, or MD); the system finds every
distinct testable scenario in it, generates a manual test case and
automated code for each, and keeps a persistent local audit trail of
every session. Fully local — same bring-your-own-key model as the rest
of the generation pipeline (`docs/getting_started.md`), no hosted
infrastructure, no external database.

## Requirements

Needs `ANTHROPIC_API_KEY` set on the backend process — scenario
extraction (turning a document into a list of distinct testable
behaviors) is a real LLM call, same as the existing free-text
requirements pipeline. Without it, `/api/audit/upload` returns a clear
422 error naming the missing key rather than failing silently or
fabricating scenarios.

## How it works

```
uploaded file (PDF/DOCX/TXT/MD)
        |
        v  document_upload/extractor.py — plain text extraction
        v
document text
        |
        v  document_upload/scenario_extractor.py — LLM call
        v
list of {scenario_name, description, acceptance_criteria}
        |
        v  document_upload/batch_generator.py, per scenario:
        v    generation/intermediate_generator.py (existing, unmodified)
        v    generation/manual_case_generator.py  (existing, unmodified)
        v    one of the 5 existing adapters        (existing, unmodified)
        v
{scenario_name, manual_test_case, automated_code, framework, intermediate_json}
        |
        v  document_upload/audit_db.py — SQLite, logged per session + per test
        v  document_upload/downloads.py — bundled into .docx / .zip on demand
```

Nothing above the `batch_generator.py` layer is new machinery — it
reuses the exact same `generate_intermediate_definition`,
`generate_manual_test_case`, and adapter classes the rest of the
project already has, just driven once per extracted scenario instead of
once per manually-typed requirement.

## Zero-scenario documents are handled explicitly, not fabricated

If a document has no identifiable testable behavior (a glossary, a
pure background section), `extract_test_scenarios()` returns an empty
list — not an error, not an invented scenario — and `/api/audit/upload`
turns that into a clear "No testable scenarios were found in this
document" response. `tests/fixtures/documents/no_test_scenarios.pdf` is
a real fixture used to verify exactly this path.

## API (`/api/audit/*`)

Namespaced separately from the existing `/api/history` (which tracks
live "Run" results — an unrelated, pre-existing concept) so nothing
already there changed:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/audit/upload` | POST (multipart: `file`, `framework`) | Upload a document, extract scenarios, generate tests, log the session |
| `/api/audit/history` | GET | List every past session, most recent first |
| `/api/audit/sessions/{id}` | GET | One session's details + all its generated tests |
| `/api/audit/download/manual/{id}` | GET | All manual test cases for a session, as one `.docx` |
| `/api/audit/download/automated/{id}` | GET | All automated code for a session, as one `.zip` |

Every session opens its own SQLite connection (`init_db()`), rather than
sharing one on `app.state` — FastAPI runs sync endpoints in a worker
threadpool, and a single `sqlite3.Connection` isn't safe to reuse across
threads. A real bug from exactly this kind of oversight (not a threading
one, but the same "test it, don't assume it" lesson) is documented
below.

## Persistence: survives a restart, verified explicitly

The audit database is a real file (`data/audit_history.db`, gitignored
— it's runtime state, not source), not in-memory. `tests/test_document_upload/test_audit_db.py::test_survives_a_restart`
closes a connection and reopens a fresh one against the same file path
— simulating the server process actually restarting — and asserts prior
sessions and tests are still there.

## A real bug this feature's own tests caught before shipping

The original design's `generated_tests` table has no `framework`
column — only the parent session does, since every test in one session
was generated for the one framework that session chose. The download
bundler needs `test["framework"]` to pick a file extension for the
`.zip`, though, so a naive `get_tests_for_session()` handed the zip
builder rows missing that field entirely — a `KeyError` caught the
first time the download endpoint was exercised end-to-end (see
`tests/test_document_upload/test_upload_endpoint.py`). Fixed by joining
in the session's `framework` inside `get_tests_for_session()` itself, so
every caller gets a complete row without having to remember to attach
it.

## What's verified, and what's pending your own API key

Fully built and tested without needing a key: document parsing (4 real
fixture files — TXT, DOCX, and 2 differently-shaped PDFs, one with zero
scenarios), the SQLite audit layer (including the explicit restart
test), the `.docx`/`.zip` download builders (content read back and
verified, not just built), and the full `/api/audit/*` request/response
flow via FastAPI's `TestClient` with only the two real network calls
mocked.

**Scenario-extraction accuracy against real, differently-shaped
documents** (the one thing this feature's own design brief calls out as
mattering more than anything else) is real code, but genuinely
unverified without a live `ANTHROPIC_API_KEY` — no key was available in
the environment this was built in. `tests/fixtures/documents/` has 3
real, differently-shaped requirements documents plus the zero-scenario
case specifically so this can be verified for real the moment a key is
available; that verification had not been run as of this writing.
