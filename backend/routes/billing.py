"""Billing routes — PayMongo Checkout Sessions + mock fallback.

PayMongo's native Subscriptions API requires merchant activation, so this
integration uses Checkout Sessions (universally available) with the first-month
charge on signup. Recurring monthly invoices are re-issued by the APScheduler
cron emailing a fresh checkout_url via Resend 3 days before next_billing_at.

When PAYMONGO_SECRET_KEY is empty, the mock activation path runs so the app
stays functional during development.
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import get_current_user
from models import CheckoutRequest, Subscription
import paymongo as pm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_CATALOG = {
    "solo":     {"name": "Solo Pro",       "amount_php": 499.0,  "amount_usd": 9.0,
                 "description": "1 business profile, unlimited 1701Q + 2551Q filings"},
    "pro":      {"name": "Pro+",           "amount_php": 999.0,  "amount_usd": 18.0,
                 "description": "Up to 3 business profiles, payroll module, AI assistant priority"},
    "reseller": {"name": "Reseller (CPA)", "amount_php": 2499.0, "amount_usd": 45.0,
                 "description": "Manage up to 25 client filings + dedicated CPA dashboard"},
}


@router.get("/plans")
async def list_plans():
    return PLAN_CATALOG


@router.get("/config")
async def get_config():
    """Client config probe. Frontend uses this to decide between redirect-based
    PayMongo checkout vs. mock instant activation."""
    return {
        "provider": "paymongo" if pm.is_configured() else "mock",
        # public_key stays informational; Checkout Sessions don't require it client-side
        "public_key": pm.public_key(),
        "flow": "checkout_session" if pm.is_configured() else "mock",
    }


# ─── Checkout ───────────────────────────────────────────────────
@router.post("/checkout")
async def checkout(req: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    if req.plan not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid plan")
    catalog = PLAN_CATALOG[req.plan]
    frontend_url = os.environ.get("FRONTEND_URL", "")

    # ─── PayMongo live path ────────────────────────────────────
    if pm.is_configured():
        try:
            # Pre-create a pending subscription row; webhook will activate it
            sub = Subscription(
                user_id=user["user_id"],
                plan=req.plan,
                amount_php=catalog["amount_php"],
                status="incomplete",
                provider="paymongo",
                next_billing_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            doc = sub.model_dump()
            doc["started_at"] = doc["started_at"].isoformat()
            if doc.get("next_billing_at"):
                doc["next_billing_at"] = doc["next_billing_at"].isoformat()
            await db.subscriptions.insert_one(doc)

            session_resp = await pm.create_checkout_session(
                amount_php=catalog["amount_php"],
                name=f"BIR Filipino — {catalog['name']}",
                description=catalog["description"],
                success_url=f"{frontend_url}/dashboard?billing=success&sub={sub.subscription_id}",
                cancel_url=f"{frontend_url}/pricing?billing=cancel",
                reference_number=sub.subscription_id,
                customer_email=user["email"],
                metadata={
                    "user_id": user["user_id"],
                    "subscription_id": sub.subscription_id,
                    "plan": req.plan,
                },
            )
            sdata = session_resp["data"]
            checkout_url = sdata["attributes"]["checkout_url"]
            session_id = sdata["id"]

            # Stash session id on the pending sub
            await db.subscriptions.update_one(
                {"subscription_id": sub.subscription_id},
                {"$set": {"paymongo_checkout_session_id": session_id}},
            )
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"subscription_status": "incomplete", "subscription_plan": req.plan}},
            )
            return {
                "ok": True,
                "provider": "paymongo",
                "flow": "checkout_session",
                "subscription_id": sub.subscription_id,
                "checkout_session_id": session_id,
                "redirect_url": checkout_url,
                "amount_php": catalog["amount_php"],
                "plan_name": catalog["name"],
            }
        except pm.PayMongoError as e:
            logger.error(f"PayMongo checkout failed: {e}")
            # Clean up the pending sub row to avoid orphans
            await db.subscriptions.delete_many(
                {"user_id": user["user_id"], "status": "incomplete",
                 "paymongo_checkout_session_id": {"$exists": False}}
            )
            raise HTTPException(status_code=502, detail=f"PayMongo error: {e.body[:200]}")

    # ─── Mock fallback (keys empty) ────────────────────────────
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
    body = await request.body()
    sig = request.headers.get("Paymongo-Signature", "")
    secret = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")

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
    inner = event_attrs.get("data") or {}
    db = request.app.state.db

    background_tasks.add_task(_process_webhook_event, db, event_type, inner)
    return JSONResponse(status_code=200, content={"status": "received", "event": event_type})


async def _process_webhook_event(db, event_type: str, inner: dict):
    inner_id = inner.get("id") if isinstance(inner, dict) else None
    attrs = (inner.get("attributes") or {}) if isinstance(inner, dict) else {}
    logger.info(f"PayMongo webhook: {event_type} id={inner_id}")

    # Always audit
    await db.paymongo_events.insert_one({
        "event_type": event_type,
        "object_id": inner_id,
        "attributes": attrs,
        "received_at": datetime.now(timezone.utc).isoformat(),
    })

    # ─── Checkout Session paid → activate subscription ─────────
    if event_type == "checkout_session.payment.paid":
        # PayMongo sends the checkout_session object as `inner`
        reference_number = attrs.get("reference_number")  # = our subscription_id
        metadata = attrs.get("metadata") or {}
        user_id = metadata.get("user_id")
        subscription_id = metadata.get("subscription_id") or reference_number

        if subscription_id:
            await db.subscriptions.update_one(
                {"subscription_id": subscription_id},
                {"$set": {
                    "status": "active",
                    "paymongo_checkout_session_id": inner_id,
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            sub = await db.subscriptions.find_one({"subscription_id": subscription_id}, {"_id": 0})
            if sub:
                await db.users.update_one(
                    {"user_id": sub["user_id"]},
                    {"$set": {
                        "subscription_status": "active",
                        "subscription_plan": sub.get("plan", "solo"),
                        "subscription_started_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )

        # Log the payment
        payments = attrs.get("payments") or []
        if payments:
            p0 = payments[0] or {}
            pay_attrs = p0.get("attributes") or {}
            await db.paymongo_payments.insert_one({
                "payment_id": p0.get("id"),
                "subscription_id": subscription_id,
                "user_id": user_id,
                "amount_php": (pay_attrs.get("amount") or 0) / 100,
                "currency": pay_attrs.get("currency", "PHP"),
                "status": pay_attrs.get("status", "paid"),
                "source_type": (pay_attrs.get("source") or {}).get("type"),
                "received_at": datetime.now(timezone.utc).isoformat(),
            })

    # ─── Payment-level signals (backup path) ───────────────────
    elif event_type in ("payment.paid", "payment.failed"):
        # Surface these for audit; the checkout_session event is the canonical activator
        pass
