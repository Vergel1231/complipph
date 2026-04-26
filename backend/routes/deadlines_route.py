"""Deadline list and calendar endpoints."""
from fastapi import APIRouter, Request, Depends
from datetime import date

from auth import get_current_user
from deadlines import generate_upcoming_deadlines, _severity

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("/")
async def list_deadlines(request: Request, user=Depends(get_current_user)):
    """Return live-computed deadlines (always fresh `days_until`)."""
    db = request.app.state.db
    bp = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not bp:
        return []
    today = date.today()
    fresh = generate_upcoming_deadlines(
        user_id=user["user_id"],
        business_id=bp["business_id"],
        classification=bp["taxpayer_classification"],
        is_vat_registered=bp["is_vat_registered"],
        today=today,
    )
    # Mark completed where filings exist
    submitted_pairs = set()
    cursor = db.filings.find(
        {"user_id": user["user_id"], "status": "submitted"},
        {"_id": 0, "form_type": 1, "period": 1},
    )
    async for f in cursor:
        submitted_pairs.add((f["form_type"], f["period"]))
    for d in fresh:
        if (d["form_type"], d["period"]) in submitted_pairs:
            d["completed"] = True
    return fresh
