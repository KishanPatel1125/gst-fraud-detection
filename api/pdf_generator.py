"""
GST Fraud Detection System
PDF Report Generator
Generates investigation reports for flagged GSTINs
"""

import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import (
    HexColor, black, white, red, orange, green
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Colors ──
RED      = HexColor("#FF3B5C")
ORANGE   = HexColor("#FF8C00")
YELLOW   = HexColor("#CA8A04")
GREEN    = HexColor("#16A34A")
BLUE     = HexColor("#1D4ED8")
DARK     = HexColor("#1C1C1E")
GRAY     = HexColor("#6B7280")
LIGHTGRAY= HexColor("#F3F4F6")
WHITE    = white

def risk_color(level: str):
    return {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": YELLOW, "LOW": GREEN}.get(level, GRAY)


def generate_gstin_report(gstin_data: dict) -> bytes:
    """
    Generate a PDF investigation report for a GSTIN
    Returns PDF as bytes
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize    = A4,
        rightMargin = 2*cm,
        leftMargin  = 2*cm,
        topMargin   = 2*cm,
        bottomMargin= 2*cm,
    )

    styles  = getSampleStyleSheet()
    content = []

    # ── Extract data ──
    gstin       = gstin_data.get("gstin", "N/A")
    company     = gstin_data.get("company_info", {})
    risk        = gstin_data.get("risk_summary", {})
    scores      = gstin_data.get("score_breakdown", {})
    indicators  = gstin_data.get("fraud_indicators", {})
    flags       = gstin_data.get("rule_flags", [])
    recommend   = gstin_data.get("recommendation", "")
    level       = risk.get("risk_level", "LOW")
    color       = risk_color(level)
    score       = risk.get("ensemble_score", 0)

    # ── Custom styles ──
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=20, textColor=DARK,
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=13, textColor=DARK,
        spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=11, textColor=GRAY,
        spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=DARK,
        spaceAfter=4, leading=16
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=9, textColor=GRAY, spaceAfter=2
    )
    center_style = ParagraphStyle(
        "Center", parent=styles["Normal"],
        fontSize=10, alignment=TA_CENTER
    )

    # ════════════════════════════════════════
    # HEADER
    # ════════════════════════════════════════
    content.append(Paragraph("🛡️ GST FraudShield", title_style))
    content.append(Paragraph(
        "AI-Powered GST Fraud Investigation Report",
        ParagraphStyle("sub", parent=styles["Normal"], fontSize=11,
                       textColor=GRAY, alignment=TA_CENTER, spaceAfter=2)
    ))
    content.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        ParagraphStyle("date", parent=styles["Normal"], fontSize=9,
                       textColor=GRAY, alignment=TA_CENTER, spaceAfter=12)
    ))
    content.append(HRFlowable(width="100%", thickness=2, color=color))
    content.append(Spacer(1, 12))

    # ════════════════════════════════════════
    # RISK SUMMARY BOX
    # ════════════════════════════════════════
    risk_table = Table(
        [[
            Paragraph(f"<b>GSTIN:</b> {gstin}", body_style),
            Paragraph(
                f"<b><font color='#{level == 'CRITICAL' and 'FF3B5C' or level == 'HIGH' and 'FF8C00' or '16A34A'}'>"
                f"{level} RISK</font></b><br/>"
                f"<font size='22'><b>{score:.1f}%</b></font>",
                ParagraphStyle("risk", parent=styles["Normal"],
                               fontSize=11, alignment=TA_RIGHT)
            ),
        ]],
        colWidths=["65%", "35%"]
    )
    risk_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), LIGHTGRAY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHTGRAY]),
        ("BOX",         (0,0), (-1,-1), 1.5, color),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]))
    content.append(risk_table)
    content.append(Spacer(1, 16))

    # ════════════════════════════════════════
    # COMPANY INFORMATION
    # ════════════════════════════════════════
    content.append(Paragraph("1. Company Information", h1_style))
    content.append(HRFlowable(width="100%", thickness=0.5, color=LIGHTGRAY))
    content.append(Spacer(1, 6))

    company_data = [
        ["Field", "Value"],
        ["Company Name",      company.get("company_name", "N/A")],
        ["GSTIN",             gstin],
        ["State",             company.get("state", "N/A")],
        ["Industry",          company.get("industry", "N/A")],
        ["Annual Turnover",   f"₹{company.get('annual_turnover', 0):,.0f}"],
        ["Registration Date", company.get("registration_date", "N/A")],
        ["Years in Business", f"{company.get('years_old', 0)} years"],
    ]

    company_table = Table(company_data, colWidths=["35%", "65%"])
    company_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  DARK),
        ("TEXTCOLOR",    (0,0), (-1,0),  WHITE),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHTGRAY]),
        ("GRID",         (0,0), (-1,-1), 0.5, HexColor("#E5E7EB")),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    content.append(company_table)
    content.append(Spacer(1, 16))

    # ════════════════════════════════════════
    # MODEL SCORE BREAKDOWN
    # ════════════════════════════════════════
    content.append(Paragraph("2. AI Model Score Breakdown", h1_style))
    content.append(HRFlowable(width="100%", thickness=0.5, color=LIGHTGRAY))
    content.append(Spacer(1, 6))

    score_data = [
        ["Model", "Score", "Weight", "Contribution", "Description"],
        ["XGBoost Classifier",    f"{scores.get('xgb_score',0):.1f}%",    "35%", f"{scores.get('xgb_score',0)*0.35:.1f} pts", "Detects known fraud patterns"],
        ["Isolation Forest",      f"{scores.get('anomaly_score',0):.1f}%", "25%", f"{scores.get('anomaly_score',0)*0.25:.1f} pts", "Detects unknown anomalies"],
        ["Graph Detector",        f"{scores.get('graph_risk_score',0):.1f}%","25%",f"{scores.get('graph_risk_score',0)*0.25:.1f} pts","Circular trading detection"],
        ["Rule-based Checks",     f"{scores.get('rule_score',0):.1f}%",    "15%", f"{scores.get('rule_score',0)*0.15:.1f} pts", "Compliance rule violations"],
        ["FINAL ENSEMBLE SCORE",  f"{score:.1f}%",                          "100%",f"{score:.1f} pts", "Combined weighted score"],
    ]

    score_table = Table(score_data, colWidths=["28%","12%","10%","16%","34%"])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),  (-1,0),  DARK),
        ("TEXTCOLOR",    (0,0),  (-1,0),  WHITE),
        ("FONTNAME",     (0,0),  (-1,0),  "Helvetica-Bold"),
        ("BACKGROUND",   (0,-1), (-1,-1), color),
        ("TEXTCOLOR",    (0,-1), (-1,-1), WHITE),
        ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),  (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-2), [WHITE, LIGHTGRAY]),
        ("GRID",         (0,0),  (-1,-1), 0.5, HexColor("#E5E7EB")),
        ("LEFTPADDING",  (0,0),  (-1,-1), 8),
        ("RIGHTPADDING", (0,0),  (-1,-1), 8),
        ("TOPPADDING",   (0,0),  (-1,-1), 7),
        ("BOTTOMPADDING",(0,0),  (-1,-1), 7),
        ("ALIGN",        (1,0),  (3,-1),  "CENTER"),
        ("VALIGN",       (0,0),  (-1,-1), "MIDDLE"),
    ]))
    content.append(score_table)
    content.append(Spacer(1, 16))

    # ════════════════════════════════════════
    # FRAUD INDICATORS
    # ════════════════════════════════════════
    content.append(Paragraph("3. Fraud Indicators", h1_style))
    content.append(HRFlowable(width="100%", thickness=0.5, color=LIGHTGRAY))
    content.append(Spacer(1, 6))

    def indicator_status(key, val):
        thresholds = {
            "avg_itc_ratio":      (1.0, 2.0),
            "filing_rate":        (0.9, 0.7),
            "missing_returns":    (0, 2),
            "spike_ratio":        (2.0, 5.0),
            "invoice_match_rate": (0.9, 0.75),
            "sales_volatility":   (0.5, 1.0),
        }
        if key not in thresholds:
            return "Normal"
        lo, hi = thresholds[key]
        if key in ["filing_rate", "invoice_match_rate"]:
            if val < hi:   return "⚠️ Critical"
            if val < lo:   return "⚠️ Warning"
            return "✅ Normal"
        else:
            if val > hi:   return "⚠️ Critical"
            if val > lo:   return "⚠️ Warning"
            return "✅ Normal"

    indicator_data = [
        ["Indicator", "Value", "Status", "Explanation"],
        ["Avg ITC Ratio",       f"{indicators.get('avg_itc_ratio',0):.3f}",       indicator_status("avg_itc_ratio", indicators.get("avg_itc_ratio",0)),        "Normal: 0.6-0.9. High = fake ITC claims"],
        ["Filing Rate",         f"{indicators.get('filing_rate',0)*100:.1f}%",    indicator_status("filing_rate", indicators.get("filing_rate",0)),              "Should be close to 100%"],
        ["Missing Returns",     f"{indicators.get('missing_returns',0)}",          indicator_status("missing_returns", indicators.get("missing_returns",0)),      "Months with no filing"],
        ["Sales Spike Ratio",   f"{indicators.get('spike_ratio',0):.2f}x",        indicator_status("spike_ratio", indicators.get("spike_ratio",0)),              "Recent vs older sales ratio"],
        ["Invoice Match Rate",  f"{indicators.get('invoice_match_rate',0)*100:.1f}%", indicator_status("invoice_match_rate", indicators.get("invoice_match_rate",0)), "GSTR-1 vs GSTR-2A match"],
        ["Sales Volatility",    f"{indicators.get('sales_volatility',0):.3f}",    indicator_status("sales_volatility", indicators.get("sales_volatility",0)),    "Coefficient of variation"],
    ]

    ind_table = Table(indicator_data, colWidths=["25%","15%","18%","42%"])
    ind_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  DARK),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),  [WHITE, LIGHTGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#E5E7EB")),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("ALIGN",         (1,0), (2,-1),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    content.append(ind_table)
    content.append(Spacer(1, 16))

    # ════════════════════════════════════════
    # RULE FLAGS
    # ════════════════════════════════════════
    if flags:
        content.append(Paragraph("4. Rule Violations Detected", h1_style))
        content.append(HRFlowable(width="100%", thickness=0.5, color=LIGHTGRAY))
        content.append(Spacer(1, 6))

        flag_data = [["#", "Violation", "Severity"]]
        for i, flag in enumerate(flags):
            severity = "HIGH" if any(w in flag.lower() for w in ["extreme","critical","high"]) else "MEDIUM"
            flag_data.append([str(i+1), flag, severity])

        flag_table = Table(flag_data, colWidths=["6%","74%","20%"])
        flag_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),  (-1,0),  DARK),
            ("TEXTCOLOR",    (0,0),  (-1,0),  WHITE),
            ("FONTNAME",     (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0,0),  (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [HexColor("#FFF5F5"), WHITE]),
            ("GRID",         (0,0),  (-1,-1), 0.5, HexColor("#E5E7EB")),
            ("LEFTPADDING",  (0,0),  (-1,-1), 8),
            ("RIGHTPADDING", (0,0),  (-1,-1), 8),
            ("TOPPADDING",   (0,0),  (-1,-1), 7),
            ("BOTTOMPADDING",(0,0),  (-1,-1), 7),
            ("ALIGN",        (0,0),  (0,-1),  "CENTER"),
            ("ALIGN",        (2,0),  (2,-1),  "CENTER"),
            ("VALIGN",       (0,0),  (-1,-1), "MIDDLE"),
        ]))
        content.append(flag_table)
        content.append(Spacer(1, 16))

    # ════════════════════════════════════════
    # RECOMMENDATION
    # ════════════════════════════════════════
    content.append(Paragraph("5. Investigation Recommendation", h1_style))
    content.append(HRFlowable(width="100%", thickness=0.5, color=LIGHTGRAY))
    content.append(Spacer(1, 6))

    rec_table = Table(
        [[Paragraph(f"<b>Action Required:</b><br/>{recommend}", body_style)]],
        colWidths=["100%"]
    )
    rec_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), HexColor("#FFF5F5") if level=="CRITICAL" else LIGHTGRAY),
        ("BOX",          (0,0), (-1,-1), 1.5, color),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
    ]))
    content.append(rec_table)
    content.append(Spacer(1, 20))

    # ════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════
    content.append(HRFlowable(width="100%", thickness=1, color=LIGHTGRAY))
    content.append(Spacer(1, 6))
    content.append(Paragraph(
        "This report is generated by GST FraudShield AI System. "
        "For official use only. Results are indicative and require human verification before action.",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))
    content.append(Paragraph(
        f"Report ID: {gstin}-{datetime.now().strftime('%Y%m%d%H%M%S')} | "
        f"Confidence: {score:.1f}% | Model Version: 2.0",
        ParagraphStyle("footer2", parent=styles["Normal"],
                       fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()