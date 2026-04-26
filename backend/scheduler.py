"""Deadline reminder scheduler.

Runs daily at 09:00 Asia/Manila and sends 30/7/1-day reminders for every
user with a business profile. Reminders are de-duplicated via the
`reminders_sent` collection so users never receive the same notice twice.
"""
import os
import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from deadlines import generate_upcoming_deadlines
from email_service import send_email, deadline_reminder_html

logger = logging.getLogger(__name__)

REMINDER_DAYS = {30, 7, 1}
_scheduler: AsyncIOScheduler | None = None


async def run_daily_reminders(db) -> dict:
    """Scan every user's deadlines, send reminders for any matching {30,7,1} day window.

    Returns a small report dict for /api/admin/run-reminders.
    """
    today = date.today()
    sent = 0
    skipped_dup = 0
    skipped_disabled = 0
    errors = 0
    users_processed = 0

    cursor = db.users.find(
        {"onboarded": True},
        {"_id": 0, "user_id": 1, "email": 1, "name": 1},
    )
    async for user in cursor:
        users_processed += 1
        bp = await db.business_profiles.find_one(
            {"user_id": user["user_id"]}, {"_id": 0}
        )
        if not bp:
            continue
        deadlines = generate_upcoming_deadlines(
            user_id=user["user_id"],
            business_id=bp["business_id"],
            classification=bp["taxpayer_classification"],
            is_vat_registered=bp["is_vat_registered"],
            today=today,
        )
        # Only consider open deadlines (no submitted filing for that period)
        submitted = set()
        async for f in db.filings.find(
            {"user_id": user["user_id"], "status": "submitted"},
            {"_id": 0, "form_type": 1, "period": 1},
        ):
            submitted.add((f["form_type"], f["period"]))

        for d in deadlines:
            if (d["form_type"], d["period"]) in submitted:
                continue
            if d["days_until"] not in REMINDER_DAYS:
                continue
            dedup_key = (
                f"{user['user_id']}:{d['form_type']}:{d['period']}:{d['days_until']}"
            )
            existing = await db.reminders_sent.find_one(
                {"dedup_key": dedup_key}, {"_id": 0}
            )
            if existing:
                skipped_dup += 1
                continue
            html = deadline_reminder_html(
                name=user["name"],
                form_type=d["form_type"],
                period=d["period"],
                due_date=d["due_date"],
                days_until=d["days_until"],
            )
            result = await send_email(
                to=user["email"],
                subject=f"BIR {d['form_type']} due in {d['days_until']} day(s) — {d['period']}",
                html=html,
            )
            if result.get("status") == "sent":
                sent += 1
            elif result.get("status") == "disabled":
                skipped_disabled += 1
            else:
                errors += 1
            await db.reminders_sent.insert_one({
                "dedup_key": dedup_key,
                "user_id": user["user_id"],
                "email": user["email"],
                "form_type": d["form_type"],
                "period": d["period"],
                "days_until": d["days_until"],
                "result_status": result.get("status"),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            })

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "users_processed": users_processed,
        "sent": sent,
        "skipped_duplicates": skipped_dup,
        "skipped_disabled_email": skipped_disabled,
        "errors": errors,
    }
    logger.info(f"Reminder run complete: {report}")
    return report


def start_scheduler(db) -> None:
    """Start the in-process daily reminder cron at 09:00 Asia/Manila."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="Asia/Manila")
    _scheduler.add_job(
        run_daily_reminders,
        CronTrigger(hour=9, minute=0, timezone="Asia/Manila"),
        args=[db],
        id="daily_bir_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("APScheduler started: daily 09:00 Asia/Manila reminder job.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
