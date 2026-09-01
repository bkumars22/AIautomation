"""
End-to-end integration test for the /api/audit/* endpoints wired into
backend/main.py: upload -> extract text -> extract scenarios (mocked LLM
call) -> generate manual+automated tests (mocked LLM call) -> log to a
REAL SQLite file (in a tmp dir, not the app's real data/ dir) -> download
both bundles and verify the content actually matches what was generated.

Only the two real network calls (_call_llm in scenario_extractor and in
intermediate_generator) are mocked -- everything else (text extraction,
scenario validation, adapter code generation, SQLite persistence, docx/zip
building) runs for real, exactly as it would with a live API key.
"""
from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import patch

import pytest
from docx import Document as DocxDocument
from fastapi.testclient import TestClient

import backend.main as backend_main
from document_upload.audit_db import init_db

_SCENARIOS_JSON = json.dumps([
    {
        "scenario_name": "Apply a valid promo code",
        "description": "Shopper enters a valid promo code and the total updates.",
        "acceptance_criteria": "Total reflects the discount.",
    },
])

_INTERMEDIATE_DEF = {
    "test_name": "Apply a valid promo code",
    "steps": [
        {"action": "navigate", "target": {"type": "url", "value": "/checkout"}},
        {"action": "assert_url", "value": "/checkout"},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "audit_history.db"
    monkeypatch.setattr(backend_main, "init_db", lambda: init_db(db_path))
    with TestClient(backend_main.app) as test_client:
        yield test_client


def test_upload_generates_logs_and_returns_tests(client):
    with patch("document_upload.scenario_extractor._call_llm", return_value=_SCENARIOS_JSON), \
         patch("generation.intermediate_generator._call_llm", return_value=json.dumps(_INTERMEDIATE_DEF)):
        response = client.post(
            "/api/audit/upload",
            files={"file": ("requirements.txt", b"Some requirements text.", "text/plain")},
            data={"framework": "playwright"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] >= 1
    assert len(body["tests"]) == 1
    assert body["tests"][0]["scenario_name"] == "Apply a valid promo code"
    assert "def test_" in body["tests"][0]["automated_code"]


def test_history_shows_the_uploaded_session(client):
    with patch("document_upload.scenario_extractor._call_llm", return_value=_SCENARIOS_JSON), \
         patch("generation.intermediate_generator._call_llm", return_value=json.dumps(_INTERMEDIATE_DEF)):
        client.post(
            "/api/audit/upload",
            files={"file": ("requirements.txt", b"Some requirements text.", "text/plain")},
            data={"framework": "playwright"},
        )

    history = client.get("/api/audit/history").json()
    assert len(history["sessions"]) == 1
    assert history["sessions"][0]["uploaded_filename"] == "requirements.txt"
    assert history["sessions"][0]["scenario_count"] == 1


def test_downloads_contain_the_real_matching_data(client):
    with patch("document_upload.scenario_extractor._call_llm", return_value=_SCENARIOS_JSON), \
         patch("generation.intermediate_generator._call_llm", return_value=json.dumps(_INTERMEDIATE_DEF)):
        upload = client.post(
            "/api/audit/upload",
            files={"file": ("requirements.txt", b"Some requirements text.", "text/plain")},
            data={"framework": "playwright"},
        )
    session_id = upload.json()["session_id"]

    manual_resp = client.get(f"/api/audit/download/manual/{session_id}")
    assert manual_resp.status_code == 200
    doc = DocxDocument(io.BytesIO(manual_resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Apply a valid promo code" in full_text

    zip_resp = client.get(f"/api/audit/download/automated/{session_id}")
    assert zip_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        assert len(zf.namelist()) == 1
        assert "def test_" in zf.read(zf.namelist()[0]).decode("utf-8")


def test_document_with_no_scenarios_returns_clear_error_not_a_fabricated_test(client):
    with patch("document_upload.scenario_extractor._call_llm", return_value="[]"):
        response = client.post(
            "/api/audit/upload",
            files={"file": ("glossary.txt", b"Just a glossary of terms.", "text/plain")},
            data={"framework": "playwright"},
        )

    assert response.status_code == 422
    assert "No testable scenarios" in response.json()["detail"]


def test_unsupported_file_type_returns_clear_error(client):
    response = client.post(
        "/api/audit/upload",
        files={"file": ("requirements.xlsx", b"not really an xlsx", "application/octet-stream")},
        data={"framework": "playwright"},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_download_for_nonexistent_session_returns_404(client):
    response = client.get("/api/audit/download/manual/999")
    assert response.status_code == 404


def test_existing_routes_still_work_unmodified(client):
    """Sanity check this feature didn't disturb anything already there."""
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/fixtures").status_code == 200
