"""
GST Fraud Detection System
Bulk Upload Processor
Phase 4 - Advanced Feature

Allows uploading 1000+ GSTINs via CSV
and analyzing all of them at once.
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
import io
from datetime import datetime
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────
# REQUIRED COLUMNS for bulk upload CSV
# ─────────────────────────────────────────
REQUIRED_COLUMNS = ["gstin"]

OPTIONAL_COLUMNS = [
    "company_name", "state_code", "industry",
    "annual_turnover", "filing_rate", "missing_returns",
    "avg_itc_ratio", "itc_claimed", "tax_collected",
    "invoice_match_rate", "spike_ratio", "sales_volatility",
]

SAMPLE_CSV_TEMPLATE = """gstin,company_name,annual_turnover,missing_returns,avg_itc_ratio
27AABCU9603R1ZX,Sample Company 1,5000000,0,0.75
07AAACR5055K1Z5,Sample Company 2,12000000,2,1.2
24AAACC1596Q1ZJ,Sample Company 3,800000,6,3.5
"""


# ─────────────────────────────────────────
# STEP 1: Validate uploaded CSV
# ─────────────────────────────────────────
def validate_csv(df: pd.DataFrame) -> dict:
    errors   = []
    warnings = []

    # Check required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Validate GSTIN format
    import re
    gstin_pattern = re.compile(
        r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    )

    df["gstin"] = df["gstin"].str.upper().str.strip()
    invalid_gstins = df[~df["gstin"].str.match(
        r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        na=False
    )]["gstin"].tolist()

    if invalid_gstins:
        warnings.append(
            f"{len(invalid_gstins)} invalid GSTIN formats detected: "
            f"{invalid_gstins[:3]}..."
        )

    # Check for duplicates
    duplicates = df["gstin"].duplicated().sum()
    if duplicates > 0:
        warnings.append(f"{duplicates} duplicate GSTINs will be removed")
        df = df.drop_duplicates(subset=["gstin"])

    return {
        "valid":    True,
        "errors":   errors,
        "warnings": warnings,
        "rows":     len(df),
    }


# ─────────────────────────────────────────
# STEP 2: Check existing GSTINs in DB
# ─────────────────────────────────────────
def check_existing_gstins(gstins: list, db) -> dict:
    from models import FraudScore, Company

    existing_scores   = {}
    existing_companies= {}

    for gstin in gstins:
        score   = db.query(FraudScore).filter(
            FraudScore.gstin == gstin
        ).first()
        company = db.query(Company).filter(
            Company.gstin == gstin
        ).first()

        if score:
            existing_scores[gstin] = score
        if company:
            existing_companies[gstin] = company

    return {
        "existing_count": len(existing_scores),
        "new_count":      len(gstins) - len(existing_scores),
        "existing_scores":    existing_scores,
        "existing_companies": existing_companies,
    }


# ─────────────────────────────────────────
# STEP 3: Prepare features for new GSTINs
# For GSTINs not in DB — estimate features
# from the uploaded CSV data
# ─────────────────────────────────────────
def prepare_features_from_csv(df: pd.DataFrame) -> pd.DataFrame:
    features_list = []

    from sklearn.preprocessing import LabelEncoder
    le_industry = LabelEncoder()
    le_state    = LabelEncoder()
    le_size     = LabelEncoder()

    # Default values for missing columns
    defaults = {
        "annual_turnover":   5_000_000,
        "years_old":         3,
        "filing_rate":       0.95,
        "missing_returns":   0,
        "avg_delay_days":    0,
        "avg_itc_ratio":     0.75,
        "total_itc_claimed": 0,
        "total_tax_paid":    0,
        "total_outward_supply": 0,
        "avg_monthly_sales": 0,
        "sales_volatility":  0.1,
        "spike_ratio":       1.0,
        "invoices_issued":   50,
        "invoices_received": 50,
        "invoice_match_rate":0.95,
        "unique_buyers":     10,
        "unique_suppliers":  10,
        "companies_same_address": 1,
        "industry":          "Trading",
        "state_code":        "24",
        "size_type":         "small",
    }

    for _, row in df.iterrows():
        feat = {}
        for col, default in defaults.items():
            feat[col] = row.get(col, default)

        # Encode categorical
        feat["industry_encoded"] = hash(str(feat["industry"])) % 20
        feat["state_encoded"]    = int(str(feat["state_code"])[:2]) if str(feat["state_code"]).isdigit() else 12
        feat["size_encoded"]     = {"small":0,"medium":1,"large":2}.get(str(feat["size_type"]),0)
        feat["gstin"]            = row["gstin"]

        features_list.append(feat)

    return pd.DataFrame(features_list)


# ─────────────────────────────────────────
# STEP 4: Run ML models on new GSTINs
# ─────────────────────────────────────────
def run_ml_models(features_df: pd.DataFrame, base_dir: str) -> pd.DataFrame:
    models_dir = os.path.join(base_dir, "src", "models", "saved")

    FEATURE_COLUMNS = [
        "years_old", "annual_turnover",
        "filing_rate", "missing_returns", "avg_delay_days",
        "avg_itc_ratio", "total_itc_claimed", "total_tax_paid",
        "total_outward_supply", "avg_monthly_sales",
        "sales_volatility", "spike_ratio",
        "invoices_issued", "invoices_received", "invoice_match_rate",
        "unique_buyers", "unique_suppliers", "companies_same_address",
        "industry_encoded", "state_encoded", "size_encoded"
    ]

    results = []

    # ── XGBoost Score ──
    xgb_scores = np.zeros(len(features_df))
    try:
        import xgboost as xgb
        model = xgb.XGBClassifier()
        model.load_model(os.path.join(models_dir, "xgboost_fraud_model.json"))
        X = features_df[FEATURE_COLUMNS].fillna(0)
        xgb_scores = model.predict_proba(X)[:, 1] * 100
    except Exception as e:
        print(f"    XGBoost warning: {e}")

    # ── Isolation Forest Score ──
    anomaly_scores = np.full(len(features_df), 50.0)
    try:
        with open(os.path.join(models_dir, "isolation_forest.pkl"), "rb") as f:
            iso_model = pickle.load(f)
        with open(os.path.join(models_dir, "anomaly_scaler.pkl"), "rb") as f:
            scaler = pickle.load(f)
        X_scaled    = scaler.transform(
            features_df[FEATURE_COLUMNS].fillna(0)
        )
        raw_scores  = iso_model.decision_function(X_scaled)
        flipped     = -raw_scores
        min_v, max_v= flipped.min(), flipped.max()
        anomaly_scores = (
            (flipped - min_v) / (max_v - min_v + 1e-8) * 100
        )
    except Exception as e:
        print(f"    Anomaly model warning: {e}")

    # ── Graph Score ──
    graph_scores_arr = np.zeros(len(features_df))
    try:
        with open(os.path.join(models_dir, "transaction_graph.pkl"), "rb") as f:
            graph_scores = pickle.load(f)
        for i, gstin in enumerate(features_df["gstin"]):
            gs = graph_scores.get(gstin, {})
            graph_scores_arr[i] = gs.get("graph_risk_score", 0)
    except Exception as e:
        print(f"    Graph model warning: {e}")

    # ── Rule-based Score ──
    rule_scores = np.zeros(len(features_df))
    for i, (_, row) in enumerate(features_df.iterrows()):
        score = 0
        itc_ratio  = row.get("avg_itc_ratio", 0)
        missing    = row.get("missing_returns", 0)
        filing_rate= row.get("filing_rate", 1)
        spike      = row.get("spike_ratio", 1)
        match_rate = row.get("invoice_match_rate", 1)

        if itc_ratio > 3.0:    score += 40
        elif itc_ratio > 1.5:  score += 25
        if missing >= 6:       score += 35
        elif missing >= 3:     score += 20
        if filing_rate < 0.5:  score += 25
        elif filing_rate < 0.75: score += 12
        if spike > 10:         score += 30
        elif spike > 5:        score += 18
        if match_rate < 0.7:   score += 20
        rule_scores[i] = min(100, score)

    # ── Ensemble Score ──
    ensemble_scores = (
        0.35 * xgb_scores      +
        0.25 * anomaly_scores   +
        0.25 * graph_scores_arr +
        0.15 * rule_scores
    ).clip(0, 100)

    # ── Risk levels ──
    def risk_label(s):
        if s >= 81: return "CRITICAL"
        if s >= 61: return "HIGH"
        if s >= 31: return "MEDIUM"
        return "LOW"

    results_df = pd.DataFrame({
        "gstin":            features_df["gstin"].values,
        "xgb_score":        xgb_scores.round(2),
        "anomaly_score":    anomaly_scores.round(2),
        "graph_risk_score": graph_scores_arr.round(2),
        "rule_score":       rule_scores.round(2),
        "ensemble_score":   ensemble_scores.round(2),
        "risk_level":       [risk_label(s) for s in ensemble_scores],
        "analyzed_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return results_df


# ─────────────────────────────────────────
# STEP 5: Generate bulk report CSV
# ─────────────────────────────────────────
def generate_bulk_report(results_df: pd.DataFrame,
                         upload_df: pd.DataFrame) -> bytes:
    # Merge with original upload data
    report = upload_df.merge(results_df, on="gstin", how="left")
    report = report.sort_values("ensemble_score", ascending=False)

    # Add human-readable columns
    report["fraud_probability"] = report["ensemble_score"].apply(
        lambda x: f"{x:.1f}%"
    )
    report["action_required"] = report["risk_level"].map({
        "CRITICAL": "IMMEDIATE - Freeze ITC and audit",
        "HIGH":     "URGENT - Verify documents within 48hrs",
        "MEDIUM":   "REVIEW - Add to watchlist",
        "LOW":      "NORMAL - Routine monitoring",
    })

    buffer = io.BytesIO()
    report.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────────────────────────
# MAIN BULK PROCESSOR
# Called by the FastAPI endpoint
# ─────────────────────────────────────────
def process_bulk_upload(
    file_contents: bytes,
    db,
    base_dir: str
) -> dict:
    """
    Main function called by FastAPI bulk upload endpoint.
    Returns analysis results for all GSTINs in the CSV.
    """

    # Parse CSV
    try:
        df = pd.read_csv(io.BytesIO(file_contents))
    except Exception as e:
        return {"error": f"Could not parse CSV: {e}"}

    # Validate
    validation = validate_csv(df)
    if not validation["valid"]:
        return {"error": validation["errors"]}

    df["gstin"] = df["gstin"].str.upper().str.strip()
    df = df.drop_duplicates(subset=["gstin"])

    # Check existing GSTINs in DB
    gstins   = df["gstin"].tolist()
    existing = check_existing_gstins(gstins, db)

    results = []

    # Return existing scores from DB
    for gstin, score in existing["existing_scores"].items():
        company = existing["existing_companies"].get(gstin)
        results.append({
            "gstin":            gstin,
            "company_name":     company.company_name if company else "Unknown",
            "ensemble_score":   score.ensemble_score,
            "xgb_score":        score.xgb_score,
            "anomaly_score":    score.anomaly_score,
            "graph_risk_score": score.graph_risk_score,
            "rule_score":       score.rule_score,
            "risk_level":       score.risk_level,
            "source":           "database",
            "analyzed_at":      str(score.analyzed_at),
        })

    # Analyze new GSTINs with ML models
    new_gstins = [g for g in gstins if g not in existing["existing_scores"]]
    if new_gstins:
        new_df       = df[df["gstin"].isin(new_gstins)].copy()
        features_df  = prepare_features_from_csv(new_df)
        ml_results   = run_ml_models(features_df, base_dir)

        for _, row in ml_results.iterrows():
            orig_row = new_df[new_df["gstin"] == row["gstin"]].iloc[0]
            results.append({
                "gstin":            row["gstin"],
                "company_name":     orig_row.get("company_name", "Unknown"),
                "ensemble_score":   row["ensemble_score"],
                "xgb_score":        row["xgb_score"],
                "anomaly_score":    row["anomaly_score"],
                "graph_risk_score": row["graph_risk_score"],
                "rule_score":       row["rule_score"],
                "risk_level":       row["risk_level"],
                "source":           "ml_model",
                "analyzed_at":      row["analyzed_at"],
            })

    # Sort by risk score
    results.sort(key=lambda x: x["ensemble_score"], reverse=True)

    # Summary statistics
    critical = sum(1 for r in results if r["risk_level"] == "CRITICAL")
    high     = sum(1 for r in results if r["risk_level"] == "HIGH")
    medium   = sum(1 for r in results if r["risk_level"] == "MEDIUM")
    low      = sum(1 for r in results if r["risk_level"] == "LOW")

    return {
        "status":          "success",
        "total_analyzed":  len(results),
        "from_database":   existing["existing_count"],
        "newly_analyzed":  len(new_gstins),
        "warnings":        validation.get("warnings", []),
        "summary": {
            "critical": critical,
            "high":     high,
            "medium":   medium,
            "low":      low,
        },
        "results": results,
    }