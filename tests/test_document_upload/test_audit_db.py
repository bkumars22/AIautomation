"""
Step 4 verification. The one requirement this feature spec calls out
explicitly: "the audit database needs to survive app restarts -- verify
explicitly that stopping and restarting the local server still shows
prior history, not a reset database each time." test_survives_a_restart
below is that exact check: close the connection (simulating the server
process ending), then open a NEW connection against the SAME file path
(simulating a fresh server start) and confirm the data is still there.
"""
import uuid

from document_upload.audit_db import (
    get_session,
    get_sessions,
    get_tests_for_session,
    init_db,
    log_download,
    log_generated_test,
    log_session,
)


def _tmp_db_path(tmp_path):
    return tmp_path / "audit_history.db"


def test_log_session_and_generated_tests(tmp_path):
    conn = init_db(_tmp_db_path(tmp_path))
    session_id = log_session(conn, "requirements.pdf", "playwright", 2, "anthropic")

    test_id = log_generated_test(conn, session_id, "User can reset password", "Test Case: ...", "def test(): ...")

    session = get_session(conn, session_id)
    assert session["uploaded_filename"] == "requirements.pdf"
    assert session["scenario_count"] == 2

    tests = get_tests_for_session(conn, session_id)
    assert len(tests) == 1
    assert tests[0]["id"] == test_id
    assert tests[0]["downloaded_at"] is None


def test_log_download_sets_timestamp_separately_from_generation(tmp_path):
    conn = init_db(_tmp_db_path(tmp_path))
    session_id = log_session(conn, "spec.docx", "cypress", 1, "anthropic")
    test_id = log_generated_test(conn, session_id, "Scenario A", "manual case text", "code text")

    before = get_tests_for_session(conn, session_id)[0]
    assert before["downloaded_at"] is None

    log_download(conn, test_id)

    after = get_tests_for_session(conn, session_id)[0]
    assert after["downloaded_at"] is not None


def test_get_sessions_orders_most_recent_first(tmp_path):
    conn = init_db(_tmp_db_path(tmp_path))
    log_session(conn, "first.txt", "selenium", 1, "anthropic")
    log_session(conn, "second.txt", "selenium", 1, "anthropic")

    sessions = get_sessions(conn)
    assert [s["uploaded_filename"] for s in sessions] == ["second.txt", "first.txt"]


def test_survives_a_restart(tmp_path):
    """The explicit, named requirement: close the connection (server
    stops), reopen against the same file path (server restarts), and
    confirm prior history is still there -- not silently reset."""
    db_path = _tmp_db_path(tmp_path)

    conn = init_db(db_path)
    session_id = log_session(conn, "restart_check.md", "testng-selenium", 3, "anthropic")
    log_generated_test(conn, session_id, "Scenario before restart", "manual", "code")
    conn.close()

    # Simulates a fresh server process starting up again against the same file.
    reopened = init_db(db_path)
    sessions = get_sessions(reopened)
    assert len(sessions) == 1
    assert sessions[0]["uploaded_filename"] == "restart_check.md"

    tests = get_tests_for_session(reopened, session_id)
    assert len(tests) == 1
    assert tests[0]["scenario_name"] == "Scenario before restart"


def test_unique_tmp_paths_dont_collide(tmp_path):
    """Sanity check the test fixtures themselves aren't accidentally sharing state."""
    path_a = tmp_path / f"{uuid.uuid4()}.db"
    path_b = tmp_path / f"{uuid.uuid4()}.db"
    conn_a = init_db(path_a)
    conn_b = init_db(path_b)
    log_session(conn_a, "a.txt", "cypress", 1, "anthropic")
    assert get_sessions(conn_b) == []
