"""Resend email wrapper. No-op if RESEND_API_KEY is empty."""
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


async def send_email(*, to: str, subject: str, html: str) -> dict:
    """Send an email via Resend. If no API key configured, log only."""
    if not _enabled():
        logger.info(f"[EMAIL_DISABLED] to={to} subject={subject}")
        return {"status": "disabled", "to": to}
    import resend
    resend.api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    params = {"from": sender, "to": [to], "subject": subject, "html": html}
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"status": "sent", "id": result.get("id")}
    except Exception as e:
        logger.error(f"resend send failed: {e}")
        return {"status": "error", "error": str(e)}


def deadline_reminder_html(name: str, form_type: str, period: str, due_date: str, days_until: int) -> str:
    return f"""
    <div style="font-family:Manrope,Arial,sans-serif;background:#F9F8F6;padding:32px;color:#1A2E24">
      <div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #E2E0D8;border-radius:8px;padding:32px">
        <h1 style="font-size:22px;color:#2C4C3B;margin:0 0 8px">Hi {name},</h1>
        <p style="font-size:15px;line-height:1.6;color:#516359;margin:0 0 24px">
          Your <strong>BIR {form_type}</strong> for <strong>{period}</strong> is due in
          <strong style="color:#E06D53">{days_until} day(s)</strong> — on <strong>{due_date}</strong>.
        </p>
        <a href="#" style="display:inline-block;background:#2C4C3B;color:#FFFFFF;
            padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
          Generate Form Now
        </a>
        <p style="font-size:13px;color:#8A9A91;margin-top:32px">
          File on time to avoid BIR penalties (25% surcharge + 12% annual interest).
        </p>
      </div>
    </div>
    """
