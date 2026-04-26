"""BIR Deadline calendar logic.

Generates upcoming filing deadlines for a business based on its taxpayer
classification. Stored deadlines can be marked complete by the user.

Standard deadlines (post-TRAIN, BIR-published):
  1701Q (Quarterly ITR):
    Q1 → May 15
    Q2 → Aug 15
    Q3 → Nov 15
    Annual 1701 → April 15 next year (deferred to v2)
  2551Q (Quarterly Percentage Tax) — only for graduated, non-VAT:
    Q1 → April 25
    Q2 → July 25
    Q3 → October 25
    Q4 → January 25 next year
"""
from datetime import date, datetime, timezone
from typing import List


PERIOD_DEADLINES = {
    "1701Q": {
        "Q1": (5, 15),
        "Q2": (8, 15),
        "Q3": (11, 15),
    },
    "2551Q": {
        "Q1": (4, 25),
        "Q2": (7, 25),
        "Q3": (10, 25),
        "Q4": (1, 25),  # filed in next year
    },
}


def _due_date(form: str, period: str, base_year: int) -> date:
    quarter = period
    month, day = PERIOD_DEADLINES[form][quarter]
    year = base_year + 1 if (form == "2551Q" and quarter == "Q4") else base_year
    return date(year, month, day)


def _severity(days: int) -> str:
    if days < 0:
        return "overdue"
    if days <= 1:
        return "urgent"
    if days <= 7:
        return "warning"
    return "upcoming"


def generate_upcoming_deadlines(
    *,
    user_id: str,
    business_id: str,
    classification: str,
    is_vat_registered: bool,
    today: date,
    horizon_days: int = 365,
) -> List[dict]:
    """Generate deadlines from `today` up to `today + horizon_days`."""
    out: List[dict] = []
    end_year = today.year + 2  # look 2 years ahead
    for year in range(today.year, end_year + 1):
        # 1701Q always applies to self-employed
        for q in ["Q1", "Q2", "Q3"]:
            d = _due_date("1701Q", q, year)
            days_until = (d - today).days
            if days_until > horizon_days or days_until < -90:
                continue
            out.append({
                "user_id": user_id,
                "business_id": business_id,
                "form_type": "1701Q",
                "period": f"{year}-{q}",
                "due_date": d.isoformat(),
                "days_until": days_until,
                "severity": _severity(days_until),
                "completed": False,
            })
        # 2551Q only for non-VAT graduated taxpayers
        if classification == "graduated" and not is_vat_registered:
            for q in ["Q1", "Q2", "Q3", "Q4"]:
                d = _due_date("2551Q", q, year)
                days_until = (d - today).days
                if days_until > horizon_days or days_until < -90:
                    continue
                out.append({
                    "user_id": user_id,
                    "business_id": business_id,
                    "form_type": "2551Q",
                    "period": f"{year}-{q}",
                    "due_date": d.isoformat(),
                    "days_until": days_until,
                    "severity": _severity(days_until),
                    "completed": False,
                })
    out.sort(key=lambda x: x["due_date"])
    return out
