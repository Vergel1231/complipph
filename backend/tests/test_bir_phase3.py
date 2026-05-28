"""Phase 3 backend tests: PayMongo live billing swap with mock fallback.

Coverage:
- GET  /api/billing/config            (provider/public_key reflect env)
- GET  /api/billing/plans             (catalog still solo/pro/reseller)
- POST /api/billing/checkout          (auth gate + mock fallback path)
- GET  /api/billing/subscription      (returns active doc)
- POST /api/billing/cancel            (status=canceled propagated to user)
- POST /api/billing/attach-payment    (400 when keys empty)
- POST /api/billing/webhook/paymongo  (unverified accepted in mock mode + 403 with bad sig + status mapping)
- paymongo.verify_webhook_signature   (unit tests on helper)
- User model now exposes managed_by_cpa_id (default None)

Per review-request: PayMongo keys are intentionally empty in /app/backend/.env;
we never touch api.paymongo.com — only local fallback + signature helper logic.
"""
import os
import sys
import json
import time
import hmac
import uuid
import hashlib
import importlib
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Make /app/backend importable for `import paymongo` in unit tests
_BE = Path(__file__).resolve().parent.parent
if str(_BE) not in sys.path:
    sys.path.insert(0, str(_BE))

load_dotenv(_BE / ".env")


def _read_frontend_backend_url() -> str:
    text = Path("/app/frontend/.env").read_text()
    for line in text.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


BASE_URL = _read_frontend_backend_url()
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

# Env-conditional skips
PAYMONGO_LIVE = bool(os.environ.get("PAYMONGO_SECRET_KEY"))
WEBHOOK_SECRET_SET = bool(os.environ.get("PAYMONGO_WEBHOOK_SECRET"))
needs_mock_mode = pytest.mark.skipif(
    PAYMONGO_LIVE,
    reason="Test requires PAYMONGO_SECRET_KEY to be empty (mock fallback path).",
)
needs_secret_empty = pytest.mark.skipif(
    WEBHOOK_SECRET_SET,
    reason="Test requires PAYMONGO_WEBHOOK_SECRET to be empty.",
)


def _sign(body: bytes, secret: str | None = None, *, when: int | None = None) -> str:
    """Build a valid Paymongo-Signature header for the given body bytes."""
    secret = secret if secret is not None else os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
    ts = str(when if when is not None else int(time.time()))
    if not secret:
        return f"t={ts},te=unsigned,li=unsigned"
    sig = hmac.new(secret.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},te={sig},li={sig}"


def _new_email(prefix="phase3"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"


# ─── Fixtures ──────────────────────────────────────────────────
@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def fresh_user():
    """Fresh registered user — used across most billing endpoints."""
    s = requests.Session()
    email = _new_email("billing")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "Phase3 User",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    # /auth/register returns the User directly (not wrapped in "user" key)
    user_id = body.get("user", body)["user_id"] if "user" in body else body["user_id"]
    return {"session": s, "email": email, "user_id": user_id}


# ─── 1. /billing/config ───────────────────────────────────────
def test_config_reports_correct_provider():
    """Provider should reflect env: 'paymongo' when key set, 'mock' otherwise."""
    r = requests.get(f"{API}/billing/config")
    assert r.status_code == 200
    body = r.json()
    if PAYMONGO_LIVE:
        assert body["provider"] == "paymongo"
        assert body["public_key"].startswith("pk_")
        assert body.get("flow") == "checkout_session"
    else:
        assert body["provider"] == "mock"
        assert body["public_key"] == ""


# ─── 2. /billing/plans catalog ────────────────────────────────
def test_plans_catalog_intact():
    r = requests.get(f"{API}/billing/plans")
    assert r.status_code == 200
    plans = r.json()
    for tier in ("solo", "pro", "reseller"):
        assert tier in plans, f"missing tier {tier}"
        assert "amount_php" in plans[tier]
        assert "name" in plans[tier]
    assert plans["solo"]["amount_php"] == 499.0
    assert plans["pro"]["amount_php"] == 999.0
    assert plans["reseller"]["amount_php"] == 2499.0


# ─── 3. /billing/checkout requires auth ───────────────────────
def test_checkout_requires_auth():
    r = requests.post(f"{API}/billing/checkout", json={"plan": "solo"})
    assert r.status_code == 401


# ─── 4. checkout activation (mode-aware) ──────────────────────
def test_checkout_activates_subscription(fresh_user, db):
    """In mock mode, checkout activates immediately.
    In live mode, checkout returns a Checkout Session URL + status='incomplete'."""
    s = fresh_user["session"]
    r = s.post(f"{API}/billing/checkout", json={"plan": "solo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["subscription_id"].startswith("s_")

    if PAYMONGO_LIVE:
        assert body["provider"] == "paymongo"
        assert body["flow"] == "checkout_session"
        assert body["redirect_url"].startswith("https://checkout.paymongo.com/")
        assert body["checkout_session_id"].startswith("cs_")
        # Sub exists in incomplete state until webhook fires
        sub_doc = db.subscriptions.find_one(
            {"user_id": fresh_user["user_id"]}, {"_id": 0}
        )
        assert sub_doc is not None
        assert sub_doc["status"] == "incomplete"
        assert sub_doc["provider"] == "paymongo"
    else:
        assert body["provider"] == "mock"
        user_doc = db.users.find_one({"user_id": fresh_user["user_id"]}, {"_id": 0})
        assert user_doc["subscription_status"] == "active"
        sub_doc = db.subscriptions.find_one(
            {"user_id": fresh_user["user_id"], "status": "active"}, {"_id": 0}
        )
        assert sub_doc["provider"] == "mock"


# ─── 5. /billing/subscription returns subscription doc ────────
def test_get_subscription_returns_doc(fresh_user):
    """Returned status depends on mode (mock=active, live=incomplete)."""
    s = fresh_user["session"]
    r = s.get(f"{API}/billing/subscription")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body is not None
    assert body["plan"] == "solo"
    if PAYMONGO_LIVE:
        assert body["status"] == "incomplete"
        assert body["provider"] == "paymongo"
    else:
        assert body["status"] == "active"
        assert body["provider"] == "mock"


# ─── 6. /attach-payment was removed in Checkout Sessions refactor ─
@pytest.mark.skip(reason="/billing/attach-payment was removed when we pivoted to "
                          "Checkout Sessions (Subscriptions API requires PayMongo activation). "
                          "Card collection now happens on PayMongo's hosted checkout page.")
def test_attach_payment_400_when_no_keys(fresh_user):
    pass


# ─── 7. /billing/cancel flips status ──────────────────────────
def test_cancel_subscription(fresh_user, db):
    s = fresh_user["session"]
    r = s.post(f"{API}/billing/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    user_doc = db.users.find_one({"user_id": fresh_user["user_id"]}, {"_id": 0})
    assert user_doc["subscription_status"] == "canceled"

    canceled_sub = db.subscriptions.find_one(
        {"user_id": fresh_user["user_id"], "status": "canceled"}, {"_id": 0}
    )
    assert canceled_sub is not None
    assert "canceled_at" in canceled_sub

    # GET /subscription should now return None (only active|incomplete|past_due)
    r2 = s.get(f"{API}/billing/subscription")
    assert r2.status_code == 200
    assert r2.json() is None


# ─── 8. webhook accepts signed payload (or unverified when secret empty) ─
def test_webhook_accepts_signed_payload(db):
    """Sign the body when PAYMONGO_WEBHOOK_SECRET is set; otherwise send
    unsigned. Both paths should return 200 and persist a paymongo_events row."""
    payload = {
        "data": {
            "attributes": {
                "type": "subscription.updated",
                "data": {
                    "id": f"sub_TEST_{uuid.uuid4().hex[:8]}",
                    "attributes": {"status": "active"},
                },
            }
        }
    }
    body = json.dumps(payload).encode()
    r = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Paymongo-Signature": _sign(body),
        },
    )
    assert r.status_code == 200, r.text
    body_json = r.json()
    assert body_json["status"] == "received"
    assert body_json["event"] == "subscription.updated"

    # Background task should have inserted into paymongo_events
    time.sleep(1.2)
    ev = db.paymongo_events.find_one(
        {"object_id": payload["data"]["attributes"]["data"]["id"]}, {"_id": 0}
    )
    assert ev is not None
    assert ev["event_type"] == "subscription.updated"


# ─── 9. webhook status-mapping (cancelled / unpaid) ───────────
@pytest.mark.parametrize("paymongo_status,local_status", [
    ("cancelled", "canceled"),
    ("incomplete_cancelled", "canceled"),
    ("unpaid", "past_due"),
])
def test_webhook_status_mapping(db, paymongo_status, local_status):
    # Seed a fake subscription with paymongo_subscription_id
    user_id = f"u_test_{uuid.uuid4().hex[:10]}"
    pm_sub_id = f"sub_TEST_{uuid.uuid4().hex[:10]}"
    db.users.insert_one({
        "user_id": user_id,
        "email": _new_email("map"),
        "name": "Map Test",
        "subscription_status": "active",
        "subscription_plan": "solo",
    })
    db.subscriptions.insert_one({
        "subscription_id": f"s_{uuid.uuid4().hex[:14]}",
        "user_id": user_id,
        "plan": "solo",
        "amount_php": 499.0,
        "status": "active",
        "provider": "paymongo",
        "paymongo_subscription_id": pm_sub_id,
    })

    payload = {
        "data": {"attributes": {
            "type": "subscription.updated",
            "data": {"id": pm_sub_id, "attributes": {"status": paymongo_status}},
        }}
    }
    body = json.dumps(payload).encode()
    r = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={"Content-Type": "application/json", "Paymongo-Signature": _sign(body)},
    )
    assert r.status_code == 200

    # Wait for background task
    time.sleep(1.5)
    sub_doc = db.subscriptions.find_one({"paymongo_subscription_id": pm_sub_id}, {"_id": 0})
    assert sub_doc is not None
    assert sub_doc["status"] == local_status, (
        f"PayMongo {paymongo_status} should map to {local_status}, got {sub_doc['status']}"
    )

    # Cleanup
    db.subscriptions.delete_many({"paymongo_subscription_id": pm_sub_id})
    db.users.delete_many({"user_id": user_id})


# ─── 10. invoice.paid creates payment + flips active ──────────
def test_webhook_invoice_paid_creates_payment_and_activates(db):
    user_id = f"u_test_{uuid.uuid4().hex[:10]}"
    pm_sub_id = f"sub_TEST_{uuid.uuid4().hex[:10]}"
    invoice_id = f"inv_TEST_{uuid.uuid4().hex[:10]}"
    db.users.insert_one({
        "user_id": user_id,
        "email": _new_email("paid"),
        "name": "Paid Test",
        "subscription_status": "incomplete",
        "subscription_plan": "solo",
    })
    db.subscriptions.insert_one({
        "subscription_id": f"s_{uuid.uuid4().hex[:14]}",
        "user_id": user_id,
        "plan": "solo",
        "amount_php": 499.0,
        "status": "incomplete",
        "provider": "paymongo",
        "paymongo_subscription_id": pm_sub_id,
    })

    payload = {
        "data": {"attributes": {
            "type": "subscription.invoice.paid",
            "data": {
                "id": invoice_id,
                "attributes": {"subscription_id": pm_sub_id, "amount": 49900},
            },
        }}
    }
    body = json.dumps(payload).encode()
    r = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={"Content-Type": "application/json", "Paymongo-Signature": _sign(body)},
    )
    assert r.status_code == 200
    time.sleep(1.5)

    pay = db.paymongo_payments.find_one({"invoice_id": invoice_id}, {"_id": 0})
    assert pay is not None
    assert pay["paymongo_subscription_id"] == pm_sub_id
    assert pay["status"] == "paid"
    assert pay["amount_php"] == 499.0

    sub_doc = db.subscriptions.find_one({"paymongo_subscription_id": pm_sub_id}, {"_id": 0})
    assert sub_doc["status"] == "active"

    # Cleanup
    db.subscriptions.delete_many({"paymongo_subscription_id": pm_sub_id})
    db.users.delete_many({"user_id": user_id})
    db.paymongo_payments.delete_many({"invoice_id": invoice_id})


# ─── 11. invoice.payment_failed flips past_due ────────────────
def test_webhook_invoice_payment_failed_flips_past_due(db):
    user_id = f"u_test_{uuid.uuid4().hex[:10]}"
    pm_sub_id = f"sub_TEST_{uuid.uuid4().hex[:10]}"
    db.users.insert_one({
        "user_id": user_id,
        "email": _new_email("failed"),
        "name": "Failed Test",
        "subscription_status": "active",
        "subscription_plan": "solo",
    })
    db.subscriptions.insert_one({
        "subscription_id": f"s_{uuid.uuid4().hex[:14]}",
        "user_id": user_id,
        "plan": "solo",
        "amount_php": 499.0,
        "status": "active",
        "provider": "paymongo",
        "paymongo_subscription_id": pm_sub_id,
    })

    payload = {
        "data": {"attributes": {
            "type": "subscription.invoice.payment_failed",
            "data": {
                "id": f"inv_TEST_{uuid.uuid4().hex[:8]}",
                "attributes": {"subscription_id": pm_sub_id},
            },
        }}
    }
    body = json.dumps(payload).encode()
    r = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={"Content-Type": "application/json", "Paymongo-Signature": _sign(body)},
    )
    assert r.status_code == 200
    time.sleep(1.5)

    sub_doc = db.subscriptions.find_one({"paymongo_subscription_id": pm_sub_id}, {"_id": 0})
    assert sub_doc["status"] == "past_due"
    user_doc = db.users.find_one({"user_id": user_id}, {"_id": 0})
    assert user_doc["subscription_status"] == "past_due"

    db.subscriptions.delete_many({"paymongo_subscription_id": pm_sub_id})
    db.users.delete_many({"user_id": user_id})


# ─── 12. paymongo.verify_webhook_signature unit tests ────────
def _add_backend_to_path():
    p = "/app/backend"
    if p not in sys.path:
        sys.path.insert(0, p)


def test_verify_webhook_signature_valid_te():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    secret = "whsec_test_secret_xyz"
    body = b'{"hello":"world"}'
    ts = "1700000000"
    expected = hmac.new(
        secret.encode(),
        f"{ts}.{body.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()
    header = f"t={ts},te={expected},li=invalid_sig"
    assert pm.verify_webhook_signature(body=body, signature_header=header, secret=secret) is True


def test_verify_webhook_signature_valid_li():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    secret = "whsec_live"
    body = b'{"a":1}'
    ts = "1700000123"
    expected = hmac.new(
        secret.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    header = f"t={ts},te=zzz,li={expected}"
    assert pm.verify_webhook_signature(body=body, signature_header=header, secret=secret) is True


def test_verify_webhook_signature_mismatch_returns_false():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    header = "t=1700000000,te=deadbeef,li=cafebabe"
    assert pm.verify_webhook_signature(
        body=b'{"x":1}', signature_header=header, secret="whsec_xyz"
    ) is False


def test_verify_webhook_signature_missing_t_returns_false():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    header = "te=abc,li=def"
    assert pm.verify_webhook_signature(
        body=b'{}', signature_header=header, secret="whsec_xyz"
    ) is False


def test_verify_webhook_signature_empty_secret_returns_false():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    assert pm.verify_webhook_signature(
        body=b'{}', signature_header="t=1,te=abc", secret=""
    ) is False


def test_paymongo_is_configured_matches_env():
    _add_backend_to_path()
    import paymongo as pm
    importlib.reload(pm)
    if PAYMONGO_LIVE:
        assert pm.is_configured() is True
        assert pm.public_key().startswith("pk_")
    else:
        assert pm.is_configured() is False
        assert pm.public_key() == ""


# ─── 13. webhook signature enforcement matches secret presence ─
def test_webhook_signature_gate_matches_env(db):
    """When PAYMONGO_WEBHOOK_SECRET is set → bad sig must return 403.
    When secret is empty → unverified is accepted with 200."""
    payload = {"data": {"attributes": {"type": "ping", "data": {}}}}
    body = json.dumps(payload).encode()
    # Always send an obviously-bad signature
    r = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Paymongo-Signature": "t=1,te=bogus,li=bogus",
        },
    )
    if WEBHOOK_SECRET_SET:
        assert r.status_code == 403, r.text
        assert r.json().get("error") == "invalid signature"
    else:
        assert r.status_code == 200
        assert r.json()["status"] == "received"

    # And a properly-signed payload should always succeed
    r2 = requests.post(
        f"{API}/billing/webhook/paymongo",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Paymongo-Signature": _sign(body),
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "received"


# ─── 14. User model exposes managed_by_cpa_id (default None) ──
def test_user_has_managed_by_cpa_id_field_on_register():
    s = requests.Session()
    email = _new_email("cpa")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "CPA Field Test",
    })
    assert r.status_code == 200, r.text
    user = r.json()
    # Field should be present and None for new direct registrations
    assert "managed_by_cpa_id" in user, "User response missing managed_by_cpa_id"
    assert user["managed_by_cpa_id"] is None


def test_user_model_managed_by_cpa_id_serializes_for_existing_user(db):
    """Existing users without managed_by_cpa_id should still serialize via /auth/me."""
    s = requests.Session()
    email = _new_email("legacy")
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass1234!", "name": "Legacy",
    })
    assert r.status_code == 200
    user_id = r.json()["user_id"]
    # Simulate legacy user — strip the field
    db.users.update_one({"user_id": user_id}, {"$unset": {"managed_by_cpa_id": ""}})
    me = s.get(f"{API}/auth/me")
    assert me.status_code == 200, me.text
    body = me.json()
    # Should not 500; field defaults to None when absent
    assert body.get("managed_by_cpa_id") is None


# ─── 15. Regression: prior endpoints still healthy ────────────
def test_regression_admin_and_auth_health():
    # Admin login still works
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    me = s.get(f"{API}/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
