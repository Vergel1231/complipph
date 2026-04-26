"""Filing exports: eBIRForms-compatible XML + PDF (via reportlab)."""
import io
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

from auth import get_current_user

router = APIRouter(prefix="/forms", tags=["forms-export"])


# ─── Helpers ────────────────────────────────────────────────────
def _format_php(v) -> str:
    if isinstance(v, (int, float)):
        return f"PHP {v:,.2f}"
    return str(v)


async def _fetch_filing(db, filing_id: str, user_id: str) -> dict:
    f = await db.filings.find_one(
        {"filing_id": filing_id, "user_id": user_id}, {"_id": 0}
    )
    if not f:
        raise HTTPException(status_code=404, detail="Filing not found")
    bp = await db.business_profiles.find_one({"user_id": user_id}, {"_id": 0})
    return {"filing": f, "profile": bp or {}}


# ─── XML export ─────────────────────────────────────────────────
def _build_xml(filing: dict, profile: dict) -> bytes:
    """Build an eBIRForms-style XML envelope.

    Note: Official eBIRForms uses a proprietary XML schema embedded in their
    desktop tool. This XML mirrors that structure (Form/Header/Body/Computation)
    so the user can paste values into the corresponding eBIRForms fields, or
    keep it as a complete machine-readable archive.
    """
    computed = filing.get("computed", {}) or {}
    inputs = filing.get("inputs", {}) or {}
    fm = computed.get("field_map", {}) or {}

    root = Element("eBIRFormsFiling")
    root.set("formType", filing["form_type"])
    root.set("period", filing["period"])
    root.set("generatedAt", filing.get("generated_at", ""))

    header = SubElement(root, "Header")
    SubElement(header, "TIN").text = profile.get("tin", "")
    SubElement(header, "RDOCode").text = profile.get("rdo_code", "")
    SubElement(header, "TaxpayerName").text = profile.get("legal_name", "")
    SubElement(header, "TradeName").text = profile.get("trade_name", "") or ""
    SubElement(header, "TaxpayerClassification").text = profile.get("taxpayer_classification", "")
    SubElement(header, "VATRegistered").text = "Y" if profile.get("is_vat_registered") else "N"
    SubElement(header, "RegisteredAddress").text = profile.get("registered_address", "") or ""
    SubElement(header, "LineOfBusiness").text = profile.get("line_of_business", "") or ""

    body = SubElement(root, "Body")
    SubElement(body, "Method").text = computed.get("method", "")
    inputs_el = SubElement(body, "Inputs")
    for k, v in inputs.items():
        el = SubElement(inputs_el, "Input")
        el.set("name", str(k))
        el.text = str(v)

    comp = SubElement(root, "Computation")
    for line, val in fm.items():
        el = SubElement(comp, "Field")
        el.set("name", str(line))
        if isinstance(val, (int, float)):
            el.set("type", "currency")
            el.text = f"{val:.2f}"
        else:
            el.set("type", "text")
            el.text = str(val)

    summary = SubElement(root, "Summary")
    SubElement(summary, "TaxPayable").text = f"{computed.get('tax_payable', 0):.2f}"

    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(
        indent="  ", encoding="utf-8"
    )
    return pretty


@router.get("/{filing_id}/export.xml")
async def export_xml(filing_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    data = await _fetch_filing(db, filing_id, user["user_id"])
    xml_bytes = _build_xml(data["filing"], data["profile"])
    fname = f"BIR_{data['filing']['form_type']}_{data['filing']['period']}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ─── PDF export ─────────────────────────────────────────────────
def _build_pdf(filing: dict, profile: dict) -> bytes:
    computed = filing.get("computed", {}) or {}
    fm = computed.get("field_map", {}) or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title=f"BIR {filing['form_type']} {filing['period']}",
    )
    styles = getSampleStyleSheet()
    OLIVE = colors.HexColor("#2C4C3B")
    SAND = colors.HexColor("#F0EFEA")
    TERRA = colors.HexColor("#E06D53")
    INK = colors.HexColor("#1A2E24")

    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=22, textColor=OLIVE, spaceAfter=4,
    )
    overline = ParagraphStyle(
        "ovl", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8, textColor=TERRA, spaceAfter=4, leading=10,
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, textColor=OLIVE, spaceBefore=14, spaceAfter=6,
    )
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, textColor=INK)  # noqa: F841 — keep available for future copy blocks
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#516359"))

    story = []
    story.append(Paragraph("BIR FILIPINO · QUARTERLY FILING WORKSHEET", overline))
    story.append(Paragraph(f"BIR {filing['form_type']} &nbsp;·&nbsp; Period {filing['period']}", title_style))
    story.append(Paragraph(
        f"Generated {filing.get('generated_at', '')[:10]} &nbsp;·&nbsp; Method: {computed.get('method', '')}",
        small,
    ))
    story.append(Spacer(1, 14))

    # Header / taxpayer block
    story.append(Paragraph("Taxpayer Information", h2))
    header_rows = [
        ["Legal Name", profile.get("legal_name", "")],
        ["Trade Name", profile.get("trade_name", "") or "—"],
        ["TIN", profile.get("tin", "")],
        ["RDO Code", profile.get("rdo_code", "") or "—"],
        ["Classification", _classification_label(profile.get("taxpayer_classification", ""))],
        ["VAT-Registered", "Yes" if profile.get("is_vat_registered") else "No"],
        ["Line of Business", profile.get("line_of_business", "") or "—"],
    ]
    t = Table(header_rows, colWidths=[1.7 * inch, 4.6 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), OLIVE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), SAND),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E0D8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Computed BIR fields
    story.append(Paragraph("Pre-filled BIR Fields", h2))
    rows = [["BIR Line", "Value"]]
    for line, val in fm.items():
        rows.append([line, _format_php(val) if isinstance(val, (int, float)) else str(val)])
    t2 = Table(rows, colWidths=[4.0 * inch, 2.3 * inch], repeatRows=1)
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), OLIVE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SAND]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E0D8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)

    # Summary big box
    story.append(Spacer(1, 14))
    summary_rows = [[
        Paragraph("<b>TAX PAYABLE</b>", ParagraphStyle("sm", fontName="Helvetica-Bold",
                                                       fontSize=9, textColor=colors.white)),
        Paragraph(f"<b>{_format_php(computed.get('tax_payable', 0))}</b>",
                  ParagraphStyle("smv", fontName="Helvetica-Bold",
                                 fontSize=18, textColor=colors.white, alignment=TA_RIGHT)),
    ]]
    sb = Table(summary_rows, colWidths=[2.0 * inch, 4.3 * inch])
    sb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), OLIVE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(sb)

    # Footer note
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "<i>This worksheet pre-fills the values needed for BIR Form "
        f"{filing['form_type']}. File via eBIRForms or eFPS by the due date "
        "to avoid the 25% surcharge and 12% annual interest. Generated by BIR Filipino.</i>",
        small,
    ))

    doc.build(story)
    return buf.getvalue()


def _classification_label(c: str) -> str:
    return {"8_percent_flat": "8% Flat Tax", "graduated": "Graduated Rates"}.get(c, c)


@router.get("/{filing_id}/export.pdf")
async def export_pdf(filing_id: str, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    data = await _fetch_filing(db, filing_id, user["user_id"])
    pdf_bytes = _build_pdf(data["filing"], data["profile"])
    fname = f"BIR_{data['filing']['form_type']}_{data['filing']['period']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
