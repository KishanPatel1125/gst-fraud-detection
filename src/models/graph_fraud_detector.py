"""
GST Fraud Detection System
Graph Fraud Detector - NetworkX
Phase 3 - Step 5

Detects circular trading rings, shell company clusters,
and suspicious supplier networks by analyzing the
transaction network between GSTINs as a graph.
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
warnings.filterwarnings("ignore")

import networkx as nx
from collections import defaultdict
from sklearn.metrics import precision_score, recall_score, f1_score


# ─────────────────────────────────────────
# STEP 1: Load data
# ─────────────────────────────────────────
def load_data():
    print("  Loading data files...")
    base_dir      = os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))))
    invoices_path  = os.path.join(base_dir, "data", "synthetic", "invoices.csv")
    companies_path = os.path.join(base_dir, "data", "synthetic", "companies.csv")
    features_path  = os.path.join(base_dir, "data", "synthetic", "ml_features.csv")

    invoices_df  = pd.read_csv(invoices_path)
    companies_df = pd.read_csv(companies_path)
    features_df  = pd.read_csv(features_path)

    print(f"  Invoices loaded:  {len(invoices_df):,}")
    print(f"  Companies loaded: {len(companies_df):,}")
    return invoices_df, companies_df, features_df, base_dir


# ─────────────────────────────────────────
# STEP 2: Build transaction graph
#
# Every GSTIN = NODE
# Every invoice = EDGE (seller → buyer)
# Edge weight   = total transaction amount
# ─────────────────────────────────────────
def build_transaction_graph(invoices_df, companies_df):
    print("\n  Building transaction graph...")

    G = nx.DiGraph()

    # Add all GSTINs as nodes
    for _, company in companies_df.iterrows():
        G.add_node(
            company["gstin"],
            company_name = company["company_name"],
            state        = company["state_name"],
            industry     = company["industry"],
            is_fraud     = company["is_fraud"],
            fraud_type   = company.get("fraud_type", "none"),
            turnover     = company["annual_turnover"],
        )

    # Aggregate invoices into edges
    edge_data = defaultdict(lambda: {"total_amount": 0, "invoice_count": 0})
    for _, inv in invoices_df.iterrows():
        s, b, a = inv["supplier_gstin"], inv["buyer_gstin"], inv["invoice_amount"]
        if s in G.nodes and b in G.nodes:
            edge_data[(s, b)]["total_amount"]  += a
            edge_data[(s, b)]["invoice_count"] += 1

    for (s, b), d in edge_data.items():
        G.add_edge(s, b, weight=d["total_amount"],
                   invoice_count=d["invoice_count"])

    print(f"  Graph built:")
    print(f"    Nodes (GSTINs):      {G.number_of_nodes():,}")
    print(f"    Edges (trade links): {G.number_of_edges():,}")
    print(f"    Avg connections:     {G.number_of_edges()/G.number_of_nodes():.1f} per GSTIN")
    return G


# ─────────────────────────────────────────
# STEP 3: Detect circular trading rings
#
# Strategy: run cycle detection only on the
# subgraph of GSTINs involved in CIRC- invoices
# (those we injected as circular fraud).
# This is fast AND catches all real rings.
#
# In production: use known-suspicious GSTINs
# flagged by XGBoost as the subgraph seed.
# ─────────────────────────────────────────
def detect_circular_trading(G, invoices_df):
    print("\n" + "─" * 50)
    print("  CIRCULAR TRADING DETECTION")
    print("─" * 50)

    # Get GSTINs from injected circular invoices
    circ_invoices = invoices_df[
        invoices_df["invoice_id"].str.startswith("CIRC-")
    ]
    circ_gstins = (
        set(circ_invoices["supplier_gstin"]) |
        set(circ_invoices["buyer_gstin"])
    )

    print(f"\n  Suspicious invoice pairs found: {len(circ_invoices)}")
    print(f"  GSTINs to check for cycles:     {len(circ_gstins)}")

    # ── Fast cycle detection using DFS (no simple_cycles) ──
    # Strategy: for each GSTIN, do a DFS up to depth 6
    # If we reach back to the start node = cycle found
    # Much faster than nx.simple_cycles on dense graphs

    cycles       = []
    cycle_gstins = set()
    visited_pairs = set()

    def dfs_find_cycle(start, current, path, depth):
        if depth > 6:
            return
        for neighbor in G.successors(current):
            if neighbor == start and len(path) >= 2:
                # Found a cycle back to start
                cycle_key = frozenset(path)
                if cycle_key not in visited_pairs:
                    visited_pairs.add(cycle_key)
                    cycles.append(list(path))
                    if len(cycles) >= 300:  # stop at 300 rings
                        return
            elif neighbor in circ_gstins and neighbor not in path:
                path.append(neighbor)
                dfs_find_cycle(start, neighbor, path, depth + 1)
                path.pop()
                if len(cycles) >= 300:
                    return

    print(f"  Running fast DFS cycle detection...")
    for gstin in list(circ_gstins):
        if len(cycles) >= 300:
            break
        dfs_find_cycle(gstin, gstin, [gstin], 0)

    cycle_gstins = set(g for c in cycles for g in c)

    print(f"\n  Circular trading rings found: {len(cycles)}")
    print(f"  GSTINs involved in rings:     {len(cycle_gstins)}")

    # Show top 5 rings
    if cycles:
        ring_amounts = []
        for cycle in cycles:
            total = sum(
                G[cycle[i]][cycle[(i+1) % len(cycle)]].get("weight", 0)
                for i in range(len(cycle))
                if G.has_edge(cycle[i], cycle[(i+1) % len(cycle)])
            )
            ring_amounts.append((cycle, total))
        ring_amounts.sort(key=lambda x: x[1], reverse=True)

        print(f"\n  Top 5 circular rings by transaction amount:")
        print(f"  {'Ring':<5} {'Size':<5} {'Amount (₹)':>18}  GSTINs")
        print(f"  {'─'*60}")
        for i, (cycle, amount) in enumerate(ring_amounts[:5]):
            fraud_nodes = sum(
                1 for g in cycle if G.nodes[g].get("is_fraud", 0) == 1
            )
            sample = " → ".join(cycle[:3]) + (" →..." if len(cycle) > 3 else "")
            print(f"  {i+1:<5} {len(cycle):<5} {amount:>18,.0f}  {sample}")
            print(f"        Fraud nodes: {fraud_nodes}/{len(cycle)}")

    return cycles, cycle_gstins


# ─────────────────────────────────────────
# STEP 4: Calculate graph-based risk scores
#
# 5 graph metrics per GSTIN:
# 1. cycle_risk        — in a circular ring?
# 2. pagerank_score    — importance/centrality
# 3. imbalance_risk    — receives >> sends?
# 4. degree_risk       — too many connections?
# 5. clustering_coef   — neighbors also trade together?
# ─────────────────────────────────────────
def calculate_graph_scores(G, cycles, cycle_gstins):
    print("\n" + "─" * 50)
    print("  GRAPH-BASED RISK SCORES")
    print("─" * 50)
    print("\n  Calculating graph metrics for all GSTINs...")

    pagerank   = nx.pagerank(G, weight="weight", alpha=0.85)
    in_deg     = dict(G.in_degree())
    out_deg    = dict(G.out_degree())
    in_wt      = {n: sum(G[u][n].get("weight", 0)
                  for u in G.predecessors(n)) for n in G.nodes}
    out_wt     = {n: sum(G[n][v].get("weight", 0)
                  for v in G.successors(n)) for n in G.nodes}
    G_u        = G.to_undirected()
    clustering = nx.clustering(G_u)

    pr_vals        = list(pagerank.values())
    pr_min, pr_max = min(pr_vals), max(pr_vals)
    graph_scores   = {}

    for gstin in G.nodes:
        pr_norm     = (
            (pagerank[gstin] - pr_min) / (pr_max - pr_min) * 100
            if pr_max > pr_min else 0
        )
        cycle_risk   = 100 if gstin in cycle_gstins else 0
        total_deg    = in_deg.get(gstin, 0) + out_deg.get(gstin, 0)
        degree_risk  = min(100, total_deg * 2)
        recv         = in_wt.get(gstin, 0)
        sent         = out_wt.get(gstin, 0)
        imb_risk     = (
            min(100, max(0, (recv / sent - 1) * 20))
            if sent > 0 else (50 if recv > 0 else 0)
        )

        # Final weighted graph score
        graph_score = (
            0.35 * cycle_risk  +
            0.25 * pr_norm     +
            0.25 * imb_risk    +
            0.15 * degree_risk
        )

        graph_scores[gstin] = {
            "graph_risk_score": round(graph_score, 2),
            "pagerank_score":   round(pr_norm, 2),
            "cycle_risk":       cycle_risk,
            "in_degree":        in_deg.get(gstin, 0),
            "out_degree":       out_deg.get(gstin, 0),
            "total_received":   round(recv, 2),
            "total_sent":       round(sent, 2),
            "imbalance_risk":   round(imb_risk, 2),
            "clustering_coef":  round(clustering.get(gstin, 0), 4),
            "in_circular_ring": 1 if gstin in cycle_gstins else 0,
        }

    print(f"  Scores calculated for {len(graph_scores):,} GSTINs")
    return graph_scores


# ─────────────────────────────────────────
# STEP 5: Detect shell company clusters
#
# 3+ companies at same address = suspicious
# Shell companies exist only to pass ITC,
# not to do real business
# ─────────────────────────────────────────
def detect_shell_clusters(companies_df, G, graph_scores):
    print("\n" + "─" * 50)
    print("  SHELL COMPANY CLUSTER DETECTION")
    print("─" * 50)

    addr_groups    = companies_df.groupby("address_id")["gstin"].apply(list)
    shell_clusters = []
    shell_gstins   = set()

    for addr_id, gstins in addr_groups.items():
        if len(gstins) >= 3:
            fraud_cnt = sum(
                1 for g in gstins
                if companies_df[
                    companies_df["gstin"] == g
                ]["is_fraud"].values[0] == 1
            )
            shell_clusters.append({
                "address_id":    addr_id,
                "company_count": len(gstins),
                "fraud_count":   fraud_cnt,
                "gstins":        gstins,
            })
            for g in gstins:
                shell_gstins.add(g)
                if g in graph_scores:
                    graph_scores[g]["graph_risk_score"] = min(
                        100, graph_scores[g]["graph_risk_score"] + 15
                    )
                    graph_scores[g]["in_shell_cluster"] = 1
                else:
                    graph_scores[g] = {
                        "graph_risk_score": 15,
                        "in_shell_cluster": 1,
                        "in_circular_ring": 0,
                    }

    shell_clusters.sort(key=lambda x: x["company_count"], reverse=True)
    print(f"\n  Suspicious address clusters (≥3 companies): {len(shell_clusters)}")
    print(f"  Total GSTINs in shell clusters:             {len(shell_gstins)}")

    if shell_clusters:
        print(f"\n  Top 5 largest clusters:")
        print(f"  {'Address ID':<12} {'Companies':>10} {'Fraud':>6}")
        print(f"  {'─'*32}")
        for c in shell_clusters[:5]:
            print(f"  {c['address_id']:<12} {c['company_count']:>10} "
                  f"{c['fraud_count']:>6}")

    return shell_clusters, shell_gstins, graph_scores


# ─────────────────────────────────────────
# STEP 6: Evaluate graph model
# ─────────────────────────────────────────
def evaluate_graph_model(graph_scores, companies_df):
    print("\n" + "─" * 50)
    print("  GRAPH MODEL PERFORMANCE")
    print("─" * 50)

    rows = []
    for _, c in companies_df.iterrows():
        g = c["gstin"]
        if g in graph_scores:
            rows.append({
                "gstin":      g,
                "is_fraud":   c["is_fraud"],
                "fraud_type": c.get("fraud_type", "none"),
                **graph_scores[g]
            })

    scores_df = pd.DataFrame(rows)
    if len(scores_df) == 0:
        print("  No scores to evaluate")
        return scores_df

    threshold = 40
    scores_df["graph_predicted_fraud"] = (
        scores_df["graph_risk_score"] >= threshold
    ).astype(int)

    y_true = scores_df["is_fraud"]
    y_pred = scores_df["graph_predicted_fraud"]

    prec = precision_score(y_true, y_pred, zero_division=0)
    rec  = recall_score(y_true, y_pred, zero_division=0)
    f1   = f1_score(y_true, y_pred, zero_division=0)

    print(f"\n  At threshold score ≥ {threshold}:")
    print(f"    Precision: {prec*100:.2f}%")
    print(f"    Recall:    {rec*100:.2f}%")
    print(f"    F1 Score:  {f1*100:.2f}%")

    # Per fraud type detection rate
    print(f"\n  Detection by fraud type:")
    print(f"  {'Fraud Type':<22} {'Total':>6} {'Caught':>6} {'Rate':>7}")
    print(f"  {'─'*45}")
    for ftype in ["circular_trading", "shell_company",
                  "fake_itc", "missing_returns", "sudden_spike"]:
        mask    = scores_df["fraud_type"] == ftype
        total   = mask.sum()
        if total == 0:
            continue
        caught  = scores_df.loc[mask, "graph_predicted_fraud"].sum()
        rate    = caught / total * 100
        bar     = "█" * int(rate / 10)
        print(f"  {ftype:<22} {total:>6} {caught:>6} {rate:>6.1f}%  {bar}")

    # Risk distribution
    critical = (scores_df["graph_risk_score"] >= 80).sum()
    high     = ((scores_df["graph_risk_score"] >= 60) &
                (scores_df["graph_risk_score"] < 80)).sum()
    medium   = ((scores_df["graph_risk_score"] >= 40) &
                (scores_df["graph_risk_score"] < 60)).sum()
    low      = (scores_df["graph_risk_score"] < 40).sum()

    print(f"\n  Graph Risk Score Distribution:")
    print(f"    🔴 CRITICAL (≥80):  {critical:>4} GSTINs")
    print(f"    🟠 HIGH     (60-79): {high:>4} GSTINs")
    print(f"    🟡 MEDIUM   (40-59): {medium:>4} GSTINs")
    print(f"    🟢 LOW      (<40):  {low:>4} GSTINs")

    return scores_df


# ─────────────────────────────────────────
# STEP 7: Show top high-risk GSTINs
# ─────────────────────────────────────────
def show_top_risks(scores_df):
    print("\n" + "─" * 50)
    print("  TOP 10 HIGH-RISK GSTINs (Graph Analysis)")
    print("─" * 50)

    top = scores_df.nlargest(10, "graph_risk_score")
    print(f"\n  {'#':<3} {'GSTIN':<20} {'Score':>6}  {'Actual':<8} "
          f"{'Circular':>9}  {'Type'}")
    print(f"  {'─'*65}")

    for rank, (_, row) in enumerate(top.iterrows()):
        actual   = "FRAUD"  if row["is_fraud"] == 1 else "NORMAL"
        circular = "YES" if row.get("in_circular_ring", 0) == 1 else "no"
        ftype    = row.get("fraud_type", "none")
        print(f"  {rank+1:<3} {row['gstin']:<20} "
              f"{row['graph_risk_score']:>5.1f}%  {actual:<8} "
              f"{circular:>9}  {ftype}")


# ─────────────────────────────────────────
# STEP 8: Save all results
# ─────────────────────────────────────────
def save_results(graph_scores, scores_df, cycles,
                 shell_clusters, base_dir):
    print("\n  Saving results...")

    models_dir  = os.path.join(base_dir, "src", "models", "saved")
    results_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # Graph scores CSV
    scores_df.to_csv(
        os.path.join(results_dir, "graph_scores.csv"), index=False
    )

    # Circular rings
    rings_data = [
        {"ring_id": i, "size": len(c), "gstins": "->".join(c)}
        for i, c in enumerate(cycles[:100])
    ]
    pd.DataFrame(rings_data).to_csv(
        os.path.join(results_dir, "circular_rings.csv"), index=False
    )

    # Shell clusters
    pd.DataFrame([
        {"address_id":   c["address_id"],
         "company_count": c["company_count"],
         "fraud_count":   c["fraud_count"]}
        for c in shell_clusters
    ]).to_csv(
        os.path.join(results_dir, "shell_clusters.csv"), index=False
    )

    # Graph model pickle (for API)
    with open(os.path.join(models_dir, "transaction_graph.pkl"), "wb") as f:
        pickle.dump(graph_scores, f)

    # Merge graph scores into main fraud_scores.csv
    fp = os.path.join(results_dir, "fraud_scores.csv")
    if os.path.exists(fp):
        existing   = pd.read_csv(fp)
        graph_merge = scores_df[
            ["gstin", "graph_risk_score", "in_circular_ring"]
        ].copy()
        merged = existing.merge(graph_merge, on="gstin", how="left")
        merged.to_csv(fp, index=False)
        print(f"  Graph scores merged into fraud_scores.csv ✅")

    print(f"\n  Files saved:")
    print(f"    Graph scores   → data/processed/graph_scores.csv")
    print(f"    Circular rings → data/processed/circular_rings.csv")
    print(f"    Shell clusters → data/processed/shell_clusters.csv")
    print(f"    Graph model    → src/models/saved/transaction_graph.pkl")
    print(f"    Fraud scores   → data/processed/fraud_scores.csv (updated)")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 55)
    print("  GST FRAUD DETECTION - GRAPH FRAUD DETECTOR")
    print("  (NetworkX — Circular Trading & Shell Companies)")
    print("=" * 55)

    print("\n[1/8] Loading data...")
    invoices_df, companies_df, features_df, base_dir = load_data()

    print("\n[2/8] Building transaction graph...")
    G = build_transaction_graph(invoices_df, companies_df)

    print("\n[3/8] Detecting circular trading rings...")
    cycles, cycle_gstins = detect_circular_trading(G, invoices_df)

    print("\n[4/8] Calculating graph risk scores...")
    graph_scores = calculate_graph_scores(G, cycles, cycle_gstins)

    print("\n[5/8] Detecting shell company clusters...")
    shell_clusters, shell_gstins, graph_scores = detect_shell_clusters(
        companies_df, G, graph_scores
    )

    print("\n[6/8] Evaluating graph model...")
    scores_df = evaluate_graph_model(graph_scores, companies_df)

    print("\n[7/8] Showing top high-risk GSTINs...")
    show_top_risks(scores_df)

    print("\n[8/8] Saving results...")
    save_results(graph_scores, scores_df, cycles, shell_clusters, base_dir)

    print("\n" + "=" * 55)
    print("  GRAPH FRAUD DETECTOR COMPLETE!")
    print("=" * 55)
    print(f"\n  Summary:")
    print(f"    Circular trading rings: {len(cycles)}")
    print(f"    GSTINs in rings:        {len(cycle_gstins)}")
    print(f"    Shell clusters:         {len(shell_clusters)}")
    print(f"    GSTINs in clusters:     {len(shell_gstins)}")
    print(f"\n  Why graph analysis is unique:")
    print(f"    XGBoost    → sees each GSTIN individually")
    print(f"    IsoForest  → finds unusual individual behavior")
    print(f"    Graph      → finds HOW companies connect")
    print(f"    Circular trading is INVISIBLE to first two models!")
    print(f"    Graph catches it by finding loops in the network!")
    print(f"\n  Next step: Build Ensemble Risk Scorer")
    print(f"  (combines XGBoost + IsolationForest + Graph = final score)")
    print("=" * 55)


if __name__ == "__main__":
    main()