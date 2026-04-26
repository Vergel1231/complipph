"""Phase 2 backend tests: Reminders cron (manual trigger + dedup) and PDF/XML exports.

- POST /api/admin/run-reminders  (RBAC, dedup, disabled-email no-op)
- GET  /api/forms/{filing_id}/export.xml  (eBIRForms-compatible XML)
- GET  /api/forms/{filing_id}/export.pdf  (reportlab PDF)
"""
import os
import uuid
import pytest
import requests
import xml.etree.ElementTree as ET
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bir-filer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@birfilipino.app"
ADMIN_PASSWORD = "Admin@2026"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def _new_email(prefix="phase2"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"


# ─── Fixtures ──────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def user_session():
    """Onboarded graduated freelancer (creates 1701Q+2551Q deadlines)."""
    s = requests.Session()
    email = _new_email("grad")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "Phase2 Grad"
    })
    assert r.status_code == 200, r.text
    r2 = s.post(f"{API}/business/profile", json={
        "legal_name": "Phase2 Consulting", "tin": "111222333", "rdo_code": "044",
        "business_type": "consultant", "taxpayer_classification": "graduated",
        "is_vat_registered": False,
    })
    assert r2.status_code == 200, r2.text
    s.email = email
    return s


@pytest.fixture(scope="module")
def filing_id(user_session):
    """Generate a 1701Q filing for export tests."""
    r = user_session.post(f"{API}/forms/generate", json={
        "form_type": "1701Q", "period": "2026-Q1",
        "gross_sales": 800000, "other_income": 50000,
        "cost_of_sales": 100000, "operating_expenses": 100000,
    })
    assert r.status_code == 200, r.text
    return r.json()["filing_id"]


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ─── Reminders: RBAC ──────────────────────────────────────────
class TestRunRemindersRBAC:
    def test_unauth_401(self):
        r = requests.post(f"{API}/admin/run-reminders")
        assert r.status_code == 401

    def test_regular_user_403(self, user_session):
        r = user_session.post(f"{API}/admin/run-reminders")
        assert r.status_code == 403

    def test_admin_200_with_report_shape(self, admin_session):
        r = admin_session.post(f"{API}/admin/run-reminders")
        assert r.status_code == 200, r.text
        rpt = r.json()
        for k in ["users_processed", "sent", "skipped_duplicates",
                  "skipped_disabled_email", "errors", "ran_at"]:
            assert k in rpt, f"missing key: {k} in report {rpt}"
        # Sanity: counters are ints
        assert isinstance(rpt["users_processed"], int)
        assert isinstance(rpt["sent"], int)
        assert isinstance(rpt["skipped_duplicates"], int)
        assert isinstance(rpt["skipped_disabled_email"], int)


# ─── Reminders: Dedup + disabled status ───────────────────────
class TestRemindersDedup:
    def test_dedup_does_not_double_insert(self, admin_session, db):
        # Snapshot before
        before_count = db.reminders_sent.count_documents({})
        # First run
        r1 = admin_session.post(f"{API}/admin/run-reminders")
        assert r1.status_code == 200
        rpt1 = r1.json()
        after_first = db.reminders_sent.count_documents({})
        new_inserts_first = after_first - before_count
        # Each NEW reminder this run = sent + skipped_disabled_email + errors (all
        # cause an insert into reminders_sent), skipped_duplicates do NOT insert.
        expected_new = rpt1["sent"] + rpt1["skipped_disabled_email"] + rpt1["errors"]
        assert new_inserts_first == expected_new, (
            f"First run new inserts {new_inserts_first} != expected {expected_new}"
        )

        # Second run immediately — every previously inserted reminder should be
        # caught by dedup_key and counted as skipped_duplicates; no new inserts.
        r2 = admin_session.post(f"{API}/admin/run-reminders")
        assert r2.status_code == 200
        rpt2 = r2.json()
        after_second = db.reminders_sent.count_documents({})
        assert after_second == after_first, (
            f"Second run inserted new reminders! before={after_first} after={after_second}"
        )
        # Second-run skipped_duplicates must be >= number of inserts from first
        # run (since those are now dedup'd). When no deadlines in the {30,7,1}
        # window exist on test day, both numbers may be 0 — that is also a pass.
        assert rpt2["skipped_duplicates"] >= new_inserts_first

    def test_reminders_sent_status_is_disabled_when_no_resend_key(self, db):
        """When RESEND_API_KEY is empty, every emitted reminder must be logged
        with result_status='disabled' (not 'sent')."""
        # Look at any reminder docs from this test run (they use TEST_ user emails
        # but we just check there is no 'sent' status while the key is empty).
        if not os.environ.get("RESEND_API_KEY"):
            statuses = set()
            for d in db.reminders_sent.find({}, {"_id": 0, "result_status": 1}):
                statuses.add(d.get("result_status"))
            # Allowed states with empty key: 'disabled' only (and possibly 'error'
            # if anything goes wrong — but never 'sent').
            assert "sent" not in statuses, (
                f"Found result_status='sent' while RESEND_API_KEY is empty: {statuses}"
            )


# ─── XML Export ───────────────────────────────────────────────
class TestExportXML:
    def test_xml_unauthenticated(self, filing_id):
        r = requests.get(f"{API}/forms/{filing_id}/export.xml")
        assert r.status_code == 401

    def test_xml_unknown_filing(self, user_session):
        r = user_session.get(f"{API}/forms/{uuid.uuid4().hex}/export.xml")
        assert r.status_code == 404

    def test_xml_other_user_404(self, filing_id):
        # Different user must NOT be able to access another user's filing
        s = requests.Session()
        email = _new_email("xother")
        s.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass1234!", "name": "Other"
        })
        r = s.get(f"{API}/forms/{filing_id}/export.xml")
        assert r.status_code == 404

    def test_xml_valid_structure(self, user_session, filing_id):
        r = user_session.get(f"{API}/forms/{filing_id}/export.xml")
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "application/xml" in ct, f"unexpected Content-Type: {ct}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert ".xml" in cd.lower()
        # Parse XML content
        root = ET.fromstring(r.content)
        assert root.tag == "eBIRFormsFiling"
        assert root.attrib.get("formType") == "1701Q"
        assert root.attrib.get("period") == "2026-Q1"
        # Must have Header / Body / Computation / Summary children
        tags = {child.tag for child in root}
        for required in ["Header", "Body", "Computation", "Summary"]:
            assert required in tags, f"missing <{required}> in XML; got {tags}"
        # TIN should be populated from profile
        tin = root.find("Header/TIN")
        assert tin is not None and tin.text == "111222333"
        # Tax payable in summary should be a numeric string
        tp = root.find("Summary/TaxPayable")
        assert tp is not None
        float(tp.text)  # should parse as number


# ─── PDF Export ───────────────────────────────────────────────
class TestExportPDF:
    def test_pdf_unauthenticated(self, filing_id):
        r = requests.get(f"{API}/forms/{filing_id}/export.pdf")
        assert r.status_code == 401

    def test_pdf_unknown_filing(self, user_session):
        r = user_session.get(f"{API}/forms/{uuid.uuid4().hex}/export.pdf")
        assert r.status_code == 404

    def test_pdf_other_user_404(self, filing_id):
        s = requests.Session()
        email = _new_email("pother")
        s.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass1234!", "name": "Other2"
        })
        r = s.get(f"{API}/forms/{filing_id}/export.pdf")
        assert r.status_code == 404

    def test_pdf_valid_binary(self, user_session, filing_id):
        r = user_session.get(f"{API}/forms/{filing_id}/export.pdf")
        assert r.status_code == 200, r.text[:200]
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"unexpected Content-Type: {ct}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert ".pdf" in cd.lower()
        # Magic bytes
        assert r.content[:5] == b"%PDF-", f"PDF magic bytes missing: {r.content[:10]}"
        # Must include the version we generate
        assert b"%PDF-1." in r.content[:10]
        # Sanity: non-trivial size
        assert len(r.content) > 1500, f"PDF too small: {len(r.content)} bytes"
