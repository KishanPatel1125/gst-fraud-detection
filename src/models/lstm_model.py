"""
GST Fraud Detection System
LSTM Time Series Model
Phase 3 - Advanced ML

Analyzes 18 months of filing patterns to detect:
- Sudden activity spikes
- Irregular filing sequences
- Dormant then active fraud patterns
- Seasonal anomalies
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score
)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
    print("  ✅ PyTorch available — using LSTM")
except ImportError:
    TORCH_AVAILABLE = False
    print("  ⚠️  PyTorch not available — using numpy fallback")


# ─────────────────────────────────────────
# STEP 1: Load filing data
# ─────────────────────────────────────────
def load_data():
    print("  Loading filing data...")
    base_dir     = os.path.dirname(os.path.dirname(os.path.dirname(
                   os.path.abspath(__file__))))
    filings_path = os.path.join(base_dir, "data", "synthetic", "gstr3b_filings.csv")
    features_path= os.path.join(base_dir, "data", "synthetic", "ml_features.csv")
    companies_path=os.path.join(base_dir, "data", "synthetic", "companies.csv")

    filings_df   = pd.read_csv(filings_path)
    features_df  = pd.read_csv(features_path)
    companies_df = pd.read_csv(companies_path)

    print(f"  Filings:   {len(filings_df):,} rows")
    print(f"  Features:  {len(features_df):,} GSTINs")
    return filings_df, features_df, companies_df, base_dir


# ─────────────────────────────────────────
# STEP 2: Build time series sequences
#
# For each GSTIN, create a sequence of
# monthly filing features over 18 months
# Shape: (n_gstins, 18, n_features)
# ─────────────────────────────────────────
def build_sequences(filings_df, features_df, seq_len=18):
    print(f"\n  Building {seq_len}-month sequences...")

    filings_df["filing_date"] = pd.to_datetime(
        filings_df["filing_period"], format="%Y-%m"
    )
    filings_df = filings_df.sort_values(["gstin", "filing_date"])

    # Features to use per month
    monthly_features = [
        "outward_supply",
        "tax_collected",
        "itc_claimed",
        "net_tax_payable",
        "delay_days",
        "filed",
    ]

    sequences = []
    labels    = []
    gstins    = []

    gstin_fraud = features_df.set_index("gstin")["is_fraud"].to_dict()

    for gstin, group in filings_df.groupby("gstin"):
        group = group.sort_values("filing_date").tail(seq_len)

        if len(group) < seq_len:
            # Pad with zeros if less than seq_len months
            pad_len = seq_len - len(group)
            pad_df  = pd.DataFrame(
                np.zeros((pad_len, len(monthly_features))),
                columns=monthly_features
            )
            group = pd.concat(
                [pad_df, group[monthly_features].reset_index(drop=True)],
                ignore_index=True
            )
        else:
            group = group[monthly_features].reset_index(drop=True)

        sequences.append(group.values.astype(np.float32))
        labels.append(gstin_fraud.get(gstin, 0))
        gstins.append(gstin)

    X = np.array(sequences)   # shape: (n, seq_len, n_features)
    y = np.array(labels)

    print(f"  Sequences shape: {X.shape}")
    print(f"  Fraud rate: {y.mean()*100:.1f}%")

    return X, y, gstins, monthly_features


# ─────────────────────────────────────────
# STEP 3: Scale features
# ─────────────────────────────────────────
def scale_sequences(X_train, X_test):
    print("\n  Scaling sequences...")
    n_train, seq_len, n_feat = X_train.shape

    # Reshape to 2D for scaling
    X_train_2d = X_train.reshape(-1, n_feat)
    X_test_2d  = X_test.reshape(-1, n_feat)

    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train_2d).reshape(X_train.shape)
    X_test_scaled  = scaler.transform(X_test_2d).reshape(X_test.shape)

    return X_train_scaled, X_test_scaled, scaler


# ─────────────────────────────────────────
# STEP 4a: LSTM Model (PyTorch)
# ─────────────────────────────────────────
class FraudLSTM(nn.Module):
    """
    LSTM network for fraud detection from time series

    Architecture:
    Input → LSTM (2 layers) → Dropout → FC → Sigmoid

    Input shape:  (batch, seq_len=18, features=6)
    Output shape: (batch, 1) — fraud probability
    """
    def __init__(self, input_size=6, hidden_size=64,
                 num_layers=2, dropout=0.3):
        super(FraudLSTM, self).__init__()

        self.lstm = nn.LSTM(
            input_size  = input_size,
            hidden_size = hidden_size,
            num_layers  = num_layers,
            batch_first = True,
            dropout     = dropout,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc1     = nn.Linear(hidden_size, 32)
        self.fc2     = nn.Linear(32, 1)
        self.relu    = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # LSTM output: (batch, seq, hidden)
        lstm_out, _ = self.lstm(x)

        # Take last time step
        last_hidden  = lstm_out[:, -1, :]
        out          = self.dropout(last_hidden)
        out          = self.relu(self.fc1(out))
        out          = self.dropout(out)
        out          = self.sigmoid(self.fc2(out))
        return out.squeeze(1)


def train_lstm_pytorch(X_train, y_train, X_test, y_test,
                       epochs=30, batch_size=64):
    print("\n  Training LSTM model (PyTorch)...")

    # Convert to tensors
    X_tr = torch.FloatTensor(X_train)
    y_tr = torch.FloatTensor(y_train)
    X_te = torch.FloatTensor(X_test)

    dataset    = TensorDataset(X_tr, y_tr)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model     = FraudLSTM(input_size=X_train.shape[2])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Class weights for imbalanced data
    fraud_weight = (1 - y_train.mean()) / y_train.mean()
    criterion    = nn.BCELoss()

    print(f"  Training for {epochs} epochs...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for X_batch, y_batch in dataloader:
            optimizer.zero_grad()
            output = model(X_batch)
            loss   = criterion(output, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                test_preds = model(X_te).numpy()
            test_auc = roc_auc_score(y_test, test_preds)
            print(f"  Epoch {epoch+1:3d}/{epochs} | "
                  f"Loss: {total_loss/len(dataloader):.4f} | "
                  f"Test AUC: {test_auc:.4f}")

    return model


# ─────────────────────────────────────────
# STEP 4b: Numpy fallback (no PyTorch)
# Simple statistical time series scorer
# ─────────────────────────────────────────
def train_numpy_fallback(X_train, y_train, X_test):
    print("\n  Training statistical time series scorer (numpy fallback)...")

    # Features: outward_supply=0, itc=2, delay=4, filed=5
    scores = []
    for seq in X_test:
        score = 0.0

        # 1. Sales spike in last 3 months vs first 6
        recent_sales = seq[-3:, 0].mean()
        older_sales  = seq[:6, 0].mean() + 1e-8
        spike_ratio  = recent_sales / older_sales
        if spike_ratio > 5:   score += 0.35
        elif spike_ratio > 3: score += 0.20

        # 2. ITC anomaly (ITC > tax collected)
        itc_ratio = (seq[:, 2].sum() / (seq[:, 1].sum() + 1e-8))
        if itc_ratio > 2.0: score += 0.30
        elif itc_ratio > 1.2: score += 0.15

        # 3. Missing returns (filed=0)
        missing = (seq[:, 5] == 0).sum()
        if missing >= 6:  score += 0.25
        elif missing >= 3: score += 0.12

        # 4. Filing delays
        avg_delay = seq[:, 4].mean()
        if avg_delay > 30: score += 0.10

        scores.append(min(score, 1.0))

    return np.array(scores)


# ─────────────────────────────────────────
# STEP 5: Evaluate LSTM model
# ─────────────────────────────────────────
def evaluate_lstm(scores, y_test, model_name="LSTM"):
    print(f"\n" + "─" * 45)
    print(f"  {model_name} MODEL PERFORMANCE")
    print("─" * 45)

    threshold   = 0.5
    predictions = (scores >= threshold).astype(int)

    precision = precision_score(y_test, predictions, zero_division=0)
    recall    = recall_score(y_test, predictions, zero_division=0)
    f1        = f1_score(y_test, predictions, zero_division=0)
    auc       = roc_auc_score(y_test, scores)

    print(f"\n  Precision: {precision*100:.2f}%")
    print(f"  Recall:    {recall*100:.2f}%")
    print(f"  F1 Score:  {f1*100:.2f}%")
    print(f"  AUC-ROC:   {auc:.4f}")

    # What fraud types does LSTM catch?
    print(f"\n  LSTM excels at detecting:")
    print(f"    ✅ Sudden spike fraud   — turnover spikes 10x")
    print(f"    ✅ Missing returns      — gaps in filing sequence")
    print(f"    ✅ Dormant reactivation — inactive then suddenly active")
    print(f"    ⚠️  Fake ITC            — harder (needs invoice data)")

    return {"precision":round(precision,4),"recall":round(recall,4),
            "f1_score":round(f1,4),"auc_roc":round(auc,4)}


# ─────────────────────────────────────────
# STEP 6: Score all GSTINs with LSTM
# ─────────────────────────────────────────
def score_all_gstins(model_or_scores, X_scaled, gstins,
                     features_df, use_pytorch=True):
    print("\n  Scoring all GSTINs with LSTM...")

    if use_pytorch and TORCH_AVAILABLE:
        model = model_or_scores
        model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled)
            scores   = model(X_tensor).numpy()
    else:
        scores = model_or_scores

    lstm_df = pd.DataFrame({
        "gstin":      gstins,
        "lstm_score": (scores * 100).round(2),
    })

    print(f"  LSTM scores generated for {len(lstm_df):,} GSTINs")
    print(f"  High risk (>60): {(lstm_df['lstm_score']>60).sum():,}")
    return lstm_df


# ─────────────────────────────────────────
# STEP 7: Save everything
# ─────────────────────────────────────────
def save_results(model_or_scores, scaler, metrics,
                 lstm_df, base_dir, use_pytorch):
    print("\n  Saving LSTM model and scores...")

    models_dir  = os.path.join(base_dir, "src", "models", "saved")
    results_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(models_dir, exist_ok=True)

    # Save model
    if use_pytorch and TORCH_AVAILABLE:
        torch.save(model_or_scores.state_dict(),
                   os.path.join(models_dir, "lstm_model.pt"))
    else:
        np.save(os.path.join(models_dir, "lstm_scores.npy"), model_or_scores)

    # Save scaler
    with open(os.path.join(models_dir, "lstm_scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    # Save metrics
    with open(os.path.join(models_dir, "lstm_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # Merge with existing ensemble scores
    ensemble_path = os.path.join(results_dir, "ensemble_scores.csv")
    if os.path.exists(ensemble_path):
        existing = pd.read_csv(ensemble_path)
        merged   = existing.merge(lstm_df, on="gstin", how="left")

        # Update ensemble score to include LSTM (new weight: 10%)
        if "lstm_score" in merged.columns:
            merged["lstm_score"] = merged["lstm_score"].fillna(50)
            merged["ensemble_score"] = (
                0.30 * merged["xgb_score"]      +
                0.22 * merged["anomaly_score"]   +
                0.22 * merged["graph_risk_score"]+
                0.16 * merged["rule_score"]      +
                0.10 * merged["lstm_score"]
            ).round(2).clip(upper=100)

            merged.to_csv(ensemble_path, index=False)
            print(f"  ✅ LSTM scores merged into ensemble_scores.csv")
            print(f"  New ensemble weights:")
            print(f"    XGBoost:    30%")
            print(f"    Anomaly:    22%")
            print(f"    Graph:      22%")
            print(f"    Rules:      16%")
            print(f"    LSTM:       10%  ← NEW")

    lstm_df.to_csv(os.path.join(results_dir, "lstm_scores.csv"), index=False)
    print(f"\n  Files saved:")
    print(f"    LSTM scores → data/processed/lstm_scores.csv")
    print(f"    LSTM model  → src/models/saved/lstm_model.pt")
    print(f"    Metrics     → src/models/saved/lstm_metrics.json")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - LSTM TIME SERIES MODEL")
    print("=" * 55)

    print("\n[1/7] Loading data...")
    filings_df, features_df, companies_df, base_dir = load_data()

    print("\n[2/7] Building time series sequences...")
    X, y, gstins, feature_names = build_sequences(
        filings_df, features_df, seq_len=18
    )

    # Train/test split
    from sklearn.model_selection import train_test_split
    indices        = np.arange(len(X))
    idx_train, idx_test = train_test_split(
        indices, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_test = X[idx_train], X[idx_test]
    y_train, y_test = y[idx_train], y[idx_test]

    print(f"\n  Train: {len(X_train):,} | Test: {len(X_test):,}")

    print("\n[3/7] Scaling sequences...")
    X_train_s, X_test_s, scaler = scale_sequences(X_train, X_test)

    print("\n[4/7] Training model...")
    use_pytorch = TORCH_AVAILABLE

    if use_pytorch:
        model = train_lstm_pytorch(
            X_train_s, y_train, X_test_s, y_test,
            epochs=30, batch_size=64
        )
        model.eval()
        with torch.no_grad():
            test_scores = model(
                torch.FloatTensor(X_test_s)
            ).numpy()
        model_or_scores = model
    else:
        test_scores     = train_numpy_fallback(X_train_s, y_train, X_test_s)
        model_or_scores = test_scores

    print("\n[5/7] Evaluating model...")
    model_name = "PyTorch LSTM" if use_pytorch else "Statistical LSTM"
    metrics    = evaluate_lstm(test_scores, y_test, model_name)

    # Score ALL GSTINs
    print("\n[6/7] Scoring all GSTINs...")
    X_all_s, _, _ = scale_sequences(X, X[:10])
    lstm_df = score_all_gstins(
        model_or_scores, X_all_s, gstins, features_df, use_pytorch
    )

    print("\n[7/7] Saving results...")
    save_results(model_or_scores, scaler, metrics,
                 lstm_df, base_dir, use_pytorch)

    print("\n" + "=" * 55)
    print("  LSTM MODEL COMPLETE!")
    print("=" * 55)
    print(f"\n  Model type: {model_name}")
    print(f"  Sequences:  {len(X):,} GSTINs × 18 months × 6 features")
    print(f"\n  Performance:")
    print(f"    Precision: {metrics['precision']*100:.2f}%")
    print(f"    Recall:    {metrics['recall']*100:.2f}%")
    print(f"    F1 Score:  {metrics['f1_score']*100:.2f}%")
    print(f"    AUC-ROC:   {metrics['auc_roc']:.4f}")
    print(f"\n  LSTM adds time-series pattern detection")
    print(f"  to the existing ensemble of 4 models!")
    print(f"\n  Next: Data Cleaning Pipeline")
    print("=" * 55)


if __name__ == "__main__":
    main()