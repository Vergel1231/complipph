"""Admin dashboard routes — MRR, churn, user count, BIR rules editor."""
from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timezone, timedelta

from auth import require_admin
from models import BirRule, BirRuleUpdate
from bir_engine import DEFAULT_RULES

router = APIRouter(prefix="/admin", tags=["admin"])

PLAN_PRICES = {"solo": 499.0, "pro": 999.0, "reseller": 2499.0}


@router.get("/metrics")
async def metrics(request: Request, _admin=Depends(require_admin)):
    db = request.app.state.db
    total_users = await db.users.count_documents({})
    active_subs = await db.subscriptions.count_documents({"status": "active"})
    canceled_subs = await db.subscriptions.count_documents({"status": "canceled"})
    # MRR = sum of active subscription PHP amounts
    cursor = db.subscriptions.find({"status": "active"}, {"_id": 0, "amount_php": 1})
    mrr_total = 0.0
    async for s in cursor:
        mrr_total += float(s.get("amount_php") or 0)
    total_subs_ever = active_subs + canceled_subs
    churn_rate = (canceled_subs / total_subs_ever * 100) if total_subs_ever else 0.0
    total_filings = await db.filings.count_documents({})
    # Last 30 days signups
    thirty = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    new_users_30d = await db.users.count_documents({"created_at": {"$gte": thirty}})
    return {
        "mrr_php": round(mrr_total, 2),
        "active_subscribers": active_subs,
        "canceled_subscribers": canceled_subs,
        "churn_rate_pct": round(churn_rate, 2),
        "total_users": total_users,
        "new_users_30d": new_users_30d,
        "total_filings": total_filings,
    }


@router.get("/users")
async def list_users(request: Request, _admin=Depends(require_admin)):
    db = request.app.state.db
    cursor = db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).limit(200)
    return await cursor.to_list(200)


# ─── BIR Rules editor ───────────────────────────────────────────
@router.get("/bir-rules")
async def list_rules(request: Request, _admin=Depends(require_admin)):
    db = request.app.state.db
    cursor = db.bir_rules.find({}, {"_id": 0})
    saved = {}
    async for d in cursor:
        saved[d["rule_key"]] = d
    # Merge defaults with saved overrides
    out = []
    for k, default_val in DEFAULT_RULES.items():
        if k in saved:
            out.append(saved[k])
        else:
            out.append({
                "rule_key": k,
                "rule_value": default_val,
                "description": _describe(k),
                "effective_date": "default",
                "updated_at": None,
            })
    return out


@router.put("/bir-rules/{rule_key}")
async def update_rule(
    rule_key: str,
    payload: BirRuleUpdate,
    request: Request,
    _admin=Depends(require_admin),
):
    db = request.app.state.db
    if rule_key not in DEFAULT_RULES:
        raise HTTPException(status_code=400, detail="Unknown rule key")
    update = {
        "rule_key": rule_key,
        "rule_value": payload.rule_value,
        "description": payload.description or _describe(rule_key),
        "effective_date": payload.effective_date or datetime.now(timezone.utc).date().isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bir_rules.update_one(
        {"rule_key": rule_key}, {"$set": update}, upsert=True
    )
    return update


def _describe(key: str) -> str:
    descriptions = {
        "personal_exemption": "Personal exemption threshold (₱) for 8% flat tax",
        "flat_tax_rate": "8% flat tax rate (decimal)",
        "percentage_tax_rate": "2551Q percentage tax rate (decimal)",
        "grad_b1_threshold": "Graduated bracket 1 cutoff (tax-free)",
        "grad_b2_threshold": "Graduated bracket 2 cutoff",
        "grad_b2_rate": "Graduated bracket 2 marginal rate",
        "grad_b3_threshold": "Graduated bracket 3 cutoff",
        "grad_b3_base": "Graduated bracket 3 base tax",
        "grad_b3_rate": "Graduated bracket 3 marginal rate",
        "grad_b4_threshold": "Graduated bracket 4 cutoff",
        "grad_b4_base": "Graduated bracket 4 base tax",
        "grad_b4_rate": "Graduated bracket 4 marginal rate",
        "grad_b5_threshold": "Graduated bracket 5 cutoff",
        "grad_b5_base": "Graduated bracket 5 base tax",
        "grad_b5_rate": "Graduated bracket 5 marginal rate",
        "grad_b6_base": "Graduated bracket 6 base tax",
        "grad_b6_rate": "Graduated bracket 6 marginal rate",
    }
    return descriptions.get(key, key)
