# Tableau Dashboard Specification

## Tableau-Ready Files
All located in data/outputs/:
- tableau_firms.csv — firm benchmark (one row per firm per period)
- tableau_products.csv — product benchmark (one row per product per period)
- tableau_market.csv — market totals by period
- tableau_opportunities.csv — scored opportunity matrix

---

## Dashboard 1 — Executive Overview

**Sheets:**
1. Market Trend (Line/Bar) — market_complaints by reporting_period from tableau_market.csv
2. Product Mix Doughnut — total_complaints by product_group, filter reporting_period='2025H2'
3. Top Firms Bar — complaints_opened by firm_name, top N, filter reporting_period='2025H2'
4. KPI Summary Text — total market complaints, YoY change, number of firms

**Filters:** Reporting period (all by default)

---

## Dashboard 2 — Firm Benchmark

**Data source:** tableau_firms.csv

**Sheets:**
1. Firm Volume Trend (Line) — complaints_opened by reporting_period, filtered by firm_name
2. Uphold Rate Trend (Line) — uphold_rate_weighted_pct by reporting_period, filtered by firm_name
3. Closure Performance Bar — pct_3days_mean * 100 by reporting_period, filtered by firm_name
4. Peer Ranking Table — firm_name, complaints_opened, uphold_rate_weighted_pct, rank_by_volume for latest period
5. KPI Cards — latest period complaints, uphold %, closure %, volume rank

**Filters:** Firm name (parameter), Reporting period, Product group

**Calculated fields:**
- Period-over-period change: ZN(complaints_opened) - LOOKUP(ZN(complaints_opened), -1)
- Complaint rate per 1k: complaints_opened / NULLIF(complaint_rate_per_1k, 0) [use from source]

---

## Dashboard 3 — Product Benchmark

**Data source:** tableau_products.csv

**Sheets:**
1. Volume by Product Over Time (Grouped Bar or Stacked) — total_complaints by reporting_period, colour by product_group
2. Uphold Rate by Product (Line) — uphold_rate_weighted_pct by reporting_period, colour by product_group
3. Complaint Share Over Time (100% Stacked Bar) — complaint_share_pct by product_group and period
4. Product Summary Table — latest period: complaints, share %, uphold %, trend arrow

**Filters:** Reporting period, Product group

---

## Dashboard 4 — Priority Opportunities

**Data source:** tableau_opportunities.csv

**Sheets:**
1. Priority Matrix (Scatter/Bubble) — X: avg_uphold_rate_pct, Y: latest_volume, Size: priority_score, Colour: product_group
2. Ranked Opportunity Table — product_group, priority_rank, latest_volume, avg_uphold_rate_pct, avg_pct_closed_3days
3. Scenario Cards (Text) — from kpi_scenarios.csv: scenario name, assumption, key values

**Annotations:**
- Label bubbles with product_group names
- Add reference lines for market average uphold rate and market average volume
- Quadrant labels: High Volume / High Uphold = Highest Priority

---

## Colour Palette
- Primary: #2563eb (Banking)
- Purple: #7c3aed (Decumulation)
- Green: #059669 (Home Finance)
- Red: #dc2626 (Insurance)
- Amber: #d97706 (Investments)
- Background: #f0f4f8
- Header: #1e3a5f

---

## Notes for Tableau Setup
1. Connect to each tableau_*.csv as a separate data source or union them
2. Create a reporting_period order field (2024H1=1, 2024H2=2, 2025H1=3, 2025H2=4)
3. For uphold rate, source is already in percentage points (0-100)
4. For closure rates, source is in percentage points (0-100)
5. Complaint rate per 1k is only valid where denominator is present — use ISNULL filter
