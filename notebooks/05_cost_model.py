"""Cost model — translates complaint volumes into £ cost exposure for finance audience."""

import pandas as pd, json
from pathlib import Path

ROOT    = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
OUTPUTS = ROOT / "data" / "outputs"
DOCS    = ROOT / "docs"

bench       = pd.read_csv(OUTPUTS / "kpi_firm_benchmark.csv")
uphold_firm = pd.read_csv(OUTPUTS / "kpi_uphold_by_firm.csv")
prod_vol    = pd.read_csv(OUTPUTS / "kpi_volume_by_product.csv")
prod_uphold = pd.read_csv(OUTPUTS / "kpi_uphold_by_product.csv")

# ── Cost assumptions (all labelled) ───────────────────────────────────────────
HANDLING  = 200    # £ per complaint — internal staff, systems, QA (industry est. £150-£400)
FOS_FEE   = 650    # £ per FOS referral — FOS published 2024/25 standard fee
FOS_RATE  = 0.08   # 8% FOS escalation rate — approximate FOS/FCA annual data
REDRESS   = 300    # £ per upheld complaint — conservative; actual varies by product and case
MKT_AVG_UPHOLD = 0.55  # fallback where firm uphold rate not available

ASSUMPTIONS = {
    "internal_handling_cost_per_complaint_gbp": HANDLING,
    "fos_case_fee_gbp": FOS_FEE,
    "fos_escalation_rate": FOS_RATE,
    "redress_per_upheld_complaint_gbp": REDRESS,
    "uphold_rate_fallback": MKT_AVG_UPHOLD,
    "source_fos_fee": "FOS published fee schedule 2024/25 — fos.org.uk",
    "source_handling": "Industry estimate; range £150-£400 per complaint",
    "source_escalation": "Approximate FCA/FOS annual complaint data",
    "source_redress": "Conservative estimate; actual varies by product and firm",
    "formula": "total_cost = (handling × vol) + (fos_fee × fos_rate × vol) + (redress × uphold_rate × vol)",
    "note": "Modelled estimates for prioritisation only — not audited figures. Label clearly in all outputs.",
}

with open(DOCS / "cost_model_assumptions.json", "w") as f:
    json.dump(ASSUMPTIONS, f, indent=2)

# ── Firm cost model (2025H2) ───────────────────────────────────────────────────
firms = bench[bench["reporting_period"]=="2025H2"][["firm_name","complaints_opened"]].copy()
uph   = uphold_firm[uphold_firm["reporting_period"]=="2025H2"][["firm_name","uphold_rate_weighted"]]
firms = firms.merge(uph, on="firm_name", how="left")
firms["uphold_rate_used"] = firms["uphold_rate_weighted"].fillna(MKT_AVG_UPHOLD)

firms["cost_handling"]  = (firms["complaints_opened"] * HANDLING).round(0)
firms["cost_fos"]       = (firms["complaints_opened"] * FOS_RATE * FOS_FEE).round(0)
firms["cost_redress"]   = (firms["complaints_opened"] * firms["uphold_rate_used"] * REDRESS).round(0)
firms["cost_total"]     = firms["cost_handling"] + firms["cost_fos"] + firms["cost_redress"]
firms["cost_per_compl"] = (firms["cost_total"] / firms["complaints_opened"]).round(0)
firms["uphold_rate_pct"]= (firms["uphold_rate_used"] * 100).round(1)
firms = firms.sort_values("cost_total", ascending=False).reset_index(drop=True)

firms[[
    "firm_name","complaints_opened","uphold_rate_pct",
    "cost_handling","cost_fos","cost_redress","cost_total","cost_per_compl"
]].to_csv(OUTPUTS / "kpi_cost_model_firms.csv", index=False)

# ── Product cost model (2025H2) ───────────────────────────────────────────────
prods = prod_vol[prod_vol["reporting_period"]=="2025H2"][["product_group","total_complaints"]].copy()
puph  = prod_uphold[prod_uphold["reporting_period"]=="2025H2"][["product_group","uphold_rate_weighted"]]
prods = prods.merge(puph, on="product_group", how="left")
prods["uphold_rate_used"] = prods["uphold_rate_weighted"].fillna(MKT_AVG_UPHOLD)

prods["cost_handling"] = (prods["total_complaints"] * HANDLING).round(0)
prods["cost_fos"]      = (prods["total_complaints"] * FOS_RATE * FOS_FEE).round(0)
prods["cost_redress"]  = (prods["total_complaints"] * prods["uphold_rate_used"] * REDRESS).round(0)
prods["cost_total"]    = prods["cost_handling"] + prods["cost_fos"] + prods["cost_redress"]
prods["cost_per_compl"]= (prods["cost_total"] / prods["total_complaints"]).round(0)
prods["uphold_rate_pct"]= (prods["uphold_rate_used"] * 100).round(1)
prods = prods.sort_values("cost_total", ascending=False).reset_index(drop=True)
prods.to_csv(OUTPUTS / "kpi_cost_by_product.csv", index=False)

# ── Market-level cost summary ──────────────────────────────────────────────────
market_total_cost = firms["cost_total"].sum()
print(f"\nMarket total estimated cost exposure (2025H2): £{market_total_cost/1e9:.2f}bn")
print(f"  Handling:  £{firms['cost_handling'].sum()/1e9:.2f}bn")
print(f"  FOS risk:  £{firms['cost_fos'].sum()/1e9:.2f}bn")
print(f"  Redress:   £{firms['cost_redress'].sum()/1e9:.2f}bn")
print(f"\nTop 10 firms by cost exposure:")
print(firms[["firm_name","complaints_opened","uphold_rate_pct","cost_total"]].head(10).to_string())
print(f"\nProduct cost breakdown:")
print(prods[["product_group","total_complaints","uphold_rate_pct","cost_total"]].to_string())
print("\n✓ Cost model complete")
