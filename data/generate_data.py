"""
GST Fraud Detection System
Synthetic Data Generator
Phase 2 - Step 2

This file generates 50,000 realistic GST records
with fraud patterns injected for ML training.
"""

import pandas as pd
import numpy as np
import random
import os
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("en_IN")
random.seed(42)
np.random.seed(42)

# ─────────────────────────────────────────
# CONSTANTS - Real GST state codes in India
# ─────────────────────────────────────────
STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh",
    "03": "Punjab",          "04": "Chandigarh",
    "05": "Uttarakhand",     "06": "Haryana",
    "07": "Delhi",           "08": "Rajasthan",
    "09": "Uttar Pradesh",   "10": "Bihar",
    "11": "Sikkim",          "12": "Arunachal Pradesh",
    "13": "Nagaland",        "14": "Manipur",
    "15": "Mizoram",         "16": "Tripura",
    "17": "Meghalaya",       "18": "Assam",
    "19": "West Bengal",     "20": "Jharkhand",
    "21": "Odisha",          "22": "Chhattisgarh",
    "23": "Madhya Pradesh",  "24": "Gujarat",
    "27": "Maharashtra",     "29": "Karnataka",
    "32": "Kerala",          "33": "Tamil Nadu",
    "36": "Telangana",       "37": "Andhra Pradesh",
}

INDUSTRIES = [
    "Textile", "Pharmaceuticals", "Electronics", "Steel",
    "Chemicals", "Food Processing", "Automobile", "Construction",
    "IT Services", "Trading", "Agriculture", "Jewellery",
    "Plastics", "Paper", "Cement", "Coal", "Fertilizers"
]

ENTITY_TYPES = ["P", "C", "H", "F", "B", "A", "T", "B", "L", "J", "G"]

# ─────────────────────────────────────────
# STEP 1: Generate valid GSTIN numbers
# Real format: 2-digit state + 10-char PAN + 1-digit entity + Z + checksum
# ─────────────────────────────────────────
def generate_gstin(state_code=None):
    if not state_code:
        state_code = random.choice(list(STATE_CODES.keys()))
    
    # PAN format: 5 letters + 4 digits + 1 letter
    pan_letters1 = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))
    pan_digits   = ''.join(random.choices('0123456789', k=4))
    pan_letter2  = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    pan          = pan_letters1 + pan_digits + pan_letter2
    
    entity_num   = str(random.randint(1, 9))
    checksum     = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    
    return f"{state_code}{pan}{entity_num}Z{checksum}"


# ─────────────────────────────────────────
# STEP 2: Generate a pool of companies
# ─────────────────────────────────────────
def generate_companies(n=5000):
    print(f"  Generating {n} companies...")
    companies = []
    
    # 80% legitimate, 20% will be fraud
    for i in range(n):
        state_code = random.choice(list(STATE_CODES.keys()))
        gstin      = generate_gstin(state_code)
        industry   = random.choice(INDUSTRIES)
        
        # Company age affects behavior
        years_old  = random.randint(1, 25)
        reg_date   = datetime.now() - timedelta(days=years_old * 365)
        
        # Turnover based on company size
        size_type  = random.choices(
            ["small", "medium", "large"],
            weights=[60, 30, 10]
        )[0]
        
        if size_type == "small":
            annual_turnover = random.uniform(20_00_000, 5_00_00_000)      # 20L to 5Cr
        elif size_type == "medium":
            annual_turnover = random.uniform(5_00_00_000, 100_00_00_000)  # 5Cr to 100Cr
        else:
            annual_turnover = random.uniform(100_00_00_000, 1000_00_00_000)  # 100Cr to 1000Cr
        
        # Shared address (shell company indicator)
        address_id = random.randint(1, 2000)  # some companies share addresses
        
        companies.append({
            "gstin":            gstin,
            "company_name":     fake.company(),
            "state_code":       state_code,
            "state_name":       STATE_CODES[state_code],
            "industry":         industry,
            "size_type":        size_type,
            "annual_turnover":  round(annual_turnover, 2),
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "years_old":        years_old,
            "address_id":       address_id,   # shared = shell company signal
            "is_fraud":         0              # label added later
        })
    
    return pd.DataFrame(companies)


# ─────────────────────────────────────────
# STEP 3: Generate GSTR-3B filings (monthly summary returns)
# Every registered company must file this monthly
# ─────────────────────────────────────────
def generate_gstr3b(companies_df, months=18):
    print(f"  Generating GSTR-3B filings for {len(companies_df)} companies x {months} months...")
    filings = []
    
    base_date = datetime.now() - timedelta(days=months * 30)
    
    for _, company in companies_df.iterrows():
        monthly_turnover = company["annual_turnover"] / 12
        
        for m in range(months):
            filing_date = base_date + timedelta(days=m * 30)
            due_date    = filing_date + timedelta(days=20)  # due 20th of next month
            
            # Some companies file late (compliance signal)
            delay_days  = random.choices(
                [0, random.randint(1, 10), random.randint(11, 60)],
                weights=[70, 20, 10]
            )[0]
            actual_filing_date = due_date + timedelta(days=delay_days)
            
            # Monthly variation in sales (seasonal business)
            seasonal_factor = random.uniform(0.6, 1.8)
            outward_supply  = monthly_turnover * seasonal_factor
            
            # Tax rate depends on industry (5%, 12%, 18%, 28%)
            tax_rate = random.choices([0.05, 0.12, 0.18, 0.28], weights=[15, 25, 45, 15])[0]
            
            tax_collected   = outward_supply * tax_rate
            
            # ITC (Input Tax Credit) = tax paid to suppliers
            # Normal: ITC should be 60-90% of tax collected
            normal_itc_ratio = random.uniform(0.6, 0.90)
            itc_claimed      = tax_collected * normal_itc_ratio
            
            net_tax_payable  = max(0, tax_collected - itc_claimed)
            
            # Was return filed? (some companies go missing)
            filed = random.choices([1, 0], weights=[95, 5])[0]
            
            filings.append({
                "gstin":              company["gstin"],
                "filing_period":      filing_date.strftime("%Y-%m"),
                "due_date":           due_date.strftime("%Y-%m-%d"),
                "actual_filing_date": actual_filing_date.strftime("%Y-%m-%d"),
                "delay_days":         delay_days,
                "outward_supply":     round(outward_supply, 2),
                "tax_rate":           tax_rate,
                "tax_collected":      round(tax_collected, 2),
                "itc_claimed":        round(itc_claimed, 2),
                "net_tax_payable":    round(net_tax_payable, 2),
                "filed":              filed,
            })
    
    return pd.DataFrame(filings)


# ─────────────────────────────────────────
# STEP 4: Generate B2B invoice data (GSTR-1)
# ─────────────────────────────────────────
def generate_invoices(companies_df, n_invoices=200000):
    print(f"  Generating {n_invoices} B2B invoices...")
    invoices   = []
    gstin_list = companies_df["gstin"].tolist()
    
    for _ in range(n_invoices):
        supplier = random.choice(gstin_list)
        buyer    = random.choice(gstin_list)
        
        while buyer == supplier:
            buyer = random.choice(gstin_list)
        
        invoice_date   = datetime.now() - timedelta(days=random.randint(1, 540))
        invoice_amount = random.uniform(10_000, 50_00_000)
        tax_rate       = random.choices([0.05, 0.12, 0.18, 0.28], weights=[15, 25, 45, 15])[0]
        tax_amount     = invoice_amount * tax_rate
        
        # Invoice matching (GSTR-1 vs GSTR-2A) - mismatch is fraud signal
        is_matched = random.choices([1, 0], weights=[88, 12])[0]
        
        invoices.append({
            "invoice_id":      fake.bothify(text="INV-????-########"),
            "supplier_gstin":  supplier,
            "buyer_gstin":     buyer,
            "invoice_date":    invoice_date.strftime("%Y-%m-%d"),
            "invoice_amount":  round(invoice_amount, 2),
            "tax_rate":        tax_rate,
            "tax_amount":      round(tax_amount, 2),
            "is_matched":      is_matched,   # 0 = unmatched = suspicious
        })
    
    return pd.DataFrame(invoices)


# ─────────────────────────────────────────
# STEP 5: Inject FRAUD patterns into 20% of companies
# These are the patterns your ML model will learn to detect
# ─────────────────────────────────────────
def inject_fraud_patterns(companies_df, filings_df, invoices_df):
    print("  Injecting fraud patterns...")
    
    n_companies  = len(companies_df)
    fraud_count  = int(n_companies * 0.20)  # 20% fraud rate
    fraud_indices = random.sample(range(n_companies), fraud_count)
    
    fraud_gstins = set()
    
    for idx in fraud_indices:
        gstin       = companies_df.iloc[idx]["gstin"]
        fraud_type  = random.choices(
            ["fake_itc", "circular_trading", "shell_company",
             "missing_returns", "sudden_spike"],
            weights=[30, 25, 20, 15, 10]
        )[0]
        
        fraud_gstins.add(gstin)
        companies_df.at[idx, "is_fraud"]    = 1
        companies_df.at[idx, "fraud_type"]  = fraud_type
        
        # ── Fraud Pattern 1: FAKE ITC CLAIMS ──
        # Company claims more ITC than actual purchases
        if fraud_type == "fake_itc":
            mask = filings_df["gstin"] == gstin
            # Inflate ITC by 2x to 5x normal amount
            filings_df.loc[mask, "itc_claimed"] *= random.uniform(2.0, 5.0)
            filings_df.loc[mask, "net_tax_payable"] = (
                filings_df.loc[mask, "tax_collected"] -
                filings_df.loc[mask, "itc_claimed"]
            ).clip(lower=0)
        
        # ── Fraud Pattern 2: MISSING RETURNS ──
        # Company stops filing returns suddenly
        elif fraud_type == "missing_returns":
            mask = filings_df["gstin"] == gstin
            filing_indices = filings_df[mask].index.tolist()
            # Make last 4-8 months unfiled
            n_missing = random.randint(4, 8)
            for fi in filing_indices[-n_missing:]:
                filings_df.at[fi, "filed"] = 0
        
        # ── Fraud Pattern 3: SUDDEN SPIKE ──
        # Turnover suddenly jumps 10x with no history
        elif fraud_type == "sudden_spike":
            mask           = filings_df["gstin"] == gstin
            filing_indices = filings_df[mask].index.tolist()
            # Last 3 months show huge spike
            for fi in filing_indices[-3:]:
                filings_df.at[fi, "outward_supply"] *= random.uniform(8, 20)
                filings_df.at[fi, "tax_collected"]  *= random.uniform(8, 20)
                filings_df.at[fi, "itc_claimed"]    *= random.uniform(8, 20)
        
        # ── Fraud Pattern 4: SHELL COMPANY ──
        # Very low actual activity but high ITC claims
        elif fraud_type == "shell_company":
            mask = filings_df["gstin"] == gstin
            # Near-zero outward supply but large ITC
            filings_df.loc[mask, "outward_supply"] *= 0.05
            filings_df.loc[mask, "tax_collected"]  *= 0.05
            filings_df.loc[mask, "itc_claimed"]    *= random.uniform(3.0, 8.0)
    
    # ── Fraud Pattern 5: CIRCULAR TRADING ──
    # Create rings of 3-5 companies trading with each other
    print("  Creating circular trading rings...")
    n_rings = 50
    for _ in range(n_rings):
        ring_size   = random.randint(3, 5)
        ring_gstins = random.sample(list(fraud_gstins), min(ring_size, len(fraud_gstins)))
        
        if len(ring_gstins) < 2:
            continue
        
        # Create circular invoices: A→B→C→A
        for i in range(len(ring_gstins)):
            supplier = ring_gstins[i]
            buyer    = ring_gstins[(i + 1) % len(ring_gstins)]
            amount   = random.uniform(50_00_000, 500_00_000)  # large amounts
            tax_rate = 0.18
            
            new_invoice = {
                "invoice_id":      fake.bothify(text="CIRC-????-########"),
                "supplier_gstin":  supplier,
                "buyer_gstin":     buyer,
                "invoice_date":    (datetime.now() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
                "invoice_amount":  round(amount, 2),
                "tax_rate":        tax_rate,
                "tax_amount":      round(amount * tax_rate, 2),
                "is_matched":      1,
            }
            invoices_df = pd.concat(
                [invoices_df, pd.DataFrame([new_invoice])],
                ignore_index=True
            )
    
    # Fill fraud_type for legitimate companies
    companies_df["fraud_type"] = companies_df.get("fraud_type", "none")
    companies_df["fraud_type"] = companies_df["fraud_type"].fillna("none")
    
    return companies_df, filings_df, invoices_df


# ─────────────────────────────────────────
# STEP 6: Calculate features for ML training
# These 20 features are what your XGBoost model learns from
# ─────────────────────────────────────────
def calculate_features(companies_df, filings_df, invoices_df):
    print("  Calculating ML features per GSTIN...")
    features_list = []
    
    for _, company in companies_df.iterrows():
        gstin = company["gstin"]
        
        # Get this company's filings
        comp_filings = filings_df[filings_df["gstin"] == gstin]
        comp_invoices_as_supplier = invoices_df[invoices_df["supplier_gstin"] == gstin]
        comp_invoices_as_buyer    = invoices_df[invoices_df["buyer_gstin"] == gstin]
        
        if len(comp_filings) == 0:
            continue
        
        filed_filings = comp_filings[comp_filings["filed"] == 1]
        
        # ── COMPLIANCE FEATURES ──
        filing_rate       = len(filed_filings) / len(comp_filings) if len(comp_filings) > 0 else 0
        missing_returns   = len(comp_filings) - len(filed_filings)
        avg_delay_days    = comp_filings["delay_days"].mean()
        
        # ── ITC FEATURES (most important fraud signal) ──
        avg_itc_ratio = (
            (filed_filings["itc_claimed"] / filed_filings["tax_collected"].replace(0, 1))
            .replace([np.inf, -np.inf], 0).mean()
        )
        total_itc_claimed  = filed_filings["itc_claimed"].sum()
        total_tax_paid     = filed_filings["net_tax_payable"].sum()
        
        # ── TRANSACTION FEATURES ──
        total_outward      = filed_filings["outward_supply"].sum()
        avg_monthly_sales  = filed_filings["outward_supply"].mean()
        sales_std          = filed_filings["outward_supply"].std()
        sales_cv           = sales_std / avg_monthly_sales if avg_monthly_sales > 0 else 0
        
        # Sudden spike detection
        if len(filed_filings) >= 6:
            recent_avg = filed_filings["outward_supply"].tail(3).mean()
            older_avg  = filed_filings["outward_supply"].head(6).mean()
            spike_ratio = recent_avg / older_avg if older_avg > 0 else 1
        else:
            spike_ratio = 1.0
        
        # ── INVOICE FEATURES ──
        total_invoices_issued   = len(comp_invoices_as_supplier)
        total_invoices_received = len(comp_invoices_as_buyer)
        invoice_match_rate = (
            comp_invoices_as_supplier["is_matched"].mean()
            if len(comp_invoices_as_supplier) > 0 else 1.0
        )
        
        # ── NETWORK FEATURES ──
        unique_buyers     = comp_invoices_as_supplier["buyer_gstin"].nunique()
        unique_suppliers  = comp_invoices_as_buyer["supplier_gstin"].nunique()
        
        # ── COMPANY FEATURES ──
        companies_same_address = companies_df[
            companies_df["address_id"] == company["address_id"]
        ].shape[0]
        
        features_list.append({
            "gstin":                    gstin,
            "industry":                 company["industry"],
            "state_code":               company["state_code"],
            "years_old":                company["years_old"],
            "size_type":                company["size_type"],
            "annual_turnover":          company["annual_turnover"],
            
            # Compliance features
            "filing_rate":              round(filing_rate, 4),
            "missing_returns":          missing_returns,
            "avg_delay_days":           round(avg_delay_days, 2),
            
            # ITC features (KEY fraud signals)
            "avg_itc_ratio":            round(avg_itc_ratio, 4),
            "total_itc_claimed":        round(total_itc_claimed, 2),
            "total_tax_paid":           round(total_tax_paid, 2),
            
            # Transaction features
            "total_outward_supply":     round(total_outward, 2),
            "avg_monthly_sales":        round(avg_monthly_sales, 2),
            "sales_volatility":         round(sales_cv, 4),
            "spike_ratio":              round(spike_ratio, 4),
            
            # Invoice features
            "invoices_issued":          total_invoices_issued,
            "invoices_received":        total_invoices_received,
            "invoice_match_rate":       round(invoice_match_rate, 4),
            
            # Network features
            "unique_buyers":            unique_buyers,
            "unique_suppliers":         unique_suppliers,
            "companies_same_address":   companies_same_address,
            
            # TARGET LABEL (what ML model predicts)
            "is_fraud":                 company["is_fraud"],
            "fraud_type":               company["fraud_type"],
        })
    
    return pd.DataFrame(features_list)


# ─────────────────────────────────────────
# STEP 7: Save all generated data to CSV files
# ─────────────────────────────────────────
def save_data(companies_df, filings_df, invoices_df, features_df):
    output_dir = os.path.join(os.path.dirname(__file__), "synthetic")
    os.makedirs(output_dir, exist_ok=True)
    
    paths = {
        "companies": os.path.join(output_dir, "companies.csv"),
        "filings":   os.path.join(output_dir, "gstr3b_filings.csv"),
        "invoices":  os.path.join(output_dir, "invoices.csv"),
        "features":  os.path.join(output_dir, "ml_features.csv"),
    }
    
    print("\n  Saving files...")
    companies_df.to_csv(paths["companies"], index=False)
    filings_df.to_csv(paths["filings"],     index=False)
    invoices_df.to_csv(paths["invoices"],   index=False)
    features_df.to_csv(paths["features"],   index=False)
    
    return paths


# ─────────────────────────────────────────
# MAIN - Run everything in order
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - SYNTHETIC DATA GENERATOR")
    print("=" * 55)
    
    print("\n[1/6] Generating companies...")
    companies_df = generate_companies(n=5000)
    
    print("\n[2/6] Generating GSTR-3B filings...")
    filings_df = generate_gstr3b(companies_df, months=18)
    
    print("\n[3/6] Generating B2B invoices...")
    invoices_df = generate_invoices(companies_df, n_invoices=200000)
    
    print("\n[4/6] Injecting fraud patterns...")
    companies_df, filings_df, invoices_df = inject_fraud_patterns(
        companies_df, filings_df, invoices_df
    )
    
    print("\n[5/6] Calculating ML features...")
    features_df = calculate_features(companies_df, filings_df, invoices_df)
    
    print("\n[6/6] Saving data files...")
    paths = save_data(companies_df, filings_df, invoices_df, features_df)
    
    # ── SUMMARY REPORT ──
    print("\n" + "=" * 55)
    print("  DATA GENERATION COMPLETE!")
    print("=" * 55)
    
    fraud_companies = companies_df[companies_df["is_fraud"] == 1]
    legit_companies = companies_df[companies_df["is_fraud"] == 0]
    
    print(f"\n  Companies generated:    {len(companies_df):,}")
    print(f"  Legitimate companies:   {len(legit_companies):,} ({len(legit_companies)/len(companies_df)*100:.0f}%)")
    print(f"  Fraudulent companies:   {len(fraud_companies):,} ({len(fraud_companies)/len(companies_df)*100:.0f}%)")
    print(f"\n  GSTR-3B filings:        {len(filings_df):,}")
    print(f"  B2B Invoices:           {len(invoices_df):,}")
    print(f"  ML feature rows:        {len(features_df):,}")
    
    print(f"\n  Fraud breakdown by type:")
    for ftype, count in fraud_companies["fraud_type"].value_counts().items():
        print(f"    {ftype:<20} {count:>4} companies")
    
    print(f"\n  Files saved to: data/synthetic/")
    for name, path in paths.items():
        size_kb = os.path.getsize(path) / 1024
        print(f"    {name:<12} → {os.path.basename(path)}  ({size_kb:.0f} KB)")
    
    print("\n  Next step: Run the feature engineering and ML model!")
    print("=" * 55)


if __name__ == "__main__":
    main()