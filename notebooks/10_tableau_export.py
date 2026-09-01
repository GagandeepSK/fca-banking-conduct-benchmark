#!/usr/bin/env python3
# 10_tableau_export.py
# Prepare and export all Tableau-ready CSVs with documentation.
# Author: Gagandeep Kapoor

import os, json, warnings
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE / "data" / "processed"
DATA_OUTPUTS   = BASE / "data" / "outputs"
TABLEAU_DIR    = BASE / "tableau"
DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
PERIODS = ["2024H1","2024H2","2025H1","2025H2"]
COST_HANDLING=200.0; COST_FOS_FEE=650.0; COST_FOS_RATE=0.08; COST_REDRESS=300.0


def export_market_summary(df):
    """
    Export: tableau_market_summary.csv
    One row per period; market-level KPIs for trend charts and headline cards.
    """
    out = TABLEAU_DIR / "tableau_market_summary.csv"
    try:
        c8 = df.groupby("period")["closed_within_8_weeks"].sum()
        agg = (df.groupby("period",as_index=False)
               .agg(total_opened=("complaints_opened","sum"),
                    total_closed=("complaints_closed","sum"),
                    total_upheld=("upheld","sum"),
                    n_firms=("firm_name","nunique")))
        agg["uphold_rate"]      = agg["total_upheld"]/agg["total_closed"]
        agg["closure_8wk_rate"] = agg["period"].map(c8)/agg["total_closed"]
        result = agg
        result.to_csv(out, index=False)
        print(f"  tableau_market_summary.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_market_summary.csv: ERROR - {e}")
        return pd.DataFrame()

def export_firm_benchmark(df):
    """
    Export: tableau_firm_benchmark.csv
    One row per firm-period; primary data source for firm-level views and scatter plots.
    """
    out = TABLEAU_DIR / "tableau_firm_benchmark.csv"
    try:
        agg = (df.groupby(["firm_name","period"],as_index=False)
               .agg(opened=("complaints_opened","sum"),
                    closed=("complaints_closed","sum"),
                    upheld_n=("upheld","sum"),
                    closed_8wk=("closed_within_8_weeks","sum")))
        agg["uphold_rate"]      = agg["upheld_n"]/agg["closed"].replace(0,float("nan"))
        agg["closure_8wk_rate"] = agg["closed_8wk"]/agg["closed"].replace(0,float("nan"))
        agg["size_band"] = agg["opened"].apply(lambda v: "Large" if v>=50000 else "Medium" if v>=10000 else "Small" if v>=1000 else "Micro")
        agg["cd_rag"] = agg["uphold_rate"].apply(lambda r: "RED" if pd.notna(r) and r>=0.5 else "AMBER" if pd.notna(r) and r>=0.35 else "GREEN")
        result = agg
        result.to_csv(out, index=False)
        print(f"  tableau_firm_benchmark.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_firm_benchmark.csv: ERROR - {e}")
        return pd.DataFrame()

def export_product_benchmark(df):
    """
    Export: tableau_product_benchmark.csv
    One row per product-period; for product mix bar charts and heat maps.
    """
    out = TABLEAU_DIR / "tableau_product_benchmark.csv"
    try:
        agg = (df.groupby(["product_group","period"],as_index=False)
               .agg(opened=("complaints_opened","sum"),
                    closed=("complaints_closed","sum"),
                    upheld_n=("upheld","sum")))
        agg["uphold_rate"] = agg["upheld_n"]/agg["closed"].replace(0,float("nan"))
        ptot = agg.groupby("period")["opened"].sum().to_dict()
        agg["market_share"] = agg.apply(lambda r: r["opened"]/ptot.get(r["period"],1),axis=1)
        result = agg
        result.to_csv(out, index=False)
        print(f"  tableau_product_benchmark.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_product_benchmark.csv: ERROR - {e}")
        return pd.DataFrame()

def export_cost_model(df):
    """
    Export: tableau_cost_model.csv
    Cost exposure per firm-period; for cost league tables and ROI modelling.
    """
    out = TABLEAU_DIR / "tableau_cost_model.csv"
    try:
        agg = (df.groupby(["firm_name","period"],as_index=False)
               .agg(opened=("complaints_opened","sum"),
                    closed=("complaints_closed","sum"),
                    upheld_n=("upheld","sum")))
        agg["uphold_rate"]  = agg["upheld_n"]/agg["closed"].replace(0,float("nan"))
        agg["handling_gbp"] = agg["opened"]*COST_HANDLING
        agg["fos_gbp"]      = agg["opened"]*COST_FOS_RATE*COST_FOS_FEE
        agg["redress_gbp"]  = agg["upheld_n"]*COST_REDRESS
        agg["total_gbp"]    = agg["handling_gbp"]+agg["fos_gbp"]+agg["redress_gbp"]
        result = agg
        result.to_csv(out, index=False)
        print(f"  tableau_cost_model.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_cost_model.csv: ERROR - {e}")
        return pd.DataFrame()

def export_top30_firms(df):
    """
    Export: tableau_top30_firms.csv
    Top 30 firms by 2025H2 volume; for ranked bar charts.
    """
    out = TABLEAU_DIR / "tableau_top30_firms.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_top30_firms.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_top30_firms.csv: ERROR - {e}")
        return pd.DataFrame()

def export_cd_scorecard(df):
    """
    Export: tableau_cd_scorecard.csv
    Consumer Duty composite score per firm; for RAG scorecards.
    """
    out = TABLEAU_DIR / "tableau_cd_scorecard.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_cd_scorecard.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_cd_scorecard.csv: ERROR - {e}")
        return pd.DataFrame()

def export_peer_benchmarks(df):
    """
    Export: tableau_peer_benchmarks.csv
    Peer group medians; for box plots and peer comparison views.
    """
    out = TABLEAU_DIR / "tableau_peer_benchmarks.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_peer_benchmarks.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_peer_benchmarks.csv: ERROR - {e}")
        return pd.DataFrame()

def export_volume_trends(df):
    """
    Export: tableau_volume_trends.csv
    Firm-level volume trend slopes; for trend scatter and waterfall charts.
    """
    out = TABLEAU_DIR / "tableau_volume_trends.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_volume_trends.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_volume_trends.csv: ERROR - {e}")
        return pd.DataFrame()

def export_anomaly_flags(df):
    """
    Export: tableau_anomaly_flags.csv
    Z-score anomaly flags; for outlier highlight views.
    """
    out = TABLEAU_DIR / "tableau_anomaly_flags.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_anomaly_flags.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_anomaly_flags.csv: ERROR - {e}")
        return pd.DataFrame()

def export_product_firm_matrix(df):
    """
    Export: tableau_product_firm_matrix.csv
    Firm x product x period; for heat maps and cross-tab analysis.
    """
    out = TABLEAU_DIR / "tableau_product_firm_matrix.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_product_firm_matrix.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_product_firm_matrix.csv: ERROR - {e}")
        return pd.DataFrame()

def export_regulatory_risk(df):
    """
    Export: tableau_regulatory_risk.csv
    Composite regulatory risk scores; for risk heat maps and sorted tables.
    """
    out = TABLEAU_DIR / "tableau_regulatory_risk.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_regulatory_risk.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_regulatory_risk.csv: ERROR - {e}")
        return pd.DataFrame()

def export_scenario_results(df):
    """
    Export: tableau_scenario_results.csv
    What-if scenario cost outcomes; for scenario comparison bar charts.
    """
    out = TABLEAU_DIR / "tableau_scenario_results.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_scenario_results.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_scenario_results.csv: ERROR - {e}")
        return pd.DataFrame()

def export_market_concentration(df):
    """
    Export: tableau_market_concentration.csv
    Cumulative market share; for Lorenz curve and CR-N bar charts.
    """
    out = TABLEAU_DIR / "tableau_market_concentration.csv"
    try:
        sub = df[df["period"]=="2025H2"].groupby("firm_name")["complaints_opened"].sum().sort_values(ascending=False).reset_index()
        tot = sub["complaints_opened"].sum()
        sub["market_share"] = sub["complaints_opened"]/tot
        sub["cumulative_share"] = sub["market_share"].cumsum()
        sub["cr_group"] = sub["cumulative_share"].apply(lambda c: "Top 4" if c<=0.4 else "Top 10" if c<=0.6 else "Top 20" if c<=0.75 else "Rest")
        sub.columns = ["firm_name","opened","market_share","cumulative_share","cr_group"]
        result = sub
        result.to_csv(out, index=False)
        print(f"  tableau_market_concentration.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_market_concentration.csv: ERROR - {e}")
        return pd.DataFrame()

def export_period_firm_pivot(df):
    """
    Export: tableau_period_firm_pivot.csv
    Firm volumes pivoted to wide format; for period-comparison scatter.
    """
    out = TABLEAU_DIR / "tableau_period_firm_pivot.csv"
    try:
        result = (df.groupby(["firm_name","period"],as_index=False)
                   .agg(opened=("complaints_opened","sum"),
                        closed=("complaints_closed","sum"),
                        upheld=("upheld","sum")))
        result.to_csv(out, index=False)
        print(f"  tableau_period_firm_pivot.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_period_firm_pivot.csv: ERROR - {e}")
        return pd.DataFrame()

def export_uphold_distribution(df):
    """
    Export: tableau_uphold_distribution.csv
    Distribution of uphold rates binned into 10pp intervals; for histogram.
    """
    out = TABLEAU_DIR / "tableau_uphold_distribution.csv"
    try:
        tmp = df[df["complaints_closed"]>0].copy()
        tmp["uphold_rate"] = tmp["upheld"]/tmp["complaints_closed"]
        fu = tmp.groupby("firm_name")["uphold_rate"].mean()
        rows = []
        for i in range(11):
            lo,hi = i/10,(i+1)/10
            n = int(((fu>=lo)&(fu<hi)).sum())
            lbl = str(round(lo*100))+"%-"+str(round(hi*100))+"%"
            rows.append({"bin_label":lbl,"bin_lo":lo,"bin_hi":hi,"n_firms":n,"pct_firms":round(n/len(fu)*100,1)})
        result = pd.DataFrame(rows)
        result.to_csv(out, index=False)
        print(f"  tableau_uphold_distribution.csv: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  tableau_uphold_distribution.csv: ERROR - {e}")
        return pd.DataFrame()


def load_data():
    c = DATA_PROCESSED/"complaints_clean.csv"
    if not c.exists(): raise FileNotFoundError(f"Missing: {c}")
    return pd.read_csv(c)


def main():
    print("
UK Banking Complaints — Tableau Export")
    print(f"Run at: {datetime.now().strftime("%%Y-%%m-%%d %%H:%%M:%%S")}")
    df = load_data()
    print(f"  Loaded: {len(df):,} rows")
    export_market_summary(df)
    export_firm_benchmark(df)
    export_product_benchmark(df)
    export_cost_model(df)
    export_top30_firms(df)
    export_cd_scorecard(df)
    export_peer_benchmarks(df)
    export_volume_trends(df)
    export_anomaly_flags(df)
    export_product_firm_matrix(df)
    export_regulatory_risk(df)
    export_scenario_results(df)
    export_market_concentration(df)
    export_period_firm_pivot(df)
    export_uphold_distribution(df)
    manifest = {
        "tableau_market_summary.csv": {"description": "One row per period; market-level KPIs for trend charts and headline cards."},
        "tableau_firm_benchmark.csv": {"description": "One row per firm-period; primary data source for firm-level views and scatter plots."},
        "tableau_product_benchmark.csv": {"description": "One row per product-period; for product mix bar charts and heat maps."},
        "tableau_cost_model.csv": {"description": "Cost exposure per firm-period; for cost league tables and ROI modelling."},
        "tableau_top30_firms.csv": {"description": "Top 30 firms by 2025H2 volume; for ranked bar charts."},
        "tableau_cd_scorecard.csv": {"description": "Consumer Duty composite score per firm; for RAG scorecards."},
        "tableau_peer_benchmarks.csv": {"description": "Peer group medians; for box plots and peer comparison views."},
        "tableau_volume_trends.csv": {"description": "Firm-level volume trend slopes; for trend scatter and waterfall charts."},
        "tableau_anomaly_flags.csv": {"description": "Z-score anomaly flags; for outlier highlight views."},
        "tableau_product_firm_matrix.csv": {"description": "Firm x product x period; for heat maps and cross-tab analysis."},
        "tableau_regulatory_risk.csv": {"description": "Composite regulatory risk scores; for risk heat maps and sorted tables."},
        "tableau_scenario_results.csv": {"description": "What-if scenario cost outcomes; for scenario comparison bar charts."},
        "tableau_market_concentration.csv": {"description": "Cumulative market share; for Lorenz curve and CR-N bar charts."},
        "tableau_period_firm_pivot.csv": {"description": "Firm volumes pivoted to wide format; for period-comparison scatter."},
        "tableau_uphold_distribution.csv": {"description": "Distribution of uphold rates binned into 10pp intervals; for histogram."},
    }
    mp = TABLEAU_DIR/"manifest.json"
    with open(mp,"w") as f: json.dump(manifest,f,indent=2)
    print(f"  Manifest: {mp}")
    print("
Tableau export complete.")


if __name__ == "__main__":
    main()