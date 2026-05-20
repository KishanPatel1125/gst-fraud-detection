"""
GST Fraud Detection System
FastAPI Backend — Phase 4
Exposes all ML models via REST API endpoints
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
import pickle
import json
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────
app = FastAPI(
    title       = "GST Fraud Detection API",
    description = "Detects GST fraud using XGBoost + Isolation Forest + Graph Analysis",
    version     = "1.0.0",
)

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR  = os.path.join(BASE_DIR, "src", "models", "saved")
RESULTS_DIR = os.path.join(BASE_DIR, "data", "processed")
SYNTH_DIR   = os.path.join(BASE_DIR, "data", "synthetic")

# ─────────────────────────────────────────
# LOAD ALL MODELS AND DATA AT STARTUP
# Models are loaded once — reused for every request
# ─────────────────────────────────────────
print("Loading models and data...")

# Load XGBoost model
try:
    import xgboost as xgb
    from sklearn.preprocessing import LabelEncoder
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(os.path.join(MODELS_DIR, "xgboost_fraud_model.json"))
    with open(os.path.join(MODELS_DIR, "encoders.pkl"), "rb") as f:
        encoders = pickle.load(f)
    print("  ✅ XGBoost model loaded")
except Exception as e:
    print(f"  ❌ XGBoost load failed: {e}")
    xgb_model = None

# Load Isolation Forest
try:
    with open(os.path.join(MODELS_DIR, "isolation_forest.pkl"), "rb") as f:
        iso_model = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "anomaly_scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    print("  ✅ Isolation Forest loaded")
except Exception as e:
    print(f"  ❌ Isolation Forest load failed: {e}")
    iso_model = None

# Load graph scores
try:
    with open(os.path.join(MODELS_DIR, "transaction_graph.pkl"), "rb") as f:
        graph_scores = pickle.load(f)
    print("  ✅ Graph model loaded")
except Exception as e:
    print(f"  ❌ Graph model load failed: {e}")
    graph_scores = {}

# Load ensemble scores (pre-computed)
try:
    ensemble_df  = pd.read_csv(os.path.join(RESULTS_DIR, "ensemble_scores.csv"))
    alerts_df    = pd.read_csv(os.path.join(RESULTS_DIR, "fraud_alerts.csv"))
    features_df  = pd.read_csv(os.path.join(SYNTH_DIR,   "ml_features.csv"))
    companies_df = pd.read_csv(os.path.join(SYNTH_DIR,   "companies.csv"))
    print("  ✅ Data files loaded")
    print(f"     {len(ensemble_df):,} GSTINs | {len(alerts_df):,} alerts")
except Exception as e:
    print(f"  ❌ Data load failed: {e}")
    ensemble_df  = pd.DataFrame()
    alerts_df    = pd.DataFrame()
    features_df  = pd.DataFrame()
    companies_df = pd.DataFrame()

print("All models ready!\n")


# ─────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# Pydantic models define what data the API
# accepts and returns
# ─────────────────────────────────────────
class GSTINAnalyzeRequest(BaseModel):
    gstin: str

class ScoreBreakdown(BaseModel):
    xgb_score:          float
    anomaly_score:      float
    graph_risk_score:   float
    rule_score:         float
    ensemble_score:     float
    risk_level:         str
    models_agreeing:    int

class FraudAlert(BaseModel):
    gstin:          str
    ensemble_score: float
    risk_level:     str
    fraud_type:     str
    xgb_score:      float
    anomaly_score:  float
    graph_risk_score: float


# ─────────────────────────────────────────
# HELPER: Get risk level label
# ─────────────────────────────────────────
def get_risk_level(score: float) -> str:
    if score >= 81: return "CRITICAL"
    if score >= 61: return "HIGH"
    if score >= 31: return "MEDIUM"
    return "LOW"

def get_risk_color(level: str) -> str:
    colors = {
        "CRITICAL": "#DC2626",
        "HIGH":     "#EA580C",
        "MEDIUM":   "#CA8A04",
        "LOW":      "#16A34A",
    }
    return colors.get(level, "#6B7280")


# ─────────────────────────────────────────
# ENDPOINT 1: Health check
# GET /health
# Simple check to confirm API is running
# ─────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Check if API is running and models are loaded"""
    return {
        "status":       "running",
        "models_loaded": {
            "xgboost":          xgb_model is not None,
            "isolation_forest": iso_model is not None,
            "graph_model":      len(graph_scores) > 0,
            "ensemble_data":    len(ensemble_df) > 0,
        },
        "total_gstins": len(ensemble_df),
        "total_alerts": len(alerts_df),
    }


# ─────────────────────────────────────────
# ENDPOINT 2: Dashboard statistics
# GET /api/dashboard/stats
# Returns summary numbers for the main dashboard
# ─────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats():
    """Get summary statistics for the main dashboard"""
    if ensemble_df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    total      = len(ensemble_df)
    critical   = len(ensemble_df[ensemble_df["risk_level"] == "CRITICAL"])
    high       = len(ensemble_df[ensemble_df["risk_level"] == "HIGH"])
    medium     = len(ensemble_df[ensemble_df["risk_level"] == "MEDIUM"])
    low        = len(ensemble_df[ensemble_df["risk_level"] == "LOW"])
    total_alerts = critical + high

    # Fraud type breakdown
    fraud_types = {}
    if "fraud_type" in ensemble_df.columns:
        ft = ensemble_df[ensemble_df["is_fraud"] == 1]["fraud_type"].value_counts()
        fraud_types = ft.to_dict()

    # Average scores
    avg_score = ensemble_df["ensemble_score"].mean()

    # State-wise fraud (from companies data)
    state_fraud = {}
    if not companies_df.empty and "state_name" in companies_df.columns:
        merged = companies_df.merge(
            ensemble_df[["gstin", "ensemble_score", "risk_level"]],
            on="gstin", how="left"
        )
        state_data = merged.groupby("state_name")["ensemble_score"].mean()
        state_fraud = state_data.round(2).to_dict()

    return {
        "total_gstins":     total,
        "critical_count":   critical,
        "high_count":       high,
        "medium_count":     medium,
        "low_count":        low,
        "total_alerts":     total_alerts,
        "alert_rate":       round(total_alerts / total * 100, 2),
        "avg_risk_score":   round(avg_score, 2),
        "fraud_type_breakdown": fraud_types,
        "state_wise_avg_risk":  state_fraud,
        "risk_distribution": {
            "CRITICAL": critical,
            "HIGH":     high,
            "MEDIUM":   medium,
            "LOW":      low,
        }
    }


# ─────────────────────────────────────────
# ENDPOINT 3: Get GSTIN fraud report
# GET /api/gstin/{gstin_id}
# Returns full fraud analysis for one GSTIN
# ─────────────────────────────────────────
@app.get("/api/gstin/{gstin_id}", tags=["GSTIN Analysis"])
def get_gstin_report(gstin_id: str):
    """Get complete fraud analysis report for a specific GSTIN"""
    gstin_id = gstin_id.upper().strip()

    # Find in ensemble scores
    row = ensemble_df[ensemble_df["gstin"] == gstin_id]
    if row.empty:
        raise HTTPException(
            status_code = 404,
            detail      = f"GSTIN {gstin_id} not found in database"
        )

    row = row.iloc[0]

    # Get company info
    company_row = companies_df[companies_df["gstin"] == gstin_id]
    company_info = {}
    if not company_row.empty:
        c = company_row.iloc[0]
        company_info = {
            "company_name":      c.get("company_name", "Unknown"),
            "state":             c.get("state_name", "Unknown"),
            "industry":          c.get("industry", "Unknown"),
            "annual_turnover":   float(c.get("annual_turnover", 0)),
            "registration_date": str(c.get("registration_date", "Unknown")),
            "years_old":         int(c.get("years_old", 0)),
        }

    # Get feature details
    feat_row = features_df[features_df["gstin"] == gstin_id]
    features_info = {}
    if not feat_row.empty:
        f = feat_row.iloc[0]
        features_info = {
            "avg_itc_ratio":      round(float(f.get("avg_itc_ratio", 0)), 4),
            "filing_rate":        round(float(f.get("filing_rate", 0)), 4),
            "missing_returns":    int(f.get("missing_returns", 0)),
            "avg_delay_days":     round(float(f.get("avg_delay_days", 0)), 2),
            "spike_ratio":        round(float(f.get("spike_ratio", 1)), 4),
            "invoice_match_rate": round(float(f.get("invoice_match_rate", 1)), 4),
            "sales_volatility":   round(float(f.get("sales_volatility", 0)), 4),
            "unique_buyers":      int(f.get("unique_buyers", 0)),
            "unique_suppliers":   int(f.get("unique_suppliers", 0)),
        }

    # Build fraud reasons from rule flags
    rule_flags = str(row.get("rule_flags", "No flags"))
    reasons    = [f.strip() for f in rule_flags.split("|") if f.strip() != "No flags"]

    # Graph info
    graph_info = graph_scores.get(gstin_id, {})

    risk_level = str(row.get("risk_level", "LOW"))

    return {
        "gstin":         gstin_id,
        "company_info":  company_info,
        "risk_summary": {
            "ensemble_score":   round(float(row.get("ensemble_score", 0)), 2),
            "risk_level":       risk_level,
            "risk_color":       get_risk_color(risk_level),
            "is_fraud":         bool(row.get("is_fraud", 0)),
            "fraud_type":       str(row.get("fraud_type", "none")),
            "in_circular_ring": bool(row.get("in_circular_ring", 0)),
            "models_agreeing":  int(row.get("models_agreeing", 0)),
        },
        "score_breakdown": {
            "xgb_score":        round(float(row.get("xgb_score", 0)), 2),
            "anomaly_score":    round(float(row.get("anomaly_score", 0)), 2),
            "graph_risk_score": round(float(row.get("graph_risk_score", 0)), 2),
            "rule_score":       round(float(row.get("rule_score", 0)), 2),
            "ensemble_score":   round(float(row.get("ensemble_score", 0)), 2),
        },
        "fraud_indicators": features_info,
        "rule_flags":       reasons,
        "graph_metrics": {
            "pagerank_score":  round(float(graph_info.get("pagerank_score", 0)), 2),
            "in_degree":       int(graph_info.get("in_degree", 0)),
            "out_degree":      int(graph_info.get("out_degree", 0)),
            "cycle_risk":      float(graph_info.get("cycle_risk", 0)),
            "imbalance_risk":  float(graph_info.get("imbalance_risk", 0)),
        },
        "recommendation": get_recommendation(risk_level, reasons),
    }


# ─────────────────────────────────────────
# ENDPOINT 4: Get all fraud alerts
# GET /api/alerts
# Returns all CRITICAL and HIGH risk GSTINs
# Supports pagination and filtering
# ─────────────────────────────────────────
@app.get("/api/alerts", tags=["Alerts"])
def get_fraud_alerts(
    risk_level:  Optional[str] = None,
    fraud_type:  Optional[str] = None,
    min_score:   Optional[float] = None,
    page:        int = 1,
    page_size:   int = 50,
):
    """
    Get all fraud alerts with optional filters.
    - risk_level: CRITICAL, HIGH, MEDIUM, LOW
    - fraud_type: fake_itc, circular_trading, shell_company, etc.
    - min_score:  minimum ensemble score (0-100)
    - page:       page number for pagination
    - page_size:  results per page (max 100)
    """
    if alerts_df.empty:
        raise HTTPException(status_code=500, detail="Alerts data not loaded")

    df = alerts_df.copy()

    # Apply filters
    if risk_level:
        df = df[df["risk_level"] == risk_level.upper()]
    if fraud_type:
        df = df[df["fraud_type"] == fraud_type.lower()]
    if min_score is not None:
        df = df[df["ensemble_score"] >= min_score]

    # Sort by highest risk
    df = df.sort_values("ensemble_score", ascending=False)

    # Pagination
    total       = len(df)
    page_size   = min(page_size, 100)
    start       = (page - 1) * page_size
    end         = start + page_size
    page_df     = df.iloc[start:end]

    alerts = []
    for _, row in page_df.iterrows():
        alerts.append({
            "gstin":            str(row["gstin"]),
            "ensemble_score":   round(float(row["ensemble_score"]), 2),
            "risk_level":       str(row["risk_level"]),
            "risk_color":       get_risk_color(str(row["risk_level"])),
            "fraud_type":       str(row.get("fraud_type", "unknown")),
            "xgb_score":        round(float(row.get("xgb_score", 0)), 2),
            "anomaly_score":    round(float(row.get("anomaly_score", 0)), 2),
            "graph_risk_score": round(float(row.get("graph_risk_score", 0)), 2),
            "in_circular_ring": bool(row.get("in_circular_ring", 0)),
            "models_agreeing":  int(row.get("models_agreeing", 0)),
        })

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     (total + page_size - 1) // page_size,
        "alerts":    alerts,
    }


# ─────────────────────────────────────────
# ENDPOINT 5: Analyze a new GSTIN on the fly
# POST /api/analyze
# Takes raw features and returns live prediction
# ─────────────────────────────────────────
@app.post("/api/analyze", tags=["GSTIN Analysis"])
def analyze_gstin(request: GSTINAnalyzeRequest):
    """
    Analyze a GSTIN from precomputed results.
    For live prediction of new GSTINs, use /api/predict.
    """
    gstin = request.gstin.upper().strip()

    # Check if already analyzed
    row = ensemble_df[ensemble_df["gstin"] == gstin]
    if not row.empty:
        return get_gstin_report(gstin)

    raise HTTPException(
        status_code = 404,
        detail      = f"GSTIN {gstin} not found. Upload data first via /api/upload"
    )


# ─────────────────────────────────────────
# ENDPOINT 6: Search GSTINs
# GET /api/search?q=24XXXXX
# ─────────────────────────────────────────
@app.get("/api/search", tags=["GSTIN Analysis"])
def search_gstin(q: str, limit: int = 10):
    """Search for GSTINs by partial match"""
    q = q.upper().strip()

    if ensemble_df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    # Find matching GSTINs
    matches = ensemble_df[
        ensemble_df["gstin"].str.contains(q, na=False)
    ].head(limit)

    results = []
    for _, row in matches.iterrows():
        risk_level = str(row.get("risk_level", "LOW"))
        results.append({
            "gstin":          str(row["gstin"]),
            "ensemble_score": round(float(row["ensemble_score"]), 2),
            "risk_level":     risk_level,
            "risk_color":     get_risk_color(risk_level),
            "fraud_type":     str(row.get("fraud_type", "none")),
        })

    return {
        "query":   q,
        "total":   len(results),
        "results": results,
    }


# ─────────────────────────────────────────
# ENDPOINT 7: Get top high-risk GSTINs
# GET /api/top-risks?n=20
# ─────────────────────────────────────────
@app.get("/api/top-risks", tags=["Dashboard"])
def get_top_risks(n: int = 20):
    """Get top N highest risk GSTINs"""
    if ensemble_df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    n   = min(n, 100)
    top = ensemble_df.nlargest(n, "ensemble_score")

    results = []
    for rank, (_, row) in enumerate(top.iterrows()):
        risk_level = str(row.get("risk_level", "LOW"))
        results.append({
            "rank":             rank + 1,
            "gstin":            str(row["gstin"]),
            "ensemble_score":   round(float(row["ensemble_score"]), 2),
            "risk_level":       risk_level,
            "risk_color":       get_risk_color(risk_level),
            "fraud_type":       str(row.get("fraud_type", "none")),
            "xgb_score":        round(float(row.get("xgb_score", 0)), 2),
            "anomaly_score":    round(float(row.get("anomaly_score", 0)), 2),
            "graph_risk_score": round(float(row.get("graph_risk_score", 0)), 2),
            "in_circular_ring": bool(row.get("in_circular_ring", 0)),
            "models_agreeing":  int(row.get("models_agreeing", 0)),
        })

    return {"total": len(results), "top_risks": results}


# ─────────────────────────────────────────
# ENDPOINT 8: Get fraud type statistics
# GET /api/stats/fraud-types
# ─────────────────────────────────────────
@app.get("/api/stats/fraud-types", tags=["Statistics"])
def get_fraud_type_stats():
    """Get breakdown of fraud by type"""
    if ensemble_df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    fraud_only = ensemble_df[ensemble_df["is_fraud"] == 1]

    stats = []
    for ftype in fraud_only["fraud_type"].unique():
        subset   = fraud_only[fraud_only["fraud_type"] == ftype]
        detected = (subset["ensemble_score"] >= 50).sum()
        stats.append({
            "fraud_type":     ftype,
            "total":          len(subset),
            "detected":       int(detected),
            "detection_rate": round(detected / len(subset) * 100, 1),
            "avg_score":      round(subset["ensemble_score"].mean(), 2),
            "max_score":      round(subset["ensemble_score"].max(), 2),
        })

    stats.sort(key=lambda x: x["total"], reverse=True)
    return {"fraud_type_stats": stats}


# ─────────────────────────────────────────
# ENDPOINT 9: Upload new CSV data
# POST /api/upload
# Accepts CSV file and returns analysis summary
# ─────────────────────────────────────────
@app.post("/api/upload", tags=["Data"])
async def upload_gstin_data(file: UploadFile = File(...)):
    """
    Upload a CSV file with GST data for analysis.
    Expected columns: gstin, itc_claimed, tax_collected,
    missing_returns, filing_rate, etc.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code = 400,
            detail      = "Only CSV files are accepted"
        )

    try:
        contents = await file.read()
        import io
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        required_cols = ["gstin"]
        missing_cols  = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code = 400,
                detail      = f"Missing required columns: {missing_cols}"
            )

        # Check how many GSTINs are already in our database
        known   = df["gstin"].isin(ensemble_df["gstin"]).sum()
        unknown = len(df) - known

        return {
            "status":          "success",
            "filename":        file.filename,
            "total_rows":      len(df),
            "columns_found":   list(df.columns),
            "known_gstins":    int(known),
            "unknown_gstins":  int(unknown),
            "message": (
                f"File uploaded successfully. "
                f"{known} GSTINs found in database, "
                f"{unknown} are new (run model pipeline to analyze)."
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────
# ENDPOINT 10: Model performance metrics
# GET /api/model-metrics
# ─────────────────────────────────────────
@app.get("/api/model-metrics", tags=["Statistics"])
def get_model_metrics():
    """Get performance metrics for all models"""
    metrics_path = os.path.join(MODELS_DIR, "ensemble_metrics.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics not found")

    with open(metrics_path) as f:
        metrics = json.load(f)

    return {
        "ensemble_model": metrics,
        "description": {
            "accuracy":  "Overall correct predictions",
            "precision": "Of flagged GSTINs, how many are real fraud",
            "recall":    "Of real fraud, how many we caught",
            "f1_score":  "Balance of precision and recall",
            "auc_roc":   "Model discrimination ability (1.0 = perfect)",
        }
    }


# ─────────────────────────────────────────
# HELPER: Generate recommendation text
# ─────────────────────────────────────────
def get_recommendation(risk_level: str, flags: list) -> str:
    if risk_level == "CRITICAL":
        return (
            "IMMEDIATE ACTION REQUIRED: This GSTIN shows strong indicators "
            "of fraud. Initiate detailed audit, freeze ITC claims pending "
            "verification, and escalate to senior GST officer."
        )
    elif risk_level == "HIGH":
        return (
            "HIGH PRIORITY REVIEW: Multiple fraud indicators detected. "
            "Request supporting documents for ITC claims, verify supplier "
            "invoices, and schedule physical verification."
        )
    elif risk_level == "MEDIUM":
        return (
            "MONITOR CLOSELY: Some anomalies detected. Add to watchlist "
            "and review next filing carefully. Request clarification on "
            "flagged items."
        )
    else:
        return (
            "LOW RISK: No significant fraud indicators. Continue routine "
            "monitoring as per standard compliance schedule."
        )


# ─────────────────────────────────────────
# ROOT — API documentation redirect
# ─────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    return {
        "message":     "GST Fraud Detection API is running!",
        "docs":        "/docs",
        "health":      "/health",
        "version":     "1.0.0",
        "endpoints": [
            "GET  /health",
            "GET  /api/dashboard/stats",
            "GET  /api/gstin/{gstin_id}",
            "GET  /api/alerts",
            "GET  /api/search?q=GSTIN",
            "GET  /api/top-risks",
            "GET  /api/stats/fraud-types",
            "POST /api/analyze",
            "POST /api/upload",
            "GET  /api/model-metrics",
        ]
    }