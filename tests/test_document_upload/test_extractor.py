"""
Step 1 verification: extract_text against REAL PDF/DOCX/TXT/MD files, not
mocks -- per this feature's own build order ("build and test document
parsing against real PDF and DOCX files first, in isolation").
"""
from pathlib import Path

import pytest

from document_upload.extractor import UnsupportedFileType, extract_text

FIXTURES = Path(__file__).parent.parent / "fixtures" / "documents"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_extracts_txt():
    text = extract_text("jira_export_checkout.txt", _read("jira_export_checkout.txt"))
    assert "CHKT-101" in text
    assert "promo code" in text.lower()


def test_extracts_docx():
    text = extract_text("business_requirements_profile.docx", _read("business_requirements_profile.docx"))
    assert "Self-service email update" in text
    assert "Password strength feedback" in text


def test_extracts_pdf():
    text = extract_text("password_reset_spec.pdf", _read("password_reset_spec.pdf"))
    assert "Forgot password" in text
    assert "30 minutes" in text


def test_extracts_pdf_with_no_scenarios():
    text = extract_text("no_test_scenarios.pdf", _read("no_test_scenarios.pdf"))
    assert "glossary" in text.lower()


def test_md_uses_txt_path():
    text = extract_text("notes.md", b"# Heading\n\nSome *markdown* text.")
    assert "Heading" in text


def test_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileType, match="foo.xlsx"):
        extract_text("foo.xlsx", b"whatever")
