"""
Phase 4-5 — KPI Calculations, Benchmarking, Scenario Modelling
Loads complaints_clean.csv, calculates all required KPIs, outputs Tableau-ready CSVs.
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT    = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
PROC    = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(PROC / "complaints_clean.csv")
print(f"Loaded {len(df)} rows")

PERIODS_ORDERED = ["2024H1", "2024H2", "2025H1", "2025H2"]
BANKING_PRODUCTS = ["Banking and credit cards", "Home finance"]

# ── KPI 1: Complaint volumes ───────────────────────────────────────────────────
# By firm
vol_firm = (df.groupby(["reporting_period","firm_name"])["complaints_opened"]
              .sum().reset_index(name="total_complaints"))
vol_firm["period_order"] = vol_firm["reporting_period"].map(
    {p: i for i, p in enumerate(PERIODS_ORDERED)})

# By product
vol_product = (df.groupby(["reporting_period","product_group"])["complaints_opened"]
                 .sum().reset_index(name="total_complaints"))

# By period (market total)
vol_period = (df.groupby("reporting_period")["complaints_opened"]
                .sum().reset_index(name="market_complaints"))

# Firm share of complaints per period
vol_firm = vol_firm.merge(vol_period, on="reporting_period")
vol_firm["complaint_share_pct"] = (
    vol_firm["total_complaints"] / vol_firm["market_complaints"] * 100).round(2)
vol_firm = vol_firm.drop(columns="market_complaints")

# Product share per period
vol_product = vol_product.merge(vol_period, on="reporting_period")
vol_product["complaint_share_pct"] = (
    vol_product["total_complaints"] / vol_product["market_complaints"] * 100).round(2)
vol_product = vol_product.drop(columns="market_complaints")

# ── KPI 2: Size-adjusted complaint rate ───────────────────────────────────────
# Denominator = Context - Provision (number of relevant accounts/policies in thousands)
# Rate = complaints_opened / denominator (= complaints per 1,000 relevant accounts)
# Only compute where denominator > 0
df_rate = df[df["denominator"].notna() & (df["denominator"] > 0)].copy()
df_rate["complaint_rate_per_1k"] = (
    df_rate["complaints_opened"] / df_rate["denominator"]).round(4)

complaint_rate = df_rate[["reporting_period","firm_name","product_group",
                           "complaints_opened","denominator","complaint_rate_per_1k"]].copy()
complaint_rate["denominator_unit"] = "thousands of relevant accounts/policies (FCA Context - Provision)"

# ── KPI 3: Closure performance ────────────────────────────────────────────────
df_closure = df[df["complaints_closed"].notna() & df["complaints_opened"].notna()].copy()
df_closure["closure_rate"] = (
    df_closure["complaints_closed"] / df_closure["complaints_opened"]).clip(upper=2).round(4)
# Note: closure_rate >1 is valid (closing backlog from prior periods)

closure_perf = df_closure[[
    "reporting_period","firm_name","product_group",
    "complaints_opened","complaints_closed","closure_rate",
    "pct_closed_3days","pct_closed_3to8weeks",
]].copy()

# ── KPI 4: Uphold rate ────────────────────────────────────────────────────────
uphold = df[df["uphold_rate"].notna()].copy()
uphold_pct = uphold.copy()
uphold_pct["uphold_rate_pct"] = (uphold_pct["uphold_rate"] * 100).round(2)

# Firm-level weighted uphold (weighted by complaints_opened where both present)
uphold_w = uphold_pct[uphold_pct["complaints_opened"].notna()].copy()
uphold_w["weighted_upheld"] = uphold_w["uphold_rate"] * uphold_w["complaints_opened"]
uphold_firm = (uphold_w.groupby(["reporting_period","firm_name"])
               .agg(complaints_opened=("complaints_opened","sum"),
                    weighted_upheld=("weighted_upheld","sum"))
               .reset_index())
uphold_firm["uphold_rate_weighted"] = (
    uphold_firm["weighted_upheld"] / uphold_firm["complaints_opened"]).round(4)
uphold_firm["uphold_rate_weighted_pct"] = (uphold_firm["uphold_rate_weighted"]*100).round(2)

# Product-level uphold
uphold_product = (uphold_w.groupby(["reporting_period","product_group"])
                  .agg(complaints_opened=("complaints_opened","sum"),
                       weighted_upheld=("weighted_upheld","sum"))
                  .reset_index())
uphold_product["uphold_rate_weighted"] = (
    uphold_product["weighted_upheld"] / uphold_product["complaints_opened"]).round(4)
uphold_product["uphold_rate_weighted_pct"] = (
    uphold_product["uphold_rate_weighted"]*100).round(2)

# ── KPI 5: Period-over-period trends ─────────────────────────────────────────
def add_trends(df_in, group_cols, metric_col):
    df_sorted = df_in.sort_values(group_cols + ["reporting_period"])
    if group_cols:
        df_sorted["prev_period_val"] = df_sorted.groupby(group_cols)[metric_col].shift(1)
    else:
        df_sorted["prev_period_val"] = df_sorted[metric_col].shift(1)
    df_sorted["abs_change"] = df_sorted[metric_col] - df_sorted["prev_period_val"]
    df_sorted["pct_change"] = np.where(
        df_sorted["prev_period_val"].notna() & (df_sorted["prev_period_val"] != 0),
        (df_sorted["abs_change"] / df_sorted["prev_period_val"] * 100).round(2),
        np.nan
    )
    return df_sorted

trends_firm    = add_trends(vol_firm,    ["firm_name"],    "total_complaints")
trends_product = add_trends(vol_product, ["product_group"],"total_complaints")
trends_market  = add_trends(vol_period,  [],               "market_complaints")

# ── Firm benchmark table ──────────────────────────────────────────────────────
# One row per firm per period: volume, uphold, closure rate, complaint rate
bench_base = (df.groupby(["reporting_period","firm_name"])
              .agg(
                  complaints_opened=("complaints_opened","sum"),
                  complaints_closed=("complaints_closed","sum"),
              ).reset_index())

bench_uphold = uphold_firm[["reporting_period","firm_name","uphold_rate_weighted_pct"]]
bench_rate   = (complaint_rate.groupby(["reporting_period","firm_name"])
                .apply(lambda g: (g["complaints_opened"].sum() / g["denominator"].sum())
                       if g["denominator"].sum() > 0 else np.nan, include_groups=False)
                .reset_index(name="complaint_rate_per_1k"))

bench_closure_agg = (df_closure.groupby(["reporting_period","firm_name"])
                    .agg(pct_3days_mean=("pct_closed_3days","mean"),
                         pct_3to8weeks_mean=("pct_closed_3to8weeks","mean"))
                    .reset_index())

firm_benchmark = (bench_base
    .merge(bench_uphold, on=["reporting_period","firm_name"], how="left")
    .merge(bench_rate,   on=["reporting_period","firm_name"], how="left")
    .merge(bench_closure_agg, on=["reporting_period","firm_name"], how="left"))

# Period order + rank by complaints
firm_benchmark["period_order"] = firm_benchmark["reporting_period"].map(
    {p: i for i, p in enumerate(PERIODS_ORDERED)})
firm_benchmark["rank_by_volume"] = (firm_benchmark.groupby("reporting_period")
    ["complaints_opened"].rank(ascending=False, method="min").astype("Int64"))

# PoP changes on firm benchmark
firm_benchmark = add_trends(firm_benchmark.sort_values("period_order"),
                            ["firm_name"], "complaints_opened")
firm_benchmark = firm_benchmark.rename(columns={
    "abs_change": "volume_abs_change",
    "pct_change": "volume_pct_change",
    "prev_period_val": "prev_complaints_opened",
})

# ── Product benchmark table ───────────────────────────────────────────────────
prod_benchmark = vol_product.copy()
prod_benchmark = prod_benchmark.merge(
    uphold_product[["reporting_period","product_group","uphold_rate_weighted_pct"]],
    on=["reporting_period","product_group"], how="left")
prod_benchmark = add_trends(prod_benchmark, ["product_group"], "total_complaints")

# ── Priority opportunities (evidence-based scoring) ──────────────────────────
latest = "2025H2"
df_latest = df[df["reporting_period"] == latest].copy()

# Score each product on 3 dimensions (1-5 scale each)
opp = []
for prod in df_latest["product_group"].unique():
    sub = df_latest[df_latest["product_group"] == prod]
    vol  = sub["complaints_opened"].sum()
    uph  = sub[sub["uphold_rate"].notna()]["uphold_rate"].mean()
    cl3  = sub[sub["pct_closed_3days"].notna()]["pct_closed_3days"].mean()
    cl8  = sub[sub["pct_closed_3to8weeks"].notna()]["pct_closed_3to8weeks"].mean()

    # Trend (PoP volume change vs prior period)
    prior_vol = df[df["reporting_period"]=="2025H1"]["complaints_opened"].sum()
    curr_vol  = vol
    trend_pct = ((curr_vol - prior_vol) / prior_vol * 100) if prior_vol > 0 else 0

    opp.append({
        "product_group": prod,
        "latest_volume": vol,
        "avg_uphold_rate_pct": round(uph * 100, 1) if pd.notna(uph) else None,
        "avg_pct_closed_3days": round(cl3 * 100, 1) if pd.notna(cl3) else None,
        "avg_pct_closed_3to8weeks": round(cl8 * 100, 1) if pd.notna(cl8) else None,
        "volume_trend_pct_vs_prior": round(trend_pct, 1),
    })

df_opp = pd.DataFrame(opp)

# Normalise to 1-5 scores
def norm_score(series, ascending=True):
    mn, mx = series.min(), series.max()
    if mx == mn: return pd.Series([3]*len(series), index=series.index)
    s = (series - mn) / (mx - mn) * 4 + 1
    return s if ascending else 6 - s

df_opp["score_volume"]    = norm_score(df_opp["latest_volume"])
df_opp["score_uphold"]    = norm_score(pd.to_numeric(df_opp["avg_uphold_rate_pct"], errors="coerce"))
df_opp["score_closure"]   = norm_score(pd.to_numeric(df_opp["avg_pct_closed_3days"], errors="coerce"), ascending=False)
# Higher volume + higher uphold + lower fast-closure = higher priority
df_opp["priority_score"]  = (df_opp["score_volume"] + df_opp["score_uphold"] + df_opp["score_closure"]).round(2)
df_opp["priority_rank"]   = df_opp["priority_score"].rank(ascending=False, method="min").astype(int)
df_opp = df_opp.sort_values("priority_rank")

# ── Scenario model ────────────────────────────────────────────────────────────
scenarios = []
baseline_vol = df[df["reporting_period"]==latest]["complaints_opened"].sum()
baseline_uph = df_opp["avg_uphold_rate_pct"].mean()

for pct_reduction in [5, 10, 15, 20]:
    reduced = baseline_vol * (1 - pct_reduction/100)
    scenarios.append({
        "scenario": f"Complaint volume reduced by {pct_reduction}%",
        "assumption": f"Process/prevention initiatives reduce complaints by {pct_reduction}%",
        "baseline_complaints": int(baseline_vol),
        "scenario_complaints": int(reduced),
        "complaints_avoided": int(baseline_vol - reduced),
        "type": "volume_reduction",
    })

# Uphold rate improvement: if top-quartile uphold firms improve to median
q75_uphold = df_opp["avg_uphold_rate_pct"].quantile(0.75)
median_uphold = df_opp["avg_uphold_rate_pct"].median()
scenarios.append({
    "scenario": "High uphold products reach market median uphold rate",
    "assumption": f"Products with uphold >75th percentile ({q75_uphold:.1f}%) partially close gap to median ({median_uphold:.1f}%)",
    "baseline_avg_uphold_pct": round(baseline_uph, 1),
    "target_uphold_pct": round(median_uphold, 1),
    "implication": "Fewer customers winning complaints implies fewer valid failures reaching complaint stage",
    "type": "uphold_improvement",
})

# Closure speed: if all firms matched the 3-day closure rate of top quartile
top_q_3days = df[df["reporting_period"]==latest]["pct_closed_3days"].quantile(0.75)
avg_3days    = df[df["reporting_period"]==latest]["pct_closed_3days"].mean()
scenarios.append({
    "scenario": "All firms reach top-quartile 3-day closure rate",
    "assumption": f"Firms currently below 75th percentile ({top_q_3days*100:.1f}%) improve to match it",
    "current_avg_pct_3days": round(avg_3days*100, 1),
    "target_pct_3days": round(top_q_3days*100, 1),
    "uplift_pct_points": round((top_q_3days - avg_3days)*100, 1),
    "type": "closure_improvement",
})

df_scenarios = pd.DataFrame(scenarios)

# ── Save all Tableau-ready CSVs ───────────────────────────────────────────────
saves = {
    "kpi_firm_benchmark.csv":         firm_benchmark,
    "kpi_product_benchmark.csv":      prod_benchmark,
    "kpi_volume_by_firm.csv":         vol_firm,
    "kpi_volume_by_product.csv":      vol_product,
    "kpi_volume_by_period.csv":       vol_period,
    "kpi_complaint_rate.csv":         complaint_rate,
    "kpi_closure_performance.csv":    closure_perf,
    "kpi_uphold_by_firm.csv":         uphold_firm,
    "kpi_uphold_by_product.csv":      uphold_product,
    "kpi_trends_firm.csv":            trends_firm,
    "kpi_trends_product.csv":         trends_product,
    "kpi_trends_market.csv":          trends_market,
    "kpi_opportunities.csv":          df_opp,
    "kpi_scenarios.csv":              df_scenarios,
    "tableau_firms.csv":              firm_benchmark,
    "tableau_products.csv":           prod_benchmark,
    "tableau_market.csv":             vol_period,
    "tableau_opportunities.csv":      df_opp,
}

for fname, dframe in saves.items():
    dframe.to_csv(OUTPUTS / fname, index=False)
    print(f"  Saved {fname} ({len(dframe)} rows)")

print("\n✓ Phase 4-5 complete — KPIs and Tableau-ready outputs saved")


# ── Cost Model ────────────────────────────────────────────────────────────────
# All figures are assumptions, clearly labelled.
# Sources:
#   FOS case fee: £650 per case (FOS published 2024/25 standard fee)
#   FOS escalation rate: ~8% industry average (FCA/FOS annual data)
#   Internal handling cost: £200 per complaint (industry estimate range £150-£400)
#   Redress per upheld complaint: £300 (conservative; actual varies by product and case)
#
# Formula:
#   Total cost = (handling × volume) + (fos_fee × escalation_rate × volume)
#              + (redress_per_upheld × uphold_rate × volume)

HANDLING_COST     = 200    # £ per complaint
FOS_FEE           = 650    # £ per FOS referral (FOS 2024/25 standard rate)
FOS_ESCALATION    = 0.08   # 8% of complaints escalated to FOS
REDRESS_PER_UPHELD= 300    # £ per upheld complaint (conservative)

ASSUMPTIONS = {
    "internal_handling_cost_per_complaint_gbp": HANDLING_COST,
    "fos_case_fee_gbp": FOS_FEE,
    "fos_escalation_rate": FOS_ESCALATION,
    "redress_per_upheld_complaint_gbp": REDRESS_PER_UPHELD,
    "source_fos_fee": "Financial Ombudsman Service published fee schedule 2024/25",
    "source_handling": "Industry estimate; range £150-£400 per complaint",
    "source_escalation": "Approximate FOS/FCA annual data",
    "source_redress": "Conservative estimate; actual varies by product and firm",
    "note": "These are modelled cost estimates for prioritisation purposes, not audited figures",
}

cost = bench[bench["reporting_period"]=="2025H2"].copy()
cost = cost.merge(
    uphold_firm[uphold_firm["reporting_period"]=="2025H2"][["firm_name","uphold_rate_weighted"]],
    on="firm_name", how="left"
)
cost["uphold_rate_for_cost"] = cost["uphold_rate_weighted"].fillna(0.55)  # market avg fallback

cost["cost_handling_gbp"]    = (cost["complaints_opened"] * HANDLING_COST).round(0)
cost["cost_fos_gbp"]         = (cost["complaints_opened"] * FOS_ESCALATION * FOS_FEE).round(0)
cost["cost_redress_gbp"]     = (cost["complaints_opened"] * cost["uphold_rate_for_cost"] * REDRESS_PER_UPHELD).round(0)
cost["cost_total_gbp"]       = cost["cost_handling_gbp"] + cost["cost_fos_gbp"] + cost["cost_redress_gbp"]
cost["cost_per_complaint_gbp"]= (cost["cost_total_gbp"] / cost["complaints_opened"]).round(0)

cost_out = cost[[
    "firm_name","complaints_opened","uphold_rate_for_cost",
    "cost_handling_gbp","cost_fos_gbp","cost_redress_gbp",
    "cost_total_gbp","cost_per_complaint_gbp"
]].sort_values("cost_total_gbp", ascending=False).reset_index(drop=True)

cost_out.to_csv(OUTPUTS / "kpi_cost_model.csv", index=False)
import json
with open(Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark\docs") / "cost_model_assumptions.json","w") as f:
    json.dump(ASSUMPTIONS, f, indent=2)
print(f"Cost model: {len(cost_out)} firms, top 5:")
print(cost_out[["firm_name","complaints_opened","cost_total_gbp"]].head().to_string())

# Product-level cost model
prod_cost = pd.read_csv(OUTPUTS / "kpi_uphold_by_product.csv")
prod_vol  = pd.read_csv(OUTPUTS / "kpi_volume_by_product.csv")
prod_cost_latest = prod_vol[prod_vol["reporting_period"]=="2025H2"].merge(
    prod_cost[prod_cost["reporting_period"]=="2025H2"][["product_group","uphold_rate_weighted"]],
    on="product_group", how="left"
)
prod_cost_latest["cost_handling_gbp"] = prod_cost_latest["total_complaints"] * HANDLING_COST
prod_cost_latest["cost_fos_gbp"]      = prod_cost_latest["total_complaints"] * FOS_ESCALATION * FOS_FEE
prod_cost_latest["cost_redress_gbp"]  = prod_cost_latest["total_complaints"] * prod_cost_latest["uphold_rate_weighted"] * REDRESS_PER_UPHELD
prod_cost_latest["cost_total_gbp"]    = (prod_cost_latest["cost_handling_gbp"] + prod_cost_latest["cost_fos_gbp"] + prod_cost_latest["cost_redress_gbp"]).round(0)
prod_cost_latest.to_csv(OUTPUTS / "kpi_cost_by_product.csv", index=False)
print("\nProduct cost model saved")
