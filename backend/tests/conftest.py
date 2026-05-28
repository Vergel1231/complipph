"""Shared pytest fixtures and helpers for BIR Filipino test suite.

Loads /app/backend/.env so tests always read live credentials (admin password,
PayMongo keys, webhook secret) instead of hardcoded values. This way the test
suite stays green whether keys are populated or empty.
"""
import os
import sys
import time
import hmac
import hashlib
import json as _json
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Ensure /app/backend is importable so tests can `import paymongo`, etc.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")


# ─── Public constants used across all test files ──────────────────────
def _api_base() -> str:
    env_path = Path("/app/frontend/.env")
    text = env_path.read_text()
    for line in text.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"') + "/api"
    raise RuntimeError("REACT_APP_BACKEND_URL missing from /app/frontend/.env")


API = _api_base()
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


# ─── Helpers exposed to test files via this module ────────────────────
def admin_login_session() -> requests.Session:
    """Return a requests.Session pre-authenticated as the seeded admin."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


def sign_webhook(body: bytes, secret: str | None = None, *, when: int | None = None) -> str:
    """Produce a valid PayMongo `Paymongo-Signature` header for `body`.

    Used by webhook tests so they remain valid whether
    PAYMONGO_WEBHOOK_SECRET is empty or populated.
    """
    secret = secret if secret is not None else os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
    ts = str(when if when is not None else int(time.time()))
    if not secret:
        # Backend accepts unverified webhooks when secret is empty; any header works.
        return f"t={ts},te=unsigned,li=unsigned"
    payload = f"{ts}.{body.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={ts},te={sig},li={sig}"


def paymongo_keys_configured() -> bool:
    return bool(os.environ.get("PAYMONGO_SECRET_KEY"))


def resend_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


# ─── Common fixtures ──────────────────────────────────────────────────
@pytest.fixture
def admin_session():
    s = admin_login_session()
    yield s
    s.close()


@pytest.fixture
def fresh_user_session():
    """Register + login a brand-new test user; clean up after."""
    s = requests.Session()
    email = f"test.{int(time.time()*1000)}.{os.getpid()}@example.com"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Pytest@2026", "name": "Pytest User"}, timeout=15)
    assert r.status_code == 200, f"Register failed: {r.text}"
    s.user_id = r.json()["user_id"]
    s.email = email
    yield s
    s.close()


# ─── Pytest config: deterministic JSON for HMAC ───────────────────────
def stable_json(obj: dict) -> bytes:
    """Stable JSON encoding for webhook signature tests."""
    return _json.dumps(obj, separators=(",", ":"), sort_keys=False).encode("utf-8")
