"""AI Tax Assistant powered by Claude Sonnet 4.5 via Emergent LLM key."""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException
from emergentintegrations.llm.chat import LlmChat, UserMessage

from auth import get_current_user
from models import ChatRequest

router = APIRouter(prefix="/ai", tags=["ai"])

SYSTEM_PROMPT = """You are a knowledgeable, calm Filipino BIR tax assistant for solo
professionals and freelancers (consultants, designers, lawyers, doctors). You explain
BIR concepts clearly with concrete numbers when helpful.

Key knowledge:
- 1701Q: Quarterly Income Tax Return (self-employed). Deadlines: May 15 (Q1),
  Aug 15 (Q2), Nov 15 (Q3). Annual 1701 due April 15.
- 2551Q: Quarterly Percentage Tax (3%, non-VAT). Deadlines: Apr 25, Jul 25,
  Oct 25, Jan 25.
- Taxpayer classifications:
  • 8% flat: gross sales/receipts net of ₱250,000 × 8%. Cannot exceed VAT
    threshold (₱3M). NOT required to file 2551Q.
  • Graduated: net taxable income (gross less cost of sales less operating
    expenses) taxed by TRAIN-Law brackets. Required to file 2551Q (3%).
- Penalties: 25% surcharge + 12% annual interest + ₱1,000 compromise penalty
  for late filing.

Always:
- Be direct and practical. No legal disclaimers in every message.
- Use Philippine peso (₱) and Philippine context.
- Suggest filing via this app when appropriate.
- Decline to give legal advice for criminal tax cases — refer to a CPA."""


@router.post("/chat")
async def chat(req: ChatRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    session_id = f"{user['user_id']}:{req.session_id}"
    chat_client = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        response = await chat_client.send_message(UserMessage(text=req.message))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")
    # Persist chat log
    await db.ai_messages.insert_many([
        {
            "user_id": user["user_id"],
            "session_id": req.session_id,
            "role": "user",
            "content": req.message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "user_id": user["user_id"],
            "session_id": req.session_id,
            "role": "assistant",
            "content": response,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ])
    return {"response": response}


@router.get("/history/{session_id}")
async def history(session_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.ai_messages.find(
        {"user_id": user["user_id"], "session_id": session_id},
        {"_id": 0},
    ).sort("created_at", 1)
    return await cursor.to_list(500)
