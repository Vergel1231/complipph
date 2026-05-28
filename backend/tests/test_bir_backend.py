"""Comprehensive backend tests for BIR Filipino Filing SaaS.
Covers: auth (register/login/me/logout), business profile, BIR form generation
(1701Q 8% & graduated, 2551Q gating), filing history & mark-submitted, deadlines,
AI chat, admin metrics & rules, billing.
"""
import os
import time
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load /app/backend/.env so ADMIN_PASSWORD reflects live value
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _read_frontend_backend_url() -> str:
    text = Path("/app/frontend/.env").read_text()
    for line in text.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


BASE_URL = _read_frontend_backend_url()
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def _new_email(prefix="testuser"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"


# ─── Fixtures ──────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def flat_user_session():
    """8% flat-tax registered freelancer, fully onboarded."""
    s = requests.Session()
    email = _new_email("flat")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "Flat Freelancer"
    })
    assert r.status_code == 200, f"register failed: {r.text}"
    # Onboard: 8% flat
    r2 = s.post(f"{API}/business/profile", json={
        "legal_name": "Flat Designs", "tin": "123456789", "rdo_code": "044",
        "business_type": "designer", "taxpayer_classification": "8_percent_flat",
        "is_vat_registered": False,
    })
    assert r2.status_code == 200, f"profile failed: {r2.text}"
    s.email = email
    return s


@pytest.fixture(scope="module")
def graduated_user_session():
    """Graduated, non-VAT freelancer."""
    s = requests.Session()
    email = _new_email("grad")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "Grad Consultant"
    })
    assert r.status_code == 200
    r2 = s.post(f"{API}/business/profile", json={
        "legal_name": "Grad Consulting", "tin": "987654321", "rdo_code": "044",
        "business_type": "consultant", "taxpayer_classification": "graduated",
        "is_vat_registered": False,
    })
    assert r2.status_code == 200
    s.email = email
    return s


# ─── Health ────────────────────────────────────────────────────
class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_health(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ─── Auth ──────────────────────────────────────────────────────
class TestAuth:
    def test_register_and_cookies(self):
        s = requests.Session()
        email = _new_email("reg")
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Strong1234!", "name": "Reg User"
        })
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == email.lower()
        assert body["onboarded"] is False
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_register_duplicate(self):
        s = requests.Session()
        email = _new_email("dup")
        s.post(f"{API}/auth/register", json={
            "email": email, "password": "Strong1234!", "name": "Dup"
        })
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Strong1234!", "name": "Dup2"
        })
        assert r.status_code == 400

    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["role"] == "admin"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL, "password": "WrongPassword!"
        })
        assert r.status_code == 401

    def test_me_with_cookies(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout_clears_cookies(self):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # After logout, /me should fail
        r2 = s.get(f"{API}/auth/me")
        assert r2.status_code == 401

    def test_protected_endpoints_require_auth(self):
        endpoints = [
            ("GET", f"{API}/auth/me"),
            ("GET", f"{API}/business/profile"),
            ("POST", f"{API}/forms/generate"),
            ("GET", f"{API}/forms/history"),
            ("GET", f"{API}/deadlines/"),
            ("GET", f"{API}/admin/metrics"),
            ("GET", f"{API}/billing/subscription"),
        ]
        for method, url in endpoints:
            r = requests.request(method, url, json={} if method == "POST" else None)
            assert r.status_code == 401, f"{method} {url} expected 401, got {r.status_code}"


# ─── Business Profile + Onboarding ─────────────────────────────
class TestBusinessProfile:
    def test_profile_created_and_user_marked_onboarded(self, flat_user_session):
        r = flat_user_session.get(f"{API}/business/profile")
        assert r.status_code == 200
        bp = r.json()
        assert bp["taxpayer_classification"] == "8_percent_flat"
        assert bp["is_non_vat"] is True
        # User must be marked onboarded
        me = flat_user_session.get(f"{API}/auth/me").json()
        assert me["onboarded"] is True

    def test_deadlines_generated_after_profile(self, flat_user_session):
        r = flat_user_session.get(f"{API}/deadlines/")
        assert r.status_code == 200
        ds = r.json()
        assert len(ds) > 0
        # 8% flat → only 1701Q Q1/Q2/Q3, NO 2551Q
        forms = {d["form_type"] for d in ds}
        assert "1701Q" in forms
        assert "2551Q" not in forms

    def test_graduated_has_2551q_deadlines(self, graduated_user_session):
        r = graduated_user_session.get(f"{API}/deadlines/")
        assert r.status_code == 200
        ds = r.json()
        forms = {d["form_type"] for d in ds}
        assert "1701Q" in forms
        assert "2551Q" in forms
        # Q4 should exist for 2551Q
        q_periods = {d["period"][-2:] for d in ds if d["form_type"] == "2551Q"}
        assert "Q4" in q_periods


# ─── BIR Engine — 1701Q 8% Flat ────────────────────────────────
class TestForm1701QFlat:
    def test_8pct_flat_correct_math(self, flat_user_session):
        # NEW SPEC: Line 41 (Net Taxable Income) = Gross Sales directly,
        # Line 42 (Income Tax Due) = 8% × Gross Sales. No deductions apply
        # at quarterly 1701Q; the ₱250k exemption is applied at the annual 1701.
        # gross 500k → Line 41 = 500000, Line 42 = 500000 × 0.08 = 40000
        payload = {
            "form_type": "1701Q", "period": "2026-Q1",
            "gross_sales": 500000, "other_income": 100000,
            "cost_of_sales": 0, "operating_expenses": 0,
            "creditable_tax_withheld": 0, "tax_paid_previous_quarters": 0,
        }
        r = flat_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()["computed"]
        assert c["form_type"] == "1701Q"
        assert c["method"] == "8% flat tax"
        assert c["net_taxable_income"] == 500000.0
        assert c["income_tax_due"] == 40000.0
        assert c["tax_payable"] == 40000.0
        # Verify field_map matches
        fm = c["field_map"]
        assert fm["Line 36 — Gross Sales/Receipts"] == 500000.0
        assert fm["Line 41 — Net Taxable Income"] == 500000.0
        assert fm["Line 42 — Income Tax Due"] == 40000.0
        assert fm["Line 45 — Tax Payable"] == 40000.0

    def test_8pct_flat_user_fixture(self, flat_user_session):
        # User-provided spec fixture: gross 150k, withheld 7500
        # → Line 42 = 12000, Line 45 = 4500
        payload = {
            "form_type": "1701Q", "period": "2026-Q1",
            "gross_sales": 150000, "other_income": 0,
            "cost_of_sales": 0, "operating_expenses": 0,
            "creditable_tax_withheld": 7500, "tax_paid_previous_quarters": 0,
        }
        r = flat_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()["computed"]
        assert c["net_taxable_income"] == 150000.0
        assert c["income_tax_due"] == 12000.0
        assert c["tax_payable"] == 4500.0
        fm = c["field_map"]
        assert fm["Line 41 — Net Taxable Income"] == 150000.0
        assert fm["Line 42 — Income Tax Due"] == 12000.0
        assert fm["Line 43 — Less Creditable Tax Withheld"] == 7500.0
        assert fm["Line 45 — Tax Payable"] == 4500.0

    def test_8pct_flat_zero_gross(self, flat_user_session):
        # gross 0 → 0 tax (no income, no liability)
        payload = {
            "form_type": "1701Q", "period": "2026-Q1",
            "gross_sales": 0, "other_income": 0,
        }
        r = flat_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200
        c = r.json()["computed"]
        assert c["net_taxable_income"] == 0.0
        assert c["income_tax_due"] == 0.0
        assert c["tax_payable"] == 0.0


# ─── BIR Engine — 1701Q Graduated ──────────────────────────────
class TestForm1701QGraduated:
    def test_graduated_train_brackets(self, graduated_user_session):
        # net taxable 600k → 22500 + (600k-400k)*0.20 = 62500
        # gross 1M, cost 200k, opex 200k → net = 600k
        payload = {
            "form_type": "1701Q", "period": "2026-Q1",
            "gross_sales": 1000000, "other_income": 0,
            "cost_of_sales": 200000, "operating_expenses": 200000,
        }
        r = graduated_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()["computed"]
        assert c["method"] == "Graduated rates"
        assert c["net_taxable_income"] == 600000.0
        assert c["income_tax_due"] == 62500.0

    def test_graduated_below_250k_zero(self, graduated_user_session):
        payload = {
            "form_type": "1701Q", "period": "2026-Q2",
            "gross_sales": 200000, "other_income": 0,
            "cost_of_sales": 0, "operating_expenses": 0,
        }
        r = graduated_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200
        c = r.json()["computed"]
        assert c["income_tax_due"] == 0.0


# ─── BIR Engine — 2551Q Gating + Math ──────────────────────────
class TestForm2551Q:
    def test_2551q_rejected_for_8pct_flat(self, flat_user_session):
        payload = {
            "form_type": "2551Q", "period": "2026-Q1",
            "gross_sales": 200000, "other_income": 0,
        }
        r = flat_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 400, f"Expected 400 reject, got {r.status_code}: {r.text}"
        assert "2551Q" in r.json()["detail"]

    def test_2551q_3pct_for_graduated_non_vat(self, graduated_user_session):
        # 200k * 0.03 = 6000
        payload = {
            "form_type": "2551Q", "period": "2026-Q1",
            "gross_sales": 200000, "other_income": 0,
        }
        r = graduated_user_session.post(f"{API}/forms/generate", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()["computed"]
        assert c["form_type"] == "2551Q"
        assert c["tax_rate"] == 0.03
        assert c["percentage_tax_due"] == 6000.0
        assert c["tax_payable"] == 6000.0


# ─── Filing History + Mark Submitted ───────────────────────────
class TestFilingHistory:
    def test_history_returns_user_filings(self, flat_user_session):
        r = flat_user_session.get(f"{API}/forms/history")
        assert r.status_code == 200
        history = r.json()
        assert isinstance(history, list)
        assert len(history) >= 1
        for f in history:
            assert "filing_id" in f
            assert f["form_type"] in ["1701Q", "2551Q"]

    def test_mark_submitted_completes_deadline(self, graduated_user_session):
        # Create a 1701Q filing
        r = graduated_user_session.post(f"{API}/forms/generate", json={
            "form_type": "1701Q", "period": "2026-Q3",
            "gross_sales": 300000, "cost_of_sales": 50000, "operating_expenses": 50000,
        })
        assert r.status_code == 200
        filing_id = r.json()["filing_id"]
        period = r.json()["period"]

        # Mark submitted
        r2 = graduated_user_session.post(f"{API}/forms/{filing_id}/mark-submitted")
        assert r2.status_code == 200
        assert r2.json()["ok"] is True

        # Deadline for that period should now be completed
        r3 = graduated_user_session.get(f"{API}/deadlines/")
        assert r3.status_code == 200
        match = [d for d in r3.json() if d["form_type"] == "1701Q" and d["period"] == period]
        if match:  # may not be in horizon
            assert match[0]["completed"] is True

        # Filing status should now be submitted
        r4 = graduated_user_session.get(f"{API}/forms/{filing_id}")
        assert r4.status_code == 200
        assert r4.json()["status"] == "submitted"


# ─── AI Assistant ──────────────────────────────────────────────
class TestAI:
    def test_ai_chat_filipino_bir_context(self, flat_user_session):
        r = flat_user_session.post(f"{API}/ai/chat", json={
            "session_id": "test-session-1",
            "message": "What is the 1701Q deadline for Q1?"
        }, timeout=60)
        assert r.status_code == 200, f"AI chat failed: {r.status_code} {r.text}"
        body = r.json()
        assert "response" in body
        text = body["response"].lower()
        # Sanity: response should mention May 15 or 1701Q context
        assert len(text) > 20
        assert any(k in text for k in ["may", "1701", "quarterly", "bir", "₱", "deadline", "filing"])


# ─── Admin ─────────────────────────────────────────────────────
class TestAdmin:
    def test_admin_metrics(self, admin_session):
        r = admin_session.get(f"{API}/admin/metrics")
        assert r.status_code == 200
        m = r.json()
        for k in ["mrr_php", "active_subscribers", "churn_rate_pct", "total_users", "total_filings"]:
            assert k in m

    def test_admin_metrics_forbidden_for_user(self, flat_user_session):
        r = flat_user_session.get(f"{API}/admin/metrics")
        assert r.status_code == 403

    def test_admin_bir_rules_list(self, admin_session):
        r = admin_session.get(f"{API}/admin/bir-rules")
        assert r.status_code == 200
        rules = r.json()
        keys = {r["rule_key"] for r in rules}
        # Must include core rules
        assert "personal_exemption" in keys
        assert "flat_tax_rate" in keys
        assert "percentage_tax_rate" in keys

    def test_admin_update_bir_rule(self, admin_session):
        r = admin_session.put(f"{API}/admin/bir-rules/percentage_tax_rate", json={
            "rule_value": 0.03, "description": "3% percentage tax"
        })
        assert r.status_code == 200
        assert r.json()["rule_value"] == 0.03

    def test_admin_update_unknown_rule(self, admin_session):
        r = admin_session.put(f"{API}/admin/bir-rules/not_a_real_rule", json={
            "rule_value": 1.0
        })
        assert r.status_code == 400


# ─── Billing ───────────────────────────────────────────────────
class TestBilling:
    def test_list_plans(self):
        r = requests.get(f"{API}/billing/plans")
        assert r.status_code == 200
        plans = r.json()
        for p in ["solo", "pro", "reseller"]:
            assert p in plans
            assert "amount_php" in plans[p]

    def test_checkout_activates_subscription(self, flat_user_session):
        """In MOCK mode (PayMongo keys empty), checkout activates immediately.
        In LIVE mode (keys configured), checkout returns a hosted redirect_url
        and the subscription stays 'incomplete' until the webhook confirms."""
        r = flat_user_session.post(f"{API}/billing/checkout", json={"plan": "solo"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert "subscription_id" in body

        live = bool(os.environ.get("PAYMONGO_SECRET_KEY"))
        if live:
            assert body["provider"] == "paymongo"
            assert body.get("flow") == "checkout_session"
            assert body.get("redirect_url", "").startswith("https://checkout.paymongo.com/")
            r2 = flat_user_session.get(f"{API}/billing/subscription")
            sub = r2.json()
            assert sub is not None
            assert sub["status"] == "incomplete"  # webhook will flip to active
            assert sub["provider"] == "paymongo"
        else:
            assert body["provider"] == "mock"
            r2 = flat_user_session.get(f"{API}/billing/subscription")
            sub = r2.json()
            assert sub is not None
            assert sub["status"] == "active"
            assert sub["plan"] == "solo"
            me = flat_user_session.get(f"{API}/auth/me").json()
            assert me["subscription_status"] == "active"

    def test_checkout_invalid_plan(self, flat_user_session):
        r = flat_user_session.post(f"{API}/billing/checkout", json={"plan": "enterprise"})
        # pydantic validation → 422
        assert r.status_code in (400, 422)
