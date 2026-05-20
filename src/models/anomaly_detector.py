"""
GST Fraud Detection System
Anomaly Detection Model - Isolation Forest
Phase 3 - Step 4

Detects unusual GSTINs WITHOUT needing labeled fraud data.
Catches new fraud patterns XGBoost has never seen before.
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_score, recall_score, f1_score
)

# ─────────────────────────────────────────
# STEP 1: Load feature data
# ─────────────────────────────────────────
def load_data():
    print("  Loading ml_features.csv...")
    base_dir      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    features_path = os.path.join(base_dir, "data", "synthetic", "ml_features.csv")
    df            = pd.read_csv(features_path)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df, base_dir


# ─────────────────────────────────────────
# STEP 2: Prepare and scale features
# Isolation Forest needs scaled numeric data
# ─────────────────────────────────────────
def prepare_features(df):
    print("\n  Encoding and scaling features...")

    le_industry = LabelEncoder()
    le_state    = LabelEncoder()
    le_size     = LabelEncoder()

    df["industry_encoded"] = le_industry.fit_transform(df["industry"])
    df["state_encoded"]    = le_state.fit_transform(df["state_code"])
    df["size_encoded"]     = le_size.fit_transform(df["size_type"])

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

    X = df[FEATURE_COLUMNS].copy()

    # Fill any missing values
    X = X.fillna(X.median())

    # Scale to same range — very important for Isolation Forest
    # Without scaling, large numbers (turnover) dominate small ones (filing_rate)
    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLUMNS)

    print(f"  Features scaled: {X_scaled.shape[1]} features for {X_scaled.shape[0]:,} GSTINs")

    return X, X_scaled, df, scaler, FEATURE_COLUMNS


# ─────────────────────────────────────────
# STEP 3: Train Isolation Forest
#
# HOW IT WORKS:
# It randomly isolates data points by splitting features.
# Normal points need many splits to isolate (they cluster together).
# Anomalies need very few splits (they are already isolated/different).
# contamination = expected % of fraud in data
# ─────────────────────────────────────────
def train_isolation_forest(X_scaled):
    print("\n  Training Isolation Forest...")
    print("  (This model needs NO fraud labels — fully unsupervised)")

    model = IsolationForest(
        n_estimators  = 200,    # number of isolation trees
        contamination = 0.20,   # we expect ~20% fraud in data
        max_samples   = "auto", # samples per tree
        random_state  = 42,
        n_jobs        = -1,     # use all CPU cores
    )

    model.fit(X_scaled)
    print("  Training complete!")
    return model


# ─────────────────────────────────────────
# STEP 4: Generate anomaly scores
#
# decision_function returns:
#   negative scores = more anomalous (fraud)
#   positive scores = more normal (legitimate)
#
# We convert to 0-100 anomaly score:
#   100 = most anomalous (likely fraud)
#   0   = most normal (legitimate)
# ─────────────────────────────────────────
def generate_anomaly_scores(model, X_scaled):
    print("\n  Generating anomaly scores...")

    # Raw scores: negative = anomaly, positive = normal
    raw_scores  = model.decision_function(X_scaled)

    # Labels: -1 = anomaly, 1 = normal
    predictions = model.predict(X_scaled)

    # Convert raw scores to 0-100 anomaly score
    # Flip sign so higher = more anomalous
    flipped     = -raw_scores

    # Normalize to 0-100 range
    min_val     = flipped.min()
    max_val     = flipped.max()
    anomaly_scores = ((flipped - min_val) / (max_val - min_val)) * 100

    # Convert -1/1 predictions to 1/0 (fraud/normal)
    fraud_pred  = (predictions == -1).astype(int)

    print(f"  Anomalies detected: {fraud_pred.sum():,} GSTINs ({fraud_pred.mean()*100:.1f}%)")
    print(f"  Score range: {anomaly_scores.min():.1f} to {anomaly_scores.max():.1f}")

    return anomaly_scores, fraud_pred


# ─────────────────────────────────────────
# STEP 5: Evaluate against known fraud labels
# ─────────────────────────────────────────
def evaluate_model(anomaly_scores, fraud_pred, df):
    print("\n" + "─" * 45)
    print("  ANOMALY DETECTION PERFORMANCE")
    print("─" * 45)

    y_true = df["is_fraud"].values

    precision = precision_score(y_true, fraud_pred, zero_division=0)
    recall    = recall_score(y_true, fraud_pred, zero_division=0)
    f1        = f1_score(y_true, fraud_pred, zero_division=0)

    # Normalize anomaly score for AUC
    norm_scores = anomaly_scores / 100
    try:
        auc = roc_auc_score(y_true, norm_scores)
    except Exception:
        auc = 0.0

    cm = confusion_matrix(y_true, fraud_pred)

    print(f"\n  Precision:  {precision*100:.2f}%  (of flagged, how many are real fraud)")
    print(f"  Recall:     {recall*100:.2f}%  (of real fraud, how many we caught)")
    print(f"  F1 Score:   {f1*100:.2f}%")
    print(f"  AUC-ROC:    {auc:.4f}")

    print(f"\n  Confusion Matrix:")
    print(f"  ┌─────────────────────────────────┐")
    print(f"  │              Predicted           │")
    print(f"  │          Normal    Fraud          │")
    print(f"  │ Actual Normal  {cm[0][0]:4d}      {cm[0][1]:4d}   │")
    print(f"  │ Actual Fraud   {cm[1][0]:4d}      {cm[1][1]:4d}   │")
    print(f"  └─────────────────────────────────┘")

    # Per fraud type breakdown
    print(f"\n  Detection by fraud type:")
    print(f"  {'Fraud Type':<22} {'Total':>6} {'Caught':>6} {'Rate':>7}")
    print(f"  {'─'*45}")

    for ftype in df["fraud_type"].unique():
        if ftype == "none":
            continue
        mask   = df["fraud_type"] == ftype
        total  = mask.sum()
        caught = (fraud_pred[mask] == 1).sum()
        rate   = caught / total * 100 if total > 0 else 0
        bar    = "█" * int(rate / 10)
        print(f"  {ftype:<22} {total:>6} {caught:>6} {rate:>6.1f}%  {bar}")

    metrics = {
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1_score":  round(f1, 4),
        "auc_roc":   round(auc, 4),
    }
    return metrics


# ─────────────────────────────────────────
# STEP 6: Find top anomalous features
# Which features made each GSTIN suspicious?
# ─────────────────────────────────────────
def analyze_anomalies(X, X_scaled, anomaly_scores, df, feature_names, top_n=5):
    print("\n" + "─" * 45)
    print("  TOP ANOMALOUS GSTINs — WHAT MADE THEM SUSPICIOUS")
    print("─" * 45)

    # Get top 10 most anomalous GSTINs
    top_idx = anomaly_scores.argsort()[::-1][:10]

    print(f"\n  {'#':<3} {'GSTIN':<20} {'Score':>6}  {'Actual':<8} Top anomalous feature")
    print(f"  {'─'*65}")

    for rank, idx in enumerate(top_idx):
        gstin   = df.iloc[idx]["gstin"]
        score   = anomaly_scores[idx]
        actual  = "FRAUD"  if df.iloc[idx]["is_fraud"] == 1 else "NORMAL"
        row     = X_scaled.iloc[idx]

        # Feature that deviates most from mean
        abs_vals     = row.abs()
        top_feature  = abs_vals.idxmax()
        top_val      = X.iloc[idx][top_feature]

        print(f"  {rank+1:<3} {gstin:<20} {score:>5.1f}%  {actual:<8} {top_feature} = {top_val:.2f}")

    # Show what normal vs anomalous looks like
    print(f"\n  Average feature values — Normal vs Anomalous GSTINs:")
    print(f"  {'Feature':<26} {'Normal':>12} {'Anomalous':>12} {'Difference':>12}")
    print(f"  {'─'*65}")

    anomaly_mask = anomaly_scores > 70
    normal_mask  = anomaly_scores < 30

    key_features = [
        "avg_itc_ratio", "filing_rate", "missing_returns",
        "spike_ratio", "sales_volatility", "invoice_match_rate"
    ]

    for feat in key_features:
        if feat not in X.columns:
            continue
        normal_avg   = X.loc[normal_mask, feat].mean()
        anomaly_avg  = X.loc[anomaly_mask, feat].mean()
        diff         = anomaly_avg - normal_avg
        direction    = "↑" if diff > 0 else "↓"
        print(f"  {feat:<26} {normal_avg:>12.3f} {anomaly_avg:>12.3f} {direction} {abs(diff):>10.3f}")


# ─────────────────────────────────────────
# STEP 7: PCA — visualize fraud clusters
# Reduces 21 features to 2D for understanding
# ─────────────────────────────────────────
def analyze_clusters(X_scaled, anomaly_scores, df):
    print("\n" + "─" * 45)
    print("  FRAUD CLUSTER ANALYSIS (via PCA)")
    print("─" * 45)

    pca        = PCA(n_components=2)
    X_pca      = pca.fit_transform(X_scaled)
    explained  = pca.explained_variance_ratio_

    print(f"\n  PCA variance explained:")
    print(f"    Component 1: {explained[0]*100:.1f}% of data patterns")
    print(f"    Component 2: {explained[1]*100:.1f}% of data patterns")
    print(f"    Total:       {sum(explained)*100:.1f}% captured in 2D")

    # Show cluster summary
    fraud_mask  = df["is_fraud"] == 1
    normal_mask = df["is_fraud"] == 0

    fraud_pc1_mean  = X_pca[fraud_mask, 0].mean()
    normal_pc1_mean = X_pca[normal_mask, 0].mean()
    separation      = abs(fraud_pc1_mean - normal_pc1_mean)

    print(f"\n  Cluster separation score: {separation:.3f}")
    print(f"  (Higher = fraud and normal are more distinct)")

    if separation > 1.0:
        print(f"  ✅ Good separation — model can distinguish fraud clearly")
    else:
        print(f"  ⚠️  Low separation — fraud patterns overlap with normal")

    return pca


# ─────────────────────────────────────────
# STEP 8: Save everything
# ─────────────────────────────────────────
def save_results(model, scaler, pca, metrics, anomaly_scores,
                 fraud_pred, df, base_dir, feature_names):
    print("\n  Saving model and results...")

    models_dir  = os.path.join(base_dir, "src", "models", "saved")
    results_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # Save Isolation Forest model
    model_path = os.path.join(models_dir, "isolation_forest.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Save scaler
    scaler_path = os.path.join(models_dir, "anomaly_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    # Save PCA
    pca_path = os.path.join(models_dir, "pca_model.pkl")
    with open(pca_path, "wb") as f:
        pickle.dump(pca, f)

    # Save metrics
    metrics_path = os.path.join(models_dir, "anomaly_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # Save anomaly scores alongside existing fraud scores
    scores_path = os.path.join(results_dir, "fraud_scores.csv")
    if os.path.exists(scores_path):
        existing_df = pd.read_csv(scores_path)
        # Merge anomaly scores into existing fraud_scores.csv
        anomaly_df = pd.DataFrame({
            "gstin":          df["gstin"].values,
            "anomaly_score":  anomaly_scores.round(2),
            "anomaly_flag":   fraud_pred,
        })
        merged = existing_df.merge(anomaly_df, on="gstin", how="left")
        merged.to_csv(scores_path, index=False)
        print(f"  Anomaly scores merged into: data/processed/fraud_scores.csv")
    else:
        # Create new scores file
        anomaly_df = pd.DataFrame({
            "gstin":          df["gstin"].values,
            "is_fraud":       df["is_fraud"].values,
            "fraud_type":     df["fraud_type"].values,
            "anomaly_score":  anomaly_scores.round(2),
            "anomaly_flag":   fraud_pred,
        })
        anomaly_df.to_csv(scores_path, index=False)

    print(f"  Files saved:")
    print(f"    Model   → src/models/saved/isolation_forest.pkl")
    print(f"    Scaler  → src/models/saved/anomaly_scaler.pkl")
    print(f"    PCA     → src/models/saved/pca_model.pkl")
    print(f"    Metrics → src/models/saved/anomaly_metrics.json")
    print(f"    Scores  → data/processed/fraud_scores.csv (updated)")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - ANOMALY DETECTION MODEL")
    print("  (Isolation Forest — No Labels Needed)")
    print("=" * 55)

    print("\n[1/8] Loading data...")
    df, base_dir = load_data()

    print("\n[2/8] Preparing and scaling features...")
    X, X_scaled, df, scaler, feature_names = prepare_features(df)

    print("\n[3/8] Training Isolation Forest...")
    model = train_isolation_forest(X_scaled)

    print("\n[4/8] Generating anomaly scores...")
    anomaly_scores, fraud_pred = generate_anomaly_scores(model, X_scaled)

    print("\n[5/8] Evaluating model...")
    metrics = evaluate_model(anomaly_scores, fraud_pred, df)

    print("\n[6/8] Analyzing top anomalies...")
    analyze_anomalies(X, X_scaled, anomaly_scores, df, feature_names)

    print("\n[7/8] Analyzing clusters...")
    pca = analyze_clusters(X_scaled, anomaly_scores, df)

    print("\n[8/8] Saving model and results...")
    save_results(model, scaler, pca, metrics, anomaly_scores,
                 fraud_pred, df, base_dir, feature_names)

    # ── Final summary ──
    print("\n" + "=" * 55)
    print("  ANOMALY DETECTION COMPLETE!")
    print("=" * 55)

    critical = (anomaly_scores >= 80).sum()
    high     = ((anomaly_scores >= 60) & (anomaly_scores < 80)).sum()
    medium   = ((anomaly_scores >= 40) & (anomaly_scores < 60)).sum()
    low      = (anomaly_scores < 40).sum()

    print(f"\n  Anomaly Score Distribution:")
    print(f"    🔴 CRITICAL  (≥80):  {critical:>4} GSTINs — investigate immediately")
    print(f"    🟠 HIGH      (60-79): {high:>4} GSTINs — review soon")
    print(f"    🟡 MEDIUM    (40-59): {medium:>4} GSTINs — monitor closely")
    print(f"    🟢 LOW       (<40):  {low:>4} GSTINs — appears normal")

    print(f"\n  Model Performance:")
    print(f"    Precision: {metrics['precision']*100:.2f}%")
    print(f"    Recall:    {metrics['recall']*100:.2f}%")
    print(f"    F1 Score:  {metrics['f1_score']*100:.2f}%")
    print(f"    AUC-ROC:   {metrics['auc_roc']:.4f}")

    print(f"\n  Key advantage over XGBoost:")
    print(f"    XGBoost catches known fraud patterns (supervised)")
    print(f"    Isolation Forest catches UNKNOWN fraud patterns (unsupervised)")
    print(f"    Together they cover both known and new fraud types!")

    print(f"\n  Next step: Build Graph Fraud Detector (circular trading)")
    print("=" * 55)


if __name__ == "__main__":
    main()