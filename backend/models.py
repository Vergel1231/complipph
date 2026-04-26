"""Pydantic models for the BIR Filing SaaS."""
from datetime import datetime, timezone, date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict
import uuid


def _uuid() -> str:
    return f"u_{uuid.uuid4().hex[:14]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── User & Auth ────────────────────────────────────────────────
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str = Field(default_factory=_uuid)
    email: EmailStr
    name: str
    picture: Optional[str] = None
    auth_provider: Literal["password", "google"] = "password"
    role: Literal["user", "admin", "reseller"] = "user"
    onboarded: bool = False
    subscription_status: Literal["trial", "active", "past_due", "canceled", "incomplete"] = "trial"
    subscription_plan: Literal["solo", "pro", "reseller"] = "solo"
    subscription_started_at: Optional[datetime] = None
    # Reseller relationship — non-breaking, optional. If a CPA "manages" this
    # user, their CPA reseller user_id lives here. Used by the future Phase 4
    # Reseller dashboard. Null for direct customers.
    managed_by_cpa_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ─── Business Profile ───────────────────────────────────────────
class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    business_id: str = Field(default_factory=lambda: f"b_{uuid.uuid4().hex[:14]}")
    user_id: str
    legal_name: str
    trade_name: Optional[str] = None
    tin: str  # 9 to 14 digits, no validation in MVP
    rdo_code: Optional[str] = None
    business_type: Literal[
        "consultant", "designer", "lawyer", "doctor", "developer",
        "writer", "coach", "other"
    ] = "other"
    taxpayer_classification: Literal["8_percent_flat", "graduated"] = "8_percent_flat"
    is_vat_registered: bool = False
    is_non_vat: bool = True  # Subject to 2551Q if non-VAT and graduated
    registered_address: Optional[str] = None
    line_of_business: Optional[str] = None
    first_filing_period: Optional[str] = None  # e.g., "2026-Q1"
    created_at: datetime = Field(default_factory=_now)


class BusinessProfileCreate(BaseModel):
    legal_name: str
    trade_name: Optional[str] = None
    tin: str
    rdo_code: Optional[str] = None
    business_type: str = "other"
    taxpayer_classification: Literal["8_percent_flat", "graduated"]
    is_vat_registered: bool = False
    registered_address: Optional[str] = None
    line_of_business: Optional[str] = None
    first_filing_period: Optional[str] = None


# ─── BIR Form Generation ────────────────────────────────────────
class FormGenerateRequest(BaseModel):
    form_type: Literal["1701Q", "2551Q"]
    period: str  # e.g., "2026-Q1"
    gross_sales: float
    other_income: float = 0.0
    cost_of_sales: float = 0.0
    operating_expenses: float = 0.0
    creditable_tax_withheld: float = 0.0
    tax_paid_previous_quarters: float = 0.0


class Filing(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filing_id: str = Field(default_factory=lambda: f"f_{uuid.uuid4().hex[:14]}")
    user_id: str
    business_id: str
    form_type: Literal["1701Q", "2551Q"]
    period: str
    inputs: dict
    computed: dict  # all computed BIR fields
    status: Literal["draft", "generated", "submitted"] = "generated"
    generated_at: datetime = Field(default_factory=_now)
    submitted_at: Optional[datetime] = None


# ─── Deadlines ──────────────────────────────────────────────────
class Deadline(BaseModel):
    model_config = ConfigDict(extra="ignore")
    deadline_id: str = Field(default_factory=lambda: f"d_{uuid.uuid4().hex[:14]}")
    user_id: str
    business_id: str
    form_type: str
    period: str
    due_date: str  # ISO date
    days_until: int
    severity: Literal["upcoming", "warning", "urgent", "overdue"] = "upcoming"
    completed: bool = False


# ─── AI Tax Assistant ───────────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=_now)


class ChatRequest(BaseModel):
    session_id: str
    message: str


# ─── Admin / BIR Rules ──────────────────────────────────────────
class BirRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rule_id: str = Field(default_factory=lambda: f"r_{uuid.uuid4().hex[:14]}")
    rule_key: str  # e.g., "percentage_tax_rate", "personal_exemption_threshold"
    rule_value: float
    description: str
    effective_date: str
    updated_at: datetime = Field(default_factory=_now)


class BirRuleUpdate(BaseModel):
    rule_value: float
    description: Optional[str] = None
    effective_date: Optional[str] = None


# ─── Billing (mock, PayMongo-ready) ─────────────────────────────
class CheckoutRequest(BaseModel):
    plan: Literal["solo", "pro", "reseller"] = "solo"


class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subscription_id: str = Field(default_factory=lambda: f"s_{uuid.uuid4().hex[:14]}")
    user_id: str
    plan: str
    amount_php: float
    status: str = "active"
    provider: str = "mock"  # will become "paymongo"
    paymongo_subscription_id: Optional[str] = None
    paymongo_customer_id: Optional[str] = None
    paymongo_plan_id: Optional[str] = None
    started_at: datetime = Field(default_factory=_now)
    next_billing_at: Optional[datetime] = None
