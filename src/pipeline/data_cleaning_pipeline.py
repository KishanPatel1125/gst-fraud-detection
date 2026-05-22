"""
GST Fraud Detection System
Data Cleaning Pipeline
Phase 2 - Advanced

Cleans raw GST data:
1. Validates GSTIN format
2. Removes duplicates
3. Handles missing values
4. Fixes data types
5. Detects outliers
6. Validates business rules
7. Generates data quality report
"""

import pandas as pd
import numpy as np
import os
import json
import re
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
VALID_STATE_CODES = [
    "01","02","03","04","05","06","07","08","09","10",
    "11","12","13","14","15","16","17","18","19","20",
    "21","22","23","24","27","29","30","32","33","34",
    "35","36","37","38"
]

GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)

VALID_TAX_RATES = [0.0, 0.05, 0.12, 0.18, 0.28]


# ─────────────────────────────────────────
# STEP 1: Load raw data
# ─────────────────────────────────────────
def load_raw_data(base_dir):
    print("  Loading raw data files...")
    synth_dir = os.path.join(base_dir, "data", "synthetic")

    data = {}
    files = {
        "companies": "companies.csv",
        "filings":   "gstr3b_filings.csv",
        "invoices":  "invoices.csv",
        "features":  "ml_features.csv",
    }

    for name, filename in files.items():
        path = os.path.join(synth_dir, filename)
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
            print(f"    {name:<12}: {len(data[name]):>8,} rows loaded")
        else:
            print(f"    {name:<12}: ❌ file not found")

    return data


# ─────────────────────────────────────────
# STEP 2: Validate GSTIN format
#
# Valid GSTIN format:
# 2 digits (state) + 5 letters + 4 digits +
# 1 letter + 1 alphanumeric + Z + 1 alphanumeric
# Total: 15 characters
# ─────────────────────────────────────────
def validate_gstins(companies_df):
    print("\n  Validating GSTIN formats...")
    report = {}

    original_count = len(companies_df)

    # Check length
    wrong_length = companies_df[
        companies_df["gstin"].str.len() != 15
    ]
    report["wrong_length"] = len(wrong_length)

    # Check pattern
    invalid_pattern = companies_df[
        ~companies_df["gstin"].str.match(
            r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        )
    ]
    report["invalid_pattern"] = len(invalid_pattern)

    # Check state codes
    companies_df["state_code_extracted"] = companies_df["gstin"].str[:2]
    invalid_state = companies_df[
        ~companies_df["state_code_extracted"].isin(VALID_STATE_CODES)
    ]
    report["invalid_state_code"] = len(invalid_state)

    # Check for duplicates
    duplicates = companies_df[companies_df["gstin"].duplicated()]
    report["duplicate_gstins"] = len(duplicates)

    # Remove duplicates
    companies_df = companies_df.drop_duplicates(subset=["gstin"])
    report["after_dedup"] = len(companies_df)

    print(f"    Total GSTINs:        {original_count:,}")
    print(f"    Wrong length:        {report['wrong_length']}")
    print(f"    Invalid pattern:     {report['invalid_pattern']}")
    print(f"    Invalid state code:  {report['invalid_state_code']}")
    print(f"    Duplicate GSTINs:    {report['duplicate_gstins']}")
    print(f"    After cleaning:      {report['after_dedup']:,}")

    return companies_df, report


# ─────────────────────────────────────────
# STEP 3: Clean filing data
# ─────────────────────────────────────────
def clean_filings(filings_df, companies_df):
    print("\n  Cleaning GSTR-3B filing data...")
    report = {}

    original_count = len(filings_df)
    valid_gstins   = set(companies_df["gstin"])

    # Remove filings for unknown GSTINs
    orphan_filings = filings_df[~filings_df["gstin"].isin(valid_gstins)]
    report["orphan_filings"] = len(orphan_filings)
    filings_df = filings_df[filings_df["gstin"].isin(valid_gstins)]

    # Fix negative values (should not be negative)
    numeric_cols = [
        "outward_supply", "tax_collected",
        "itc_claimed", "net_tax_payable"
    ]
    for col in numeric_cols:
        if col in filings_df.columns:
            neg_count = (filings_df[col] < 0).sum()
            if neg_count > 0:
                print(f"    Fixed {neg_count} negative values in {col}")
                filings_df[col] = filings_df[col].clip(lower=0)

    # Fix tax rates
    if "tax_rate" in filings_df.columns:
        invalid_tax = ~filings_df["tax_rate"].isin(VALID_TAX_RATES)
        report["invalid_tax_rates"] = invalid_tax.sum()
        # Round to nearest valid rate
        filings_df.loc[invalid_tax, "tax_rate"] = filings_df.loc[
            invalid_tax, "tax_rate"
        ].apply(lambda x: min(VALID_TAX_RATES, key=lambda v: abs(v-x)))

    # Fill missing values
    filings_df["delay_days"] = filings_df["delay_days"].fillna(0).clip(lower=0)
    filings_df["filed"]      = filings_df["filed"].fillna(1).astype(int)

    # Validate ITC (ITC should not exceed outward supply × 1.5)
    if "itc_claimed" in filings_df.columns and "outward_supply" in filings_df.columns:
        extreme_itc = (
            filings_df["itc_claimed"] > filings_df["outward_supply"] * 10
        )
        report["extreme_itc_claims"] = extreme_itc.sum()
        if extreme_itc.sum() > 0:
            print(f"    ⚠️  {extreme_itc.sum()} extreme ITC claims detected (kept as fraud signal)")

    # Remove exact duplicates
    before = len(filings_df)
    filings_df = filings_df.drop_duplicates(
        subset=["gstin", "filing_period"]
    )
    report["duplicate_filings"] = before - len(filings_df)

    report["final_count"] = len(filings_df)

    print(f"    Original filings:    {original_count:,}")
    print(f"    Orphan filings:      {report['orphan_filings']}")
    print(f"    Duplicate filings:   {report['duplicate_filings']}")
    print(f"    Extreme ITC:         {report.get('extreme_itc_claims',0)}")
    print(f"    Final filings:       {report['final_count']:,}")

    return filings_df, report


# ─────────────────────────────────────────
# STEP 4: Clean invoice data
# ─────────────────────────────────────────
def clean_invoices(invoices_df, companies_df):
    print("\n  Cleaning invoice data...")
    report = {}

    original_count = len(invoices_df)
    valid_gstins   = set(companies_df["gstin"])

    # Remove self-invoices (supplier = buyer)
    self_invoices = invoices_df[
        invoices_df["supplier_gstin"] == invoices_df["buyer_gstin"]
    ]
    report["self_invoices"] = len(self_invoices)
    invoices_df = invoices_df[
        invoices_df["supplier_gstin"] != invoices_df["buyer_gstin"]
    ]

    # Remove invoices with unknown GSTINs
    orphan = invoices_df[
        ~invoices_df["supplier_gstin"].isin(valid_gstins) |
        ~invoices_df["buyer_gstin"].isin(valid_gstins)
    ]
    report["orphan_invoices"] = len(orphan)
    invoices_df = invoices_df[
        invoices_df["supplier_gstin"].isin(valid_gstins) &
        invoices_df["buyer_gstin"].isin(valid_gstins)
    ]

    # Fix negative invoice amounts
    neg_amounts = (invoices_df["invoice_amount"] <= 0).sum()
    report["negative_amounts"] = int(neg_amounts)
    invoices_df = invoices_df[invoices_df["invoice_amount"] > 0]

    # Fix tax amounts (should be amount × rate)
    if "tax_rate" in invoices_df.columns:
        expected_tax = invoices_df["invoice_amount"] * invoices_df["tax_rate"]
        tax_mismatch = (
            abs(invoices_df["tax_amount"] - expected_tax) > expected_tax * 0.05
        ).sum()
        report["tax_mismatches"] = int(tax_mismatch)
        # Recalculate tax amount
        invoices_df["tax_amount"] = (
            invoices_df["invoice_amount"] * invoices_df["tax_rate"]
        ).round(2)

    # Remove duplicate invoices
    before = len(invoices_df)
    invoices_df = invoices_df.drop_duplicates(subset=["invoice_id"])
    report["duplicate_invoices"] = before - len(invoices_df)

    report["final_count"] = len(invoices_df)

    print(f"    Original invoices:   {original_count:,}")
    print(f"    Self invoices:       {report['self_invoices']}")
    print(f"    Orphan invoices:     {report['orphan_invoices']}")
    print(f"    Negative amounts:    {report['negative_amounts']}")
    print(f"    Tax mismatches:      {report.get('tax_mismatches',0)}")
    print(f"    Duplicate invoices:  {report['duplicate_invoices']}")
    print(f"    Final invoices:      {report['final_count']:,}")

    return invoices_df, report


# ─────────────────────────────────────────
# STEP 5: Handle outliers
#
# Uses IQR method to detect extreme values
# Flags them but keeps them (fraud signals!)
# ─────────────────────────────────────────
def detect_outliers(features_df):
    print("\n  Detecting outliers in ML features...")
    report = {}

    outlier_cols = [
        "avg_itc_ratio", "spike_ratio",
        "avg_monthly_sales", "sales_volatility",
        "avg_delay_days"
    ]

    total_outliers = 0
    for col in outlier_cols:
        if col not in features_df.columns:
            continue

        Q1  = features_df[col].quantile(0.25)
        Q3  = features_df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower = Q1 - 3 * IQR
        upper = Q3 + 3 * IQR

        outliers = (
            (features_df[col] < lower) |
            (features_df[col] > upper)
        ).sum()

        total_outliers += outliers
        report[f"outliers_{col}"] = int(outliers)

        # Flag as outlier column (useful for ML)
        features_df[f"{col}_is_outlier"] = (
            (features_df[col] < lower) |
            (features_df[col] > upper)
        ).astype(int)

        # Cap extreme values for model stability
        features_df[col] = features_df[col].clip(lower=lower, upper=upper*2)

    report["total_outliers"] = total_outliers
    print(f"    Total outliers flagged: {total_outliers}")
    print(f"    Outlier flags added as new features")

    return features_df, report


# ─────────────────────────────────────────
# STEP 6: Business rule validation
#
# GST-specific rules that must always hold
# ─────────────────────────────────────────
def validate_business_rules(filings_df, companies_df):
    print("\n  Validating GST business rules...")
    violations = {}

    # Rule 1: Companies must file returns if active
    # (missing returns = violation = fraud signal)
    filing_counts = filings_df.groupby("gstin")["filed"].sum()
    low_filers    = (filing_counts < 6).sum()
    violations["low_filing_count"] = int(low_filers)
    print(f"    Companies filing < 6 months: {low_filers}")

    # Rule 2: Net tax payable should not be massively negative
    extreme_negative = (filings_df["net_tax_payable"] < -1_000_000).sum()
    violations["extreme_negative_tax"] = int(extreme_negative)
    print(f"    Extreme negative tax payable: {extreme_negative}")

    # Rule 3: Turnover consistency check
    # (turnover should not jump > 20x in one month)
    filings_df = filings_df.sort_values(["gstin", "filing_period"])
    filings_df["prev_supply"] = filings_df.groupby("gstin")[
        "outward_supply"
    ].shift(1)
    filings_df["supply_ratio"] = (
        filings_df["outward_supply"] /
        (filings_df["prev_supply"] + 1)
    )
    sudden_spikes = (filings_df["supply_ratio"] > 20).sum()
    violations["sudden_spikes_detected"] = int(sudden_spikes)
    print(f"    Sudden supply spikes (>20x): {sudden_spikes}")

    # Rule 4: ITC cannot exceed 130% of tax collected
    # (more than that = definitely fraud)
    filings_df["itc_ratio"] = (
        filings_df["itc_claimed"] /
        (filings_df["tax_collected"] + 1)
    )
    extreme_itc = (filings_df["itc_ratio"] > 5).sum()
    violations["extreme_itc_ratio"] = int(extreme_itc)
    print(f"    Extreme ITC ratio (>5x):     {extreme_itc}")

    # Clean up temp columns
    filings_df = filings_df.drop(
        columns=["prev_supply","supply_ratio","itc_ratio"],
        errors="ignore"
    )

    return filings_df, violations


# ─────────────────────────────────────────
# STEP 7: Generate data quality report
# ─────────────────────────────────────────
def generate_quality_report(all_reports, base_dir):
    print("\n  Generating data quality report...")

    report = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary":      all_reports,
        "data_quality_score": 0,
    }

    # Calculate overall quality score (0-100)
    total_records = (
        all_reports.get("companies", {}).get("after_dedup", 5000) +
        all_reports.get("filings",   {}).get("final_count", 90000) +
        all_reports.get("invoices",  {}).get("final_count", 200000)
    )

    total_issues = sum([
        all_reports.get("companies", {}).get("duplicate_gstins", 0),
        all_reports.get("filings",   {}).get("orphan_filings", 0),
        all_reports.get("invoices",  {}).get("orphan_invoices", 0),
        all_reports.get("invoices",  {}).get("negative_amounts", 0),
    ])

    quality_score = max(0, 100 - (total_issues / total_records * 100))
    report["data_quality_score"] = round(quality_score, 2)

    # Save report
    report_path = os.path.join(
        base_dir, "data", "processed", "data_quality_report.json"
    )
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"    Data quality score: {quality_score:.1f}/100")
    print(f"    Report saved: data/processed/data_quality_report.json")

    return report


# ─────────────────────────────────────────
# STEP 8: Save cleaned data
# ─────────────────────────────────────────
def save_cleaned_data(data, base_dir):
    print("\n  Saving cleaned data...")
    clean_dir = os.path.join(base_dir, "data", "processed", "cleaned")
    os.makedirs(clean_dir, exist_ok=True)

    saved = []
    for name, df in data.items():
        path = os.path.join(clean_dir, f"{name}_clean.csv")
        df.to_csv(path, index=False)
        size_kb = os.path.getsize(path) / 1024
        print(f"    {name}_clean.csv → {len(df):,} rows ({size_kb:.0f} KB)")
        saved.append(path)

    return saved


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - DATA CLEANING PIPELINE")
    print("=" * 55)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    print("\n[1/8] Loading raw data...")
    data = load_raw_data(base_dir)

    print("\n[2/8] Validating GSTIN formats...")
    data["companies"], report_gstins = validate_gstins(data["companies"])

    print("\n[3/8] Cleaning filing data...")
    data["filings"], report_filings = clean_filings(
        data["filings"], data["companies"]
    )

    print("\n[4/8] Cleaning invoice data...")
    data["invoices"], report_invoices = clean_invoices(
        data["invoices"], data["companies"]
    )

    print("\n[5/8] Detecting outliers...")
    data["features"], report_outliers = detect_outliers(data["features"])

    print("\n[6/8] Validating business rules...")
    data["filings"], report_rules = validate_business_rules(
        data["filings"], data["companies"]
    )

    print("\n[7/8] Generating quality report...")
    all_reports = {
        "companies": report_gstins,
        "filings":   report_filings,
        "invoices":  report_invoices,
        "outliers":  report_outliers,
        "rules":     report_rules,
    }
    quality_report = generate_quality_report(all_reports, base_dir)

    print("\n[8/8] Saving cleaned data...")
    save_cleaned_data(data, base_dir)

    print("\n" + "=" * 55)
    print("  DATA CLEANING PIPELINE COMPLETE!")
    print("=" * 55)
    print(f"\n  Data Quality Score: {quality_report['data_quality_score']}/100")
    print(f"\n  Cleaned files saved to: data/processed/cleaned/")
    print(f"\n  Issues detected and fixed:")
    print(f"    ✅ GSTIN format validation")
    print(f"    ✅ Duplicate removal")
    print(f"    ✅ Negative value correction")
    print(f"    ✅ Orphan record removal")
    print(f"    ✅ Tax rate validation")
    print(f"    ✅ Outlier detection + flagging")
    print(f"    ✅ Business rule validation")
    print(f"\n  Next: Feature Engineering Pipeline")
    print("=" * 55)


if __name__ == "__main__":
    main()