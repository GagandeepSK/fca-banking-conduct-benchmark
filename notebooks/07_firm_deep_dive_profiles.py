#!/usr/bin/env python3
# 07_firm_deep_dive_profiles.py
# Per-firm deep dive: complaint profiles, trends, product mix, CD scoring, cost exposure.
# Author: Gagandeep Kapoor

import os, json, math, warnings
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE / "data" / "processed"
DATA_OUTPUTS   = BASE / "data" / "outputs"
DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
PERIODS = ["2024H1","2024H2","2025H1","2025H2"]
PRODUCT_GROUPS = ["Banking and credit cards","Home finance",
    "Insurance and pure protection","Decumulation and pensions","Investments"]
COST_HANDLING=200.0; COST_FOS_FEE=650.0; COST_FOS_RATE=0.08; COST_REDRESS=300.0


def q01_market_totals_by_period(con):
    """
    Market totals by period.
    
    SQL
    ---
    SELECT period, SUM(complaints_opened) AS total_opened, SUM(complaints_closed) AS
     total_closed, SUM(upheld) AS total_upheld, COUNT(DISTINCT firm_name) AS n_firms
     FROM complaints GROUP BY period ORDER BY period
    """
    query = """
    SELECT period, SUM(complaints_opened) AS total_opened, SUM(complaints_closed) AS total_closed, SUM(upheld) AS total_upheld, COUNT(DISTINCT firm_name) AS n_firms FROM complaints GROUP BY period ORDER BY period
    """
    try:
        result = con.execute(query).df()
        print(f"  q01_market_totals_by_period: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q01_market_totals_by_period: ERROR - {e}")
        return pd.DataFrame()

def q02_top_firms_by_volume(con):
    """
    Top firms by complaint volume.
    
    SQL
    ---
    SELECT firm_name, period, SUM(complaints_opened) AS opened FROM complaints GROUP
     BY firm_name, period ORDER BY opened DESC LIMIT 50
    """
    query = """
    SELECT firm_name, period, SUM(complaints_opened) AS opened FROM complaints GROUP BY firm_name, period ORDER BY opened DESC LIMIT 50
    """
    try:
        result = con.execute(query).df()
        print(f"  q02_top_firms_by_volume: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q02_top_firms_by_volume: ERROR - {e}")
        return pd.DataFrame()

def q03_uphold_rate_by_firm(con):
    """
    Uphold rate per firm (min 100 closed).
    
    SQL
    ---
    SELECT firm_name, period, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS up
    hold_rate FROM complaints WHERE complaints_closed > 0 GROUP BY firm_name, period
     HAVING SUM(complaints_closed) >= 100 ORDER BY uphold_rate DESC
    """
    query = """
    SELECT firm_name, period, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS uphold_rate FROM complaints WHERE complaints_closed > 0 GROUP BY firm_name, period HAVING SUM(complaints_closed) >= 100 ORDER BY uphold_rate DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q03_uphold_rate_by_firm: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q03_uphold_rate_by_firm: ERROR - {e}")
        return pd.DataFrame()

def q04_8wk_closure_by_firm(con):
    """
    8-week closure rate per firm.
    
    SQL
    ---
    SELECT firm_name, period, SUM(closed_within_8_weeks)*1.0/NULLIF(SUM(complaints_c
    losed),0) AS closure_8wk_rate FROM complaints GROUP BY firm_name, period ORDER B
    Y closure_8wk_rate ASC
    """
    query = """
    SELECT firm_name, period, SUM(closed_within_8_weeks)*1.0/NULLIF(SUM(complaints_closed),0) AS closure_8wk_rate FROM complaints GROUP BY firm_name, period ORDER BY closure_8wk_rate ASC
    """
    try:
        result = con.execute(query).df()
        print(f"  q04_8wk_closure_by_firm: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q04_8wk_closure_by_firm: ERROR - {e}")
        return pd.DataFrame()

def q05_product_mix_by_firm(con):
    """
    Product mix per firm.
    
    SQL
    ---
    SELECT firm_name, product_group, period, SUM(complaints_opened) AS opened FROM c
    omplaints GROUP BY firm_name, product_group, period ORDER BY firm_name, period, 
    opened DESC
    """
    query = """
    SELECT firm_name, product_group, period, SUM(complaints_opened) AS opened FROM complaints GROUP BY firm_name, product_group, period ORDER BY firm_name, period, opened DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q05_product_mix_by_firm: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q05_product_mix_by_firm: ERROR - {e}")
        return pd.DataFrame()

def q06_uphold_by_product_period(con):
    """
    Uphold rate by product group and period.
    
    SQL
    ---
    SELECT product_group, period, SUM(complaints_opened) AS opened, SUM(upheld)*1.0/
    NULLIF(SUM(complaints_closed),0) AS uphold_rate, SUM(closed_within_8_weeks)*1.0/
    NULLIF(SUM(complaints_closed),0) AS closure_8wk FROM complaints GROUP BY product_group, period ORDER BY product_group, period
    """
    query = """
    SELECT product_group, period, SUM(complaints_opened) AS opened, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS uphold_rate, SUM(closed_within_8_weeks)*1.0/NULLIF(SUM(complaints_closed),0) AS closure_8wk FROM complaints GROUP BY product_group, period ORDER BY product_group, period
    """
    try:
        result = con.execute(query).df()
        print(f"  q06_uphold_by_product_period: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q06_uphold_by_product_period: ERROR - {e}")
        return pd.DataFrame()

def q07_firms_above_cd_threshold(con):
    """
    Firms with uphold rate above Consumer Duty red threshold (50%).
    
    SQL
    ---
    SELECT firm_name, period, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS up
    hold_rate FROM complaints GROUP BY firm_name, period HAVING uphold_rate > 0.5 AN
    D SUM(complaints_closed) >= 500 ORDER BY uphold_rate DESC
    """
    query = """
    SELECT firm_name, period, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS uphold_rate FROM complaints GROUP BY firm_name, period HAVING uphold_rate > 0.5 AND SUM(complaints_closed) >= 500 ORDER BY uphold_rate DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q07_firms_above_cd_threshold: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q07_firms_above_cd_threshold: ERROR - {e}")
        return pd.DataFrame()

def q08_market_share_latest(con):
    """
    Market share of complaints in 2025H2.
    
    SQL
    ---
    SELECT firm_name, SUM(complaints_opened) AS opened, SUM(complaints_opened)*1.0/(
    SELECT SUM(complaints_opened) FROM complaints WHERE period='2025H2') AS market_s
    hare FROM complaints WHERE period='2025H2' GROUP BY firm_name ORDER BY opened DESC
    """
    query = """
    SELECT firm_name, SUM(complaints_opened) AS opened, SUM(complaints_opened)*1.0/(SELECT SUM(complaints_opened) FROM complaints WHERE period='2025H2') AS market_share FROM complaints WHERE period='2025H2' GROUP BY firm_name ORDER BY opened DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q08_market_share_latest: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q08_market_share_latest: ERROR - {e}")
        return pd.DataFrame()

def q09_period_trend_per_firm(con):
    """
    Volume trend per firm across all 4 periods.
    
    SQL
    ---
    SELECT firm_name, MIN(CASE WHEN period='2024H1' THEN complaints_opened END) AS v
    _2024h1, MIN(CASE WHEN period='2024H2' THEN complaints_opened END) AS v_2024h2, 
    MIN(CASE WHEN period='2025H1' THEN complaints_opened END) AS v_2025h1, MIN(CASE WHEN period='2025H2' THEN complaints_opened END) AS v_2025h2 FROM (SELECT firm_name, period, SUM(complaints_opened) AS complaints_opened FROM complaints GROUP BY firm_name,period) t GROUP BY firm_name
    """
    query = """
    SELECT firm_name, MIN(CASE WHEN period='2024H1' THEN complaints_opened END) AS v_2024h1, MIN(CASE WHEN period='2024H2' THEN complaints_opened END) AS v_2024h2, MIN(CASE WHEN period='2025H1' THEN complaints_opened END) AS v_2025h1, MIN(CASE WHEN period='2025H2' THEN complaints_opened END) AS v_2025h2 FROM (SELECT firm_name, period, SUM(complaints_opened) AS complaints_opened FROM complaints GROUP BY firm_name,period) t GROUP BY firm_name
    """
    try:
        result = con.execute(query).df()
        print(f"  q09_period_trend_per_firm: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q09_period_trend_per_firm: ERROR - {e}")
        return pd.DataFrame()

def q10_cost_exposure_per_firm(con):
    """
    Modelled cost exposure per firm in 2025H2.
    
    SQL
    ---
    SELECT firm_name, period, SUM(complaints_opened) AS opened, SUM(upheld) AS uphel
    d_n, SUM(complaints_opened)*200 AS handling_cost, SUM(complaints_opened)*0.08*65
    0 AS fos_cost, SUM(upheld)*300 AS redress_cost, SUM(complaints_opened)*200 + SUM(complaints_opened)*0.08*650 + SUM(upheld)*300 AS total_cost FROM complaints WHERE period='2025H2' GROUP BY firm_name, period ORDER BY total_cost DESC
    """
    query = """
    SELECT firm_name, period, SUM(complaints_opened) AS opened, SUM(upheld) AS upheld_n, SUM(complaints_opened)*200 AS handling_cost, SUM(complaints_opened)*0.08*650 AS fos_cost, SUM(upheld)*300 AS redress_cost, SUM(complaints_opened)*200 + SUM(complaints_opened)*0.08*650 + SUM(upheld)*300 AS total_cost FROM complaints WHERE period='2025H2' GROUP BY firm_name, period ORDER BY total_cost DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q10_cost_exposure_per_firm: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q10_cost_exposure_per_firm: ERROR - {e}")
        return pd.DataFrame()

def q11_slow_closure_firms(con):
    """
    Firms with slowest 8-week complaint closure (2025H2).
    
    SQL
    ---
    SELECT firm_name, period, SUM(closed_within_8_weeks)*1.0/NULLIF(SUM(complaints_c
    losed),0) AS closure_rate FROM complaints WHERE period='2025H2' GROUP BY firm_na
    me, period HAVING SUM(complaints_closed) >= 500 ORDER BY closure_rate ASC LIMIT 30
    """
    query = """
    SELECT firm_name, period, SUM(closed_within_8_weeks)*1.0/NULLIF(SUM(complaints_closed),0) AS closure_rate FROM complaints WHERE period='2025H2' GROUP BY firm_name, period HAVING SUM(complaints_closed) >= 500 ORDER BY closure_rate ASC LIMIT 30
    """
    try:
        result = con.execute(query).df()
        print(f"  q11_slow_closure_firms: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q11_slow_closure_firms: ERROR - {e}")
        return pd.DataFrame()

def q12_decumulation_pensions_risk(con):
    """
    Decumulation and pensions uphold rates (Consumer Duty red flag product).
    
    SQL
    ---
    SELECT firm_name, period, SUM(complaints_opened) AS opened, SUM(upheld)*1.0/NULL
    IF(SUM(complaints_closed),0) AS uphold_rate FROM complaints WHERE product_group=
    'Decumulation and pensions' GROUP BY firm_name, period HAVING SUM(complaints_closed) >= 50 ORDER BY uphold_rate DESC
    """
    query = """
    SELECT firm_name, period, SUM(complaints_opened) AS opened, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS uphold_rate FROM complaints WHERE product_group='Decumulation and pensions' GROUP BY firm_name, period HAVING SUM(complaints_closed) >= 50 ORDER BY uphold_rate DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q12_decumulation_pensions_risk: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q12_decumulation_pensions_risk: ERROR - {e}")
        return pd.DataFrame()

def q13_firm_product_heatmap(con):
    """
    Firm x product complaint heatmap for 2025H2.
    
    SQL
    ---
    SELECT firm_name, product_group, SUM(complaints_opened) AS opened, SUM(upheld)*1
    .0/NULLIF(SUM(complaints_closed),0) AS uphold_rate FROM complaints WHERE period=
    '2025H2' GROUP BY firm_name, product_group ORDER BY firm_name, opened DESC
    """
    query = """
    SELECT firm_name, product_group, SUM(complaints_opened) AS opened, SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) AS uphold_rate FROM complaints WHERE period='2025H2' GROUP BY firm_name, product_group ORDER BY firm_name, opened DESC
    """
    try:
        result = con.execute(query).df()
        print(f"  q13_firm_product_heatmap: {len(result):,} rows")
        return result
    except Exception as e:
        print(f"  q13_firm_product_heatmap: ERROR - {e}")
        return pd.DataFrame()


def load_data():
    clean = DATA_PROCESSED / "complaints_clean.csv"
    if not clean.exists():
        raise FileNotFoundError(f"Run 01_ingest_and_clean.py first. Missing: {clean}")
    df = pd.read_csv(clean)
    print(f"  Loaded: {len(df):,} rows")
    return df


def agg_firm_period(df):
    agg = (df.groupby(["firm_name","period"], as_index=False)
           .agg(opened=("complaints_opened","sum"), closed=("complaints_closed","sum"),
                closed_8wk=("closed_within_8_weeks","sum"), upheld_n=("upheld","sum")))
    agg["uphold_rate"]    = np.where(agg["closed"]>0, agg["upheld_n"]/agg["closed"],    np.nan)
    agg["closure_8wk_rt"] = np.where(agg["closed"]>0, agg["closed_8wk"]/agg["closed"], np.nan)
    agg["period_order"]   = agg["period"].map({p:i for i,p in enumerate(PERIODS)})
    return agg.sort_values(["firm_name","period_order"]).reset_index(drop=True)


def firm_cost_profile(opened, uphold_rate):
    """Compute detailed cost breakdown for a single firm-period."""
    upheld  = opened * uphold_rate if not math.isnan(uphold_rate) else opened * 0.35
    handling = opened * COST_HANDLING
    fos      = opened * COST_FOS_RATE * COST_FOS_FEE
    redress  = upheld * COST_REDRESS
    total    = handling + fos + redress
    return {
        "handling_gbp": round(handling, 0),
        "fos_gbp":      round(fos, 0),
        "redress_gbp":  round(redress, 0),
        "total_gbp":    round(total, 0),
        "cost_per_complaint": round(total/opened, 2) if opened > 0 else 0,
    }


def cd_rag(uphold_rate, closure_8wk_rt):
    """Simple Consumer Duty RAG rating for a firm-period."""
    if pd.isna(uphold_rate): return "UNKNOWN"
    if uphold_rate >= 0.50:  return "RED"
    if uphold_rate >= 0.35:  return "AMBER"
    if pd.isna(closure_8wk_rt) or closure_8wk_rt < 0.60: return "AMBER"
    return "GREEN"


def trend_direction(values):
    """OLS slope direction for a list of values."""
    n = len(values)
    if n < 2: return "STABLE"
    x = list(range(n))
    xm = sum(x)/n; ym = sum(values)/n
    num = sum((xi-xm)*(yi-ym) for xi,yi in zip(x,values))
    den = sum((xi-xm)**2 for xi in x)
    if den == 0: return "STABLE"
    slope = num/den
    mean_v = sum(values)/n
    pct = slope/mean_v*100 if mean_v > 0 else 0
    if pct >  5: return "INCREASING"
    if pct < -5: return "DECREASING"
    return "STABLE"


def generate_firm_profile(firm_name, agg, df_clean):
    """Generate a complete analytical profile for one firm."""
    firm_agg  = agg[agg["firm_name"]==firm_name].sort_values("period_order")
    firm_prod = df_clean[(df_clean["firm_name"]==firm_name)].copy() if "firm_name" in df_clean.columns else pd.DataFrame()
    if len(firm_agg) == 0:
        return {"firm_name": firm_name, "error": "no data found"}
    latest    = firm_agg.iloc[-1]
    vols      = firm_agg["opened"].tolist()
    upholds   = firm_agg["uphold_rate"].tolist()
    closures  = firm_agg["closure_8wk_rt"].tolist()
    cost      = firm_cost_profile(latest["opened"], latest["uphold_rate"] if not pd.isna(latest["uphold_rate"]) else 0.35)
    rag_rating = cd_rag(latest["uphold_rate"], latest["closure_8wk_rt"])
    vol_trend = trend_direction(vols)
    pct_chg   = (vols[-1]-vols[0])/vols[0]*100 if len(vols)>1 and vols[0]>0 else 0
    prod_mix  = {}
    if len(firm_prod) > 0 and "product_group" in firm_prod.columns:
        latest_prod = firm_prod[firm_prod["period"]=="2025H2"] if "period" in firm_prod.columns else firm_prod
        total_p = latest_prod["complaints_opened"].sum() if "complaints_opened" in latest_prod.columns else 0
        if total_p > 0:
            for pg, grp in latest_prod.groupby("product_group"):
                v = grp["complaints_opened"].sum()
                prod_mix[pg] = {"volume": int(v), "share": round(v/total_p*100, 1)}
    return {
        "firm_name":           firm_name,
        "periods_present":     firm_agg["period"].tolist(),
        "latest_period":       latest["period"],
        "latest_opened":       int(latest["opened"]),
        "latest_uphold_rate":  round(float(latest["uphold_rate"]),4) if not pd.isna(latest["uphold_rate"]) else None,
        "latest_closure_8wk":  round(float(latest["closure_8wk_rt"]),4) if not pd.isna(latest["closure_8wk_rt"]) else None,
        "cd_rag":               rag_rating,
        "volume_trend":         vol_trend,
        "pct_change_2024h1_2025h2": round(pct_chg, 2),
        "period_volumes":       {r["period"]: int(r["opened"]) for _,r in firm_agg.iterrows()},
        "period_uphold_rates":  {r["period"]: round(float(r["uphold_rate"]),4) if not pd.isna(r["uphold_rate"]) else None for _,r in firm_agg.iterrows()},
        "period_closure_rates": {r["period"]: round(float(r["closure_8wk_rt"]),4) if not pd.isna(r["closure_8wk_rt"]) else None for _,r in firm_agg.iterrows()},
        "cost_profile":         cost,
        "product_mix":          prod_mix,
    }


def run_firm_profiles(df, top_n=50):
    """Generate profiles for the top-N firms by 2025H2 volume."""
    print("
" + "="*70)
    print(f"FIRM DEEP DIVE PROFILES — TOP {top_n} FIRMS")
    print("="*70)
    agg = agg_firm_period(df)
    latest = agg[agg["period"]=="2025H2"].sort_values("opened",ascending=False)
    top_firms = latest.head(top_n)["firm_name"].tolist()
    profiles = []
    for firm in top_firms:
        p = generate_firm_profile(firm, agg, df)
        profiles.append(p)
        rag   = p.get("cd_rag","?")
        trend = p.get("volume_trend","?")
        vol   = p.get("latest_opened",0)
        ur    = p.get("latest_uphold_rate")
        ur_s  = f"{ur:.1%}" if ur is not None else "N/A"
        print(f"  {firm:<42} vol={vol:>8,}  uphold={ur_s:>7}  {rag:<7}  {trend}")
    return profiles, agg


def save_profiles(profiles):
    out = DATA_OUTPUTS / "firm_profiles_top50.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, default=str)
    print(f"  Saved: {out}  ({len(profiles)} firm profiles)")
    flat = []
    for p in profiles:
        row = {
            "firm_name":     p.get("firm_name"),
            "latest_opened": p.get("latest_opened"),
            "uphold_rate":   p.get("latest_uphold_rate"),
            "closure_8wk":   p.get("latest_closure_8wk"),
            "cd_rag":        p.get("cd_rag"),
            "vol_trend":     p.get("volume_trend"),
            "pct_change":    p.get("pct_change_2024h1_2025h2"),
            "total_cost_gbp": p.get("cost_profile",{}).get("total_gbp"),
        }
        flat.append(row)
    df_flat = pd.DataFrame(flat)
    csv_out = DATA_OUTPUTS / "firm_profiles_top50.csv"
    df_flat.to_csv(csv_out, index=False)
    print(f"  Saved: {csv_out}")


def generate_rag_summary(profiles):
    """Print Consumer Duty RAG summary for profiled firms."""
    print("
" + "="*70)
    print("CONSUMER DUTY RAG SUMMARY")
    print("="*70)
    from collections import Counter
    rag_counts = Counter(p.get("cd_rag","UNKNOWN") for p in profiles)
    total = len(profiles)
    for rag in ["GREEN","AMBER","RED","UNKNOWN"]:
        n = rag_counts.get(rag,0)
        pct = n/total*100 if total>0 else 0
        bar = chr(9608)*int(pct/2)
        print(f"  {rag:<10} {n:>4} ({pct:>5.1f}%) {bar}")
    print("")
    trend_counts = Counter(p.get("volume_trend","?") for p in profiles)
    print("  Volume trend summary:")
    for t in ["INCREASING","STABLE","DECREASING"]:
        n = trend_counts.get(t,0)
        print(f"    {t:<12} {n:>4} firms")


def cost_league_table(profiles):
    """Print top-20 highest cost exposure firms."""
    print("
" + "="*70)
    print("COST EXPOSURE LEAGUE TABLE (TOP 20)")
    print("="*70)
    sorted_p = sorted(profiles, key=lambda p: p.get("cost_profile",{}).get("total_gbp",0), reverse=True)
    print(f"  {'Firm':<42} {'Total GBP':>14} {'Handling':>12} {'FOS':>10} {'Redress':>10} {'CD RAG':>8}")
    print("  "+"-"*100)
    for p in sorted_p[:20]:
        c = p.get("cost_profile",{})
        t = c.get("total_gbp",0)
        h = c.get("handling_gbp",0)
        fo = c.get("fos_gbp",0)
        r = c.get("redress_gbp",0)
        print(f"  {p['firm_name']:<42} GBP {t:>9,.0f}  {h:>11,.0f}  {fo:>9,.0f}  {r:>9,.0f}  {p.get('cd_rag','?'):>8}")


def main():
    print("
UK Banking Complaints — Firm Deep Dive Profiles")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    df = load_data()
    profiles, agg = run_firm_profiles(df, top_n=50)
    generate_rag_summary(profiles)
    cost_league_table(profiles)
    save_profiles(profiles)
    print("
Firm deep dive profiles complete.")


if __name__ == "__main__":
    main()