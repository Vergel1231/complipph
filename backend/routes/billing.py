"""Billing routes — MOCK provider, structured for clean PayMongo swap-in.

PayMongo swap notes:
- Replace `_mock_create_checkout` with PayMongo `payment_intents` / `links` API call
- Add webhook handler at /api/billing/webhook/paymongo to update subscription status
- Stripe path can mirror this with /api/billing/checkout?provider=stripe
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException

from auth import get_current_user
from models import CheckoutRequest, Subscription

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


@router.post("/checkout")
async def checkout(req: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    if req.plan not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan = PLAN_CATALOG[req.plan]

    # MOCK: create subscription immediately. Replace with PayMongo session URL.
    sub = Subscription(
        user_id=user["user_id"],
        plan=req.plan,
        amount_php=plan["amount_php"],
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
        "subscription_id": sub.subscription_id,
        "redirect_url": None,  # PayMongo will return checkout URL here
        "provider": "mock",
        "message": "Subscription activated (MOCKED — PayMongo swap-in ready).",
    }


@router.get("/subscription")
async def my_subscription(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    sub = await db.subscriptions.find_one(
        {"user_id": user["user_id"], "status": "active"}, {"_id": 0}
    )
    return sub  # may be None


@router.post("/cancel")
async def cancel(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    await db.subscriptions.update_many(
        {"user_id": user["user_id"], "status": "active"},
        {"$set": {"status": "canceled", "canceled_at": datetime.now(timezone.utc).isoformat()}},
    )
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"subscription_status": "canceled"}},
    )
    return {"ok": True}
