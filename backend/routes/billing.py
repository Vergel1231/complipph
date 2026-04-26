"""Billing routes — PayMongo live integration with mock fallback.

When `PAYMONGO_SECRET_KEY` is empty, the existing mock activation flow runs so
the app continues to work. When the key is populated, real PayMongo customer +
subscription + payment-intent objects are created and returned to the frontend
so it can collect the card via PayMongo's public-key tokenization.

Phase 4 swap-in: replace mock branch entirely once PayMongo is verified working.
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from models import CheckoutRequest, Subscription
import paymongo as pm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_CATALOG = {
    "solo":     {"name": "Solo Pro",      "amount_php": 499.0,  "amount_usd": 9.0,
                 "description": "1 business profile, unlimited 1701Q + 2551Q filings"},
    "pro":      {"name": "Pro+",          "amount_php": 999.0,  "amount_usd": 18.0,
                 "description": "Up to 3 business profiles, payroll module, AI assistant priority"},
    "reseller": {"name": "Reseller (CPA)", "amount_php": 2499.0, "amount_usd": 45.0,
                 "description": "Manage up to 25 client filings + dedicated CPA dashboard"},
}


@router.get("/plans")
async def list_plans():
    return PLAN_CATALOG


@router.get("/config")
async def get_config():
    """Public client config — used by the frontend to know whether to render
    PayMongo card form or fall through to mock checkout."""
    return {
        "provider": "paymongo" if pm.is_configured() else "mock",
        "public_key": pm.public_key(),  # safe to expose
    }


# ─── Helper: ensure PayMongo plan exists for a tier ─────────────
async def _ensure_paymongo_plan(db, tier: str) -> str:
    """Create the PayMongo plan for `tier` once and cache its ID in MongoDB."""
    cached = await db.paymongo_plans.find_one({"tier": tier}, {"_id": 0})
    if cached:
        return cached["paymongo_plan_id"]
    catalog = PLAN_CATALOG[tier]
    resp = await pm.create_plan(
        name=f"BIR Filipino — {catalog['name']}",
        description=catalog["description"],
        amount_php=catalog["amount_php"],
    )
    plan_id = resp["data"]["id"]
    await db.paymongo_plans.insert_one({
        "tier": tier,
        "paymongo_plan_id": plan_id,
        "amount_php": catalog["amount_php"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"Created PayMongo plan for tier={tier}: {plan_id}")
    return plan_id


# ─── Checkout ───────────────────────────────────────────────────
@router.post("/checkout")
async def checkout(req: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    if req.plan not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid plan")
    catalog = PLAN_CATALOG[req.plan]

    # ─── PayMongo live path ────────────────────────────────────
    if pm.is_configured():
        try:
            paymongo_plan_id = await _ensure_paymongo_plan(db, req.plan)
            # Reuse existing PayMongo customer if user has subscribed before
            existing_sub = await db.subscriptions.find_one(
                {"user_id": user["user_id"]}, {"_id": 0}
            )
            if existing_sub and existing_sub.get("paymongo_customer_id"):
                customer_id = existing_sub["paymongo_customer_id"]
            else:
                cust_resp = await pm.create_customer(name=user["name"], email=user["email"])
                customer_id = cust_resp["data"]["id"]

            sub_resp = await pm.create_subscription(
                customer_id=customer_id,
                plan_id=paymongo_plan_id,
                reference_number=user["user_id"],
            )
            sub_data = sub_resp["data"]
            sub_id = sub_data["id"]
            invoice = (sub_data.get("attributes", {}) or {}).get("latest_invoice", {}) or {}
            pi = (invoice.get("payment_intent", {}) or {})
            payment_intent_id = pi.get("id")
            client_key = (pi.get("attributes", {}) or {}).get("client_key")

            # Persist incomplete subscription (will flip to active on webhook)
            sub = Subscription(
                user_id=user["user_id"],
                plan=req.plan,
                amount_php=catalog["amount_php"],
                status="incomplete",
                provider="paymongo",
                paymongo_subscription_id=sub_id,
                paymongo_customer_id=customer_id,
                paymongo_plan_id=paymongo_plan_id,
                next_billing_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            doc = sub.model_dump()
            doc["started_at"] = doc["started_at"].isoformat()
            if doc.get("next_billing_at"):
                doc["next_billing_at"] = doc["next_billing_at"].isoformat()
            await db.subscriptions.insert_one(doc)
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "subscription_status": "incomplete",
                    "subscription_plan": req.plan,
                }},
            )
            return {
                "ok": True,
                "provider": "paymongo",
                "subscription_id": sub.subscription_id,
                "paymongo_subscription_id": sub_id,
                "paymongo_customer_id": customer_id,
                "payment_intent_id": payment_intent_id,
                "client_key": client_key,
                "amount_php": catalog["amount_php"],
                "plan_name": catalog["name"],
                "message": "Collect payment method, then POST /api/billing/attach-payment.",
            }
        except pm.PayMongoError as e:
            logger.error(f"PayMongo checkout failed: {e}")
            raise HTTPException(status_code=502, detail="PayMongo error — check keys & try again.")

    # ─── Mock fallback ─────────────────────────────────────────
    sub = Subscription(
        user_id=user["user_id"],
        plan=req.plan,
        amount_php=catalog["amount_php"],
        status="active",
        provider="mock",
        next_billing_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    doc = sub.model_dump()
    doc["started_at"] = doc["started_at"].isoformat()
    if doc.get("next_billing_at"):
        doc["next_billing_at"] = doc["next_billing_at"].isoformat()
    await db.subscriptions.insert_one(doc)
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "subscription_status": "active",
            "subscription_plan": req.plan,
            "subscription_started_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {
        "ok": True,
        "provider": "mock",
        "subscription_id": sub.subscription_id,
        "redirect_url": None,
        "message": "Subscription activated (MOCK — set PAYMONGO_SECRET_KEY for live billing).",
    }


# ─── Attach payment method (PayMongo path) ──────────────────────
class AttachRequest(BaseModel):
    payment_intent_id: str
    payment_method_id: str
    client_key: str


@router.post("/attach-payment")
async def attach_payment(payload: AttachRequest, request: Request, user=Depends(get_current_user)):
    if not pm.is_configured():
        raise HTTPException(status_code=400, detail="PayMongo not configured.")
    frontend_url = os.environ.get("FRONTEND_URL", "")
    return_url = f"{frontend_url}/dashboard?billing=return"
    try:
        resp = await pm.attach_payment_method(
            payment_intent_id=payload.payment_intent_id,
            payment_method_id=payload.payment_method_id,
            client_key=payload.client_key,
            return_url=return_url,
        )
    except pm.PayMongoError as e:
        raise HTTPException(status_code=502, detail=f"PayMongo attach failed: {e.body[:200]}")
    pi = (resp.get("data", {}) or {}).get("attributes", {}) or {}
    status = pi.get("status")
    next_action = (pi.get("next_action") or {}).get("redirect", {}) or {}
    return {
        "ok": True,
        "status": status,
        "next_action_url": next_action.get("url"),
    }


# ─── Subscription state ─────────────────────────────────────────
@router.get("/subscription")
async def my_subscription(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    sub = await db.subscriptions.find_one(
        {"user_id": user["user_id"], "status": {"$in": ["active", "incomplete", "past_due"]}},
        {"_id": 0},
        sort=[("started_at", -1)],
    )
    return sub  # may be None


@router.post("/cancel")
async def cancel(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    sub = await db.subscriptions.find_one(
        {"user_id": user["user_id"], "status": {"$in": ["active", "incomplete", "past_due"]}},
        {"_id": 0},
        sort=[("started_at", -1)],
    )
    # Cancel upstream if PayMongo
    if sub and sub.get("provider") == "paymongo" and sub.get("paymongo_subscription_id") and pm.is_configured():
        try:
            await pm.cancel_subscription(sub["paymongo_subscription_id"])
        except pm.PayMongoError as e:
            logger.warning(f"PayMongo cancel failed (will mark local canceled): {e}")
    await db.subscriptions.update_many(
        {"user_id": user["user_id"], "status": {"$in": ["active", "incomplete", "past_due"]}},
        {"$set": {"status": "canceled", "canceled_at": datetime.now(timezone.utc).isoformat()}},
    )
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"subscription_status": "canceled"}},
    )
    return {"ok": True}


# ─── Webhook ────────────────────────────────────────────────────
@router.post("/webhook/paymongo")
async def paymongo_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive subscription / invoice / payment events from PayMongo.
    Always returns 200 (per PayMongo retry semantics) once signature is verified."""
    body = await request.body()
    sig = request.headers.get("Paymongo-Signature", "")
    secret = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")

    # When secret is empty (pre-keys), accept in dev but log loudly
    if secret:
        if not pm.verify_webhook_signature(body=body, signature_header=sig, secret=secret):
            logger.warning("PayMongo webhook: invalid signature")
            return JSONResponse(status_code=403, content={"error": "invalid signature"})
    else:
        logger.warning("PAYMONGO_WEBHOOK_SECRET not set — accepting webhook unverified.")

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        return JSONResponse(status_code=200, content={"status": "bad-payload"})

    event_attrs = (payload.get("data") or {}).get("attributes") or {}
    event_type = event_attrs.get("type")
    inner = (event_attrs.get("data") or {})
    db = request.app.state.db

    background_tasks.add_task(_process_webhook_event, db, event_type, inner)
    return JSONResponse(status_code=200, content={"status": "received", "event": event_type})


async def _process_webhook_event(db, event_type: str, inner: dict):
    sub_id = inner.get("id") if isinstance(inner, dict) else None
    attrs = (inner.get("attributes") or {}) if isinstance(inner, dict) else {}
    logger.info(f"PayMongo webhook event: {event_type} sub_id={sub_id}")

    # Persist raw event for audit
    await db.paymongo_events.insert_one({
        "event_type": event_type,
        "object_id": sub_id,
        "attributes": attrs,
        "received_at": datetime.now(timezone.utc).isoformat(),
    })

    if event_type in ("subscription.activated", "subscription.updated"):
        new_status = attrs.get("status") or "active"
        # Map PayMongo statuses to our internal ones
        status_map = {
            "active": "active",
            "incomplete": "incomplete",
            "past_due": "past_due",
            "unpaid": "past_due",
            "cancelled": "canceled",
            "incomplete_cancelled": "canceled",
        }
        local_status = status_map.get(new_status, new_status)
        result = await db.subscriptions.update_one(
            {"paymongo_subscription_id": sub_id},
            {"$set": {"status": local_status}},
        )
        if result.matched_count:
            sub = await db.subscriptions.find_one({"paymongo_subscription_id": sub_id}, {"_id": 0})
            await db.users.update_one(
                {"user_id": sub["user_id"]},
                {"$set": {
                    "subscription_status": local_status,
                    "subscription_started_at": datetime.now(timezone.utc).isoformat() if local_status == "active" else None,
                }},
            )
    elif event_type == "subscription.invoice.paid":
        subscription_id = attrs.get("subscription_id")
        amount = attrs.get("amount", 0)
        await db.paymongo_payments.insert_one({
            "paymongo_subscription_id": subscription_id,
            "amount_php": (amount or 0) / 100,
            "status": "paid",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "invoice_id": sub_id,
        })
        if subscription_id:
            await db.subscriptions.update_one(
                {"paymongo_subscription_id": subscription_id},
                {"$set": {"status": "active"}},
            )
    elif event_type == "subscription.invoice.payment_failed":
        subscription_id = attrs.get("subscription_id")
        if subscription_id:
            await db.subscriptions.update_one(
                {"paymongo_subscription_id": subscription_id},
                {"$set": {"status": "past_due"}},
            )
            sub = await db.subscriptions.find_one({"paymongo_subscription_id": subscription_id}, {"_id": 0})
            if sub:
                await db.users.update_one(
                    {"user_id": sub["user_id"]},
                    {"$set": {"subscription_status": "past_due"}},
                )
