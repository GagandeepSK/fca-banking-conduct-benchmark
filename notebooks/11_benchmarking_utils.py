#!/usr/bin/env python3
# 11_benchmarking_utils.py
# Shared utility functions, constants, and validators used across all benchmark notebooks.
# Author: Gagandeep Kapoor

import os, json, math, re, hashlib, warnings
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict, Counter
from typing import Optional, Dict, List, Tuple, Union
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE / "data" / "processed"
DATA_OUTPUTS   = BASE / "data" / "outputs"
PERIODS = ["2024H1","2024H2","2025H1","2025H2"]
PERIOD_ORDER = {p:i for i,p in enumerate(PERIODS)}

PRODUCT_GROUPS = [
    "Banking and credit cards",
    "Home finance",
    "Insurance and pure protection",
    "Decumulation and pensions",
    "Investments",
]

COST_HANDLING = 200.0
COST_FOS_FEE  = 650.0
COST_FOS_RATE = 0.08
COST_REDRESS  = 300.0

CD_UPHOLD_RED    = 0.50
CD_UPHOLD_AMBER  = 0.35
CD_CLOSURE_RED   = 0.60
CD_CLOSURE_AMBER = 0.75

FCA_PUBLISHED_TOTALS = {
    "2024H1": 1_774_139,
    "2024H2": 1_698_000,
    "2025H1": 1_670_000,
    "2025H2": 1_652_438,
}



def safe_divide(num, den, default=float("nan")):
    """Division returning default when denominator is zero or NaN."""
    if den is None or (isinstance(den, float) and math.isnan(den)) or den == 0:
        return default
    return num / den


def pct_change(old, new):
    """Percentage change from old to new; returns NaN if old is zero."""
    if old == 0: return float("nan")
    return (new - old) / old * 100


def pp_change(old_rate, new_rate):
    """Percentage-point change between two rates."""
    return (new_rate - old_rate) * 100


def ols_slope(x, y):
    """Ordinary least-squares slope for paired x, y sequences."""
    n = len(x)
    if n < 2: return 0.0
    xm = sum(x) / n
    ym = sum(y) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y))
    den = sum((xi - xm) ** 2 for xi in x)
    return num / den if den != 0 else 0.0


def ols_intercept(x, y):
    """Ordinary least-squares intercept."""
    n = len(x)
    if n < 2: return y[0] if y else 0.0
    xm = sum(x) / n
    ym = sum(y) / n
    slope = ols_slope(x, y)
    return ym - slope * xm


def r_squared(y_true, y_pred):
    """Coefficient of determination R^2."""
    if len(y_true) < 2: return float("nan")
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    mean_t = sum(y_true) / len(y_true)
    ss_tot = sum((t - mean_t) ** 2 for t in y_true)
    return 1 - ss_res / ss_tot if ss_tot != 0 else float("nan")


def median(values):
    """Median of a sequence (handles even/odd length)."""
    s = sorted(v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    n = len(s)
    if n == 0: return float("nan")
    return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2


def percentile(values, p):
    """p-th percentile of a sequence (linear interpolation)."""
    s = sorted(v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    n = len(s)
    if n == 0: return float("nan")
    idx = (n - 1) * p / 100
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def iqr(values):
    """Interquartile range (Q3 - Q1)."""
    return percentile(values, 75) - percentile(values, 25)


def tukey_fence_hi(values, k=1.5):
    """Upper Tukey fence: Q3 + k * IQR."""
    return percentile(values, 75) + k * iqr(values)


def z_score(value, mean, std):
    """Standardised z-score."""
    return (value - mean) / std if std > 0 else 0.0


def winsorise(values, lo_pct=1, hi_pct=99):
    """Winsorise values at given percentile bounds."""
    lo = percentile(values, lo_pct)
    hi = percentile(values, hi_pct)
    return [max(lo, min(hi, v)) for v in values]


def moving_average(values, window=2):
    """Simple moving average with given window."""
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(sum(values[start:i+1]) / (i - start + 1))
    return result


def hhi(shares):
    """Herfindahl-Hirschman Index from a list of market shares (0-1). Returns 0-10000 scale."""
    return sum(s ** 2 for s in shares) * 10_000


def cr_n(values, n):
    """Combined market share of top-N firms. Values are raw volumes."""
    total = sum(values)
    if total == 0: return float("nan")
    top = sorted(values, reverse=True)[:n]
    return sum(top) / total


def lorenz_curve(values):
    """Compute Lorenz curve points (cumulative population %, cumulative share %)."""
    s = sorted(values)
    n = len(s)
    if n == 0: return [], []
    total = sum(s)
    cum_pop  = [i / n * 100 for i in range(n + 1)]
    cum_share = [0.0] + [sum(s[:i+1]) / total * 100 for i in range(n)]
    return cum_pop, cum_share


def gini_coefficient(values):
    """Gini coefficient from raw values (0 = perfect equality, 1 = maximum inequality)."""
    s = sorted(values)
    n = len(s)
    if n == 0 or sum(s) == 0: return float("nan")
    cum = [sum(s[:i+1]) for i in range(n)]
    return 1 - 2 * sum(cum) / (n * sum(s)) + 1 / n


def normalise_min_max(values):
    """Min-max normalisation to [0, 1]."""
    lo, hi = min(values), max(values)
    if hi == lo: return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def standardise(values):
    """Z-score standardisation (mean 0, std 1)."""
    n = len(values)
    if n == 0: return []
    mu = sum(values) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in values) / n)
    if sd == 0: return [0.0] * n
    return [(v - mu) / sd for v in values]


def assign_rag(value, amber_lo, red_hi, direction="higher_worse"):
    """Assign RAG rating. direction=higher_worse: high value = RED."""
    if direction == "higher_worse":
        if value >= red_hi:   return "RED"
        if value >= amber_lo: return "AMBER"
        return "GREEN"
    else:  # lower_worse
        if value <= red_hi:   return "RED"
        if value <= amber_lo: return "AMBER"
        return "GREEN"


def cost_total(opened, uphold_rate):
    """Compute total modelled cost for a firm-period."""
    if math.isnan(uphold_rate): uphold_rate = 0.35
    return (opened * COST_HANDLING
            + opened * COST_FOS_RATE * COST_FOS_FEE
            + opened * uphold_rate * COST_REDRESS)


def format_gbp(value, unit="m"):
    """Format a GBP value as a readable string."""
    if unit == "bn":  return f"GBP {value/1e9:.3f}bn"
    if unit == "m":   return f"GBP {value/1e6:.1f}m"
    if unit == "k":   return f"GBP {value/1e3:.0f}k"
    return f"GBP {value:,.0f}"


def period_label(period):
    """Convert internal period code to display label."""
    mapping = {"2024H1":"2024 H1","2024H2":"2024 H2","2025H1":"2025 H1","2025H2":"2025 H2"}
    return mapping.get(period, period)


def is_valid_period(period):
    """Check whether a string is a valid reporting period."""
    return period in PERIODS


def is_valid_product_group(pg):
    """Check whether a string is a known product group."""
    return pg in PRODUCT_GROUPS


def clean_firm_name(name):
    """Strip whitespace and normalise case for firm name comparison."""
    if not isinstance(name, str): return ""
    return re.sub(r"\s+", " ", name.strip())


def hash_firm_name(name):
    """Deterministic short hash of a firm name for anonymisation."""
    return hashlib.md5(clean_firm_name(name).lower().encode()).hexdigest()[:8]


def size_band(volume):
    """Classify a firm into a size band by complaint volume."""
    if volume >= 50_000: return "Large (>50k)"
    if volume >= 10_000: return "Medium (10-50k)"
    if volume >= 1_000:  return "Small (1-10k)"
    return "Micro (<1k)"


def reconcile_with_fca(period, computed_total):
    """Check computed market total against FCA published figure; return delta %."""
    fca = FCA_PUBLISHED_TOTALS.get(period)
    if fca is None: return None
    return abs(computed_total - fca) / fca * 100


def summarise_series(values, name=""):
    """Print descriptive statistics for a numeric series."""
    clean = [v for v in values if v is not None and not (isinstance(v,float) and math.isnan(v))]
    if not clean: print(f"  {name}: no valid values"); return
    n = len(clean)
    mu = sum(clean)/n
    sd = math.sqrt(sum((v-mu)**2 for v in clean)/n)
    print(f"  {name}: n={n}  min={min(clean):.4g}  p25={percentile(clean,25):.4g}  median={median(clean):.4g}  p75={percentile(clean,75):.4g}  max={max(clean):.4g}  mean={mu:.4g}  std={sd:.4g}")


# -- Validation helpers --


def validate_dataframe(df, required_cols, name="df"):
    """Assert required columns are present; print summary."""
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")
    print(f"  {name}: {len(df):,} rows  cols={list(df.columns[:6])}")
    return True


def assert_rates_in_range(df, col, lo=0.0, hi=1.0):
    """Assert a rate column is within [lo, hi]; return count of violations."""
    if col not in df.columns: return 0
    s = df[col].dropna()
    n = ((s < lo) | (s > hi)).sum()
    if n > 0: print(f"  WARNING: {col} has {n} values outside [{lo},{hi}]")
    return int(n)


def assert_no_negatives(df, col):
    """Assert a column has no negative values; return count."""
    if col not in df.columns: return 0
    n = (df[col].fillna(0) < 0).sum()
    if n > 0: print(f"  WARNING: {col} has {n} negative values")
    return int(n)


def assert_no_duplicates(df, key_cols):
    """Assert no duplicate key combinations; return count."""
    n = df.duplicated(subset=[c for c in key_cols if c in df.columns]).sum()
    if n > 0: print(f"  WARNING: {n} duplicate rows on keys {key_cols}")
    return int(n)


# -- Reporting helpers --


def print_section(title, width=70):
    """Print a section header."""
    print("
" + "="*width)
    print(title)
    print("="*width)


def print_table(rows, headers, widths=None, pct_cols=None):
    """Print a formatted ASCII table."""
    pct_cols = pct_cols or []
    if widths is None: widths = [20]*len(headers)
    header_line = "  " + "  ".join(str(h).ljust(w) for h,w in zip(headers,widths))
    print("
" + header_line)
    print("  " + "-"*sum(w+2 for w in widths))
    for row in rows:
        cells = []
        for val,h,w in zip(row,headers,widths):
            if h in pct_cols and isinstance(val,float) and not math.isnan(val):
                cells.append(f"{val:.1%}".rjust(w))
            elif isinstance(val,float) and not math.isnan(val):
                cells.append(f"{val:,.2f}".rjust(w))
            elif isinstance(val,(int,np.integer)):
                cells.append(f"{val:,}".rjust(w))
            else:
                cells.append(str(val).ljust(w))
        print("  " + "  ".join(cells))


def save_json(data, path, indent=2):
    """Save a dict to JSON, handling numpy types."""
    def default(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return str(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=default)
    print(f"  Saved JSON: {path}")


def load_kpi(filename):
    """Load a KPI CSV from the outputs directory."""
    path = DATA_OUTPUTS / filename
    if not path.exists():
        raise FileNotFoundError(f"KPI file not found: {path}")
    df = pd.read_csv(path)
    print(f"  Loaded {filename}: {len(df):,} rows")
    return df


if __name__ == "__main__":
    print("benchmarking_utils.py — shared utilities loaded")
    print(f"  Periods: {PERIODS}")
    print(f"  Product groups: {len(PRODUCT_GROUPS)}")
    print(f"  Cost assumptions: handling=GBP {COST_HANDLING:.0f}  FOS=GBP {COST_FOS_FEE:.0f} x {COST_FOS_RATE:.0%}  redress=GBP {COST_REDRESS:.0f}")
    x = [1774139, 1698000, 1670000, 1652438]
    print(f"  Market median: {median(x):,.0f}")
    print(f"  Market HHI (equal share): {hhi([0.25]*4):.1f}")
    print(f"  Gini test: {gini_coefficient([1,2,3,4,5]):.4f}")