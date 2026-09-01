#!/usr/bin/env python3
# 06_data_quality_validation_report.py
# Data quality checks, cross-period validation, reconciliation and HTML report
# for the UK Retail Banking Complaints Benchmark.
# Author: Gagandeep Kapoor

import os, json, math, warnings, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BASE           = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE / "data" / "processed"
DATA_OUTPUTS   = BASE / "data" / "outputs"
DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
PERIODS = ["2024H1","2024H2","2025H1","2025H2"]
PRODUCT_GROUPS = ["Banking and credit cards","Home finance",
    "Insurance and pure protection","Decumulation and pensions","Investments"]
FCA_TOTALS = {"2024H1":1_774_139,"2024H2":1_698_000,"2025H1":1_670_000,"2025H2":1_652_438}
COST_HANDLING=200.0; COST_FOS_FEE=650.0; COST_FOS_RATE=0.08; COST_REDRESS=300.0
SIZE_BANDS={"Large (>50k)":(50000,1e9),"Medium (10-50k)":(10000,50000),
    "Small (1-10k)":(1000,10000),"Micro (<1k)":(0,1000)}
def _load_data():
    print("=" * 70)
    print("SECTION 1 — DATA LOADING AND VALIDATION")
    print("=" * 70)
    clean_path = DATA_PROCESSED / "complaints_clean.csv"
    if not clean_path.exists():
        raise FileNotFoundError(f"Run 01_ingest_and_clean.py first. Missing: {clean_path}")
    df = pd.read_csv(clean_path)
    print(f"  Loaded: {len(df):,} rows, {df.shape[1]} columns")
    if "period" in df.columns:
        for p, g in df.groupby("period"):
            print(f"    {p}: {len(g):,} firm-product rows, {g['firm_name'].nunique()} firms")
    required = ["firm_name","period","product_group","complaints_opened",
                "complaints_closed","closed_within_8_weeks","upheld"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  WARNING — missing columns: {missing}")
    else:
        print(f"  Schema OK — all {len(required)} required columns present")
    return df


# ===========================================================================
# 2. Firm rankings
# ===========================================================================

def _agg((df):
    agg = (
        df.groupby(["firm_name","period"], as_index=False)
        .agg(
            opened     =("complaints_opened",     "sum"),
            closed     =("complaints_closed",     "sum"),
            closed_8wk =("closed_within_8_weeks", "sum"),
            upheld_n   =("upheld",                "sum"),
        )
    )
    agg["uphold_rate"]    = np.where(agg["closed"]>0, agg["upheld_n"]/agg["closed"],    np.nan)
    agg["closure_8wk_rt"] = np.where(agg["closed"]>0, agg["closed_8wk"]/agg["closed"], np.nan)
    agg["size_band"]      = agg["opened"].apply(assign_size_band)
    return agg


def assign_size_band_dq((vol):
    for label, (lo, hi) in SIZE_BANDS.items():
        if lo <= vol < hi:
            return label
    return "Unknown"


def print_firm_rankings(agg, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 2 — FIRM RANKINGS  (" + period + ")")
    print("=" * 70)
    sub = agg[agg["period"]==period].copy()

    top_vol = sub.sort_values("opened", ascending=False).head(20).reset_index(drop=True)
    print("\n  Top 20 firms by complaints opened:")
    print(f"  {'#':>3}  {'Firm':<40} {'Opened':>10} {'Uphold%':>9} {'8wk%':>8}")
    print("  " + "-" * 74)
    for i, row in top_vol.iterrows():
        u = f"{row['uphold_rate']:.1%}" if not pd.isna(row["uphold_rate"]) else "N/A"
        c = f"{row['closure_8wk_rt']:.1%}" if not pd.isna(row["closure_8wk_rt"]) else "N/A"
        print(f"  {i+1:>3}  {row['firm_name']:<40} {row['opened']:>10,.0f} {u:>9} {c:>8}")

    # Highest uphold (min 500 complaints)
    top_uphold = sub[sub["opened"]>=500].sort_values("uphold_rate", ascending=False).head(15).reset_index(drop=True)
    print("\n  Top 15 highest uphold rate firms (min 500 complaints):")
    print(f"  {'#':>3}  {'Firm':<40} {'Opened':>10} {'Uphold%':>9}")
    print("  " + "-" * 66)
    for i, row in top_uphold.iterrows():
        u = f"{row['uphold_rate']:.1%}" if not pd.isna(row["uphold_rate"]) else "N/A"
        print(f"  {i+1:>3}  {row['firm_name']:<40} {row['opened']:>10,.0f} {u:>9}")

    # Slowest closure
    slow = sub[sub["opened"]>=500].sort_values("closure_8wk_rt", ascending=True).head(15).reset_index(drop=True)
    print("\n  Top 15 slowest 8-week closure firms (min 500 complaints):")
    print(f"  {'#':>3}  {'Firm':<40} {'Opened':>10} {'8wk%':>8}")
    print("  " + "-" * 65)
    for i, row in slow.iterrows():
        c = f"{row['closure_8wk_rt']:.1%}" if not pd.isna(row["closure_8wk_rt"]) else "N/A"
        print(f"  {i+1:>3}  {row['firm_name']:<40} {row['opened']:>10,.0f} {c:>8}")


# ===========================================================================
# 3. Period-over-period trends
# ===========================================================================

def compute_market_totals(df):
    print("\n" + "=" * 70)
    print("SECTION 3 — PERIOD-OVER-PERIOD TRENDS")
    print("=" * 70)
    market = (
        df.groupby("period", as_index=False)
        .agg(
            total_opened    =("complaints_opened",     "sum"),
            total_closed    =("complaints_closed",     "sum"),
            total_closed_8w =("closed_within_8_weeks", "sum"),
            total_upheld    =("upheld",                "sum"),
            n_firms         =("firm_name",             "nunique"),
        )
    )
    market["uphold_rate"]    = market["total_upheld"]    / market["total_closed"]
    market["closure_8wk_rt"] = market["total_closed_8w"] / market["total_closed"]
    market["period_order"]   = market["period"].map({p:i for i,p in enumerate(PERIODS)})
    market = market.sort_values("period_order").reset_index(drop=True)

    print(f"\n  {'Period':<10} {'Opened':>12} {'Change':>8} {'Uphold%':>9} {'8wk%':>8} {'Firms':>7}")
    print("  " + "-" * 58)
    for i, row in market.iterrows():
        chg = "—" if i==0 else f"{(row['total_opened']-market.loc[i-1,'total_opened'])/market.loc[i-1,'total_opened']*100:+.1f}%"
        print(f"  {row['period']:<10} {row['total_opened']:>12,.0f} {chg:>8} {row['uphold_rate']:>8.1%} {row['closure_8wk_rt']:>8.1%} {row['n_firms']:>7}")
    return market


def compute_firm_trends(agg):
    period_map = {p:i for i,p in enumerate(PERIODS)}
    agg = agg.copy()
    agg["period_n"] = agg["period"].map(period_map)
    firms_4 = agg.groupby("firm_name")["period"].nunique()
    firms_4 = firms_4[firms_4==4].index.tolist()
    results = []
    for firm in firms_4:
        sub = agg[agg["firm_name"]==firm].sort_values("period_n")
        x = sub["period_n"].values.astype(float)
        y = sub["opened"].values.astype(float)
        xm, ym = x.mean(), y.mean()
        denom = np.sum((x-xm)**2)
        slope = np.sum((x-xm)*(y-ym))/denom if denom>0 else 0.0
        pct = (y[-1]-y[0])/y[0]*100 if y[0]>0 else np.nan
        results.append({"firm_name":firm,"slope":slope,"pct_change":pct,"avg_volume":ym,"latest_vol":y[-1]})
    return pd.DataFrame(results).sort_values("pct_change", ascending=False)


def print_trend_leaders(trend_df, n=10):
    print("\n  Fastest-growing firms (2024H1 → 2025H2):")
    for _, row in trend_df.nlargest(n,"pct_change").iterrows():
        print(f"    {row['firm_name']:<42} {row['pct_change']:>+7.1f}%  avg={row['avg_volume']:,.0f}")
    print("\n  Fastest-declining firms:")
    for _, row in trend_df.nsmallest(n,"pct_change").iterrows():
        print(f"    {row['firm_name']:<42} {row['pct_change']:>+7.1f}%  avg={row['avg_volume']:,.0f}")


# ===========================================================================
# 4. Peer group benchmarking
# ===========================================================================

def compute_peer_benchmarks(agg, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 4 — PEER GROUP BENCHMARKING  (" + period + ")")
    print("=" * 70)
    sub = agg[agg["period"]==period].copy()
    peer = (
        sub.groupby("size_band", as_index=False)
        .agg(
            n_firms       =("firm_name",      "count"),
            median_vol    =("opened",         "median"),
            median_uphold =("uphold_rate",    "median"),
            median_8wk    =("closure_8wk_rt", "median"),
            p25_uphold    =("uphold_rate",    lambda x: x.quantile(0.25)),
            p75_uphold    =("uphold_rate",    lambda x: x.quantile(0.75)),
            p25_8wk       =("closure_8wk_rt", lambda x: x.quantile(0.25)),
            p75_8wk       =("closure_8wk_rt", lambda x: x.quantile(0.75)),
        )
    )
    print(f"\n  {'Band':<22} {'N':>5} {'Med vol':>10} {'Med uphold':>11} {'IQR uphold':>13} {'Med 8wk':>9}")
    print("  " + "-" * 74)
    for _, row in peer.iterrows():
        print(f"  {row['size_band']:<22} {row['n_firms']:>5} {row['median_vol']:>10,.0f}"
              f" {row['median_uphold']:>10.1%}  {row['p25_uphold']:.1%}-{row['p75_uphold']:.1%}"
              f" {row['median_8wk']:>9.1%}")

    # Tukey outliers within band
    outliers = []
    for band, grp in sub.groupby("size_band"):
        q1 = grp["uphold_rate"].quantile(0.25)
        q3 = grp["uphold_rate"].quantile(0.75)
        fence = q3 + 1.5*(q3-q1)
        out = grp[grp["uphold_rate"]>fence].copy()
        out["peer_fence"] = fence
        out["size_band"]  = band
        outliers.append(out)
    if outliers:
        df_out = pd.concat(outliers).sort_values("uphold_rate", ascending=False)
        print(f"\n  Peer outliers (uphold > Tukey fence):")
        for _, row in df_out.head(20).iterrows():
            print(f"    {row['firm_name']:<42} {row['uphold_rate']:.1%}  fence={row['peer_fence']:.1%}  [{row['size_band']}]")
        return peer, df_out
    return peer, pd.DataFrame()


# ===========================================================================
# 5. Consumer Duty compliance scoring
# ===========================================================================

def score_uphold(r):
    if pd.isna(r): return 50.0
    if r >= CD_UPHOLD_RED:    return max(0.0, 100.0*(1.0-r))
    if r >= CD_UPHOLD_AMBER:  return 50.0+50.0*(CD_UPHOLD_RED-r)/(CD_UPHOLD_RED-CD_UPHOLD_AMBER)
    return 100.0 - r*100.0

def score_closure(r):
    if pd.isna(r): return 50.0
    return min(100.0, r*100.0)

def compute_cd_scores(agg, trend_df, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 5 — CONSUMER DUTY COMPLIANCE SCORING")
    print("=" * 70)
    sub = agg[agg["period"]==period].copy()
    peer_med = sub.groupby("size_band")["uphold_rate"].median().to_dict()
    trend_map = trend_df.set_index("firm_name")["pct_change"].to_dict()
    rows = []
    for _, row in sub.iterrows():
        u = score_uphold(row["uphold_rate"])
        c = score_closure(row["closure_8wk_rt"])
        pct = trend_map.get(row["firm_name"], 0.0)
        if pd.isna(pct): pct = 0.0
        t = min(100.0, max(0.0, 50.0 - pct))
        diff = peer_med.get(row["size_band"],0.3) - (row["uphold_rate"] if not pd.isna(row["uphold_rate"]) else peer_med.get(row["size_band"],0.3))
        p = min(100.0, max(0.0, 50.0 + diff*200.0))
        comp = (CD_WEIGHTS["uphold_rate_score"]*u + CD_WEIGHTS["closure_8wk_score"]*c +
                CD_WEIGHTS["volume_trend_score"]*t + CD_WEIGHTS["peer_relative_score"]*p)
        rag = "GREEN" if comp>=70 else ("AMBER" if comp>=45 else "RED")
        rows.append({"firm_name":row["firm_name"],"size_band":row["size_band"],"opened":row["opened"],
                     "uphold_rate":row["uphold_rate"],"closure_8wk_rt":row["closure_8wk_rt"],
                     "u_score":round(u,1),"c_score":round(c,1),"t_score":round(t,1),"p_score":round(p,1),
                     "cd_score":round(comp,1),"cd_rag":rag})
    df_cd = pd.DataFrame(rows).sort_values("cd_score", ascending=False).reset_index(drop=True)
    rag_c = df_cd["cd_rag"].value_counts()
    print(f"\n  CD compliance RAG ({period}):")
    for rag in ["GREEN","AMBER","RED"]:
        n = rag_c.get(rag,0)
        print(f"    {rag:<8}: {n:>4} firms ({n/len(df_cd)*100:.1f}%)")
    print("\n  Top 10 best performers:")
    for _, row in df_cd.head(10).iterrows():
        print(f"    {row['firm_name']:<42} score={row['cd_score']:>5.1f}  {row['cd_rag']}")
    print("\n  Bottom 10 highest risk:")
    for _, row in df_cd.tail(10).iterrows():
        print(f"    {row['firm_name']:<42} score={row['cd_score']:>5.1f}  {row['cd_rag']}")
    return df_cd


# ===========================================================================
# 6. Product deep dive
# ===========================================================================

def compute_product_benchmarks(df):
    print("\n" + "=" * 70)
    print("SECTION 6 — PRODUCT-LEVEL DEEP DIVE")
    print("=" * 70)
    prod = (
        df.groupby(["product_group","period"], as_index=False)
        .agg(opened=("complaints_opened","sum"), closed=("complaints_closed","sum"),
             closed_8wk=("closed_within_8_weeks","sum"), upheld_n=("upheld","sum"),
             n_firms=("firm_name","nunique"))
    )
    prod["uphold_rate"]    = prod["upheld_n"]   / prod["closed"]
    prod["closure_8wk_rt"] = prod["closed_8wk"] / prod["closed"]
    prod["period_order"]   = prod["period"].map({p:i for i,p in enumerate(PERIODS)})
    prod = prod.sort_values(["product_group","period_order"]).reset_index(drop=True)

    latest = prod[prod["period"]=="2025H2"].copy()
    total  = latest["opened"].sum()
    latest["share"] = latest["opened"]/total
    print("\n  Market share by product group (2025H2):")
    for _, row in latest.sort_values("opened",ascending=False).iterrows():
        bar = "█" * int(row["share"]*40)
        print(f"    {row['product_group']:<38} {bar:<40} {row['share']:.1%}")

    print(f"\n  Uphold rates by product group (all periods):")
    header = "  " + f"{'Product':<38} " + "  ".join(f"{p:>8}" for p in PERIODS)
    print(header)
    print("  " + "-" * 72)
    for pg in PRODUCT_GROUPS:
        sub = prod[prod["product_group"]==pg]
        rates = []
        for p in PERIODS:
            r = sub[sub["period"]==p]["uphold_rate"]
            rates.append(f"{r.values[0]:.1%}" if len(r)>0 else "  N/A  ")
        print(f"  {pg:<38} " + "  ".join(f"{r:>8}" for r in rates))

    # Trend alerts
    alerts = []
    for pg in prod["product_group"].unique():
        sub = prod[prod["product_group"]==pg].sort_values("period_order")
        if len(sub)<2: continue
        f,l = sub.iloc[0]["uphold_rate"], sub.iloc[-1]["uphold_rate"]
        if pd.isna(f) or pd.isna(l): continue
        delta = l - f
        if abs(delta) > 0.05:
            alerts.append({"product_group":pg,"uphold_2024H1":f,"uphold_2025H2":l,
                           "delta_pp":delta*100,"direction":"DETERIORATING" if delta>0 else "IMPROVING"})
    if alerts:
        df_alerts = pd.DataFrame(alerts).sort_values("delta_pp",ascending=False)
        print("\n  Product trend alerts (>5pp change):")
        for _, row in df_alerts.iterrows():
            print(f"    {row['product_group']:<38} {row['uphold_2024H1']:.1%} -> {row['uphold_2025H2']:.1%}  ({row['delta_pp']:+.1f}pp)  [{row['direction']}]")
    return prod


# ===========================================================================
# 7. Statistical significance testing
# ===========================================================================

def chi_square_product_uphold(df, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 7 — STATISTICAL SIGNIFICANCE TESTING")
    print("=" * 70)
    sub = df[df["period"]==period] if "period" in df.columns else df
    grp = (sub.groupby("product_group")
           .agg(upheld=("upheld","sum"), closed=("complaints_closed","sum"))
           .reset_index())
    grp["not_upheld"] = grp["closed"] - grp["upheld"]
    grp = grp[(grp["upheld"]>0)&(grp["not_upheld"]>0)]
    obs = grp[["upheld","not_upheld"]].values.astype(float)
    rt  = obs.sum(axis=1, keepdims=True)
    ct  = obs.sum(axis=0, keepdims=True)
    exp = rt*ct/obs.sum()
    chi2 = float(np.sum((obs-exp)**2/exp))
    dof  = (obs.shape[0]-1)*(obs.shape[1]-1)
    z = (chi2/dof)**(1/3)
    mu = 1 - 2/(9*dof)
    sig = math.sqrt(2/(9*dof))
    p = 0.5*math.erfc((z-mu)/(sig*math.sqrt(2)))
    print(f"\n  Chi-square: uphold rate ~ product group ({period})")
    print(f"    chi2={chi2:,.2f}  dof={dof}  p={p:.2e}")
    print(f"    Result: {'HIGHLY SIGNIFICANT' if p<0.001 else 'SIGNIFICANT' if p<0.05 else 'NOT SIGNIFICANT'}")
    return {"chi2":chi2,"dof":dof,"p":p}


def period_z_test(market):
    if len(market)<4: return
    r1 = market[market["period"]=="2024H1"].iloc[0]
    r2 = market[market["period"]=="2025H2"].iloc[0]
    n1,n2 = r1["total_closed"],r2["total_closed"]
    x1,x2 = r1["total_upheld"],r2["total_upheld"]
    p1,p2 = x1/n1, x2/n2
    pp = (x1+x2)/(n1+n2)
    se = math.sqrt(pp*(1-pp)*(1/n1+1/n2))
    z  = (p1-p2)/se if se>0 else 0.0
    pv = 2*(1-0.5*math.erfc(-abs(z)/math.sqrt(2)))
    print(f"\n  Two-proportion z-test: uphold rate 2024H1 vs 2025H2")
    print(f"    2024H1={p1:.3%}  2025H2={p2:.3%}  delta={( p2-p1)*100:+.3f}pp  z={z:.4f}  p={pv:.4e}")
    print(f"    Result: {'HIGHLY SIGNIFICANT' if pv<0.001 else 'SIGNIFICANT' if pv<0.05 else 'NOT SIGNIFICANT'}")


# ===========================================================================
# 8. Market concentration
# ===========================================================================

def compute_concentration(agg, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 8 — MARKET CONCENTRATION")
    print("=" * 70)
    sub = agg[agg["period"]==period].sort_values("opened",ascending=False).copy()
    total = sub["opened"].sum()
    sub["share"] = sub["opened"]/total
    hhi = float((sub["share"]**2).sum()*10_000)
    print(f"\n  HHI ({period}): {hhi:.1f}  -> {'COMPETITIVE' if hhi<1500 else 'MODERATE' if hhi<2500 else 'CONCENTRATED'}")
    sub["cumshare"] = sub["opened"].cumsum()/total
    for n in [1,4,10,20,50]:
        sh = sub.head(n)["opened"].sum()/total
        print(f"    CR{n:<3}: top {n:<3} firms = {sh:.1%} of all complaints")
    return hhi


# ===========================================================================
# 9. Anomaly detection
# ===========================================================================

def detect_anomalies(agg, period="2025H2", z_thresh=3.0):
    print("\n" + "=" * 70)
    print("SECTION 9 — ANOMALY DETECTION")
    print("=" * 70)
    sub = agg[agg["period"]==period].copy()
    anomalies = []
    for band, grp in sub.groupby("size_band"):
        valid = grp["uphold_rate"].dropna()
        if len(valid)<3: continue
        mu,sd = valid.mean(), valid.std()
        if sd==0: continue
        for _, row in grp.iterrows():
            if pd.isna(row["uphold_rate"]): continue
            z = (row["uphold_rate"]-mu)/sd
            if abs(z)>=z_thresh:
                anomalies.append({"firm_name":row["firm_name"],"size_band":band,
                                   "opened":row["opened"],"uphold_rate":row["uphold_rate"],
                                   "z_score":z,"band_mean":mu,"band_std":sd})
    if anomalies:
        df_a = pd.DataFrame(anomalies).sort_values("z_score",ascending=False)
        print(f"\n  Z-score anomalies (|z|>={z_thresh}):")
        for _,row in df_a.iterrows():
            print(f"    {row['firm_name']:<42} uphold={row['uphold_rate']:.1%}  z={row['z_score']:+.2f}  mean={row['band_mean']:.1%}")
        return df_a
    print(f"  No anomalies at z>={z_thresh}.")
    return pd.DataFrame()


def detect_spikes(agg, thresh=50.0):
    period_map = {p:i for i,p in enumerate(PERIODS)}
    agg = agg.copy()
    agg["pn"] = agg["period"].map(period_map)
    spikes=[]
    for firm,grp in agg.groupby("firm_name"):
        grp=grp.sort_values("pn").reset_index(drop=True)
        for i in range(1,len(grp)):
            p,c = grp.loc[i-1,"opened"], grp.loc[i,"opened"]
            if p==0: continue
            pct = (c-p)/p*100
            if pct>=thresh:
                spikes.append({"firm_name":firm,"from":grp.loc[i-1,"period"],"to":grp.loc[i,"period"],
                               "prev":p,"curr":c,"pct_change":pct})
    if spikes:
        df_s=pd.DataFrame(spikes).sort_values("pct_change",ascending=False)
        print(f"\n  Volume spikes (>{thresh:.0f}% period-on-period):")
        for _,row in df_s.head(15).iterrows():
            print(f"    {row['firm_name']:<42} {row['from']} -> {row['to']}: {row['prev']:,.0f} -> {row['curr']:,.0f} ({row['pct_change']:+.1f}%)")
        return df_s
    print(f"  No spikes >{thresh:.0f}% detected.")
    return pd.DataFrame()


# ===========================================================================
# 10. Cost scenario analysis
# ===========================================================================

def run_scenario_analysis(market):
    print("\n" + "=" * 70)
    print("SECTION 10 — COST SCENARIO ANALYSIS")
    print("=" * 70)
    row = market[market["period"]=="2025H2"]
    if len(row)==0:
        print("  2025H2 not available.")
        return
    bv = float(row["total_opened"].iloc[0])
    bu = float(row["uphold_rate"].iloc[0])
    print(f"\n  Baseline: {bv:,.0f} complaints, {bu:.1%} uphold rate")
    def cost(v,u): return v*COST_HANDLING + v*COST_FOS_RATE*COST_FOS_FEE + v*u*COST_REDRESS
    base_cost = cost(bv,bu)
    print(f"  Baseline cost: GBP {base_cost/1e9:.4f}bn per half-year")
    print(f"\n  {'Scenario':<52} {'Vol':>10} {'Uphold':>8} {'Cost GBP':>14} {'Delta':>10}")
    print("  " + "-" * 98)
    for k,sc in SCENARIOS.items():
        v = bv*(1-sc["vol_delta"])
        u = max(0.0, bu-sc["uphold_delta"])
        c = cost(v,u)
        delta = c - base_cost
        print(f"  {sc['label']:<52} {v:>10,.0f} {u:>7.1%}  GBP {c/1e9:>8.4f}bn {delta/1e6:>+9.0f}m")


# ===========================================================================
# 11. Regulatory risk scoring
# ===========================================================================

def compute_reg_risk(cd_scores, trend_df, outlier_df):
    print("\n" + "=" * 70)
    print("SECTION 11 — REGULATORY RISK SCORING")
    print("=" * 70)
    risk = cd_scores.copy()
    risk["cd_risk"]           = 100.0 - risk["cd_score"]
    trend_map = trend_df.set_index("firm_name")["pct_change"].fillna(0).to_dict()
    risk["vol_trend_pct"]     = risk["firm_name"].map(trend_map).fillna(0.0)
    risk["vol_trend_risk"]    = risk["vol_trend_pct"].clip(-50,50).apply(lambda x: min(100,max(0,50+x)))
    risk["closure_speed_risk"]= (1.0-risk["closure_8wk_rt"].fillna(0.75))*100.0
    out_firms = set(outlier_df["firm_name"].tolist()) if len(outlier_df)>0 else set()
    risk["peer_outlier_risk"] = risk["firm_name"].apply(lambda x: 70.0 if x in out_firms else 30.0)
    max_vol = risk["opened"].max()
    risk["volume_risk"]       = (risk["opened"]/max_vol*100).clip(0,100)
    risk["reg_risk_score"]    = (
        REG_WEIGHTS["cd_risk"]            * risk["cd_risk"] +
        REG_WEIGHTS["vol_trend_risk"]     * risk["vol_trend_risk"] +
        REG_WEIGHTS["closure_speed_risk"] * risk["closure_speed_risk"] +
        REG_WEIGHTS["peer_outlier_risk"]  * risk["peer_outlier_risk"] +
        REG_WEIGHTS["volume_risk"]        * risk["volume_risk"]
    )
    risk["reg_risk_score"] = risk["reg_risk_score"].round(1)
    risk["reg_rag"] = risk["reg_risk_score"].apply(lambda s: "HIGH" if s>=65 else ("MEDIUM" if s>=40 else "LOW"))
    risk = risk.sort_values("reg_risk_score", ascending=False).reset_index(drop=True)
    rag_c = risk["reg_rag"].value_counts()
    print(f"\n  Regulatory risk RAG:")
    for rag in ["HIGH","MEDIUM","LOW"]:
        n=rag_c.get(rag,0)
        print(f"    {rag:<8}: {n:>4} firms ({n/len(risk)*100:.1f}%)")
    print("\n  Top 15 highest regulatory risk:")
    for _,row in risk.head(15).iterrows():
        print(f"    {row['firm_name']:<42} risk={row['reg_risk_score']:>5.1f}  {row['reg_rag']}  uphold={row['uphold_rate']:.1%}")
    return risk


# ===========================================================================
# 12. Executive summary
# ===========================================================================

def generate_executive_summary(market, agg, cd_scores, risk_df, period="2025H2"):
    print("\n" + "=" * 70)
    print("SECTION 12 — EXECUTIVE SUMMARY")
    print("=" * 70)
    lm = market[market["period"]==period].iloc[0]
    em = market[market["period"]=="2024H1"].iloc[0]
    vol_chg   = (lm["total_opened"]-em["total_opened"])/em["total_opened"]*100
    uphold_chg = (lm["uphold_rate"]-em["uphold_rate"])*100
    top_firm   = agg[agg["period"]==period].sort_values("opened",ascending=False).iloc[0]
    base_cost  = (lm["total_opened"]*COST_HANDLING + lm["total_opened"]*COST_FOS_RATE*COST_FOS_FEE +
                  lm["total_upheld"]*COST_REDRESS)
    summary = {
        "generated_at":              datetime.now().isoformat(),
        "period":                    period,
        "market_total":              int(lm["total_opened"]),
        "vol_change_pct":            round(vol_chg,1),
        "uphold_rate_pct":           round(float(lm["uphold_rate"])*100,2),
        "uphold_change_pp":          round(uphold_chg,2),
        "closure_8wk_pct":           round(float(lm["closure_8wk_rt"])*100,2),
        "n_firms":                   int(len(cd_scores)),
        "top_firm":                  top_firm["firm_name"],
        "top_firm_volume":           int(top_firm["opened"]),
        "cd_red_firms":              int((cd_scores["cd_rag"]=="RED").sum()),
        "reg_high_risk_firms":       int((risk_df["reg_rag"]=="HIGH").sum()),
        "modelled_cost_gbp":         round(base_cost,0),
    }
    print(f"\n  {'Market total':30} {summary['market_total']:>15,.0f}")
    print(f"  {'Change from 2024H1':30} {summary['vol_change_pct']:>+14.1f}%")
    print(f"  {'Market uphold rate':30} {summary['uphold_rate_pct']:>14.2f}%")
    print(f"  {'8-week closure rate':30} {summary['closure_8wk_pct']:>14.2f}%")
    print(f"  {'Firms analysed':30} {summary['n_firms']:>15,}")
    print(f"  {'Top firm by volume':30} {summary['top_firm']}")
    print(f"  {'  volume':30} {summary['top_firm_volume']:>15,}")
    print(f"  {'CD RED firms':30} {summary['cd_red_firms']:>15,}")
    print(f"  {'High regulatory risk':30} {summary['reg_high_risk_firms']:>15,}")
    print(f"  {'Modelled cost (GBP)':30} GBP {summary['modelled_cost_gbp']/1e9:.3f}bn")
    out = DATA_OUTPUTS / "executive_summary.json"
    with open(out,"w") as f: json.dump(summary,f,indent=2)
    print(f"\n  Saved: {out}")
    return summary


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("\nUK Retail Banking Complaints — Extended Analysis")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    df      = load_data()
    agg     = compute_firm_aggregates(df)
    print_firm_rankings(agg)
    market  = compute_market_totals(df)
    trend   = compute_firm_trends(agg)
    print_trend_leaders(trend)
    peer, outlier_df = compute_peer_benchmarks(agg)
    cd_scores = compute_cd_scores(agg, trend)
    prod_df = compute_product_benchmarks(df)
    chi_square_product_uphold(df)
    period_z_test(market)
    compute_concentration(agg)
    anom_df  = detect_anomalies(agg)
    spike_df = detect_spikes(agg)
    run_scenario_analysis(market)
    risk_df  = compute_reg_risk(cd_scores, trend, outlier_df)
    summary  = generate_executive_summary(market, agg, cd_scores, risk_df)

    print("\n" + "=" * 70)
    print("SAVING OUTPUTS")
    print("=" * 70)
    outputs = [
        (agg,           "firm_aggregates_all_periods.csv"),
        (cd_scores,     "cd_compliance_scores.csv"),
        (risk_df,       "regulatory_risk_scores.csv"),
        (trend,         "firm_volume_trends.csv"),
        (prod_df,       "product_period_benchmarks.csv"),
        (peer,          "peer_group_benchmarks.csv"),
    ]
    for df_out, fname in outputs:
        path = DATA_OUTPUTS / fname
        df_out.to_csv(path, index=False)
        print(f"  Saved: {fname}  ({len(df_out):,} rows)")
    if len(anom_df)>0:
        anom_df.to_csv(DATA_OUTPUTS/"anomaly_flags.csv", index=False)
        print(f"  Saved: anomaly_flags.csv")
    if len(spike_df)>0:
        spike_df.to_csv(DATA_OUTPUTS/"volume_spikes.csv", index=False)
        print(f"  Saved: volume_spikes.csv")

    print("\nExtended analysis complete.")


if __name__ == "__main__":
    main()


class QALog:
    def __init__(self):
        self.checks=[]; self.errors=[]; self.warnings=[]
    def add(self,sec,name,status,detail="",count=0):
        r={"section":sec,"check":name,"status":status,"detail":detail,"count":count}
        self.checks.append(r)
        if status=="FAIL": self.errors.append(r)
        elif status=="WARN": self.warnings.append(r)
    def score(self):
        if not self.checks: return 0.0
        p=sum(1 for c in self.checks if c["status"]=="PASS")
        w=sum(1 for c in self.checks if c["status"]=="WARN")
        return (p+0.5*w)/len(self.checks)*100
    def summary(self):
        return {"total":len(self.checks),
                "pass":sum(1 for c in self.checks if c["status"]=="PASS"),
                "warn":sum(1 for c in self.checks if c["status"]=="WARN"),
                "fail":sum(1 for c in self.checks if c["status"]=="FAIL")}

qa=QALog()

def check_completeness(df):
    print("
" + "="*70 + "
SECTION B — COMPLETENESS
" + "="*70)
    found=[p for p in PERIODS if p in df["period"].unique()]
    missing=[p for p in PERIODS if p not in found]
    print(f"  Periods present: {found}")
    qa.add("B","period_coverage","PASS" if not missing else "FAIL",
           f"{len(found)}/{len(PERIODS)}",len(missing))
    if "firm_name" in df.columns:
        pivot=df.groupby(["firm_name","period"])["complaints_opened"].sum().unstack(fill_value=0)
        all4=(pivot>0).all(axis=1).sum()
        print(f"  Firms in all 4 periods: {all4} / {len(pivot)}")
        qa.add("B","firm_all_periods","PASS" if all4>=len(pivot)*0.4 else "WARN",
               f"{all4}/{len(pivot)} firms in all periods")
    for col in ["complaints_opened","complaints_closed","upheld"]:
        if col not in df.columns: continue
        n=df[col].isna().sum(); pct=n/len(df)*100
        s="PASS" if pct<5 else ("WARN" if pct<20 else "FAIL")
        print(f"  {col:<30} nulls={n:,} ({pct:.1f}%)")
        qa.add("B",f"null_{col}",s,f"{pct:.1f}% nulls",n)

def check_consistency(df):
    print("
" + "="*70 + "
SECTION C — CONSISTENCY
" + "="*70)
    if "closed_within_8_weeks" in df.columns and "complaints_closed" in df.columns:
        n=(df["closed_within_8_weeks"].fillna(0)>df["complaints_closed"].fillna(0)).sum()
        print(f"  closed_8wk > closed: {n}")
        qa.add("C","8wk_le_closed","PASS" if n==0 else "FAIL",f"{n} violations",n)
    if "upheld" in df.columns and "complaints_closed" in df.columns:
        n=(df["upheld"].fillna(0)>df["complaints_closed"].fillna(0)).sum()
        print(f"  upheld > closed:     {n}")
        qa.add("C","upheld_le_closed","PASS" if n==0 else "FAIL",f"{n} violations",n)
    for col in ["complaints_opened","complaints_closed","upheld"]:
        if col not in df.columns: continue
        n=(df[col].fillna(0)<0).sum()
        print(f"  {col:<30} negatives={n}")
        qa.add("C",f"non_neg_{col}","PASS" if n==0 else "FAIL",f"{n} negatives",n)

def check_reconciliation(df):
    print("
" + "="*70 + "
SECTION D — FCA RECONCILIATION
" + "="*70)
    print(f"  {'Period':<10} {'Computed':>14} {'FCA':>14} {'Delta%':>9} Status")
    print("  "+"-"*55)
    for p in PERIODS:
        comp=df[df["period"]==p]["complaints_opened"].sum() if "period" in df.columns else 0
        fca=FCA_TOTALS.get(p,0)
        if fca==0: continue
        d=abs(comp-fca)/fca*100
        s="PASS" if d<1 else ("WARN" if d<3 else "FAIL")
        print(f"  {p:<10} {comp:>14,.0f} {fca:>14,.0f} {d:>8.2f}%  {s}")
        qa.add("D",f"fca_recon_{p}",s,f"delta={d:.2f}%",int(abs(comp-fca)))

def check_duplicates(df):
    print("
" + "="*70 + "
SECTION E — DUPLICATES
" + "="*70)
    keys=[c for c in ["firm_name","period","product_group"] if c in df.columns]
    if len(keys)<2: return
    n=df.duplicated(subset=keys,keep=False).sum()
    n_exact=df.duplicated(keep=False).sum()
    print(f"  Key duplicates:   {n}")
    print(f"  Exact duplicates: {n_exact}")
    qa.add("E","key_dupes","PASS" if n==0 else "FAIL",f"{n} key duplicates",n)
    qa.add("E","exact_dupes","PASS" if n_exact==0 else "FAIL",f"{n_exact} exact duplicates",n_exact)

def check_outliers(df):
    print("
" + "="*70 + "
SECTION F — OUTLIERS
" + "="*70)
    for col in ["complaints_opened","complaints_closed","upheld"]:
        if col not in df.columns: continue
        s=df[col].dropna()
        if len(s)<10: continue
        q1,q3=s.quantile(0.25),s.quantile(0.75)
        iqr=q3-q1
        fence_hi=q3+3.0*iqr
        n=((s<q1-3*iqr)|(s>fence_hi)).sum()
        pct=n/len(s)*100
        print(f"  {col:<30} IQR outliers={n} ({pct:.1f}%)")
        qa.add("F",f"iqr_{col}","PASS" if pct<5 else "WARN",f"{n} outliers ({pct:.1f}%)",n)
    if "upheld" in df.columns and "complaints_closed" in df.columns:
        tmp=df[df["complaints_closed"]>0].copy()
        rate=tmp["upheld"]/tmp["complaints_closed"]
        z=(rate-rate.mean())/rate.std()
        n=(z.abs()>3).sum()
        print(f"  uphold_rate z>3:               {n}")
        qa.add("F","zscore_uphold","PASS" if n<10 else "WARN",f"{n} z>3",n)

def check_firm_names(df):
    print("
" + "="*70 + "
SECTION G — FIRM NAMES
" + "="*70)
    if "firm_name" not in df.columns: return
    firms=df["firm_name"].dropna().unique()
    print(f"  Total unique firm names: {len(firms)}")
    n_ws=sum(1 for f in firms if f!=f.strip())
    lower_map=defaultdict(list)
    for f in firms: lower_map[f.lower()].append(f)
    n_case=sum(1 for v in lower_map.values() if len(v)>1)
    n_short=sum(1 for f in firms if len(f.strip())<=3)
    print(f"  Whitespace issues: {n_ws}  Case variants: {n_case}  Short names: {n_short}")
    qa.add("G","firm_whitespace","PASS" if n_ws==0 else "WARN",f"{n_ws} whitespace issues",n_ws)
    qa.add("G","firm_case_dupes","PASS" if n_case==0 else "WARN",f"{n_case} case variants",n_case)
    qa.add("G","firm_short","PASS" if n_short==0 else "WARN",f"{n_short} short names",n_short)
    if "period" in df.columns:
        for i in range(1,len(PERIODS)):
            pp,pc=PERIODS[i-1],PERIODS[i]
            fp=set(df[df["period"]==pp]["firm_name"].unique())
            fc=set(df[df["period"]==pc]["firm_name"].unique())
            print(f"  {pp}->{pc}: +{len(fc-fp)} new, -{len(fp-fc)} exited")

def print_scorecard():
    print("
" + "="*70 + "
SCORECARD
" + "="*70)
    secs=sorted(set(c["section"] for c in qa.checks))
    names={"A":"Raw Files","B":"Completeness","C":"Consistency",
           "D":"FCA Reconciliation","E":"Duplicates","F":"Outliers","G":"Firm Names"}
    print(f"  {'Sec':<4} {'Name':<24} {'N':>5} {'P':>5} {'W':>5} {'F':>5} {'Score':>7}")
    print("  "+"-"*54)
    scores=[]
    for sec in secs:
        cc=[c for c in qa.checks if c["section"]==sec]
        n,p=len(cc),sum(1 for c in cc if c["status"]=="PASS")
        w,f=sum(1 for c in cc if c["status"]=="WARN"),sum(1 for c in cc if c["status"]=="FAIL")
        sc=(p+0.5*w)/n*100 if n>0 else 100
        scores.append(sc)
        print(f"  {sec:<4} {names.get(sec,sec):<24} {n:>5} {p:>5} {w:>5} {f:>5} {sc:>6.1f}%")
    ov=sum(scores)/len(scores) if scores else 0
    print(f"  {'OVERALL':<30} {ov:>6.1f}%")
    print(f"  Rating: {'EXCELLENT' if ov>=90 else 'GOOD' if ov>=75 else 'ACCEPTABLE' if ov>=60 else 'NEEDS ATTENTION'}")
    if qa.errors:
        print(f"  FAILURES ({len(qa.errors)}):")
        for e in qa.errors: print(f"    [{e['section']}] {e['check']}: {e['detail']}")
    return ov

def generate_html_report(df, score):
    print("
" + "="*70 + "
GENERATING HTML REPORT
" + "="*70)
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s=qa.summary()
    sc_color="#065f46" if score>=90 else ("#92400e" if score>=60 else "#991b1b")
    sc_bg="#d1fae5" if score>=90 else ("#fef3c7" if score>=60 else "#fee2e2")
    def st_style(st):
        return {"PASS":"background:#d1fae5;color:#065f46","WARN":"background:#fef3c7;color:#92400e",
                "FAIL":"background:#fee2e2;color:#991b1b"}.get(st,"")
    rows=""
    for c in qa.checks:
        rows+=(f"<tr><td>{c['section']}</td><td>{c['check']}</td>"
               f"<td style="padding:2px 8px;border-radius:4px;font-weight:700;font-size:11px;{st_style(c['status'])}">{c['status']}</td>"
               f"<td>{c['detail']}</td><td style="text-align:right">{c['count'] or ''}</td></tr>")
    period_rows=""
    if "period" in df.columns:
        for p in PERIODS:
            sub=df[df["period"]==p]
            nf=sub["firm_name"].nunique() if "firm_name" in sub.columns else 0
            tot=sub["complaints_opened"].sum() if "complaints_opened" in sub.columns else 0
            period_rows+=f"<tr><td>{p}</td><td>{len(sub):,}</td><td>{nf:,}</td><td>{tot:,.0f}</td></tr>"
    html=f"""<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>
<title>Data Quality Report</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#f0f4f8;color:#1e293b;font-size:14px}}
header{{background:#1e3a5f;color:#fff;padding:14px 28px}}
header h1{{font-size:17px;font-weight:700}}header p{{font-size:11px;opacity:.7;margin-top:4px}}
main{{padding:20px 28px}}.card{{background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:16px}}
.card h2{{font-size:13px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px}}
.sr{{display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap}}.st{{flex:1;min-width:110px;background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.08);text-align:center}}
.st .n{{font-size:26px;font-weight:700}}.st .l{{font-size:11px;color:#64748b;margin-top:3px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{padding:7px 10px;text-align:left;font-weight:700;color:#475569;border-bottom:2px solid #e2e8f0;background:#f8fafc}}
td{{padding:5px 10px;border-bottom:1px solid #f1f5f9}}tr:hover td{{background:#f8fafc}}
footer{{text-align:center;padding:12px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;margin-top:8px}}</style>
</head><body>
<header><h1>Data Quality Validation Report — UK Retail Banking Complaints Benchmark</h1>
<p>Generated: {now} | Author: Gagandeep Kapoor | FCA Data 2024H1-2025H2</p></header>
<main>
<div class='sr'>
<div class='st'><div class='n'>{s['total']}</div><div class='l'>Total Checks</div></div>
<div class='st'><div class='n' style='color:#065f46'>{s['pass']}</div><div class='l'>Pass</div></div>
<div class='st'><div class='n' style='color:#92400e'>{s['warn']}</div><div class='l'>Warn</div></div>
<div class='st'><div class='n' style='color:#991b1b'>{s['fail']}</div><div class='l'>Fail</div></div>
<div class='st'><div class='n' style='color:{sc_color};background:{sc_bg};padding:4px 12px;border-radius:6px'>{score:.1f}</div><div class='l'>Score/100</div></div>
</div>
<div class='card'><h2>Dataset Overview</h2>
<table><tr><th>Period</th><th>Rows</th><th>Firms</th><th>Complaints Opened</th></tr>{period_rows}</table></div>
<div class='card'><h2>All Quality Checks ({s['total']} checks)</h2>
<table><tr><th>Sec</th><th>Check</th><th>Status</th><th>Detail</th><th>Count</th></tr>{rows}</table></div>
</main>
<footer>&copy; 2026 Gagandeep Kapoor &middot; UK Retail Banking Complaints Benchmark</footer>
</body></html>"""
    out=DATA_OUTPUTS/"data_quality_report.html"
    with open(out,"w",encoding="utf-8") as f: f.write(html)
    print(f"  Saved: {out}")
    log=DATA_OUTPUTS/"data_quality_log.json"
    with open(log,"w") as f: json.dump({"score":score,"summary":s,"checks":qa.checks},f,indent=2)
    print(f"  Saved: {log}")

def main():
    print("
UK Banking Complaints — Data Quality Validation")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    clean=DATA_PROCESSED/"complaints_clean.csv"
    if not clean.exists():
        print(f"  complaints_clean.csv not found at {clean}")
        print("  Run 01_ingest_and_clean.py first.")
        return
    df=pd.read_csv(clean)
    print(f"  Loaded: {len(df):,} rows")
    check_completeness(df)
    check_consistency(df)
    check_reconciliation(df)
    check_duplicates(df)
    check_outliers(df)
    check_firm_names(df)
    score=print_scorecard()
    generate_html_report(df, score)
    print("
Data quality validation complete.")

if __name__=="__main__":
    main()
