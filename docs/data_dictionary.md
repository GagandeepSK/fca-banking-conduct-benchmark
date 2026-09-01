# Data Dictionary

| Column | Definition | Source | Data Type | Transformation | Notes |
|--------|-----------|--------|-----------|---------------|-------|
| reporting_period | FCA 6-month reporting period label | Derived | String | Mapped from period_start/end dates | Values: 2024H1, 2024H2, 2025H1, 2025H2 |
| firm_name | Standardised firm name | FCA Firm Name column | String | Title-case; abbreviations preserved | Minor variations may exist for rare firms |
| firm_group | Parent group name as reported to FCA | FCA Group column | String | None | Some firms report NO GROUP |
| joint_reporting | Whether firm is a joint reporter | FCA Joint Reporting column | String | None | yes/no |
| product_group | FCA product category | Column header in source wide format | String | Whitespace trimmed | 5 groups: Banking and credit cards, Decumulation & pensions, Home finance, Insurance & pure protection, Investments |
| complaints_opened | Number of complaints opened in the reporting period | FCA Opened sheet | Integer | Negative values set to NaN (none found) | Raw count |
| complaints_closed | Number of complaints closed in the reporting period | FCA Closed sheet | Integer | None | May exceed complaints_opened (backlog clearance) |
| pct_closed_3days | Proportion of closed complaints resolved within 3 days | FCA closure timing sheet | Float [0,1] | Out-of-range set to NaN (none found) | FCA-defined closure timing metric |
| pct_closed_3to8weeks | Proportion of closed complaints resolved after 3 days but within 8 weeks | FCA closure timing sheet | Float [0,1] | Out-of-range set to NaN (none found) | FCA-defined closure timing metric |
| uphold_rate | Proportion of closed complaints upheld in favour of the complainant | FCA Upheld/Percentage upheld sheet | Float [0,1] | Out-of-range set to NaN (none found) | Not a causal indicator on its own |
| denominator | Number of relevant accounts, policies, or transactions in thousands | FCA Context - Provision sheet | Float | None | Used to calculate size-adjusted complaint rate; see methodology for PPI caveat |
| source_file | Original source filename | Derived | String | None | Traceability to raw file |

## Derived KPIs (data/outputs/)

| KPI | Definition | File | Notes |
|-----|-----------|------|-------|
| complaint_rate_per_1k | complaints_opened / denominator | kpi_complaint_rate.csv | Only where denominator > 0 |
| closure_rate | complaints_closed / complaints_opened | kpi_closure_performance.csv | Capped at 2.0 |
| uphold_rate_weighted_pct | Weighted avg uphold rate % by firm | kpi_uphold_by_firm.csv | Weight = complaints_opened |
| complaint_share_pct | Firm or product complaints / market total * 100 | kpi_volume_by_firm/product.csv | Per period |
| abs_change | current_period_KPI - previous_period_KPI | trend files | NaN for first period |
| pct_change | abs_change / previous_period_KPI * 100 | trend files | NaN where prior = 0 |
| estimated_upheld_complaints | complaints_opened * uphold_rate | sql_08_redress_ranking.csv | Redress risk proxy only |
| priority_score | Composite score: volume (1-5) + uphold signal (1-5) + inverse closure (1-5) | kpi_opportunities.csv | Higher = higher priority |
