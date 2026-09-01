"""
Step 1 of the document-upload feature: turn an uploaded file's raw bytes
into plain text, for PDF/DOCX/TXT/MD. Deliberately takes (filename,
content: bytes) rather than a FastAPI UploadFile -- this must be testable
in isolation against real PDF/DOCX files with no HTTP layer involved at
all, per the build order this feature was specified with (parsing proven
correct BEFORE it's wired into scenario extraction or anything else).
"""
from __future__ import annotations

import io


class UnsupportedFileType(Exception):
    pass


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf(content)
    if lower.endswith(".docx"):
        return _extract_docx(content)
    if lower.endswith(".txt") or lower.endswith(".md"):
        return content.decode("utf-8")

    raise UnsupportedFileType(f"Unsupported file type: {filename}. Use PDF, DOCX, TXT, or MD.")


def _extract_pdf(content: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(content: bytes) -> str:
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)
