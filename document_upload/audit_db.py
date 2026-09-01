"""
Step 4 of the document-upload feature: a persistent (file-based, not
in-memory) SQLite audit trail of every document-upload generation
session and the tests it produced. Must survive an app restart -- see
tests/test_document_upload/test_audit_db.py's explicit
close-connection-then-reopen-same-file test for that requirement.

log_download() is deliberately separate from log_generated_test(): "this
test was generated" and "a user actually retrieved it" are different
facts worth keeping apart in an audit trail (see the module's original
design brief for the reasoning).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "audit_history.db"


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploaded_filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            framework TEXT NOT NULL,
            scenario_count INTEGER NOT NULL,
            provider_used TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generated_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES generation_sessions(id),
            scenario_name TEXT NOT NULL,
            manual_test_case TEXT NOT NULL,
            automated_code TEXT NOT NULL,
            downloaded_at TEXT
        )
    """)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_session(conn: sqlite3.Connection, filename: str, framework: str, scenario_count: int, provider: str) -> int:
    cursor = conn.execute(
        "INSERT INTO generation_sessions (uploaded_filename, uploaded_at, framework, scenario_count, provider_used) "
        "VALUES (?, ?, ?, ?, ?)",
        (filename, _now(), framework, scenario_count, provider),
    )
    conn.commit()
    return cursor.lastrowid


def log_generated_test(conn: sqlite3.Connection, session_id: int, scenario_name: str, manual_test_case: str, automated_code: str) -> int:
    cursor = conn.execute(
        "INSERT INTO generated_tests (session_id, scenario_name, manual_test_case, automated_code) VALUES (?, ?, ?, ?)",
        (session_id, scenario_name, manual_test_case, automated_code),
    )
    conn.commit()
    return cursor.lastrowid


def log_download(conn: sqlite3.Connection, test_id: int) -> None:
    conn.execute("UPDATE generated_tests SET downloaded_at = ? WHERE id = ?", (_now(), test_id))
    conn.commit()


def get_sessions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM generation_sessions ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def get_session(conn: sqlite3.Connection, session_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM generation_sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def get_tests_for_session(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    """Joins in the parent session's `framework` -- generated_tests has no
    framework column of its own (every test in one session was generated
    for the one framework the session chose), but downloads.py's zip
    builder needs test["framework"] to pick a file extension, so callers
    must never have to remember to attach it themselves."""
    rows = conn.execute(
        """
        SELECT generated_tests.*, generation_sessions.framework AS framework
        FROM generated_tests
        JOIN generation_sessions ON generation_sessions.id = generated_tests.session_id
        WHERE generated_tests.session_id = ?
        ORDER BY generated_tests.id
        """,
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]
