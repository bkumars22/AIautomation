"""One-off script: generates tests/fixtures/documents/password_reset_spec.pdf.
Run once (`python scripts/generate_pdf_fixtures.py` from the repo root) to
(re)produce the fixture; not imported at runtime. Also generates
no_test_scenarios.pdf, a glossary-only doc with nothing testable in it.

Note: reportlab is only needed to author these fixtures, not by the app
itself -- it is intentionally not in requirements.txt."""
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "documents"


def build(filename, title, paragraphs):
    doc = SimpleDocTemplate(str(FIXTURES_DIR / filename), pagesize=LETTER)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for p in paragraphs:
        story.append(Paragraph(p, styles["Normal"]))
        story.append(Spacer(1, 10))
    doc.build(story)
    print("wrote", FIXTURES_DIR / filename)


build(
    "password_reset_spec.pdf",
    "Functional Spec: Password Reset Flow (v3)",
    [
        "1. A user who has forgotten their password clicks 'Forgot password?' "
        "on the login screen and is taken to a page where they enter their "
        "registered email address and submit it.",

        "2. Upon submission, the system sends a reset link to that email "
        "address if an account with it exists, and shows the same generic "
        "'If that email is registered, a reset link has been sent' message "
        "regardless of whether the account exists, to avoid revealing which "
        "emails are registered.",

        "3. Clicking the reset link within 30 minutes of it being sent takes "
        "the user to a page where they can enter and confirm a new password. "
        "After 30 minutes, the link must show an 'expired' page instead and "
        "must not allow a password change.",

        "4. After successfully setting a new password via the reset link, "
        "all of that user's existing login sessions on other devices must be "
        "invalidated, requiring them to log in again everywhere.",

        "5. This document was last reviewed by the security team on "
        "2026-02-14 and supersedes the v2 spec dated 2025-11-03.",
    ],
)

build(
    "no_test_scenarios.pdf",
    "Glossary of Terms — Internal Platform Vocabulary",
    [
        "SKU: Stock Keeping Unit, a unique identifier assigned to each "
        "distinct product variant carried in inventory.",

        "Churn: the rate at which customers stop doing business with the "
        "company over a given period, usually expressed as a percentage.",

        "Tenant: in a multi-tenant system, an isolated customer organization "
        "whose data is logically separated from every other tenant's data.",

        "This document is a reference glossary only and does not describe "
        "any user-facing behavior, screen, or workflow.",
    ],
)
