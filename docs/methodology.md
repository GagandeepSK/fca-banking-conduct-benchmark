# Methodology

## Scope
Four FCA firm-level complaints reporting periods: 2024H1, 2024H2, 2025H1, 2025H2.
~300 firms per period. Five product groups: Banking and credit cards, Decumulation & pensions, Home finance, Insurance & pure protection, Investments.

## Data Collection
FCA publishes firm-level complaints data twice yearly (April and October). Files downloaded directly from fca.org.uk on 2026-09-01. Originals stored unchanged in data/raw/.

## Schema Mapping Across Periods
Sheet names differ between 2024 and 2025 files but data format is identical:

| Metric | 2024H1, 2024H2 Sheet | 2025H1, 2025H2 Sheet |
|--------|---------------------|---------------------|
| Complaints opened | Opened | Opened |
| Complaints closed | Closed | Closed |
| % closed within 3 days | Closed within 3 days | Percentage within 3 days |
| % closed 3 days to 8 weeks | After 3 days within 8 weeks | Percentage after 3 days, within |
| Uphold rate | Upheld | Percentage upheld |
| Denominator | Context - Provision | Context - Provision |

H2 2025 added a Grand Total column to main sheets — excluded from product-level melting.

## Data Structure
Each FCA sheet uses a wide format (products as columns). All sheets melted to long format (one row per firm, product, period), then joined on firm/product/period keys to produce a single clean table.

## Cleaning Rules
- Firm names standardised to title case; common abbreviations (PLC, LTD, HSBC, RBS etc.) preserved in upper case
- Product group names used as published; whitespace trimmed
- Percentages stored as proportions (0.0–1.0) in source; converted to % in KPI outputs
- Negative complaint volumes set to NaN (none found in this dataset)
- Proportions outside [0, 1] set to NaN (none found)
- Duplicate firm/product/period rows dropped (none found)

## KPI Definitions

### Complaint Volume
Total complaints_opened summed by firm, product, or period. Raw count from FCA data.

### Size-Adjusted Complaint Rate
complaints_opened / denominator
where denominator = Context - Provision value (thousands of relevant accounts/policies).
Scale: complaints per 1,000 relevant accounts/policies.
Only computed where denominator > 0 and not null.

### Closure Rate
complaints_closed / complaints_opened
Values above 1.0 are valid (firm closing backlog from prior periods). Capped at 2.0 for display.

### Uphold Rate
Stored as proportion in FCA data. For firm-level aggregation, weighted average by complaints_opened is used.
uphold_rate_weighted = SUM(uphold_rate * complaints_opened) / SUM(complaints_opened)

### Period-over-Period Change
Absolute: current_period_KPI - previous_period_KPI
Percentage: (current - previous) / previous * 100
Zero denominators produce NaN, not infinity.

### Priority Score (Opportunity Ranking)
Normalised 1–5 scores on three dimensions, combined additively:
- Volume score: higher complaint volume = higher score (1–5)
- Uphold signal score: higher uphold rate = higher score (1–5, proxy for valid complaint rate)
- Inverse closure score: lower % closed within 3 days = higher score (1–5)
Priority score = volume_score + uphold_score + inverse_closure_score
A higher score indicates a higher-priority operational improvement area.

### Redress Risk Proxy
Monetary redress is not available at firm level in FCA firm-specific data.
Proxy = complaints_opened * uphold_rate (estimated upheld complaints).
Used only as a relative risk indicator, not as a monetary estimate.

## Denominator Notes
Context - Provision values are in thousands of relevant accounts, policies, or transactions. FCA notes that PPI-related figures may be inflated because some firms cannot calculate total policies sold and use shorter-period or in-force figures instead. Complaint rates for Insurance and pure protection should be interpreted with this caveat.

## Validation
Python and SQL (DuckDB) totals reconcile exactly for all four period market totals. See data_quality_summary.json for per-field missing value counts.

## Limitations
1. Causal claims cannot be made from aggregate FCA data alone
2. Firm-level redress data not available; proxy used
3. Denominator availability varies by firm and product; complaint rates are not available for all combinations
4. Firm name standardisation is programmatic; manual review recommended for production use
5. Consumer Credit sheet (yearly/bi-annual reporters on a different schedule) excluded from main benchmark; available as separate table in raw data
6. Joint reporters appear once in data; their group attribution is as reported to FCA
