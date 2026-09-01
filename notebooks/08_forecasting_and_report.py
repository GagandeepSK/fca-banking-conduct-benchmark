#!/usr/bin/env python3
# 08_forecasting_and_report.py
# Complaint volume forecasting, what-if modelling, and full written report generation.
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


def naive_forecast(series, n_periods=4):
    """Naive forecast: next value = last observed value."""
    if len(series) == 0: return []
    last = series[-1]
    return [last] * n_periods


def linear_trend_forecast(series, n_periods=4):
    """Fit OLS linear trend and extrapolate."""
    n = len(series)
    if n < 2: return [series[-1]]*n_periods if series else []
    x = list(range(n))
    xm = sum(x)/n; ym = sum(series)/n
    num = sum((xi-xm)*(yi-ym) for xi,yi in zip(x,series))
    den = sum((xi-xm)**2 for xi in x)
    slope = num/den if den>0 else 0
    intercept = ym - slope*xm
    return [intercept + slope*(n+i) for i in range(n_periods)]


def simple_moving_average_forecast(series, n_periods=4, window=2):
    """SMA forecast using last window periods."""
    window = min(window, len(series))
    if window == 0: return []
    result = []
    hist = list(series)
    for _ in range(n_periods):
        ma = sum(hist[-window:])/window
        result.append(ma)
        hist.append(ma)
    return result


def exponential_smoothing_forecast(series, n_periods=4, alpha=0.3):
    """Single exponential smoothing."""
    if len(series) == 0: return []
    level = series[0]
    for v in series[1:]:
        level = alpha*v + (1-alpha)*level
    return [level]*n_periods


def holt_linear_forecast(series, n_periods=4, alpha=0.3, beta=0.1):
    """Holt two-parameter linear exponential smoothing."""
    if len(series) < 2: return [series[-1]]*n_periods if series else []
    level = series[0]
    trend = series[1] - series[0]
    for v in series[1:]:
        prev_l = level
        level = alpha*v + (1-alpha)*(level+trend)
        trend = beta*(level-prev_l) + (1-beta)*trend
    return [level + (i+1)*trend for i in range(n_periods)]


def pct_change_forecast(series, n_periods=4):
    """Forecast by applying mean period-on-period % change."""
    if len(series) < 2: return [series[-1]]*n_periods if series else []
    pcts = [(series[i]-series[i-1])/series[i-1] for i in range(1,len(series)) if series[i-1]>0]
    if not pcts: return [series[-1]]*n_periods
    mean_pct = sum(pcts)/len(pcts)
    result = []
    last = series[-1]
    for _ in range(n_periods):
        last = last*(1+mean_pct)
        result.append(last)
    return result


def median_forecast(series, n_periods=4):
    """Forecast as the median of the observed series (robust to outliers)."""
    if len(series) == 0: return []
    s = sorted(series)
    n = len(s)
    med = s[n//2] if n%2==1 else (s[n//2-1]+s[n//2])/2
    return [med]*n_periods


def ensemble_forecast(series, n_periods=4):
    """Average of three forecast methods for robustness."""
    f1 = linear_trend_forecast(series, n_periods)
    f2 = exponential_smoothing_forecast(series, n_periods, alpha=0.4)
    f3 = pct_change_forecast(series, n_periods)
    if not f1 or not f2 or not f3: return naive_forecast(series, n_periods)
    return [(a+b+c)/3 for a,b,c in zip(f1,f2,f3)]


COST_FOS_FEE_CURRENT = 650.0

def scenario_consumer_duty_compliance(base_vol, base_uphold):
    """
    Scenario: Consumer Duty — Full Compliance.
    Volume delta: -20%  Uphold delta: -15%
    """
    vol    = base_vol    * (1 + (-0.2))
    uphold = max(0.0, min(1.0, base_uphold + (-0.15)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Consumer Duty — Full Compliance",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_regulatory_action_single_firm(base_vol, base_uphold):
    """
    Scenario: Regulatory action: top-5 firms reduce volume 30%.
    Volume delta: -12%  Uphold delta: -5%
    """
    vol    = base_vol    * (1 + (-0.12))
    uphold = max(0.0, min(1.0, base_uphold + (-0.05)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Regulatory action: top-5 firms reduce volume 30%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_macro_recession(base_vol, base_uphold):
    """
    Scenario: Macro recession: complaint volume +25%, uphold +5pp.
    Volume delta: +25%  Uphold delta: +5%
    """
    vol    = base_vol    * (1 + (0.25))
    uphold = max(0.0, min(1.0, base_uphold + (0.05)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Macro recession: complaint volume +25%, uphold +5pp",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_product_reform_banking_cc(base_vol, base_uphold):
    """
    Scenario: Banking & CC product reform: sector volume -20%.
    Volume delta: -10%  Uphold delta: -8%
    """
    vol    = base_vol    * (1 + (-0.1))
    uphold = max(0.0, min(1.0, base_uphold + (-0.08)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Banking & CC product reform: sector volume -20%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_fos_fee_increase(base_vol, base_uphold):
    """
    Scenario: FOS fee increase to GBP 950 per case.
    Volume delta: +0%  Uphold delta: +0%
    """
    vol    = base_vol    * (1 + (0.0))
    uphold = max(0.0, min(1.0, base_uphold + (0.0)))
    fos_fee = 950.0  # increased from GBP 650
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "FOS fee increase to GBP 950 per case",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_digital_complaints_surge(base_vol, base_uphold):
    """
    Scenario: Digital complaints surge: volume +15%.
    Volume delta: +15%  Uphold delta: +0%
    """
    vol    = base_vol    * (1 + (0.15))
    uphold = max(0.0, min(1.0, base_uphold + (0.0)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Digital complaints surge: volume +15%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_redress_reduction(base_vol, base_uphold):
    """
    Scenario: Improved products: redress -20% (fewer upheld).
    Volume delta: +0%  Uphold delta: -10%
    """
    vol    = base_vol    * (1 + (0.0))
    uphold = max(0.0, min(1.0, base_uphold + (-0.1)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Improved products: redress -20% (fewer upheld)",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_industry_benchmark_sharing(base_vol, base_uphold):
    """
    Scenario: Benchmark transparency: uphold rate converges to median.
    Volume delta: +0%  Uphold delta: -8%
    """
    vol    = base_vol    * (1 + (0.0))
    uphold = max(0.0, min(1.0, base_uphold + (-0.08)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Benchmark transparency: uphold rate converges to median",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_pension_product_crisis(base_vol, base_uphold):
    """
    Scenario: Pensions crisis: decumulation volume +40%.
    Volume delta: +8%  Uphold delta: +12%
    """
    vol    = base_vol    * (1 + (0.08))
    uphold = max(0.0, min(1.0, base_uphold + (0.12)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Pensions crisis: decumulation volume +40%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_insurance_claim_surge(base_vol, base_uphold):
    """
    Scenario: Insurance claim surge post-extreme-weather.
    Volume delta: +12%  Uphold delta: +3%
    """
    vol    = base_vol    * (1 + (0.12))
    uphold = max(0.0, min(1.0, base_uphold + (0.03)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Insurance claim surge post-extreme-weather",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_best_practice_adoption(base_vol, base_uphold):
    """
    Scenario: Best practice: 8-week closure improves to 90%.
    Volume delta: +0%  Uphold delta: -5%
    """
    vol    = base_vol    * (1 + (0.0))
    uphold = max(0.0, min(1.0, base_uphold + (-0.05)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "Best practice: 8-week closure improves to 90%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }

def scenario_new_entrant_growth(base_vol, base_uphold):
    """
    Scenario: New fintech entrants: market +5 new firms, volume +3%.
    Volume delta: +3%  Uphold delta: -2%
    """
    vol    = base_vol    * (1 + (0.03))
    uphold = max(0.0, min(1.0, base_uphold + (-0.02)))
    fos_fee = COST_FOS_FEE_CURRENT
    handling = vol * COST_HANDLING
    fos      = vol * COST_FOS_RATE * fos_fee
    redress  = vol * uphold * COST_REDRESS
    total    = handling + fos + redress
    return {
        "scenario":    "New fintech entrants: market +5 new firms, volume +3%",
        "volume":      round(vol, 0),
        "uphold_rate": round(uphold, 4),
        "handling":    round(handling, 0),
        "fos":         round(fos, 0),
        "redress":     round(redress, 0),
        "total":       round(total, 0),
    }


def analyse_banking_cc(df):
    """Deep-dive analysis for Banking Cc product group."""
    if "product_group" not in df.columns: return {}
    pg_map = {
        "banking_cc":             "Banking and credit cards",
        "home_finance":           "Home finance",
        "insurance_pp":           "Insurance and pure protection",
        "decumulation_pensions":  "Decumulation and pensions",
        "investments":            "Investments",
    }
    pg_name = pg_map.get("banking_cc", "Banking Cc")
    sub = df[df["product_group"]==pg_name].copy()
    if len(sub)==0: return {"product":"Banking Cc","status":"no data"}
    result = {"product": pg_name}
    if "period" in sub.columns:
        period_totals = (sub.groupby("period")[["complaints_opened","complaints_closed","upheld"]]
                        .sum().reindex(PERIODS).to_dict())
        result["period_opened"] = {k:int(v) for k,v in period_totals.get("complaints_opened",{}).items() if not (isinstance(v,float) and math.isnan(v))}
        totals = sub.groupby("period").agg(
            opened=("complaints_opened","sum"),
            closed=("complaints_closed","sum"),
            upheld=("upheld","sum")).reset_index()
        totals["uphold_rate"] = totals["upheld"] / totals["closed"].replace(0, np.nan)
        latest = totals[totals["period"]=="2025H2"]
        if len(latest)>0:
            result["latest_opened"]     = int(latest["opened"].iloc[0])
            result["latest_uphold_rate"] = round(float(latest["uphold_rate"].iloc[0]),4) if not pd.isna(latest["uphold_rate"].iloc[0]) else None
        if "firm_name" in sub.columns:
            top_firms = (sub[sub["period"]=="2025H2"].groupby("firm_name")["complaints_opened"]
                         .sum().sort_values(ascending=False).head(5).to_dict())
            result["top_5_firms_2025h2"] = {k:int(v) for k,v in top_firms.items()}
    return result

def analyse_home_finance(df):
    """Deep-dive analysis for Home Finance product group."""
    if "product_group" not in df.columns: return {}
    pg_map = {
        "banking_cc":             "Banking and credit cards",
        "home_finance":           "Home finance",
        "insurance_pp":           "Insurance and pure protection",
        "decumulation_pensions":  "Decumulation and pensions",
        "investments":            "Investments",
    }
    pg_name = pg_map.get("home_finance", "Home Finance")
    sub = df[df["product_group"]==pg_name].copy()
    if len(sub)==0: return {"product":"Home Finance","status":"no data"}
    result = {"product": pg_name}
    if "period" in sub.columns:
        period_totals = (sub.groupby("period")[["complaints_opened","complaints_closed","upheld"]]
                        .sum().reindex(PERIODS).to_dict())
        result["period_opened"] = {k:int(v) for k,v in period_totals.get("complaints_opened",{}).items() if not (isinstance(v,float) and math.isnan(v))}
        totals = sub.groupby("period").agg(
            opened=("complaints_opened","sum"),
            closed=("complaints_closed","sum"),
            upheld=("upheld","sum")).reset_index()
        totals["uphold_rate"] = totals["upheld"] / totals["closed"].replace(0, np.nan)
        latest = totals[totals["period"]=="2025H2"]
        if len(latest)>0:
            result["latest_opened"]     = int(latest["opened"].iloc[0])
            result["latest_uphold_rate"] = round(float(latest["uphold_rate"].iloc[0]),4) if not pd.isna(latest["uphold_rate"].iloc[0]) else None
        if "firm_name" in sub.columns:
            top_firms = (sub[sub["period"]=="2025H2"].groupby("firm_name")["complaints_opened"]
                         .sum().sort_values(ascending=False).head(5).to_dict())
            result["top_5_firms_2025h2"] = {k:int(v) for k,v in top_firms.items()}
    return result

def analyse_insurance_pp(df):
    """Deep-dive analysis for Insurance Pp product group."""
    if "product_group" not in df.columns: return {}
    pg_map = {
        "banking_cc":             "Banking and credit cards",
        "home_finance":           "Home finance",
        "insurance_pp":           "Insurance and pure protection",
        "decumulation_pensions":  "Decumulation and pensions",
        "investments":            "Investments",
    }
    pg_name = pg_map.get("insurance_pp", "Insurance Pp")
    sub = df[df["product_group"]==pg_name].copy()
    if len(sub)==0: return {"product":"Insurance Pp","status":"no data"}
    result = {"product": pg_name}
    if "period" in sub.columns:
        period_totals = (sub.groupby("period")[["complaints_opened","complaints_closed","upheld"]]
                        .sum().reindex(PERIODS).to_dict())
        result["period_opened"] = {k:int(v) for k,v in period_totals.get("complaints_opened",{}).items() if not (isinstance(v,float) and math.isnan(v))}
        totals = sub.groupby("period").agg(
            opened=("complaints_opened","sum"),
            closed=("complaints_closed","sum"),
            upheld=("upheld","sum")).reset_index()
        totals["uphold_rate"] = totals["upheld"] / totals["closed"].replace(0, np.nan)
        latest = totals[totals["period"]=="2025H2"]
        if len(latest)>0:
            result["latest_opened"]     = int(latest["opened"].iloc[0])
            result["latest_uphold_rate"] = round(float(latest["uphold_rate"].iloc[0]),4) if not pd.isna(latest["uphold_rate"].iloc[0]) else None
        if "firm_name" in sub.columns:
            top_firms = (sub[sub["period"]=="2025H2"].groupby("firm_name")["complaints_opened"]
                         .sum().sort_values(ascending=False).head(5).to_dict())
            result["top_5_firms_2025h2"] = {k:int(v) for k,v in top_firms.items()}
    return result

def analyse_decumulation_pensions(df):
    """Deep-dive analysis for Decumulation Pensions product group."""
    if "product_group" not in df.columns: return {}
    pg_map = {
        "banking_cc":             "Banking and credit cards",
        "home_finance":           "Home finance",
        "insurance_pp":           "Insurance and pure protection",
        "decumulation_pensions":  "Decumulation and pensions",
        "investments":            "Investments",
    }
    pg_name = pg_map.get("decumulation_pensions", "Decumulation Pensions")
    sub = df[df["product_group"]==pg_name].copy()
    if len(sub)==0: return {"product":"Decumulation Pensions","status":"no data"}
    result = {"product": pg_name}
    if "period" in sub.columns:
        period_totals = (sub.groupby("period")[["complaints_opened","complaints_closed","upheld"]]
                        .sum().reindex(PERIODS).to_dict())
        result["period_opened"] = {k:int(v) for k,v in period_totals.get("complaints_opened",{}).items() if not (isinstance(v,float) and math.isnan(v))}
        totals = sub.groupby("period").agg(
            opened=("complaints_opened","sum"),
            closed=("complaints_closed","sum"),
            upheld=("upheld","sum")).reset_index()
        totals["uphold_rate"] = totals["upheld"] / totals["closed"].replace(0, np.nan)
        latest = totals[totals["period"]=="2025H2"]
        if len(latest)>0:
            result["latest_opened"]     = int(latest["opened"].iloc[0])
            result["latest_uphold_rate"] = round(float(latest["uphold_rate"].iloc[0]),4) if not pd.isna(latest["uphold_rate"].iloc[0]) else None
        if "firm_name" in sub.columns:
            top_firms = (sub[sub["period"]=="2025H2"].groupby("firm_name")["complaints_opened"]
                         .sum().sort_values(ascending=False).head(5).to_dict())
            result["top_5_firms_2025h2"] = {k:int(v) for k,v in top_firms.items()}
    return result

def analyse_investments(df):
    """Deep-dive analysis for Investments product group."""
    if "product_group" not in df.columns: return {}
    pg_map = {
        "banking_cc":             "Banking and credit cards",
        "home_finance":           "Home finance",
        "insurance_pp":           "Insurance and pure protection",
        "decumulation_pensions":  "Decumulation and pensions",
        "investments":            "Investments",
    }
    pg_name = pg_map.get("investments", "Investments")
    sub = df[df["product_group"]==pg_name].copy()
    if len(sub)==0: return {"product":"Investments","status":"no data"}
    result = {"product": pg_name}
    if "period" in sub.columns:
        period_totals = (sub.groupby("period")[["complaints_opened","complaints_closed","upheld"]]
                        .sum().reindex(PERIODS).to_dict())
        result["period_opened"] = {k:int(v) for k,v in period_totals.get("complaints_opened",{}).items() if not (isinstance(v,float) and math.isnan(v))}
        totals = sub.groupby("period").agg(
            opened=("complaints_opened","sum"),
            closed=("complaints_closed","sum"),
            upheld=("upheld","sum")).reset_index()
        totals["uphold_rate"] = totals["upheld"] / totals["closed"].replace(0, np.nan)
        latest = totals[totals["period"]=="2025H2"]
        if len(latest)>0:
            result["latest_opened"]     = int(latest["opened"].iloc[0])
            result["latest_uphold_rate"] = round(float(latest["uphold_rate"].iloc[0]),4) if not pd.isna(latest["uphold_rate"].iloc[0]) else None
        if "firm_name" in sub.columns:
            top_firms = (sub[sub["period"]=="2025H2"].groupby("firm_name")["complaints_opened"]
                         .sum().sort_values(ascending=False).head(5).to_dict())
            result["top_5_firms_2025h2"] = {k:int(v) for k,v in top_firms.items()}
    return result


def load_data():
    clean = DATA_PROCESSED / "complaints_clean.csv"
    if not clean.exists():
        raise FileNotFoundError(f"Run 01_ingest_and_clean.py first. Missing: {clean}")
    return pd.read_csv(clean)


def run_market_forecasts(df):
    """Run all 8 forecasting methods on market-level complaint volumes."""
    print("
" + "="*70)
    print("MARKET VOLUME FORECASTS — 2026H1 and 2026H2")
    print("="*70)
    market = (df.groupby("period")["complaints_opened"].sum().reindex(PERIODS).fillna(0).tolist())
    print(f"  Historical: {[int(v) for v in market]}")
    forecasts = {}
    methods_map = {
        "Naive":               naive_forecast,
        "Linear trend":        linear_trend_forecast,
        "SMA-2":               simple_moving_average_forecast,
        "Exp smoothing":       exponential_smoothing_forecast,
        "Holt linear":         holt_linear_forecast,
        "Pct change":          pct_change_forecast,
        "Median":              median_forecast,
        "Ensemble":            ensemble_forecast,
    }
    print(f"
  {'Method':<22} {'2026H1':>12} {'2026H2':>12} {'Direction':>12}")
    print("  "+"-"*60)
    for name, fn in methods_map.items():
        try:
            fc = fn(market, n_periods=2)
            pct = (fc[0]-market[-1])/market[-1]*100 if market[-1]>0 else 0
            direction = "UP" if pct>1 else ("DOWN" if pct<-1 else "FLAT")
            print(f"  {name:<22} {int(fc[0]):>12,} {int(fc[1]):>12,} {direction:>12}  ({pct:+.1f}%)")
            forecasts[name] = {"2026H1": int(fc[0]), "2026H2": int(fc[1])}
        except Exception as e:
            print(f"  {name:<22} ERROR: {e}")
    return forecasts


def run_scenarios(df):
    """Run all 12 what-if cost scenarios."""
    print("
" + "="*70)
    print("WHAT-IF SCENARIO ANALYSIS")
    print("="*70)
    latest = df[df["period"]=="2025H2"] if "period" in df.columns else df
    base_vol = float(latest["complaints_opened"].sum())
    closed = latest["complaints_closed"].sum()
    upheld = latest["upheld"].sum()
    base_uphold = upheld/closed if closed>0 else 0.35
    base_cost = base_vol*COST_HANDLING + base_vol*COST_FOS_RATE*COST_FOS_FEE + base_vol*base_uphold*COST_REDRESS
    print(f"  Baseline: vol={base_vol:,.0f}  uphold={base_uphold:.1%}  cost=GBP {base_cost/1e9:.4f}bn")
    print(f"  {'Scenario':<52} {'Volume':>12} {'Uphold':>8} {'Cost GBP':>14} {'vs Base':>10}")
    print("  "+"-"*100)
    scenario_fns = [
        scenario_consumer_duty_compliance,
        scenario_regulatory_action_single_firm,
        scenario_macro_recession,
        scenario_product_reform_banking_cc,
        scenario_fos_fee_increase,
        scenario_digital_complaints_surge,
        scenario_redress_reduction,
        scenario_industry_benchmark_sharing,
        scenario_pension_product_crisis,
        scenario_insurance_claim_surge,
        scenario_best_practice_adoption,
        scenario_new_entrant_growth,
    ]
    results = []
    for fn in scenario_fns:
        r = fn(base_vol, base_uphold)
        delta = r["total"] - base_cost
        print(f"  {r['scenario']:<52} {r['volume']:>12,.0f} {r['uphold_rate']:>7.1%}  GBP {r['total']/1e9:>8.4f}bn {delta/1e6:>+9.0f}m")
        r["baseline_cost"] = base_cost
        r["delta_gbp"] = delta
        results.append(r)
    df_sc = pd.DataFrame(results)
    df_sc.to_csv(DATA_OUTPUTS/"scenario_results.csv", index=False)
    print(f"  Saved: scenario_results.csv")
    return results


def run_product_analysis(df):
    """Run deep-dive analysis for all 5 product groups."""
    print("
" + "="*70)
    print("PRODUCT GROUP DEEP DIVES")
    print("="*70)
    results = {}
    for pg_key in ["banking_cc","home_finance","insurance_pp","decumulation_pensions","investments"]:
        fn_map = {
            "banking_cc":             analyse_banking_cc,
            "home_finance":           analyse_home_finance,
            "insurance_pp":           analyse_insurance_pp,
            "decumulation_pensions":  analyse_decumulation_pensions,
            "investments":            analyse_investments,
        }
        fn = fn_map.get(pg_key)
        if fn:
            r = fn(df)
            results[pg_key] = r
            vol = r.get("latest_opened", "N/A")
            ur  = r.get("latest_uphold_rate")
            ur_s = f"{ur:.1%}" if ur is not None else "N/A"
            print(f"  {r.get('product',pg_key):<40} vol={str(vol):>10}  uphold={ur_s:>7}")
    return results


def main():
    print("
UK Banking Complaints — Forecasting and Report")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    df = load_data()
    print(f"  Loaded: {len(df):,} rows")
    forecasts  = run_market_forecasts(df)
    scenarios  = run_scenarios(df)
    products   = run_product_analysis(df)
    out = DATA_OUTPUTS / "forecast_and_scenarios.json"
    with open(out, "w") as f:
        json.dump({"forecasts":forecasts,"products":products}, f, indent=2, default=str)
    print(f"
  Saved: {out}")
    print("
Forecasting and report complete.")


if __name__ == "__main__":
    main()