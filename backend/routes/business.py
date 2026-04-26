"""Business profile + onboarding routes."""
from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timezone
from auth import get_current_user
from models import BusinessProfile, BusinessProfileCreate
from deadlines import generate_upcoming_deadlines
from datetime import date

router = APIRouter(prefix="/business", tags=["business"])


@router.get("/profile")
async def get_profile(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    bp = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return bp  # may be None


@router.post("/profile")
async def create_or_update_profile(
    payload: BusinessProfileCreate,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    existing = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if existing:
        update = payload.model_dump()
        update["is_non_vat"] = not update["is_vat_registered"]
        await db.business_profiles.update_one(
            {"user_id": user["user_id"]}, {"$set": update}
        )
        bp = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    else:
        profile = BusinessProfile(
            user_id=user["user_id"],
            **payload.model_dump(),
            is_non_vat=not payload.is_vat_registered,
        )
        doc = profile.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.business_profiles.insert_one(doc)
        bp = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})

    # Mark user as onboarded + regenerate deadline cache
    await db.users.update_one(
        {"user_id": user["user_id"]}, {"$set": {"onboarded": True}}
    )
    # Wipe and regenerate deadlines
    await db.deadlines.delete_many({"user_id": user["user_id"]})
    deadlines = generate_upcoming_deadlines(
        user_id=user["user_id"],
        business_id=bp["business_id"],
        classification=bp["taxpayer_classification"],
        is_vat_registered=bp["is_vat_registered"],
        today=date.today(),
    )
    if deadlines:
        await db.deadlines.insert_many([{**d} for d in deadlines])
    return bp
