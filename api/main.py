"""
GST Fraud Detection System
FastAPI Backend — Phase 4 (Updated with PostgreSQL)
All data now reads from Supabase PostgreSQL database
"""
from bulk_processor import process_bulk_upload, generate_bulk_report, SAMPLE_CSV_TEMPLATE
from fastapi import Form
from fastapi.responses import StreamingResponse
from auth import authenticate_user, create_access_token, get_current_active_user, Token
from pdf_generator import generate_gstin_report
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import pandas as pd
import numpy as np
import pickle
import json
import os
import io
import sys
import warnings
warnings.filterwarnings("ignore")

# Add database path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "database"))

from db_config import get_db, engine
from models import (
    Company, FraudScore, MLFeature,
    FraudAlert, CircularRing, AuditLog
)

# ─────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────
app = FastAPI(
    title       = "GST Fraud Detection API",
    description = "AI-powered GST fraud detection — backed by Supabase PostgreSQL",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────
# PATHS & MODEL LOADING
# ─────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "src", "models", "saved")

print("Loading ML models...")
try:
    import xgboost as xgb
    from sklearn.preprocessing import LabelEncoder
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(os.path.join(MODELS_DIR, "xgboost_fraud_model.json"))
    with open(os.path.join(MODELS_DIR, "encoders.pkl"), "rb") as f:
        encoders = pickle.load(f)
    print("  ✅ XGBoost loaded")
except Exception as e:
    print(f"  ❌ XGBoost: {e}")
    xgb_model = None

try:
    with open(os.path.join(MODELS_DIR, "transaction_graph.pkl"), "rb") as f:
        graph_scores = pickle.load(f)
    print("  ✅ Graph model loaded")
except Exception as e:
    graph_scores = {}
    print(f"  ❌ Graph: {e}")

print("All models ready!\n")


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def risk_color(level: str) -> str:
    return {"CRITICAL":"#FF3B5C","HIGH":"#FF8C00","MEDIUM":"#FFD60A","LOW":"#30D158"}.get(level,"#8E8E93")

def log_action(db: Session, action: str, gstin: str = None, details: str = None):
    db.add(AuditLog(action=action, gstin=gstin, user="api", details=details))
    db.commit()

def get_recommendation(risk_level: str) -> str:
    return {
        "CRITICAL": "IMMEDIATE ACTION REQUIRED: Initiate detailed audit, freeze ITC claims, escalate to senior GST officer.",
        "HIGH":     "HIGH PRIORITY REVIEW: Request supporting documents, verify supplier invoices, schedule physical verification.",
        "MEDIUM":   "MONITOR CLOSELY: Add to watchlist and review next filing carefully.",
        "LOW":      "LOW RISK: Continue routine monitoring as per standard compliance schedule.",
    }.get(risk_level, "No recommendation available.")


# ─────────────────────────────────────────
# ENDPOINT 1: Health check
# ─────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        total = db.query(FraudScore).count()
        alerts = db.query(FraudAlert).count()
        db_ok = True
    except Exception:
        total = alerts = 0
        db_ok = False

    return {
        "status":       "running",
        "version":      "2.0.0",
        "database":     "Supabase PostgreSQL" if db_ok else "disconnected",
        "db_connected": db_ok,
        "total_gstins": total,
        "total_alerts": alerts,
        "models_loaded": {
            "xgboost":    xgb_model is not None,
            "graph_model":len(graph_scores) > 0,
        }
    }


# ─────────────────────────────────────────
# ENDPOINT 2: Dashboard statistics
# ─────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get summary statistics — reads from PostgreSQL"""

    # Risk level counts from fraud_scores table
    from sqlalchemy import case
    scores = db.query(FraudScore).all()

    critical = sum(1 for s in scores if s.risk_level == "CRITICAL")
    high     = sum(1 for s in scores if s.risk_level == "HIGH")
    medium   = sum(1 for s in scores if s.risk_level == "MEDIUM")
    low      = sum(1 for s in scores if s.risk_level == "LOW")
    total    = len(scores)
    avg_score= sum(s.ensemble_score for s in scores) / total if total > 0 else 0

    # Fraud type breakdown from companies
    fraud_companies = db.query(Company).filter(Company.is_fraud == 1).all()
    fraud_types = {}
    for c in fraud_companies:
        ft = c.fraud_type or "unknown"
        fraud_types[ft] = fraud_types.get(ft, 0) + 1

    # Circular rings count
    rings = db.query(CircularRing).count()

    return {
        "total_gstins":         total,
        "critical_count":       critical,
        "high_count":           high,
        "medium_count":         medium,
        "low_count":            low,
        "total_alerts":         critical + high,
        "alert_rate":           round((critical + high) / total * 100, 2) if total > 0 else 0,
        "avg_risk_score":       round(avg_score, 2),
        "fraud_type_breakdown": fraud_types,
        "circular_rings_found": rings,
        "risk_distribution":    {"CRITICAL":critical,"HIGH":high,"MEDIUM":medium,"LOW":low},
        "data_source":          "Supabase PostgreSQL",
    }


# ─────────────────────────────────────────
# ENDPOINT 3: Get GSTIN full report
# ─────────────────────────────────────────
@app.get("/api/gstin/{gstin_id}", tags=["GSTIN Analysis"])
def get_gstin_report(gstin_id: str, db: Session = Depends(get_db)):
    """Get complete fraud report for a GSTIN — from PostgreSQL"""
    gstin_id = gstin_id.upper().strip()

    # Get fraud score
    score = db.query(FraudScore).filter(FraudScore.gstin == gstin_id).first()
    if not score:
        raise HTTPException(status_code=404, detail=f"GSTIN {gstin_id} not found")

    # Get company info
    company = db.query(Company).filter(Company.gstin == gstin_id).first()

    # Get ML features
    features = db.query(MLFeature).filter(MLFeature.gstin == gstin_id).first()

    # Get alert if exists
    alert = db.query(FraudAlert).filter(FraudAlert.gstin == gstin_id).first()

    # Graph info
    graph_info = graph_scores.get(gstin_id, {})

    # Log this lookup
    log_action(db, "GSTIN_SEARCHED", gstin_id, f"Risk: {score.risk_level}")

    # Parse rule flags
    flags = [f.strip() for f in (score.rule_flags or "").split("|") if f.strip() != "No flags"]

    return {
        "gstin": gstin_id,
        "company_info": {
            "company_name":     company.company_name if company else "Unknown",
            "state":            company.state_name if company else "Unknown",
            "industry":         company.industry if company else "Unknown",
            "annual_turnover":  company.annual_turnover if company else 0,
            "registration_date":company.registration_date if company else "Unknown",
            "years_old":        company.years_old if company else 0,
        } if company else {},
        "risk_summary": {
            "ensemble_score":   round(score.ensemble_score, 2),
            "risk_level":       score.risk_level,
            "risk_color":       risk_color(score.risk_level),
            "is_fraud":         bool(company.is_fraud) if company else False,
            "fraud_type":       company.fraud_type if company else "unknown",
            "in_circular_ring": score.in_circular_ring,
            "models_agreeing":  score.models_agreeing,
        },
        "score_breakdown": {
            "xgb_score":        round(score.xgb_score, 2),
            "anomaly_score":    round(score.anomaly_score, 2),
            "graph_risk_score": round(score.graph_risk_score, 2),
            "rule_score":       round(score.rule_score, 2),
            "ensemble_score":   round(score.ensemble_score, 2),
        },
        "fraud_indicators": {
            "avg_itc_ratio":      round(features.avg_itc_ratio, 4) if features else 0,
            "filing_rate":        round(features.filing_rate, 4) if features else 0,
            "missing_returns":    features.missing_returns if features else 0,
            "avg_delay_days":     round(features.avg_delay_days, 2) if features else 0,
            "spike_ratio":        round(features.spike_ratio, 4) if features else 0,
            "invoice_match_rate": round(features.invoice_match_rate, 4) if features else 0,
            "sales_volatility":   round(features.sales_volatility, 4) if features else 0,
        } if features else {},
        "rule_flags":    flags,
        "alert_status":  alert.status if alert else None,
        "graph_metrics": {
            "pagerank_score": round(float(graph_info.get("pagerank_score", 0)), 2),
            "in_degree":      int(graph_info.get("in_degree", 0)),
            "out_degree":     int(graph_info.get("out_degree", 0)),
            "cycle_risk":     float(graph_info.get("cycle_risk", 0)),
        },
        "recommendation": get_recommendation(score.risk_level),
        "data_source":    "Supabase PostgreSQL",
    }


# ─────────────────────────────────────────
# ENDPOINT 4: Get all alerts
# ─────────────────────────────────────────
@app.get("/api/alerts", tags=["Alerts"])
def get_fraud_alerts(
    risk_level: Optional[str] = None,
    fraud_type: Optional[str] = None,
    status:     Optional[str] = None,
    min_score:  Optional[float] = None,
    page:       int = 1,
    page_size:  int = 50,
    db: Session = Depends(get_db),
):
    """Get fraud alerts from PostgreSQL with filters"""
    query = db.query(FraudAlert)

    if risk_level: query = query.filter(FraudAlert.risk_level == risk_level.upper())
    if status:     query = query.filter(FraudAlert.status == status.upper())
    if fraud_type: query = query.filter(FraudAlert.fraud_type == fraud_type.lower())
    if min_score:  query = query.filter(FraudAlert.ensemble_score >= min_score)

    query = query.order_by(desc(FraudAlert.ensemble_score))
    total = query.count()

    page_size = min(page_size, 100)
    alerts    = query.offset((page-1)*page_size).limit(page_size).all()

    results = []
    for a in alerts:
        score = db.query(FraudScore).filter(FraudScore.gstin == a.gstin).first()
        results.append({
            "id":               a.id,
            "gstin":            a.gstin,
            "ensemble_score":   a.ensemble_score,
            "risk_level":       a.risk_level,
            "risk_color":       risk_color(a.risk_level),
            "fraud_type":       a.fraud_type,
            "status":           a.status,
            "xgb_score":        round(score.xgb_score, 2) if score else 0,
            "anomaly_score":    round(score.anomaly_score, 2) if score else 0,
            "graph_risk_score": round(score.graph_risk_score, 2) if score else 0,
            "in_circular_ring": score.in_circular_ring if score else False,
            "models_agreeing":  score.models_agreeing if score else 0,
            "created_at":       str(a.created_at),
        })

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     (total + page_size - 1) // page_size,
        "alerts":    results,
        "data_source": "Supabase PostgreSQL",
    }


# ─────────────────────────────────────────
# ENDPOINT 5: Search GSTINs
# ─────────────────────────────────────────
@app.get("/api/search", tags=["GSTIN Analysis"])
def search_gstin(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """Search GSTINs by partial match — from PostgreSQL"""
    q = q.upper().strip()

    companies = db.query(Company).filter(
        Company.gstin.like(f"%{q}%")
    ).limit(limit).all()

    results = []
    for c in companies:
        score = db.query(FraudScore).filter(FraudScore.gstin == c.gstin).first()
        if score:
            results.append({
                "gstin":          c.gstin,
                "company_name":   c.company_name,
                "ensemble_score": round(score.ensemble_score, 2),
                "risk_level":     score.risk_level,
                "risk_color":     risk_color(score.risk_level),
                "fraud_type":     c.fraud_type,
            })

    return {"query": q, "total": len(results), "results": results}


# ─────────────────────────────────────────
# ENDPOINT 6: Top risks
# ─────────────────────────────────────────
@app.get("/api/top-risks", tags=["Dashboard"])
def get_top_risks(n: int = 20, db: Session = Depends(get_db)):
    """Get top N highest risk GSTINs from PostgreSQL"""
    n      = min(n, 100)
    scores = db.query(FraudScore).order_by(
        desc(FraudScore.ensemble_score)
    ).limit(n).all()

    results = []
    for rank, s in enumerate(scores):
        company = db.query(Company).filter(Company.gstin == s.gstin).first()
        results.append({
            "rank":             rank + 1,
            "gstin":            s.gstin,
            "ensemble_score":   round(s.ensemble_score, 2),
            "risk_level":       s.risk_level,
            "risk_color":       risk_color(s.risk_level),
            "fraud_type":       company.fraud_type if company else "unknown",
            "xgb_score":        round(s.xgb_score, 2),
            "anomaly_score":    round(s.anomaly_score, 2),
            "graph_risk_score": round(s.graph_risk_score, 2),
            "in_circular_ring": s.in_circular_ring,
            "models_agreeing":  s.models_agreeing,
        })

    return {"total": len(results), "top_risks": results, "data_source": "Supabase PostgreSQL"}


# ─────────────────────────────────────────
# ENDPOINT 7: Update alert status
# PATCH /api/alerts/{alert_id}
# ─────────────────────────────────────────
class AlertUpdate(BaseModel):
    status:      Optional[str] = None
    assigned_to: Optional[str] = None
    notes:       Optional[str] = None

@app.patch("/api/alerts/{alert_id}", tags=["Alerts"])
def update_alert(alert_id: int, update: AlertUpdate, db: Session = Depends(get_db)):
    """Update alert status — OPEN / INVESTIGATING / CLOSED"""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    if update.status:
        valid = ["OPEN","INVESTIGATING","CLOSED"]
        if update.status.upper() not in valid:
            raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
        alert.status = update.status.upper()
    if update.assigned_to: alert.assigned_to = update.assigned_to
    if update.notes:       alert.notes       = update.notes

    db.commit()
    log_action(db, "ALERT_UPDATED", alert.gstin, f"Status: {alert.status}")
    return {"message": "Alert updated", "alert_id": alert_id, "status": alert.status}


# ─────────────────────────────────────────
# ENDPOINT 8: Fraud type statistics
# ─────────────────────────────────────────
@app.get("/api/stats/fraud-types", tags=["Statistics"])
def get_fraud_type_stats(db: Session = Depends(get_db)):
    """Fraud type breakdown from PostgreSQL"""
    fraud_companies = db.query(Company).filter(Company.is_fraud == 1).all()

    stats = {}
    for c in fraud_companies:
        ft = c.fraud_type or "unknown"
        if ft not in stats:
            stats[ft] = {"fraud_type":ft,"total":0,"detected":0,"scores":[]}
        stats[ft]["total"] += 1
        score = db.query(FraudScore).filter(FraudScore.gstin == c.gstin).first()
        if score:
            stats[ft]["scores"].append(score.ensemble_score)
            if score.ensemble_score >= 50:
                stats[ft]["detected"] += 1

    result = []
    for ft, data in stats.items():
        scores = data["scores"]
        result.append({
            "fraud_type":     ft,
            "total":          data["total"],
            "detected":       data["detected"],
            "detection_rate": round(data["detected"]/data["total"]*100,1) if data["total"]>0 else 0,
            "avg_score":      round(sum(scores)/len(scores),2) if scores else 0,
            "max_score":      round(max(scores),2) if scores else 0,
        })

    result.sort(key=lambda x: x["total"], reverse=True)
    return {"fraud_type_stats": result, "data_source": "Supabase PostgreSQL"}


# ─────────────────────────────────────────
# ENDPOINT 9: Model metrics
# ─────────────────────────────────────────
@app.get("/api/model-metrics", tags=["Statistics"])
def get_model_metrics():
    metrics_path = os.path.join(MODELS_DIR, "ensemble_metrics.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics file not found")
    with open(metrics_path) as f:
        return {"ensemble_model": json.load(f), "data_source": "File"}


# ─────────────────────────────────────────
# ENDPOINT 10: Audit log
# ─────────────────────────────────────────
@app.get("/api/audit-log", tags=["System"])
def get_audit_log(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent system actions from PostgreSQL"""
    logs = db.query(AuditLog).order_by(
        desc(AuditLog.created_at)
    ).limit(limit).all()
    return {"logs": [l.to_dict() for l in logs], "total": len(logs)}


# ─────────────────────────────────────────
# ROOT
# ─────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    return {
        "message":     "GST Fraud Detection API v2.0 — PostgreSQL Edition",
        "docs":        "/docs",
        "database":    "Supabase PostgreSQL (South Asia - Mumbai)",
        "version":     "2.0.0",
    }
"""
ADD THESE TO YOUR api/main.py
New endpoints for Authentication + PDF Reports
"""

# ── ADD THESE IMPORTS at the top of main.py ──


# ── Auth endpoints ──────────────────────────

from auth import (
    authenticate_user, create_access_token,
    get_current_active_user, require_role, Token
)

@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Login with username and password.
    Returns JWT token valid for 8 hours.

    Default accounts:
    - admin / secret
    - officer / secret
    - ca / secret
    """
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code = 401,
            detail      = "Incorrect username or password",
            headers     = {"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user["username"]})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "username":  user["username"],
            "full_name": user["full_name"],
            "email":     user["email"],
            "role":      user["role"],
        }
    }


@app.get("/api/auth/me", tags=["Auth"])
async def get_me(current_user=Depends(get_current_active_user)):
    """Get current logged-in user details"""
    return {
        "username":  current_user["username"],
        "full_name": current_user["full_name"],
        "email":     current_user["email"],
        "role":      current_user["role"],
    }


@app.post("/api/auth/logout", tags=["Auth"])
async def logout():
    """Logout — client should delete the token"""
    return {"message": "Logged out successfully"}


# ── PDF Report endpoints ─────────────────────

from pdf_generator import generate_gstin_report

@app.get("/api/report/{gstin_id}", tags=["Reports"])
async def download_gstin_report(
    gstin_id: str,
    db: Session = Depends(get_db),
):
    """
    Download a PDF investigation report for a GSTIN.
    Returns a downloadable PDF file.
    """
    gstin_id = gstin_id.upper().strip()

    # Get all data (reuse existing endpoint logic)
    score = db.query(FraudScore).filter(
        FraudScore.gstin == gstin_id
    ).first()
    if not score:
        raise HTTPException(
            status_code=404,
            detail=f"GSTIN {gstin_id} not found"
        )

    company  = db.query(Company).filter(Company.gstin == gstin_id).first()
    features = db.query(MLFeature).filter(MLFeature.gstin == gstin_id).first()
    flags    = [
        f.strip() for f in (score.rule_flags or "").split("|")
        if f.strip() != "No flags"
    ]

    gstin_data = {
        "gstin": gstin_id,
        "company_info": {
            "company_name":     company.company_name if company else "Unknown",
            "state":            company.state_name if company else "Unknown",
            "industry":         company.industry if company else "Unknown",
            "annual_turnover":  company.annual_turnover if company else 0,
            "registration_date":company.registration_date if company else "N/A",
            "years_old":        company.years_old if company else 0,
        },
        "risk_summary": {
            "ensemble_score":   score.ensemble_score,
            "risk_level":       score.risk_level,
            "in_circular_ring": score.in_circular_ring,
            "models_agreeing":  score.models_agreeing,
        },
        "score_breakdown": {
            "xgb_score":        score.xgb_score,
            "anomaly_score":    score.anomaly_score,
            "graph_risk_score": score.graph_risk_score,
            "rule_score":       score.rule_score,
        },
        "fraud_indicators": {
            "avg_itc_ratio":      features.avg_itc_ratio if features else 0,
            "filing_rate":        features.filing_rate if features else 0,
            "missing_returns":    features.missing_returns if features else 0,
            "spike_ratio":        features.spike_ratio if features else 0,
            "invoice_match_rate": features.invoice_match_rate if features else 0,
            "sales_volatility":   features.sales_volatility if features else 0,
        },
        "rule_flags":    flags,
        "recommendation": get_recommendation(score.risk_level),
    }

    # Generate PDF
    pdf_bytes = generate_gstin_report(gstin_data)

    # Log the report download
    log_action(db, "REPORT_DOWNLOADED", gstin_id,
               f"PDF report downloaded for {score.risk_level} risk GSTIN")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type = "application/pdf",
        headers    = {
            "Content-Disposition": f"attachment; filename=GST_Report_{gstin_id}.pdf",
            "Content-Length":      str(len(pdf_bytes)),
        }
    )


@app.get("/api/report/bulk/alerts", tags=["Reports"])
async def download_alerts_report(
    risk_level: Optional[str] = "CRITICAL",
    db: Session = Depends(get_db),
):
    """Download a summary PDF of all alerts at a given risk level"""
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore[import]
        from reportlab.lib.pagesizes import A4  # type: ignore[import]
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import]
        from reportlab.lib.colors import HexColor  # type: ignore[import]
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation requires the reportlab package. Install it to enable PDF export."
        )

    alerts = db.query(FraudAlert).filter(
        FraudAlert.risk_level == risk_level.upper()
    ).order_by(FraudAlert.ensemble_score.desc()).all()

    if not alerts:
        raise HTTPException(
            status_code=404,
            detail=f"No {risk_level} alerts found"
        )

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=40, leftMargin=40,
                               topMargin=40, bottomMargin=40)
    styles  = getSampleStyleSheet()
    content = []

    content.append(Paragraph(
        f"GST FraudShield — {risk_level} Risk Alert Report",
        styles["Title"]
    ))
    content.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y')} | "
        f"Total Alerts: {len(alerts)}",
        styles["Normal"]
    ))
    content.append(Spacer(1, 20))

    data = [["#", "GSTIN", "Score", "Fraud Type", "Status"]]
    for i, a in enumerate(alerts):
        data.append([
            str(i+1),
            a.gstin,
            f"{a.ensemble_score:.1f}%",
            a.fraud_type or "unknown",
            a.status,
        ])

    table = Table(data, colWidths=["5%","30%","12%","30%","23%"])
    table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0),  HexColor("#1C1C1E")),
        ("TEXTCOLOR",    (0,0),(-1,0),  HexColor("#FFFFFF")),
        ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[HexColor("#FFFFFF"),HexColor("#F9FAFB")]),
        ("GRID",         (0,0),(-1,-1), 0.5, HexColor("#E5E7EB")),
        ("ALIGN",        (0,0),(0,-1),  "CENTER"),
        ("ALIGN",        (2,0),(2,-1),  "CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    content.append(table)
    doc.build(content)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type = "application/pdf",
        headers    = {
            "Content-Disposition": f"attachment; filename=GST_Alerts_{risk_level}.pdf",
        }
    )
# ────────────────────────────────────────
# ENDPOINT: Bulk Upload and Analyze
# POST /api/bulk/upload
# ────────────────────────────────────────
@app.post("/api/bulk/upload", tags=["Bulk Analysis"])
async def bulk_upload_analyze(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file with multiple GSTINs for bulk analysis.
 
    CSV Format (minimum):
    gstin
    27AABCU9603R1ZX
    07AAACR5055K1Z5
 
    CSV Format (with optional features):
    gstin,company_name,annual_turnover,missing_returns,avg_itc_ratio
    27AABCU9603R1ZX,Company A,5000000,0,0.75
 
    Returns fraud scores for all GSTINs.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files accepted"
        )
 
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum 10MB allowed"
        )
 
    contents = await file.read()
 
    results = process_bulk_upload(
        file_contents = contents,
        db            = db,
        base_dir      = BASE_DIR,
    )
 
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
 
    # Log the bulk upload
    log_action(
        db, "BULK_UPLOAD",
        details=f"Analyzed {results['total_analyzed']} GSTINs | "
                f"Critical: {results['summary']['critical']} | "
                f"High: {results['summary']['high']}"
    )
 
    return results
 
 
# ────────────────────────────────────────
# ENDPOINT: Download Bulk Report as CSV
# POST /api/bulk/download
# ────────────────────────────────────────
@app.post("/api/bulk/download", tags=["Bulk Analysis"])
async def bulk_download_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload CSV → analyze all GSTINs → download results as CSV report.
    The downloaded CSV includes fraud scores, risk levels, and recommended actions.
    """
    contents = await file.read()
 
    results = process_bulk_upload(
        file_contents = contents,
        db            = db,
        base_dir      = BASE_DIR,
    )
 
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
 
    # Convert results to DataFrame
    results_df = pd.DataFrame(results["results"])
 
    # Read original upload for company names
    import io as _io
    upload_df = pd.read_csv(_io.BytesIO(contents))
    upload_df["gstin"] = upload_df["gstin"].str.upper().str.strip()
 
    csv_bytes = generate_bulk_report(results_df, upload_df)
 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type = "text/csv",
        headers    = {
            "Content-Disposition":
                f"attachment; filename=GST_Bulk_Analysis_{timestamp}.csv"
        }
    )
 
 
# ────────────────────────────────────────
# ENDPOINT: Download Sample CSV Template
# GET /api/bulk/template
# ────────────────────────────────────────
@app.get("/api/bulk/template", tags=["Bulk Analysis"])
async def download_template():
    """
    Download a sample CSV template for bulk upload.
    Fill this template with your GSTINs and upload via /api/bulk/upload
    """
    return StreamingResponse(
        io.BytesIO(SAMPLE_CSV_TEMPLATE.encode()),
        media_type = "text/csv",
        headers    = {
            "Content-Disposition":
                "attachment; filename=GST_Bulk_Upload_Template.csv"
        }
    )
 
 
# ────────────────────────────────────────
# ENDPOINT: Bulk Upload Stats
# GET /api/bulk/stats
# ────────────────────────────────────────
@app.get("/api/bulk/stats", tags=["Bulk Analysis"])
async def get_bulk_stats(db: Session = Depends(get_db)):
    """Get statistics about bulk upload usage"""
    bulk_logs = db.query(AuditLog).filter(
        AuditLog.action == "BULK_UPLOAD"
    ).all()
 
    return {
        "total_bulk_uploads": len(bulk_logs),
        "last_upload":        str(bulk_logs[-1].created_at) if bulk_logs else None,
        "total_gstins_analyzed": sum(
            int(log.details.split("Analyzed")[1].split("GSTINs")[0].strip())
            for log in bulk_logs
            if log.details and "Analyzed" in log.details
        ) if bulk_logs else 0,
    }
 