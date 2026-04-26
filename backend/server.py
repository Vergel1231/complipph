"""Main FastAPI app for BIR Filipino Filing SaaS."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth import router as auth_router, hash_password, verify_password
from routes.business import router as business_router
from routes.forms import router as forms_router
from routes.deadlines_route import router as deadlines_router
from routes.ai_assistant import router as ai_router
from routes.admin import router as admin_router
from routes.billing import router as billing_router
from routes.exports import router as exports_router
from scheduler import start_scheduler, stop_scheduler

# ─── App + DB ───────────────────────────────────────────────────
app = FastAPI(title="BIR Filipino — Filing SaaS")
api_router = APIRouter(prefix="/api")

mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo_client[os.environ["DB_NAME"]]
app.state.db = db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@api_router.get("/")
async def root():
    return {"app": "BIR Filipino", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


# Mount sub-routers
api_router.include_router(auth_router)
api_router.include_router(business_router)
api_router.include_router(forms_router)
api_router.include_router(exports_router)
api_router.include_router(deadlines_router)
api_router.include_router(ai_router)
api_router.include_router(admin_router)
api_router.include_router(billing_router)

app.include_router(api_router)

# CORS — explicit origin for credentialed requests, plus preview-host regex
frontend_url = os.environ.get("FRONTEND_URL")
allow_origins = [frontend_url] if frontend_url else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=r"https://[a-z0-9\-]+\.preview\.emergentagent\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.business_profiles.create_index("user_id", unique=True)
    await db.filings.create_index([("user_id", 1), ("generated_at", -1)])
    await db.deadlines.create_index([("user_id", 1), ("due_date", 1)])
    await db.user_sessions.create_index("session_token", unique=True)
    await db.bir_rules.create_index("rule_key", unique=True)
    await db.subscriptions.create_index([("user_id", 1), ("status", 1)])
    await db.ai_messages.create_index([("user_id", 1), ("session_id", 1)])
    await db.reminders_sent.create_index("dedup_key", unique=True)
    await db.reminders_sent.create_index("sent_at")
    await db.reminder_attempts.create_index([("user_id", 1), ("attempted_at", -1)])

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@birfilipino.app")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "Admin@2026")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        import uuid
        await db.users.insert_one({
            "user_id": f"u_{uuid.uuid4().hex[:14]}",
            "email": admin_email,
            "name": "Admin",
            "auth_provider": "password",
            "role": "admin",
            "onboarded": True,
            "subscription_status": "active",
            "subscription_plan": "pro",
            "password_hash": hash_password(admin_pw),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded admin user: {admin_email}")
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_pw), "role": "admin"}},
        )
        logger.info(f"Updated admin password for: {admin_email}")
    elif existing.get("role") != "admin":
        await db.users.update_one(
            {"email": admin_email}, {"$set": {"role": "admin"}}
        )

    logger.info("BIR Filipino API ready.")

    # Start in-process daily reminder cron (09:00 Asia/Manila)
    start_scheduler(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    stop_scheduler()
    mongo_client.close()
