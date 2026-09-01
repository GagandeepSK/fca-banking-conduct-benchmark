#!/usr/bin/env python3
# 09_sql_query_library.py
# Complete DuckDB SQL query library — all benchmark queries with execution and validation.
# Author: Gagandeep Kapoor

import os, json, warnings
from pathlib import Path
from datetime import datetime
import pandas as pd
import duckdb
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE / "data" / "processed"
DATA_OUTPUTS   = BASE / "data" / "outputs"
DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
PERIODS = ["2024H1","2024H2","2025H1","2025H2"]



# ──────────────────────────────────────────────────────────────────
# Q01_market_overview: Market Overview by Period
# ──────────────────────────────────────────────────────────────────

SQL_Q01_market_overview = """
SELECT
    period,
    COUNT(DISTINCT firm_name)                                           AS n_firms,
    SUM(complaints_opened)                                              AS total_opened,
    SUM(complaints_closed)                                              AS total_closed,
    SUM(closed_within_8_weeks)                                         AS total_closed_8wk,
    SUM(upheld)                                                        AS total_upheld,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate
FROM complaints
GROUP BY period
ORDER BY period
"""

def run_q01_market_overview(con, verbose=True):
    """
    Market Overview by Period
    
    Aggregate market-level complaint totals, rates, and firm counts across all periods.
    """
    try:
        df = con.execute(SQL_Q01_market_overview).df()
        if verbose:
            print(f"  Q01_market_overview: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q01_market_overview.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q01_market_overview: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q02_top30_by_volume: Top 30 Firms by Complaint Volume (2025H2)
# ──────────────────────────────────────────────────────────────────

SQL_Q02_top30_by_volume = """
SELECT
    ROW_NUMBER() OVER (ORDER BY SUM(complaints_opened) DESC) AS rank,
    firm_name,
    SUM(complaints_opened)                                             AS opened,
    SUM(complaints_closed)                                             AS closed,
    SUM(upheld)                                                        AS upheld_n,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate
FROM complaints
WHERE period = '2025H2'
GROUP BY firm_name
ORDER BY opened DESC
LIMIT 30
"""

def run_q02_top30_by_volume(con, verbose=True):
    """
    Top 30 Firms by Complaint Volume (2025H2)
    
    Rank firms by total complaints opened in 2025H2; include uphold and closure metrics.
    """
    try:
        df = con.execute(SQL_Q02_top30_by_volume).df()
        if verbose:
            print(f"  Q02_top30_by_volume: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q02_top30_by_volume.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q02_top30_by_volume: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q03_highest_uphold_rate: Firms with Highest Uphold Rate (min 500 complaints)
# ──────────────────────────────────────────────────────────────────

SQL_Q03_highest_uphold_rate = """
SELECT
    firm_name,
    period,
    SUM(complaints_opened)                                             AS opened,
    SUM(complaints_closed)                                             AS closed,
    SUM(upheld)                                                        AS upheld_n,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    CASE WHEN SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) >= 0.5 THEN 'RED'
         WHEN SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) >= 0.35 THEN 'AMBER'
         ELSE 'GREEN' END                                              AS cd_rag
FROM complaints
WHERE period = '2025H2'
GROUP BY firm_name, period
HAVING SUM(complaints_closed) >= 500
ORDER BY uphold_rate DESC
LIMIT 30
"""

def run_q03_highest_uphold_rate(con, verbose=True):
    """
    Firms with Highest Uphold Rate (min 500 complaints)
    
    Identify firms where the FCA is most likely to take supervisory interest under Consumer Duty.
    """
    try:
        df = con.execute(SQL_Q03_highest_uphold_rate).df()
        if verbose:
            print(f"  Q03_highest_uphold_rate: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q03_highest_uphold_rate.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q03_highest_uphold_rate: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q04_slowest_closure: Firms with Slowest 8-Week Closure Rate
# ──────────────────────────────────────────────────────────────────

SQL_Q04_slowest_closure = """
SELECT
    firm_name,
    period,
    SUM(complaints_opened)                                              AS opened,
    SUM(complaints_closed)                                              AS closed,
    SUM(closed_within_8_weeks)                                         AS closed_8wk,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)       AS uphold_rate
FROM complaints
WHERE period = '2025H2'
GROUP BY firm_name, period
HAVING SUM(complaints_closed) >= 500
ORDER BY closure_8wk_rate ASC
LIMIT 30
"""

def run_q04_slowest_closure(con, verbose=True):
    """
    Firms with Slowest 8-Week Closure Rate
    
    Under Consumer Duty, slow closure is a process quality metric. Low 8-week rates indicate systemic issues.
    """
    try:
        df = con.execute(SQL_Q04_slowest_closure).df()
        if verbose:
            print(f"  Q04_slowest_closure: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q04_slowest_closure.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q04_slowest_closure: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q05_product_period_matrix: Product Group × Period Complaint Matrix
# ──────────────────────────────────────────────────────────────────

SQL_Q05_product_period_matrix = """
SELECT
    product_group,
    period,
    SUM(complaints_opened)                                              AS opened,
    SUM(complaints_closed)                                              AS closed,
    SUM(upheld)                                                        AS upheld_n,
    COUNT(DISTINCT firm_name)                                          AS n_firms,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate,
    ROUND(SUM(complaints_opened)*1.0 / SUM(SUM(complaints_opened)) OVER (PARTITION BY period), 4) AS market_share
FROM complaints
GROUP BY product_group, period
ORDER BY product_group, period
"""

def run_q05_product_period_matrix(con, verbose=True):
    """
    Product Group × Period Complaint Matrix
    
    Cross-tab of complaint volumes and uphold rates for all product groups across all periods.
    """
    try:
        df = con.execute(SQL_Q05_product_period_matrix).df()
        if verbose:
            print(f"  Q05_product_period_matrix: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q05_product_period_matrix.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q05_product_period_matrix: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q06_market_share_2025h2: Market Share of Complaints (2025H2)
# ──────────────────────────────────────────────────────────────────

SQL_Q06_market_share_2025h2 = """
WITH ranked AS (
    SELECT
        firm_name,
        SUM(complaints_opened) AS opened,
        SUM(complaints_opened) * 1.0 / SUM(SUM(complaints_opened)) OVER () AS share
    FROM complaints
    WHERE period = '2025H2'
    GROUP BY firm_name
)
SELECT
    firm_name,
    opened,
    ROUND(share, 6)                                           AS market_share,
    ROUND(SUM(share) OVER (ORDER BY opened DESC ROWS UNBOUNDED PRECEDING), 4) AS cumulative_share
FROM ranked
ORDER BY opened DESC
LIMIT 50
"""

def run_q06_market_share_2025h2(con, verbose=True):
    """
    Market Share of Complaints (2025H2)
    
    Cumulative concentration analysis: how many firms account for 50%, 80%, 90% of complaints.
    """
    try:
        df = con.execute(SQL_Q06_market_share_2025h2).df()
        if verbose:
            print(f"  Q06_market_share_2025h2: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q06_market_share_2025h2.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q06_market_share_2025h2: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q07_period_change_per_firm: Period-on-Period Volume Change Per Firm
# ──────────────────────────────────────────────────────────────────

SQL_Q07_period_change_per_firm = """
WITH period_vols AS (
    SELECT firm_name, period, SUM(complaints_opened) AS opened
    FROM complaints
    GROUP BY firm_name, period
),
with_prev AS (
    SELECT
        firm_name, period, opened,
        LAG(opened) OVER (PARTITION BY firm_name ORDER BY period) AS prev_opened
    FROM period_vols
)
SELECT
    firm_name, period, opened, prev_opened,
    ROUND((opened - prev_opened) * 1.0 / NULLIF(prev_opened, 0), 4) AS pct_change
FROM with_prev
WHERE prev_opened IS NOT NULL
ORDER BY ABS(pct_change) DESC
LIMIT 50
"""

def run_q07_period_change_per_firm(con, verbose=True):
    """
    Period-on-Period Volume Change Per Firm
    
    Flag firms with largest increases or decreases in complaint volumes between consecutive periods.
    """
    try:
        df = con.execute(SQL_Q07_period_change_per_firm).df()
        if verbose:
            print(f"  Q07_period_change_per_firm: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q07_period_change_per_firm.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q07_period_change_per_firm: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q08_decumulation_pensions_risk: Decumulation & Pensions — Consumer Duty Red Flag
# ──────────────────────────────────────────────────────────────────

SQL_Q08_decumulation_pensions_risk = """
SELECT
    firm_name, period,
    SUM(complaints_opened)                                              AS opened,
    SUM(complaints_closed)                                              AS closed,
    SUM(upheld)                                                        AS upheld_n,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate,
    CASE WHEN SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) >= 0.70 THEN 'CRITICAL'
         WHEN SUM(upheld)*1.0/NULLIF(SUM(complaints_closed),0) >= 0.50 THEN 'HIGH'
         ELSE 'MODERATE' END                                           AS risk_level
FROM complaints
WHERE product_group = 'Decumulation and pensions'
GROUP BY firm_name, period
HAVING SUM(complaints_closed) >= 50
ORDER BY uphold_rate DESC
"""

def run_q08_decumulation_pensions_risk(con, verbose=True):
    """
    Decumulation & Pensions — Consumer Duty Red Flag
    
    This product group consistently shows the highest uphold rates. Firms above 70% face heightened supervisory risk.
    """
    try:
        df = con.execute(SQL_Q08_decumulation_pensions_risk).df()
        if verbose:
            print(f"  Q08_decumulation_pensions_risk: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q08_decumulation_pensions_risk.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q08_decumulation_pensions_risk: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q09_cost_exposure_top20: Modelled Cost Exposure — Top 20 Firms (2025H2)
# ──────────────────────────────────────────────────────────────────

SQL_Q09_cost_exposure_top20 = """
SELECT
    firm_name,
    SUM(complaints_opened)                                              AS opened,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(complaints_opened) * 200.0, 0)                          AS handling_cost_gbp,
    ROUND(SUM(complaints_opened) * 0.08 * 650.0, 0)                   AS fos_cost_gbp,
    ROUND(SUM(upheld) * 300.0, 0)                                      AS redress_cost_gbp,
    ROUND(SUM(complaints_opened)*200.0 + SUM(complaints_opened)*0.08*650.0 + SUM(upheld)*300.0, 0) AS total_cost_gbp
FROM complaints
WHERE period = '2025H2'
GROUP BY firm_name
ORDER BY total_cost_gbp DESC
LIMIT 20
"""

def run_q09_cost_exposure_top20(con, verbose=True):
    """
    Modelled Cost Exposure — Top 20 Firms (2025H2)
    
    Modelled total cost = handling (GBP 200) + FOS (GBP 650 x 8%) + redress (GBP 300 per upheld).
    """
    try:
        df = con.execute(SQL_Q09_cost_exposure_top20).df()
        if verbose:
            print(f"  Q09_cost_exposure_top20: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q09_cost_exposure_top20.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q09_cost_exposure_top20: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q10_firm_trend_4periods: Firm Volume Trend Across All 4 Periods
# ──────────────────────────────────────────────────────────────────

SQL_Q10_firm_trend_4periods = """
WITH firm_period AS (
    SELECT firm_name, period, SUM(complaints_opened) AS opened
    FROM complaints
    GROUP BY firm_name, period
),
pivot AS (
    SELECT
        firm_name,
        MAX(CASE WHEN period = '2024H1' THEN opened END) AS v_2024h1,
        MAX(CASE WHEN period = '2024H2' THEN opened END) AS v_2024h2,
        MAX(CASE WHEN period = '2025H1' THEN opened END) AS v_2025h1,
        MAX(CASE WHEN period = '2025H2' THEN opened END) AS v_2025h2
    FROM firm_period
    GROUP BY firm_name
    HAVING COUNT(DISTINCT period) = 4
)
SELECT *,
    ROUND((v_2025h2 - v_2024h1) * 1.0 / NULLIF(v_2024h1, 0), 4) AS pct_change_total
FROM pivot
ORDER BY pct_change_total DESC
"""

def run_q10_firm_trend_4periods(con, verbose=True):
    """
    Firm Volume Trend Across All 4 Periods
    
    Pivot complaint volumes for firms present in all 4 periods; flag direction of trend.
    """
    try:
        df = con.execute(SQL_Q10_firm_trend_4periods).df()
        if verbose:
            print(f"  Q10_firm_trend_4periods: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q10_firm_trend_4periods.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q10_firm_trend_4periods: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q11_peer_group_medians: Peer Group Median Uphold Rates by Size Band (2025H2)
# ──────────────────────────────────────────────────────────────────

SQL_Q11_peer_group_medians = """
WITH firm_stats AS (
    SELECT
        firm_name,
        SUM(complaints_opened) AS opened,
        ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS uphold_rate,
        ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk,
        CASE WHEN SUM(complaints_opened) >= 50000 THEN 'Large (>50k)'
             WHEN SUM(complaints_opened) >= 10000 THEN 'Medium (10-50k)'
             WHEN SUM(complaints_opened) >= 1000  THEN 'Small (1-10k)'
             ELSE 'Micro (<1k)' END AS size_band
    FROM complaints
    WHERE period = '2025H2'
    GROUP BY firm_name
)
SELECT
    size_band,
    COUNT(*) AS n_firms,
    ROUND(MEDIAN(opened), 0)      AS median_volume,
    ROUND(MEDIAN(uphold_rate), 4) AS median_uphold,
    ROUND(MEDIAN(closure_8wk), 4) AS median_closure_8wk,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY uphold_rate), 4) AS p25_uphold,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY uphold_rate), 4) AS p75_uphold
FROM firm_stats
GROUP BY size_band
ORDER BY median_volume DESC
"""

def run_q11_peer_group_medians(con, verbose=True):
    """
    Peer Group Median Uphold Rates by Size Band (2025H2)
    
    Segment firms into size bands; compute median and IQR uphold rates for peer benchmarking.
    """
    try:
        df = con.execute(SQL_Q11_peer_group_medians).df()
        if verbose:
            print(f"  Q11_peer_group_medians: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q11_peer_group_medians.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q11_peer_group_medians: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q12_banking_cc_top_firms: Banking & Credit Cards — Top 15 Firms (2025H2)
# ──────────────────────────────────────────────────────────────────

SQL_Q12_banking_cc_top_firms = """
SELECT
    firm_name,
    SUM(complaints_opened)                                              AS opened,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4)      AS uphold_rate,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate,
    ROUND(SUM(complaints_opened)*1.0 / SUM(SUM(complaints_opened)) OVER (), 4) AS sector_share
FROM complaints
WHERE period = '2025H2'
  AND product_group = 'Banking and credit cards'
GROUP BY firm_name
ORDER BY opened DESC
LIMIT 15
"""

def run_q12_banking_cc_top_firms(con, verbose=True):
    """
    Banking & Credit Cards — Top 15 Firms (2025H2)
    
    Banking and credit cards accounts for 51% of market complaints. Firm-level breakdown.
    """
    try:
        df = con.execute(SQL_Q12_banking_cc_top_firms).df()
        if verbose:
            print(f"  Q12_banking_cc_top_firms: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q12_banking_cc_top_firms.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q12_banking_cc_top_firms: ERROR — {e}")
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Q13_cd_red_flag_firms: All Consumer Duty RED Flag Firms (All Periods)
# ──────────────────────────────────────────────────────────────────

SQL_Q13_cd_red_flag_firms = """
SELECT
    firm_name, period,
    SUM(complaints_opened)  AS opened,
    SUM(complaints_closed)  AS closed,
    SUM(upheld)            AS upheld_n,
    ROUND(SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS uphold_rate,
    product_group,
    ROUND(SUM(closed_within_8_weeks)*1.0 / NULLIF(SUM(complaints_closed),0), 4) AS closure_8wk_rate
FROM complaints
GROUP BY firm_name, period, product_group
HAVING SUM(complaints_closed) >= 500
   AND SUM(upheld)*1.0 / NULLIF(SUM(complaints_closed),0) >= 0.50
ORDER BY uphold_rate DESC, opened DESC
"""

def run_q13_cd_red_flag_firms(con, verbose=True):
    """
    All Consumer Duty RED Flag Firms (All Periods)
    
    List all firm-period combinations where uphold rate >= 50% and volume >= 500. Primary supervisory signal.
    """
    try:
        df = con.execute(SQL_Q13_cd_red_flag_firms).df()
        if verbose:
            print(f"  Q13_cd_red_flag_firms: {len(df):,} rows")
            if len(df) > 0:
                cols = list(df.columns)
                print(f"    cols: {cols[:6]}")
        out = DATA_OUTPUTS / "q13_cd_red_flag_firms.csv"
        df.to_csv(out, index=False)
        return df
    except Exception as e:
        if verbose: print(f"  Q13_cd_red_flag_firms: ERROR — {e}")
        return pd.DataFrame()


ALL_QUERIES = [
    (run_q01_market_overview, "Market Overview by Period"),
    (run_q02_top30_by_volume, "Top 30 Firms by Complaint Volume (2025H2)"),
    (run_q03_highest_uphold_rate, "Firms with Highest Uphold Rate (min 500 complaints)"),
    (run_q04_slowest_closure, "Firms with Slowest 8-Week Closure Rate"),
    (run_q05_product_period_matrix, "Product Group × Period Complaint Matrix"),
    (run_q06_market_share_2025h2, "Market Share of Complaints (2025H2)"),
    (run_q07_period_change_per_firm, "Period-on-Period Volume Change Per Firm"),
    (run_q08_decumulation_pensions_risk, "Decumulation & Pensions — Consumer Duty Red Flag"),
    (run_q09_cost_exposure_top20, "Modelled Cost Exposure — Top 20 Firms (2025H2)"),
    (run_q10_firm_trend_4periods, "Firm Volume Trend Across All 4 Periods"),
    (run_q11_peer_group_medians, "Peer Group Median Uphold Rates by Size Band (2025H2)"),
    (run_q12_banking_cc_top_firms, "Banking & Credit Cards — Top 15 Firms (2025H2)"),
    (run_q13_cd_red_flag_firms, "All Consumer Duty RED Flag Firms (All Periods)"),
]


def setup_duckdb(df):
    """Create in-memory DuckDB connection with complaints table."""
    con = duckdb.connect(":memory:")
    con.register("complaints", df)
    print(f"  DuckDB: registered complaints table ({len(df):,} rows)")
    return con


def load_data():
    clean = DATA_PROCESSED / "complaints_clean.csv"
    if not clean.exists():
        raise FileNotFoundError(f"Run 01_ingest_and_clean.py first. Missing: {clean}")
    return pd.read_csv(clean)


def run_all_queries(con):
    print("
" + "="*70)
    print("RUNNING ALL SQL QUERIES")
    print("="*70)
    results = {}
    for fn, title in ALL_QUERIES:
        print(f"
  Running: {title}")
        df = fn(con, verbose=True)
        results[fn.__name__] = {"rows": len(df), "columns": list(df.columns)}
    return results


def main():
    print("
UK Banking Complaints — SQL Query Library")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    df  = load_data()
    con = setup_duckdb(df)
    results = run_all_queries(con)
    print("
" + "="*70)
    print(f"COMPLETE: {len(results)} queries run, outputs saved to {DATA_OUTPUTS}")
    print("="*70)


if __name__ == "__main__":
    main()