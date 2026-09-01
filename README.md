# UK Retail Banking Complaints Benchmark

## Overview
Reproducible benchmark of UK retail banking complaint performance using publicly available FCA firm-level complaints data across four consecutive reporting periods (2024H1 – 2025H2).

## Project Structure
```
uk-banking-complaints-benchmark/
├── data/
│   ├── raw/                   FCA source Excel files (unchanged originals)
│   ├── processed/             complaints_clean.csv + DuckDB database
│   └── outputs/               KPI CSVs, SQL results, Tableau-ready files
├── notebooks/
│   ├── 01_ingest_and_clean.py   Phase 1-3: download validation, schema mapping, cleaning
│   ├── 02_kpis_and_analysis.py  Phase 4-5: KPI calculations, benchmarking, scenario model
│   ├── 03_sql_analysis.py       Phase 4 (SQL): DuckDB setup, 13 benchmark queries, validation
│   └── 04_build_dashboard.py    Build interactive HTML dashboard
├── sql/                       13 reusable SQL query files
├── tableau/                   Tableau-ready CSVs + dashboard specification
├── docs/
│   ├── methodology.md
│   ├── data_dictionary.md
│   ├── source_log.csv
│   └── data_quality_summary.json
├── dashboard.html             Interactive benchmark dashboard (open in browser)
└── README.md
```

## Data Sources
| Period | File | URL |
|--------|------|-----|
| 2024H1 | firm-level-complaints-data-2024-h1.xlsx | https://www.fca.org.uk/publication/data/firm-level-complaints-data-2024-h1.xlsx |
| 2024H2 | firm-level-complaints-data-2024-h2.xlsx | https://www.fca.org.uk/publication/data/firm-level-complaints-data-2024-h2.xlsx |
| 2025H1 | firm-level-complaints-data-2025-h1.xlsx | https://www.fca.org.uk/publication/data/firm-level-complaints-data-2025-h1.xlsx |
| 2025H2 | firm-level-complaints-data-2025-h2.xlsx | https://www.fca.org.uk/publication/data/firm-level-complaints-data-2025-h2.xlsx |

Downloaded: 2026-09-01. FCA publishes updates ~April and ~October each year.

## Quick Start

### Requirements
```bash
uv run --with pandas --with openpyxl --with numpy --with duckdb python notebooks/01_ingest_and_clean.py
uv run --with pandas --with numpy python notebooks/02_kpis_and_analysis.py
uv run --with pandas --with numpy --with duckdb python notebooks/03_sql_analysis.py
uv run --with pandas --with numpy python notebooks/04_build_dashboard.py
```
Or install dependencies: `pip install pandas openpyxl numpy duckdb`

### Run Order
1. `01_ingest_and_clean.py` — produces `data/processed/complaints_clean.csv`
2. `02_kpis_and_analysis.py` — produces all KPI and Tableau-ready CSVs in `data/outputs/`
3. `03_sql_analysis.py` — creates DuckDB database, runs 13 benchmark queries, validates against Python
4. `04_build_dashboard.py` — builds `dashboard.html`
5. Open `dashboard.html` in any browser — no server required

## Key Findings (2025H2)
- Market total: **1,652,438 complaints** opened across ~300 firms
- Banking and credit cards: **51% of all complaints** (844,807)
- Insurance and pure protection: **38% of all complaints** (620,885)
- Top firm by volume: NatWest (97,511), Lloyds (90,837), Barclays UK (85,996)
- Market trend: complaints fell from 1,774,139 (2024H1) to 1,652,438 (2025H2) — a 6.9% reduction

## Dashboard

[![Open Dashboard](https://img.shields.io/badge/Open%20Dashboard-Live%20Preview-2563eb?style=for-the-badge)](http://htmlpreview.github.io/?https://github.com/GagandeepSK/fca-banking-conduct-benchmark/blob/main/dashboard.html)

**[Click to open the interactive dashboard](http://htmlpreview.github.io/?https://github.com/GagandeepSK/fca-banking-conduct-benchmark/blob/main/dashboard.html)**

Or download `dashboard.html` and open locally — no server required. Four tabs:
1. **Executive Overview** — market totals, product mix, top firms
2. **Firm Benchmark** — select any top-30 firm, view volume/uphold/closure trends
3. **Product Benchmark** — all 5 product groups across all 4 periods
4. **Priority Opportunities** — scored opportunity matrix, scenario modelling

## Tableau
Tableau-ready CSVs in `data/outputs/`: `tableau_firms.csv`, `tableau_products.csv`, `tableau_market.csv`, `tableau_opportunities.csv`.
See `tableau/dashboard_spec.md` for full dashboard specification.

## Limitations
- Redress monetary values are not available at firm level in FCA data; a redress-risk proxy (upheld complaints × volume) is used instead
- Denominator (Context - Provision) units are thousands of relevant accounts/policies; PPI-related figures may be inflated per FCA notes
- Firm names standardised programmatically — minor variations may persist for less common names
- Rankings using complaint rate require denominator data; not all firms report denominators for all products
- Uphold rate does not alone imply root cause; aggregate data cannot establish causality

## Analytical Rules Applied
1. Raw FCA files are preserved unchanged in `data/raw/`
2. No missing values treated as zero unless explicitly stated
3. Scenario outputs are labelled as modelled, not observed
4. Size-adjusted rates only computed where denominator > 0
5. Python and SQL totals reconcile exactly for all four periods

## Source
Financial Conduct Authority (FCA) — https://www.fca.org.uk/data/complaints-data
Data published under Open Government Licence v3.0.
