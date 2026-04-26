"""PayMongo HTTP client wrapper.

If `PAYMONGO_SECRET_KEY` is empty, `is_configured()` returns False and callers
should fall back to mock behaviour so the app stays functional while the user
adds live credentials.

API reference: https://developers.paymongo.com/reference
"""
import os
import base64
import hmac
import hashlib
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.paymongo.com/v1"


def is_configured() -> bool:
    return bool(os.environ.get("PAYMONGO_SECRET_KEY"))


def public_key() -> str:
    return os.environ.get("PAYMONGO_PUBLIC_KEY", "")


def _auth_header() -> dict:
    sk = os.environ.get("PAYMONGO_SECRET_KEY", "")
    token = base64.b64encode(f"{sk}:".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{API_BASE}{path}", json=payload, headers=_auth_header())
        if r.status_code >= 400:
            logger.error(f"PayMongo {path} failed: {r.status_code} {r.text}")
            raise PayMongoError(r.status_code, r.text)
        return r.json()


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{API_BASE}{path}", headers=_auth_header())
        if r.status_code >= 400:
            logger.error(f"PayMongo {path} failed: {r.status_code} {r.text}")
            raise PayMongoError(r.status_code, r.text)
        return r.json()


class PayMongoError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"PayMongo error {status}: {body[:200]}")


# ─── Plans ──────────────────────────────────────────────────────
async def create_plan(*, name: str, description: str, amount_php: float,
                      interval: str = "month", interval_count: int = 1) -> dict:
    """Create a recurring billing plan. Amount is converted to centavos."""
    return await _post("/plans", {
        "data": {"attributes": {
            "name": name,
            "description": description,
            "amount": int(round(amount_php * 100)),
            "currency": "PHP",
            "interval": interval,
            "interval_count": interval_count,
        }}
    })


# ─── Customers ──────────────────────────────────────────────────
async def create_customer(*, name: str, email: str, phone: Optional[str] = None) -> dict:
    attrs = {"name": name, "email": email}
    if phone:
        attrs["phone"] = phone
    return await _post("/customers", {"data": {"attributes": attrs}})


# ─── Subscriptions ──────────────────────────────────────────────
async def create_subscription(*, customer_id: str, plan_id: str,
                              reference_number: Optional[str] = None) -> dict:
    attrs = {"customer_id": customer_id, "plan_id": plan_id}
    if reference_number:
        attrs["reference_number"] = reference_number
    return await _post("/subscriptions", {"data": {"attributes": attrs}})


async def cancel_subscription(subscription_id: str) -> dict:
    return await _post(f"/subscriptions/{subscription_id}/cancel", {"data": {"attributes": {}}})


async def retrieve_subscription(subscription_id: str) -> dict:
    return await _get(f"/subscriptions/{subscription_id}")


# ─── Payment intents ────────────────────────────────────────────
async def attach_payment_method(*, payment_intent_id: str, payment_method_id: str,
                                client_key: str, return_url: str) -> dict:
    return await _post(f"/payment_intents/{payment_intent_id}/attach", {
        "data": {"attributes": {
            "client_key": client_key,
            "payment_method": payment_method_id,
            "return_url": return_url,
        }}
    })


# ─── Webhook signature verification ─────────────────────────────
def verify_webhook_signature(*, body: bytes, signature_header: str,
                             secret: Optional[str] = None) -> bool:
    """Verify a PayMongo webhook.

    Header format: `t=<unix_ts>,te=<test_sig>,li=<live_sig>`
    Signature is HMAC-SHA256 over `<timestamp>.<body>` using the webhook secret.
    """
    secret = secret or os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
    if not secret or not signature_header:
        return False
    parts = {}
    for kv in signature_header.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            parts[k.strip()] = v.strip()
    timestamp = parts.get("t")
    if not timestamp:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body.decode('utf-8')}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    for cand in (parts.get("te"), parts.get("li")):
        if cand and hmac.compare_digest(cand, expected):
            return True
    return False
