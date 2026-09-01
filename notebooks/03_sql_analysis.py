"""
Phase 4 (SQL) — Create DuckDB database and run all 13 benchmark queries.
Validates results against Python KPI outputs.
"""

import duckdb, pandas as pd, numpy as np
from pathlib import Path

ROOT    = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
PROC    = ROOT / "data" / "processed"
OUTPUTS = ROOT / "data" / "outputs"
SQL_DIR = ROOT / "sql"
SQL_DIR.mkdir(exist_ok=True)

DB_PATH = PROC / "complaints.duckdb"
if DB_PATH.exists(): DB_PATH.unlink()
con = duckdb.connect(str(DB_PATH))

# Load clean data into DuckDB
con.execute(f"""
CREATE TABLE complaints AS
SELECT * FROM read_csv_auto('{(PROC/"complaints_clean.csv").as_posix()}', header=true)
""")
print(f"DuckDB table created: {con.execute('SELECT COUNT(*) FROM complaints').fetchone()[0]} rows")

# ── Write and run each query ───────────────────────────────────────────────────
queries = {}

queries["01_total_by_firm.sql"] = """
-- Q1: Total complaints by firm (all periods)
SELECT
    firm_name,
    SUM(complaints_opened)                          AS total_complaints_all_periods,
    SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened ELSE 0 END) AS complaints_2025H2,
    SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened ELSE 0 END) AS complaints_2025H1,
    SUM(CASE WHEN reporting_period='2024H2' THEN complaints_opened ELSE 0 END) AS complaints_2024H2,
    SUM(CASE WHEN reporting_period='2024H1' THEN complaints_opened ELSE 0 END) AS complaints_2024H1
FROM complaints
GROUP BY firm_name
ORDER BY total_complaints_all_periods DESC;
"""

queries["02_total_by_product.sql"] = """
-- Q2: Total complaints by product group (all periods)
SELECT
    product_group,
    SUM(complaints_opened)  AS total_complaints,
    ROUND(SUM(complaints_opened) * 100.0 /
          SUM(SUM(complaints_opened)) OVER (), 2) AS market_share_pct
FROM complaints
GROUP BY product_group
ORDER BY total_complaints DESC;
"""

queries["03_by_period.sql"] = """
-- Q3: Complaints by reporting period (market totals)
SELECT
    reporting_period,
    SUM(complaints_opened)  AS total_complaints,
    SUM(complaints_closed)  AS total_closed,
    COUNT(DISTINCT firm_name) AS firms_reporting
FROM complaints
GROUP BY reporting_period
ORDER BY reporting_period;
"""

queries["04_firm_complaint_rate_ranking.sql"] = """
-- Q4: Firm complaint-rate ranking (complaints per 1,000 relevant accounts)
-- Only for firms with denominator data; latest period
SELECT
    firm_name,
    reporting_period,
    product_group,
    SUM(complaints_opened)          AS complaints_opened,
    SUM(denominator)                AS total_denominator_k,
    ROUND(SUM(complaints_opened) / NULLIF(SUM(denominator), 0), 4)
                                    AS complaint_rate_per_1k,
    RANK() OVER (
        PARTITION BY reporting_period
        ORDER BY SUM(complaints_opened) / NULLIF(SUM(denominator), 0) DESC
    )                               AS rate_rank
FROM complaints
WHERE denominator IS NOT NULL AND denominator > 0
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period, product_group
ORDER BY complaint_rate_per_1k DESC NULLS LAST
LIMIT 50;
"""

queries["05_product_complaint_rate_ranking.sql"] = """
-- Q5: Product complaint-rate ranking (latest period, weighted by denominator)
SELECT
    product_group,
    reporting_period,
    SUM(complaints_opened)   AS total_complaints,
    SUM(denominator)         AS total_denominator_k,
    ROUND(SUM(complaints_opened) / NULLIF(SUM(denominator), 0), 4)
                             AS complaint_rate_per_1k,
    RANK() OVER (ORDER BY SUM(complaints_opened) / NULLIF(SUM(denominator), 0) DESC)
                             AS rate_rank
FROM complaints
WHERE denominator IS NOT NULL AND denominator > 0
  AND reporting_period = '2025H2'
GROUP BY product_group, reporting_period
ORDER BY complaint_rate_per_1k DESC NULLS LAST;
"""

queries["06_closure_performance_ranking.sql"] = """
-- Q6: Closure performance ranking by firm (latest period, avg % closed within 3 days)
SELECT
    firm_name,
    reporting_period,
    ROUND(AVG(pct_closed_3days) * 100, 2)       AS avg_pct_closed_3days,
    ROUND(AVG(pct_closed_3to8weeks) * 100, 2)   AS avg_pct_closed_3to8weeks,
    ROUND(AVG(pct_closed_3days + pct_closed_3to8weeks) * 100, 2)
                                                 AS avg_pct_within_8weeks,
    SUM(complaints_opened)                       AS complaints_opened,
    RANK() OVER (ORDER BY AVG(pct_closed_3days) DESC)
                                                 AS fast_closure_rank
FROM complaints
WHERE pct_closed_3days IS NOT NULL
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period
ORDER BY avg_pct_closed_3days DESC;
"""

queries["07_uphold_rate_ranking.sql"] = """
-- Q7: Uphold rate ranking by firm (weighted by complaints_opened, latest period)
SELECT
    firm_name,
    reporting_period,
    SUM(complaints_opened)                                          AS complaints_opened,
    ROUND(SUM(uphold_rate * complaints_opened) /
          NULLIF(SUM(complaints_opened), 0) * 100, 2)             AS uphold_rate_weighted_pct,
    RANK() OVER (
        ORDER BY SUM(uphold_rate * complaints_opened) /
                 NULLIF(SUM(complaints_opened), 0) DESC
    )                                                              AS uphold_rank
FROM complaints
WHERE uphold_rate IS NOT NULL AND complaints_opened IS NOT NULL
  AND reporting_period = '2025H2'
GROUP BY firm_name, reporting_period
ORDER BY uphold_rate_weighted_pct DESC;
"""

queries["08_redress_ranking.sql"] = """
-- Q8: Redress proxy — high uphold rate + high volume = highest redress risk
-- (Monetary redress not available at firm level in FCA data; this is a risk proxy)
SELECT
    firm_name,
    reporting_period,
    product_group,
    complaints_opened,
    ROUND(uphold_rate * 100, 2)          AS uphold_rate_pct,
    ROUND(complaints_opened * uphold_rate, 0)
                                         AS estimated_upheld_complaints,
    RANK() OVER (
        PARTITION BY reporting_period
        ORDER BY complaints_opened * uphold_rate DESC
    )                                    AS redress_risk_rank
FROM complaints
WHERE uphold_rate IS NOT NULL AND complaints_opened IS NOT NULL
  AND reporting_period = '2025H2'
ORDER BY estimated_upheld_complaints DESC NULLS LAST
LIMIT 50;
"""

queries["09_period_over_period.sql"] = """
-- Q9: Period-over-period complaint volume change by firm
WITH pivoted AS (
    SELECT
        firm_name,
        SUM(CASE WHEN reporting_period='2024H1' THEN complaints_opened END) AS vol_2024H1,
        SUM(CASE WHEN reporting_period='2024H2' THEN complaints_opened END) AS vol_2024H2,
        SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened END) AS vol_2025H1,
        SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened END) AS vol_2025H2
    FROM complaints
    GROUP BY firm_name
)
SELECT
    firm_name,
    vol_2024H1, vol_2024H2, vol_2025H1, vol_2025H2,
    ROUND((vol_2025H2 - vol_2025H1) * 100.0 / NULLIF(vol_2025H1, 0), 2)
        AS pct_change_2025H2_vs_2025H1,
    ROUND((vol_2025H2 - vol_2024H2) * 100.0 / NULLIF(vol_2024H2, 0), 2)
        AS pct_change_yoy
FROM pivoted
WHERE vol_2025H2 IS NOT NULL
ORDER BY ABS(pct_change_2025H2_vs_2025H1) DESC NULLS LAST;
"""

queries["10_top_firms_by_product.sql"] = """
-- Q10: Top 10 firms by complaint volume for each product group (latest period)
SELECT *
FROM (
    SELECT
        product_group,
        firm_name,
        complaints_opened,
        RANK() OVER (PARTITION BY product_group ORDER BY complaints_opened DESC)
            AS product_rank
    FROM complaints
    WHERE reporting_period = '2025H2'
      AND complaints_opened IS NOT NULL
)
WHERE product_rank <= 10
ORDER BY product_group, product_rank;
"""

queries["11_top_products_by_firm.sql"] = """
-- Q11: Top products by firm (latest period, firms with >1000 complaints)
SELECT
    firm_name,
    product_group,
    complaints_opened,
    ROUND(complaints_opened * 100.0 /
          SUM(complaints_opened) OVER (PARTITION BY firm_name), 2)
        AS pct_of_firm_total
FROM complaints
WHERE reporting_period = '2025H2'
  AND firm_name IN (
      SELECT firm_name FROM complaints
      WHERE reporting_period = '2025H2'
      GROUP BY firm_name
      HAVING SUM(complaints_opened) > 1000
  )
ORDER BY firm_name, complaints_opened DESC;
"""

queries["12_largest_deteriorations.sql"] = """
-- Q12: Largest deteriorations in complaint volume (2025H2 vs 2025H1)
WITH changes AS (
    SELECT
        firm_name,
        SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened END) AS vol_prior,
        SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened END) AS vol_curr
    FROM complaints
    GROUP BY firm_name
)
SELECT
    firm_name,
    vol_prior,
    vol_curr,
    (vol_curr - vol_prior)  AS abs_change,
    ROUND((vol_curr - vol_prior) * 100.0 / NULLIF(vol_prior, 0), 2)
                            AS pct_change
FROM changes
WHERE vol_prior IS NOT NULL AND vol_curr IS NOT NULL
  AND vol_curr > vol_prior
ORDER BY abs_change DESC
LIMIT 20;
"""

queries["13_largest_improvements.sql"] = """
-- Q13: Largest improvements in complaint volume (2025H2 vs 2025H1)
WITH changes AS (
    SELECT
        firm_name,
        SUM(CASE WHEN reporting_period='2025H1' THEN complaints_opened END) AS vol_prior,
        SUM(CASE WHEN reporting_period='2025H2' THEN complaints_opened END) AS vol_curr
    FROM complaints
    GROUP BY firm_name
)
SELECT
    firm_name,
    vol_prior,
    vol_curr,
    (vol_prior - vol_curr)  AS abs_improvement,
    ROUND((vol_prior - vol_curr) * 100.0 / NULLIF(vol_prior, 0), 2)
                            AS pct_improvement
FROM changes
WHERE vol_prior IS NOT NULL AND vol_curr IS NOT NULL
  AND vol_curr < vol_prior
ORDER BY abs_improvement DESC
LIMIT 20;
"""

# Write SQL files and run them
for fname, sql in queries.items():
    sql_path = SQL_DIR / fname
    with open(sql_path, "w") as f:
        f.write(sql.strip() + "\n")
    result = con.execute(sql).df()
    out_csv = OUTPUTS / f"sql_{fname.replace('.sql','.csv')}"
    result.to_csv(out_csv, index=False)
    print(f"  {fname}: {len(result)} rows → {out_csv.name}")

# ── Validation: Python vs SQL reconciliation ──────────────────────────────────
print("\n── Validation: Python vs SQL ──")

py_market = pd.read_csv(OUTPUTS / "kpi_volume_by_period.csv")
sql_market = con.execute("""
SELECT reporting_period, SUM(complaints_opened) AS total FROM complaints
GROUP BY reporting_period ORDER BY reporting_period
""").df()

for period in ["2024H1","2024H2","2025H1","2025H2"]:
    py_val = py_market[py_market["reporting_period"]==period]["market_complaints"].values
    sql_val = sql_market[sql_market["reporting_period"]==period]["total"].values
    if len(py_val) and len(sql_val):
        match = "✓" if abs(float(py_val[0]) - float(sql_val[0])) < 0.01 else "✗ MISMATCH"
        print(f"  {period}: Python={int(py_val[0]):,}  SQL={int(sql_val[0]):,}  {match}")

print("\n✓ SQL phase complete")
con.close()
