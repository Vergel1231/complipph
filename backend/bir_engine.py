"""BIR Tax Form Computation Engine.

Implements:
- 1701Q (Quarterly Income Tax Return for Self-Employed Individuals & Professionals)
  • 8% flat tax (gross sales/receipts > 250,000 threshold * 8%)
  • Graduated rates per TRAIN Law (effective 2023+)
- 2551Q (Quarterly Percentage Tax) — 3% of gross sales/receipts (non-VAT)

Tax tables and thresholds are looked up from the bir_rules collection so they can
be updated by admins via the dashboard. Defaults below are TRAIN-Law 2023+ values.
"""
from typing import Literal

# ─── Default constants (overridable via bir_rules) ──────────────
DEFAULT_RULES = {
    "personal_exemption": 250_000.0,  # First 250k tax-free
    "flat_tax_rate": 0.08,            # 8% flat option
    "percentage_tax_rate": 0.03,      # 2551Q rate (3% post-CREATE)
    # Graduated brackets stored as separate rule_keys for admin editing
    "grad_b1_threshold": 250_000.0,
    "grad_b2_threshold": 400_000.0,
    "grad_b2_rate": 0.15,
    "grad_b3_threshold": 800_000.0,
    "grad_b3_base": 22_500.0,
    "grad_b3_rate": 0.20,
    "grad_b4_threshold": 2_000_000.0,
    "grad_b4_base": 102_500.0,
    "grad_b4_rate": 0.25,
    "grad_b5_threshold": 8_000_000.0,
    "grad_b5_base": 402_500.0,
    "grad_b5_rate": 0.30,
    "grad_b6_base": 2_202_500.0,
    "grad_b6_rate": 0.35,
}


async def get_rules(db) -> dict:
    """Load BIR rules from MongoDB, falling back to defaults."""
    rules = dict(DEFAULT_RULES)
    cursor = db.bir_rules.find({}, {"_id": 0})
    async for doc in cursor:
        if doc.get("rule_key") in rules:
            rules[doc["rule_key"]] = float(doc["rule_value"])
    return rules


def _round2(x: float) -> float:
    return round(float(x), 2)


def compute_graduated_tax(taxable_income: float, r: dict) -> float:
    if taxable_income <= r["grad_b1_threshold"]:
        return 0.0
    if taxable_income <= r["grad_b2_threshold"]:
        return (taxable_income - r["grad_b1_threshold"]) * r["grad_b2_rate"]
    if taxable_income <= r["grad_b3_threshold"]:
        return r["grad_b3_base"] + (taxable_income - r["grad_b2_threshold"]) * r["grad_b3_rate"]
    if taxable_income <= r["grad_b4_threshold"]:
        return r["grad_b4_base"] + (taxable_income - r["grad_b3_threshold"]) * r["grad_b4_rate"]
    if taxable_income <= r["grad_b5_threshold"]:
        return r["grad_b5_base"] + (taxable_income - r["grad_b4_threshold"]) * r["grad_b5_rate"]
    return r["grad_b6_base"] + (taxable_income - r["grad_b5_threshold"]) * r["grad_b6_rate"]


def compute_1701q(
    *,
    gross_sales: float,
    other_income: float,
    cost_of_sales: float,
    operating_expenses: float,
    creditable_tax_withheld: float,
    tax_paid_previous_quarters: float,
    classification: Literal["8_percent_flat", "graduated"],
    rules: dict,
) -> dict:
    gross_total = gross_sales + other_income
    if classification == "8_percent_flat":
        # 8% on gross sales/receipts net of 250k exemption
        taxable_base = max(0.0, gross_sales + other_income - rules["personal_exemption"])
        income_tax_due = taxable_base * rules["flat_tax_rate"]
        net_taxable_income = taxable_base
        method = "8% flat tax"
    else:
        # Graduated: gross less cost of sales less operating expenses
        net_income = max(0.0, gross_total - cost_of_sales - operating_expenses)
        income_tax_due = compute_graduated_tax(net_income, rules)
        net_taxable_income = net_income
        method = "Graduated rates"
    tax_payable = max(0.0, income_tax_due - creditable_tax_withheld - tax_paid_previous_quarters)
    return {
        "form_type": "1701Q",
        "method": method,
        "gross_sales_receipts": _round2(gross_sales),
        "other_income": _round2(other_income),
        "gross_total": _round2(gross_total),
        "cost_of_sales": _round2(cost_of_sales) if classification == "graduated" else 0.0,
        "operating_expenses": _round2(operating_expenses) if classification == "graduated" else 0.0,
        "personal_exemption": _round2(rules["personal_exemption"]) if classification == "8_percent_flat" else 0.0,
        "net_taxable_income": _round2(net_taxable_income),
        "income_tax_due": _round2(income_tax_due),
        "creditable_tax_withheld": _round2(creditable_tax_withheld),
        "tax_paid_previous_quarters": _round2(tax_paid_previous_quarters),
        "tax_payable": _round2(tax_payable),
        # Form-field mapping (BIR 1701Q line numbers used as reference)
        "field_map": {
            "Line 36 — Gross Sales/Receipts": _round2(gross_sales),
            "Line 37 — Other Income": _round2(other_income),
            "Line 38 — Total": _round2(gross_total),
            "Line 39 — Less Cost of Sales/Services": _round2(cost_of_sales) if classification == "graduated" else 0.0,
            "Line 40 — Less Operating Expenses": _round2(operating_expenses) if classification == "graduated" else 0.0,
            "Line 41 — Net Taxable Income": _round2(net_taxable_income),
            "Line 42 — Income Tax Due": _round2(income_tax_due),
            "Line 43 — Less Creditable Tax Withheld": _round2(creditable_tax_withheld),
            "Line 44 — Less Tax Paid Previous Quarters": _round2(tax_paid_previous_quarters),
            "Line 45 — Tax Payable": _round2(tax_payable),
        },
    }


def compute_2551q(
    *,
    gross_sales: float,
    creditable_tax_withheld: float,
    tax_paid_previous_quarters: float,
    rules: dict,
) -> dict:
    rate = rules["percentage_tax_rate"]
    percentage_tax_due = gross_sales * rate
    tax_payable = max(0.0, percentage_tax_due - creditable_tax_withheld - tax_paid_previous_quarters)
    return {
        "form_type": "2551Q",
        "method": f"Percentage Tax ({int(rate*100)}%)",
        "taxable_amount": _round2(gross_sales),
        "tax_rate": rate,
        "percentage_tax_due": _round2(percentage_tax_due),
        "creditable_tax_withheld": _round2(creditable_tax_withheld),
        "tax_paid_previous_quarters": _round2(tax_paid_previous_quarters),
        "tax_payable": _round2(tax_payable),
        "field_map": {
            "Line 14 — Taxable Amount": _round2(gross_sales),
            "Line 15 — Tax Rate": f"{rate*100:.0f}%",
            "Line 16 — Percentage Tax Due": _round2(percentage_tax_due),
            "Line 17 — Less Creditable Tax Withheld": _round2(creditable_tax_withheld),
            "Line 18 — Less Tax Paid Previous Quarters": _round2(tax_paid_previous_quarters),
            "Line 19 — Tax Still Payable": _round2(tax_payable),
        },
    }


def is_2551q_required(classification: str, is_vat_registered: bool) -> bool:
    """If the freelancer chose 8% flat OR is VAT-registered, 2551Q is NOT required."""
    if is_vat_registered:
        return False
    if classification == "8_percent_flat":
        return False
    return True
