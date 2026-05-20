"""
GST Fraud Detection System
Ensemble Risk Scorer
Phase 3 - Step 6

Combines XGBoost + Isolation Forest + Graph Detector
into one final risk score per GSTIN.
Also adds rule-based compliance checks.
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder, StandardScaler


# ─────────────────────────────────────────
# STEP 1: Load all model scores
# ─────────────────────────────────────────
def load_all_scores():
    print("  Loading all model scores...")
    base_dir    = os.path.dirname(os.path.dirname(os.path.dirname(
                  os.path.abspath(__file__))))
    results_dir = os.path.join(base_dir, "data", "processed")
    synth_dir   = os.path.join(base_dir, "data", "synthetic")

    # Main fraud scores (has XGBoost + anomaly + graph scores)
    fraud_scores_path = os.path.join(results_dir, "fraud_scores.csv")
    graph_scores_path = os.path.join(results_dir, "graph_scores.csv")
    features_path     = os.path.join(synth_dir,   "ml_features.csv")
    filings_path      = os.path.join(synth_dir,   "gstr3b_filings.csv")

    fraud_df    = pd.read_csv(fraud_scores_path)
    graph_df    = pd.read_csv(graph_scores_path)
    features_df = pd.read_csv(features_path)
    filings_df  = pd.read_csv(filings_path)

    print(f"  Fraud scores loaded:   {len(fraud_df):,} rows")
    print(f"  Graph scores loaded:   {len(graph_df):,} rows")
    print(f"  Features loaded:       {len(features_df):,} rows")
    print(f"  Filings loaded:        {len(filings_df):,} rows")

    return fraud_df, graph_df, features_df, filings_df, base_dir


# ─────────────────────────────────────────
# STEP 2: Rebuild XGBoost scores
# Load saved model + re-predict for clean scores
# ─────────────────────────────────────────
def get_xgboost_scores(features_df, base_dir):
    print("\n  Loading XGBoost model and generating scores...")

    models_dir = os.path.join(base_dir, "src", "models", "saved")
    model_path = os.path.join(models_dir, "xgboost_fraud_model.json")
    enc_path   = os.path.join(models_dir, "encoders.pkl")

    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model(model_path)

    with open(enc_path, "rb") as f:
        encoders = pickle.load(f)

    df = features_df.copy()

    # Encode same way as training
    le_ind  = LabelEncoder()
    le_st   = LabelEncoder()
    le_sz   = LabelEncoder()
    df["industry_encoded"] = le_ind.fit_transform(df["industry"])
    df["state_encoded"]    = le_st.fit_transform(df["state_code"])
    df["size_encoded"]     = le_sz.fit_transform(df["size_type"])

    FEATURE_COLUMNS = encoders.get("feature_columns", [
        "years_old", "annual_turnover",
        "filing_rate", "missing_returns", "avg_delay_days",
        "avg_itc_ratio", "total_itc_claimed", "total_tax_paid",
        "total_outward_supply", "avg_monthly_sales",
        "sales_volatility", "spike_ratio",
        "invoices_issued", "invoices_received", "invoice_match_rate",
        "unique_buyers", "unique_suppliers", "companies_same_address",
        "industry_encoded", "state_encoded", "size_encoded"
    ])

    X = df[FEATURE_COLUMNS]
    proba = model.predict_proba(X)[:, 1]

    xgb_scores = pd.DataFrame({
        "gstin":       df["gstin"],
        "xgb_score":   (proba * 100).round(2),
    })

    print(f"  XGBoost scores generated for {len(xgb_scores):,} GSTINs")
    return xgb_scores


# ─────────────────────────────────────────
# STEP 3: Get Isolation Forest scores
# Already saved in fraud_scores.csv
# ─────────────────────────────────────────
def get_anomaly_scores(fraud_df):
    print("\n  Extracting anomaly scores...")

    if "anomaly_score" in fraud_df.columns:
        scores = fraud_df[["gstin", "anomaly_score"]].copy()
        scores.columns = ["gstin", "anomaly_score"]
    else:
        # Rebuild if not present
        print("  Anomaly score not found — using default 50")
        scores = pd.DataFrame({
            "gstin":         fraud_df["gstin"],
            "anomaly_score": 50.0
        })

    print(f"  Anomaly scores ready for {len(scores):,} GSTINs")
    print(f"  Score range: {scores['anomaly_score'].min():.1f}"
          f" to {scores['anomaly_score'].max():.1f}")
    return scores


# ─────────────────────────────────────────
# STEP 4: Rule-based compliance checks
#
# Simple hard rules that always apply:
# These are instant red flags regardless
# of what ML models say
# ─────────────────────────────────────────
def calculate_rule_scores(features_df, filings_df):
    print("\n  Calculating rule-based compliance scores...")

    rule_scores = []

    for _, row in features_df.iterrows():
        gstin = row["gstin"]
        score = 0
        flags = []

        # ── Rule 1: ITC ratio extremely high ──
        # Normal ITC ratio = 0.6 to 0.9
        # Above 1.5 = claiming more credit than tax paid
        itc_ratio = row.get("avg_itc_ratio", 0)
        if itc_ratio > 3.0:
            score += 40
            flags.append(f"ITC ratio {itc_ratio:.1f}x (extreme)")
        elif itc_ratio > 1.5:
            score += 25
            flags.append(f"ITC ratio {itc_ratio:.1f}x (high)")
        elif itc_ratio > 1.0:
            score += 10
            flags.append(f"ITC ratio {itc_ratio:.1f}x (above normal)")

        # ── Rule 2: Missing returns ──
        # More than 3 missing returns = serious
        missing = row.get("missing_returns", 0)
        if missing >= 6:
            score += 35
            flags.append(f"{missing} missing returns (critical)")
        elif missing >= 3:
            score += 20
            flags.append(f"{missing} missing returns (high)")
        elif missing >= 1:
            score += 8
            flags.append(f"{missing} missing return(s)")

        # ── Rule 3: Filing rate very low ──
        filing_rate = row.get("filing_rate", 1.0)
        if filing_rate < 0.5:
            score += 25
            flags.append(f"Filing rate {filing_rate*100:.0f}% (very low)")
        elif filing_rate < 0.75:
            score += 12
            flags.append(f"Filing rate {filing_rate*100:.0f}% (low)")

        # ── Rule 4: Sudden sales spike ──
        spike = row.get("spike_ratio", 1.0)
        if spike > 10:
            score += 30
            flags.append(f"Sales spike {spike:.1f}x (extreme)")
        elif spike > 5:
            score += 18
            flags.append(f"Sales spike {spike:.1f}x (high)")
        elif spike > 3:
            score += 8
            flags.append(f"Sales spike {spike:.1f}x (moderate)")

        # ── Rule 5: Invoice mismatch ──
        # Supplier invoices don't match buyer records
        match_rate = row.get("invoice_match_rate", 1.0)
        if match_rate < 0.7:
            score += 20
            flags.append(f"Invoice match rate {match_rate*100:.0f}% (low)")
        elif match_rate < 0.85:
            score += 8
            flags.append(f"Invoice match rate {match_rate*100:.0f}%")

        # ── Rule 6: Very new company, high turnover ──
        years_old = row.get("years_old", 5)
        turnover  = row.get("annual_turnover", 0)
        if years_old <= 1 and turnover > 10_00_00_000:  # 1yr old, >10Cr
            score += 20
            flags.append(f"New company ({years_old}yr) with high turnover")

        # ── Rule 7: High sales volatility ──
        volatility = row.get("sales_volatility", 0)
        if volatility > 2.0:
            score += 15
            flags.append(f"Sales volatility {volatility:.2f} (very high)")
        elif volatility > 1.0:
            score += 7
            flags.append(f"Sales volatility {volatility:.2f} (high)")

        # Cap at 100
        score = min(100, score)

        rule_scores.append({
            "gstin":      gstin,
            "rule_score": score,
            "rule_flags": " | ".join(flags) if flags else "No flags",
            "flag_count": len(flags),
        })

    rule_df = pd.DataFrame(rule_scores)
    print(f"  Rule scores calculated for {len(rule_df):,} GSTINs")
    flagged = (rule_df["rule_score"] > 0).sum()
    print(f"  GSTINs with at least one flag: {flagged:,} "
          f"({flagged/len(rule_df)*100:.1f}%)")
    return rule_df


# ─────────────────────────────────────────
# STEP 5: Combine all scores into ensemble
#
# Final Score = weighted average of all models
# Weights based on each model's strength:
#   XGBoost    35% — most accurate overall
#   Anomaly    25% — catches unknown fraud
#   Graph      25% — catches circular trading
#   Rules      15% — hard compliance checks
# ─────────────────────────────────────────
def calculate_ensemble_score(xgb_scores, anomaly_scores,
                              graph_df, rule_df, features_df):
    print("\n" + "─" * 50)
    print("  CALCULATING ENSEMBLE RISK SCORES")
    print("─" * 50)

    # Start with base features
    ensemble = features_df[["gstin", "is_fraud", "fraud_type"]].copy()

    # Merge all scores
    ensemble = ensemble.merge(
        xgb_scores[["gstin", "xgb_score"]], on="gstin", how="left"
    )
    ensemble = ensemble.merge(
        anomaly_scores[["gstin", "anomaly_score"]], on="gstin", how="left"
    )
    ensemble = ensemble.merge(
        graph_df[["gstin", "graph_risk_score", "in_circular_ring"]],
        on="gstin", how="left"
    )
    ensemble = ensemble.merge(
        rule_df[["gstin", "rule_score", "rule_flags", "flag_count"]],
        on="gstin", how="left"
    )

    # Fill missing scores with 50 (neutral)
    ensemble["xgb_score"]        = ensemble["xgb_score"].fillna(50)
    ensemble["anomaly_score"]     = ensemble["anomaly_score"].fillna(50)
    ensemble["graph_risk_score"]  = ensemble["graph_risk_score"].fillna(0)
    ensemble["rule_score"]        = ensemble["rule_score"].fillna(0)

    # ── ENSEMBLE FORMULA ──
    ensemble["ensemble_score"] = (
        0.35 * ensemble["xgb_score"]       +
        0.25 * ensemble["anomaly_score"]    +
        0.25 * ensemble["graph_risk_score"] +
        0.15 * ensemble["rule_score"]
    ).round(2)

    # Boost score if multiple models agree it's fraud
    # This increases confidence when all models flag same GSTIN
    xgb_flag    = (ensemble["xgb_score"]       >= 60).astype(int)
    anom_flag   = (ensemble["anomaly_score"]    >= 60).astype(int)
    graph_flag  = (ensemble["graph_risk_score"] >= 60).astype(int)
    rule_flag   = (ensemble["rule_score"]       >= 40).astype(int)
    agreement   = xgb_flag + anom_flag + graph_flag + rule_flag

    # Boost by 5% for each additional model that agrees
    boost = (agreement - 1).clip(lower=0) * 5
    ensemble["ensemble_score"] = (
        ensemble["ensemble_score"] + boost
    ).clip(upper=100).round(2)

    ensemble["models_agreeing"] = agreement

    # Risk level labels
    def risk_label(score):
        if score >= 81: return "CRITICAL"
        if score >= 61: return "HIGH"
        if score >= 31: return "MEDIUM"
        return "LOW"

    ensemble["risk_level"] = ensemble["ensemble_score"].apply(risk_label)

    # Sort by highest risk
    ensemble = ensemble.sort_values("ensemble_score", ascending=False)

    print(f"\n  Ensemble scores calculated for {len(ensemble):,} GSTINs")
    print(f"\n  Score weights used:")
    print(f"    XGBoost model:       35%")
    print(f"    Isolation Forest:    25%")
    print(f"    Graph detector:      25%")
    print(f"    Rule-based checks:   15%")
    print(f"    Multi-model boost:   +5% per extra model agreeing")

    return ensemble


# ─────────────────────────────────────────
# STEP 6: Evaluate ensemble performance
# ─────────────────────────────────────────
def evaluate_ensemble(ensemble):
    print("\n" + "─" * 50)
    print("  ENSEMBLE MODEL PERFORMANCE")
    print("─" * 50)

    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score
    )

    y_true      = ensemble["is_fraud"]
    y_pred      = (ensemble["ensemble_score"] >= 50).astype(int)
    y_score     = ensemble["ensemble_score"] / 100

    accuracy  = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall    = recall_score(y_true, y_pred, zero_division=0)
    f1        = f1_score(y_true, y_pred, zero_division=0)
    auc       = roc_auc_score(y_true, y_score)

    print(f"\n  At threshold score ≥ 50:")
    print(f"    Accuracy:  {accuracy*100:.2f}%")
    print(f"    Precision: {precision*100:.2f}%")
    print(f"    Recall:    {recall*100:.2f}%")
    print(f"    F1 Score:  {f1*100:.2f}%")
    print(f"    AUC-ROC:   {auc:.4f}")

    # Per fraud type breakdown
    print(f"\n  Detection by fraud type (threshold=50):")
    print(f"  {'Fraud Type':<22} {'Total':>6} {'Caught':>6} {'Rate':>7}")
    print(f"  {'─'*50}")
    for ftype in ["fake_itc", "circular_trading", "shell_company",
                  "missing_returns", "sudden_spike"]:
        mask   = ensemble["fraud_type"] == ftype
        total  = mask.sum()
        if total == 0:
            continue
        caught = (ensemble.loc[mask, "ensemble_score"] >= 50).sum()
        rate   = caught / total * 100
        bar    = "█" * int(rate / 10)
        print(f"  {ftype:<22} {total:>6} {caught:>6} {rate:>6.1f}%  {bar}")

    # Compare vs individual models
    print(f"\n  Ensemble vs Individual Models:")
    print(f"  {'Model':<22} {'AUC-ROC':>8} {'Recall':>8} {'Precision':>10}")
    print(f"  {'─'*52}")

    models_comparison = [
        ("XGBoost alone",     ensemble["xgb_score"] / 100),
        ("Isolation Forest",  ensemble["anomaly_score"] / 100),
        ("Graph detector",    ensemble["graph_risk_score"] / 100),
        ("ENSEMBLE (final)",  ensemble["ensemble_score"] / 100),
    ]

    for name, scores in models_comparison:
        try:
            m_auc  = roc_auc_score(y_true, scores)
            m_pred = (scores >= 0.5).astype(int)
            m_rec  = recall_score(y_true, m_pred, zero_division=0)
            m_pre  = precision_score(y_true, m_pred, zero_division=0)
            marker = " ← BEST" if name == "ENSEMBLE (final)" else ""
            print(f"  {name:<22} {m_auc:>8.4f} {m_rec*100:>7.1f}% "
                  f"{m_pre*100:>9.1f}%{marker}")
        except Exception:
            print(f"  {name:<22}  N/A")

    metrics = {
        "accuracy":  round(accuracy, 4),
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1_score":  round(f1, 4),
        "auc_roc":   round(auc, 4),
    }
    return metrics


# ─────────────────────────────────────────
# STEP 7: Show final risk dashboard
# ─────────────────────────────────────────
def show_risk_dashboard(ensemble):
    print("\n" + "─" * 50)
    print("  FINAL RISK DASHBOARD")
    print("─" * 50)

    critical = ensemble[ensemble["risk_level"] == "CRITICAL"]
    high     = ensemble[ensemble["risk_level"] == "HIGH"]
    medium   = ensemble[ensemble["risk_level"] == "MEDIUM"]
    low      = ensemble[ensemble["risk_level"] == "LOW"]

    total = len(ensemble)
    print(f"\n  Risk Distribution (all {total:,} GSTINs):")
    print(f"  ┌────────────────────────────────────────┐")
    print(f"  │ 🔴 CRITICAL (81-100): {len(critical):>5} GSTINs "
          f"({len(critical)/total*100:>4.1f}%) │")
    print(f"  │ 🟠 HIGH     (61-80):  {len(high):>5} GSTINs "
          f"({len(high)/total*100:>4.1f}%) │")
    print(f"  │ 🟡 MEDIUM   (31-60):  {len(medium):>5} GSTINs "
          f"({len(medium)/total*100:>4.1f}%) │")
    print(f"  │ 🟢 LOW      (0-30):   {len(low):>5} GSTINs "
          f"({len(low)/total*100:>4.1f}%) │")
    print(f"  └────────────────────────────────────────┘")

    # Multi-model agreement stats
    print(f"\n  Model Agreement (how many models flagged same GSTIN):")
    for i in range(5):
        count = (ensemble["models_agreeing"] == i).sum()
        bar   = "█" * (count // 50)
        print(f"    {i} models agree: {count:>5} GSTINs  {bar}")

    # Top 15 critical GSTINs
    print(f"\n  TOP 15 CRITICAL GSTINs — Investigate Immediately:")
    print(f"  {'#':<3} {'GSTIN':<20} {'Score':>6} {'XGB':>6} "
          f"{'Anom':>6} {'Graph':>6} {'Rules':>6} {'Type'}")
    print(f"  {'─'*80}")

    for rank, (_, row) in enumerate(critical.head(15).iterrows()):
        print(
            f"  {rank+1:<3} {row['gstin']:<20} "
            f"{row['ensemble_score']:>5.1f}% "
            f"{row['xgb_score']:>5.1f}% "
            f"{row['anomaly_score']:>5.1f}% "
            f"{row['graph_risk_score']:>5.1f}% "
            f"{row['rule_score']:>5.1f}% "
            f"{row['fraud_type']}"
        )

    # Show a sample fraud explanation
    if len(critical) > 0:
        sample = critical.iloc[0]
        print(f"\n  Sample fraud investigation — GSTIN: {sample['gstin']}")
        print(f"  {'─'*50}")
        print(f"  Final Risk Score:   {sample['ensemble_score']:.1f}% 🔴 CRITICAL")
        print(f"  Fraud Type:         {sample['fraud_type']}")
        print(f"  In circular ring:   {'YES' if sample.get('in_circular_ring',0)==1 else 'NO'}")
        print(f"\n  Score Breakdown:")
        print(f"    XGBoost score:    {sample['xgb_score']:.1f}%  × 35% = "
              f"{sample['xgb_score']*0.35:.1f} pts")
        print(f"    Anomaly score:    {sample['anomaly_score']:.1f}%  × 25% = "
              f"{sample['anomaly_score']*0.25:.1f} pts")
        print(f"    Graph score:      {sample['graph_risk_score']:.1f}%  × 25% = "
              f"{sample['graph_risk_score']*0.25:.1f} pts")
        print(f"    Rule score:       {sample['rule_score']:.1f}%  × 15% = "
              f"{sample['rule_score']*0.15:.1f} pts")
        print(f"    Multi-model boost: +{(sample['models_agreeing']-1)*5:.0f} pts")
        print(f"    ─────────────────────────────────")
        print(f"    FINAL SCORE:      {sample['ensemble_score']:.1f}%")
        print(f"\n  Rule flags triggered:")
        for flag in str(sample["rule_flags"]).split(" | "):
            print(f"    ⚠️  {flag}")


# ─────────────────────────────────────────
# STEP 8: Save final ensemble results
# ─────────────────────────────────────────
def save_ensemble_results(ensemble, metrics, base_dir):
    print("\n  Saving ensemble results...")

    results_dir = os.path.join(base_dir, "data", "processed")
    models_dir  = os.path.join(base_dir, "src", "models", "saved")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    # Save complete ensemble scores
    ensemble_path = os.path.join(results_dir, "ensemble_scores.csv")
    ensemble.to_csv(ensemble_path, index=False)

    # Save only critical + high risk for quick access
    alerts_path = os.path.join(results_dir, "fraud_alerts.csv")
    alerts = ensemble[ensemble["risk_level"].isin(["CRITICAL", "HIGH"])]
    alerts.to_csv(alerts_path, index=False)

    # Save metrics
    metrics_path = os.path.join(models_dir, "ensemble_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  Files saved:")
    print(f"    Full scores  → data/processed/ensemble_scores.csv")
    print(f"    Alerts only  → data/processed/fraud_alerts.csv")
    print(f"    Metrics      → src/models/saved/ensemble_metrics.json")
    print(f"\n  Alerts breakdown:")
    print(f"    CRITICAL alerts: {len(ensemble[ensemble['risk_level']=='CRITICAL']):,}")
    print(f"    HIGH alerts:     {len(ensemble[ensemble['risk_level']=='HIGH']):,}")
    print(f"    Total alerts:    {len(alerts):,}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - ENSEMBLE RISK SCORER")
    print("  (XGBoost + Isolation Forest + Graph + Rules)")
    print("=" * 55)

    print("\n[1/8] Loading all model scores...")
    fraud_df, graph_df, features_df, filings_df, base_dir = load_all_scores()

    print("\n[2/8] Getting XGBoost scores...")
    xgb_scores = get_xgboost_scores(features_df, base_dir)

    print("\n[3/8] Getting Isolation Forest scores...")
    anomaly_scores = get_anomaly_scores(fraud_df)

    print("\n[4/8] Calculating rule-based scores...")
    rule_df = calculate_rule_scores(features_df, filings_df)

    print("\n[5/8] Calculating ensemble scores...")
    ensemble = calculate_ensemble_score(
        xgb_scores, anomaly_scores, graph_df, rule_df, features_df
    )

    print("\n[6/8] Evaluating ensemble performance...")
    metrics = evaluate_ensemble(ensemble)

    print("\n[7/8] Final risk dashboard...")
    show_risk_dashboard(ensemble)

    print("\n[8/8] Saving results...")
    save_ensemble_results(ensemble, metrics, base_dir)

    print("\n" + "=" * 55)
    print("  ENSEMBLE SCORER COMPLETE!")
    print("=" * 55)

    critical = ensemble[ensemble["risk_level"] == "CRITICAL"]
    high     = ensemble[ensemble["risk_level"] == "HIGH"]

    print(f"\n  Final Summary:")
    print(f"    Total GSTINs analyzed: {len(ensemble):,}")
    print(f"    CRITICAL risk:         {len(critical):,} GSTINs")
    print(f"    HIGH risk:             {len(high):,} GSTINs")
    print(f"    Total alerts:          {len(critical)+len(high):,} GSTINs")
    print(f"\n  Model Performance:")
    print(f"    Accuracy:  {metrics['accuracy']*100:.2f}%")
    print(f"    Precision: {metrics['precision']*100:.2f}%")
    print(f"    Recall:    {metrics['recall']*100:.2f}%")
    print(f"    F1 Score:  {metrics['f1_score']*100:.2f}%")
    print(f"    AUC-ROC:   {metrics['auc_roc']:.4f}")
    print(f"\n  Phase 3 COMPLETE! All 4 models built:")
    print(f"    ✅ XGBoost Fraud Classifier")
    print(f"    ✅ Isolation Forest Anomaly Detector")
    print(f"    ✅ Graph Circular Trading Detector")
    print(f"    ✅ Ensemble Risk Scorer")
    print(f"\n  Next: Phase 4 — FastAPI Backend")
    print(f"  (expose all models via REST API)")
    print("=" * 55)


if __name__ == "__main__":
    main()