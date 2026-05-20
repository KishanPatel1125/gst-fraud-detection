"""
GST Fraud Detection System
Database Migration + Data Loader
Run this ONCE to:
1. Create all 6 tables in Supabase PostgreSQL
2. Load all 5,000 companies
3. Load all ML features
4. Load all fraud scores
5. Create fraud alerts
6. Load circular rings
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import engine, Base, test_connection
from models import (
    Company, FraudScore, MLFeature,
    FraudAlert, CircularRing, AuditLog
)
from sqlalchemy.orm import Session
from sqlalchemy import text

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH_DIR   = os.path.join(BASE_DIR, "data", "synthetic")
RESULTS_DIR = os.path.join(BASE_DIR, "data", "processed")


# ─────────────────────────────────────────
# STEP 1: Create all tables
# ─────────────────────────────────────────
def create_tables():
    print("\n  Creating tables in PostgreSQL...")
    try:
        Base.metadata.create_all(bind=engine)
        print("  ✅ All 6 tables created:")
        print("     companies, fraud_scores, ml_features,")
        print("     fraud_alerts, circular_rings, audit_log")
        return True
    except Exception as e:
        print(f"  ❌ Table creation failed: {e}")
        return False


# ─────────────────────────────────────────
# STEP 2: Load companies
# ─────────────────────────────────────────
def load_companies(session):
    print("\n  Loading companies...")
    path = os.path.join(SYNTH_DIR, "companies.csv")

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        return 0

    df = pd.read_csv(path)
    df = df.fillna("")

    # Check if already loaded
    existing = session.query(Company).count()
    if existing > 0:
        print(f"  ⚠️  {existing} companies already in DB — skipping")
        return existing

    batch_size = 500
    loaded     = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        objs  = []
        for _, row in batch.iterrows():
            objs.append(Company(
                gstin             = str(row["gstin"]),
                company_name      = str(row["company_name"]),
                state_code        = str(row["state_code"]),
                state_name        = str(row["state_name"]),
                industry          = str(row["industry"]),
                size_type         = str(row["size_type"]),
                annual_turnover   = float(row["annual_turnover"]) if row["annual_turnover"] else 0,
                registration_date = str(row["registration_date"]),
                years_old         = int(row["years_old"]) if row["years_old"] else 0,
                address_id        = int(row["address_id"]) if row["address_id"] else 0,
                is_fraud          = int(row["is_fraud"]) if row["is_fraud"] else 0,
                fraud_type        = str(row.get("fraud_type", "none")),
            ))

        session.bulk_save_objects(objs)
        session.commit()
        loaded += len(batch)
        print(f"    Loaded {loaded}/{len(df)} companies...")

    print(f"  ✅ {loaded} companies loaded")
    return loaded


# ─────────────────────────────────────────
# STEP 3: Load ML features
# ─────────────────────────────────────────
def load_ml_features(session):
    print("\n  Loading ML features...")
    path = os.path.join(SYNTH_DIR, "ml_features.csv")

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        return 0

    df = pd.read_csv(path)
    df = df.fillna(0)

    existing = session.query(MLFeature).count()
    if existing > 0:
        print(f"  ⚠️  {existing} features already in DB — skipping")
        return existing

    batch_size = 500
    loaded     = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        objs  = []
        for _, row in batch.iterrows():
            objs.append(MLFeature(
                gstin                  = str(row["gstin"]),
                filing_rate            = float(row.get("filing_rate", 0)),
                missing_returns        = int(row.get("missing_returns", 0)),
                avg_delay_days         = float(row.get("avg_delay_days", 0)),
                avg_itc_ratio          = float(row.get("avg_itc_ratio", 0)),
                total_itc_claimed      = float(row.get("total_itc_claimed", 0)),
                total_tax_paid         = float(row.get("total_tax_paid", 0)),
                total_outward_supply   = float(row.get("total_outward_supply", 0)),
                avg_monthly_sales      = float(row.get("avg_monthly_sales", 0)),
                sales_volatility       = float(row.get("sales_volatility", 0)),
                spike_ratio            = float(row.get("spike_ratio", 1)),
                invoices_issued        = int(row.get("invoices_issued", 0)),
                invoices_received      = int(row.get("invoices_received", 0)),
                invoice_match_rate     = float(row.get("invoice_match_rate", 1)),
                unique_buyers          = int(row.get("unique_buyers", 0)),
                unique_suppliers       = int(row.get("unique_suppliers", 0)),
                companies_same_address = int(row.get("companies_same_address", 0)),
            ))

        session.bulk_save_objects(objs)
        session.commit()
        loaded += len(batch)
        print(f"    Loaded {loaded}/{len(df)} features...")

    print(f"  ✅ {loaded} ML feature rows loaded")
    return loaded


# ─────────────────────────────────────────
# STEP 4: Load fraud scores (ensemble results)
# ─────────────────────────────────────────
def load_fraud_scores(session):
    print("\n  Loading fraud scores...")
    path = os.path.join(RESULTS_DIR, "ensemble_scores.csv")

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        return 0

    df = pd.read_csv(path)
    df = df.fillna(0)

    existing = session.query(FraudScore).count()
    if existing > 0:
        print(f"  ⚠️  {existing} scores already in DB — skipping")
        return existing

    batch_size = 500
    loaded     = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        objs  = []
        for _, row in batch.iterrows():
            objs.append(FraudScore(
                gstin            = str(row["gstin"]),
                xgb_score        = float(row.get("xgb_score", 0)),
                anomaly_score    = float(row.get("anomaly_score", 0)),
                graph_risk_score = float(row.get("graph_risk_score", 0)),
                rule_score       = float(row.get("rule_score", 0)),
                ensemble_score   = float(row.get("ensemble_score", 0)),
                risk_level       = str(row.get("risk_level", "LOW")),
                models_agreeing  = int(row.get("models_agreeing", 0)),
                in_circular_ring = bool(row.get("in_circular_ring", 0)),
                anomaly_flag     = bool(row.get("anomaly_flag", 0)),
                predicted_fraud  = bool(row.get("predicted_fraud", 0)),
                rule_flags       = str(row.get("rule_flags", "No flags")),
                flag_count       = int(row.get("flag_count", 0)),
            ))

        session.bulk_save_objects(objs)
        session.commit()
        loaded += len(batch)
        print(f"    Loaded {loaded}/{len(df)} scores...")

    print(f"  ✅ {loaded} fraud scores loaded")
    return loaded


# ─────────────────────────────────────────
# STEP 5: Create fraud alerts
# (CRITICAL and HIGH risk only)
# ─────────────────────────────────────────
def load_fraud_alerts(session):
    print("\n  Creating fraud alerts...")
    path = os.path.join(RESULTS_DIR, "ensemble_scores.csv")

    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        return 0

    df = pd.read_csv(path)
    alerts_df = df[df["risk_level"].isin(["CRITICAL", "HIGH"])].copy()

    existing = session.query(FraudAlert).count()
    if existing > 0:
        print(f"  ⚠️  {existing} alerts already in DB — skipping")
        return existing

    loaded = 0
    for _, row in alerts_df.iterrows():
        session.add(FraudAlert(
            gstin          = str(row["gstin"]),
            alert_type     = "AUTO",
            risk_level     = str(row["risk_level"]),
            ensemble_score = float(row["ensemble_score"]),
            fraud_type     = str(row.get("fraud_type", "unknown")),
            status         = "OPEN",
        ))
        loaded += 1

    session.commit()
    print(f"  ✅ {loaded} fraud alerts created ({len(alerts_df[alerts_df['risk_level']=='CRITICAL'])} CRITICAL, {len(alerts_df[alerts_df['risk_level']=='HIGH'])} HIGH)")
    return loaded


# ─────────────────────────────────────────
# STEP 6: Load circular trading rings
# ─────────────────────────────────────────
def load_circular_rings(session):
    print("\n  Loading circular trading rings...")
    path = os.path.join(RESULTS_DIR, "circular_rings.csv")

    if not os.path.exists(path):
        print(f"  ⚠️  circular_rings.csv not found — skipping")
        return 0

    df = pd.read_csv(path)

    existing = session.query(CircularRing).count()
    if existing > 0:
        print(f"  ⚠️  {existing} rings already in DB — skipping")
        return existing

    loaded = 0
    for _, row in df.iterrows():
        session.add(CircularRing(
            ring_id   = int(row["ring_id"]),
            ring_size = int(row["size"]),
            gstins    = str(row["gstins"]),
        ))
        loaded += 1

    session.commit()
    print(f"  ✅ {loaded} circular rings loaded")
    return loaded


# ─────────────────────────────────────────
# STEP 7: Add initial audit log entry
# ─────────────────────────────────────────
def add_audit_log(session):
    session.add(AuditLog(
        action  = "SYSTEM_INITIALIZED",
        user    = "system",
        details = "Database initialized with synthetic GST fraud detection data",
    ))
    session.commit()
    print("  ✅ Audit log initialized")


# ─────────────────────────────────────────
# STEP 8: Verify everything loaded correctly
# ─────────────────────────────────────────
def verify_data(session):
    print("\n" + "=" * 50)
    print("  DATABASE VERIFICATION")
    print("=" * 50)

    counts = {
        "companies":      session.query(Company).count(),
        "fraud_scores":   session.query(FraudScore).count(),
        "ml_features":    session.query(MLFeature).count(),
        "fraud_alerts":   session.query(FraudAlert).count(),
        "circular_rings": session.query(CircularRing).count(),
        "audit_log":      session.query(AuditLog).count(),
    }

    for table, count in counts.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {table:<20} {count:>6} rows")

    # Check critical alerts
    critical = session.query(FraudAlert).filter(
        FraudAlert.risk_level == "CRITICAL"
    ).count()
    high = session.query(FraudAlert).filter(
        FraudAlert.risk_level == "HIGH"
    ).count()

    print(f"\n  Alert breakdown:")
    print(f"    🔴 CRITICAL: {critical}")
    print(f"    🟠 HIGH:     {high}")

    # Top 3 highest risk
    top3 = session.query(FraudScore).order_by(
        FraudScore.ensemble_score.desc()
    ).limit(3).all()

    print(f"\n  Top 3 highest risk GSTINs:")
    for i, s in enumerate(top3):
        print(f"    {i+1}. {s.gstin} — {s.ensemble_score:.1f}% {s.risk_level}")

    return all(c > 0 for c in counts.values())


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 50)
    print("  GST FRAUD DETECTION - DATABASE MIGRATION")
    print("=" * 50)

    print("\n[1/9] Testing database connection...")
    if not test_connection():
        print("  Cannot connect to database. Check your .env file!")
        return

    print("\n[2/9] Creating tables...")
    if not create_tables():
        return

    with Session(engine) as session:
        print("\n[3/9] Loading companies...")
        load_companies(session)

        print("\n[4/9] Loading ML features...")
        load_ml_features(session)

        print("\n[5/9] Loading fraud scores...")
        load_fraud_scores(session)

        print("\n[6/9] Creating fraud alerts...")
        load_fraud_alerts(session)

        print("\n[7/9] Loading circular rings...")
        load_circular_rings(session)

        print("\n[8/9] Adding audit log...")
        add_audit_log(session)

        print("\n[9/9] Verifying data...")
        success = verify_data(session)

    print("\n" + "=" * 50)
    if success:
        print("  ✅ DATABASE SETUP COMPLETE!")
        print("  All data loaded into Supabase PostgreSQL")
        print("\n  Next: Update FastAPI to read from DB")
    else:
        print("  ⚠️  Some tables are empty — check errors above")
    print("=" * 50)


if __name__ == "__main__":
    main()