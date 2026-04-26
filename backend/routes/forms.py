"""BIR form generation + filing history."""
from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timezone
from typing import Optional

from auth import get_current_user
from models import FormGenerateRequest, Filing
from bir_engine import compute_1701q, compute_2551q, get_rules, is_2551q_required

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/generate")
async def generate_form(
    payload: FormGenerateRequest,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    bp = await db.business_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not bp:
        raise HTTPException(status_code=400, detail="Complete your business profile first")

    rules = await get_rules(db)
    if payload.form_type == "1701Q":
        computed = compute_1701q(
            gross_sales=payload.gross_sales,
            other_income=payload.other_income,
            cost_of_sales=payload.cost_of_sales,
            operating_expenses=payload.operating_expenses,
            creditable_tax_withheld=payload.creditable_tax_withheld,
            tax_paid_previous_quarters=payload.tax_paid_previous_quarters,
            classification=bp["taxpayer_classification"],
            rules=rules,
        )
    elif payload.form_type == "2551Q":
        if not is_2551q_required(bp["taxpayer_classification"], bp["is_vat_registered"]):
            raise HTTPException(
                status_code=400,
                detail="2551Q is not required for your taxpayer classification "
                       "(8% flat or VAT-registered).",
            )
        computed = compute_2551q(
            gross_sales=payload.gross_sales,
            creditable_tax_withheld=payload.creditable_tax_withheld,
            tax_paid_previous_quarters=payload.tax_paid_previous_quarters,
            rules=rules,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported form type")

    filing = Filing(
        user_id=user["user_id"],
        business_id=bp["business_id"],
        form_type=payload.form_type,
        period=payload.period,
        inputs=payload.model_dump(),
        computed=computed,
        status="generated",
    )
    doc = filing.model_dump()
    doc["generated_at"] = doc["generated_at"].isoformat()
    if doc.get("submitted_at"):
        doc["submitted_at"] = doc["submitted_at"].isoformat()
    await db.filings.insert_one(doc)
    return filing.model_dump(mode="json")


@router.get("/history")
async def list_history(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.filings.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("generated_at", -1)
    return await cursor.to_list(500)


@router.get("/{filing_id}")
async def get_filing(filing_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    f = await db.filings.find_one(
        {"filing_id": filing_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not f:
        raise HTTPException(status_code=404, detail="Filing not found")
    return f


@router.post("/{filing_id}/mark-submitted")
async def mark_submitted(filing_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    f = await db.filings.find_one(
        {"filing_id": filing_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not f:
        raise HTTPException(status_code=404, detail="Filing not found")
    await db.filings.update_one(
        {"filing_id": filing_id},
        {"$set": {
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    # Mark deadline complete
    await db.deadlines.update_many(
        {"user_id": user["user_id"], "form_type": f["form_type"], "period": f["period"]},
        {"$set": {"completed": True}},
    )
    return {"ok": True}
