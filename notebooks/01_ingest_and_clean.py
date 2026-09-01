"""
Phase 1-3 — Ingest, Inspect, Clean, Combine
Reads all 4 FCA firm-level Excel files, maps fields across schema versions,
melts wide product columns to long format, joins metrics, outputs clean CSV.
"""

import pandas as pd
import numpy as np
import os, json
from pathlib import Path
from datetime import date

ROOT = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
PROC.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

PRODUCT_COLS = [
    "Banking and credit cards",
    "Decumulation & pensions",
    "Home finance",
    "Insurance & pure protection",
    "Investments",
]

# Canonical key for each possible sheet name
SHEET_ALIASES = {
    "Opened":                           "opened",
    "Closed":                           "closed",
    "Closed within 3 days":             "pct_3days",
    "Percentage within 3 days":         "pct_3days",
    "After 3 days within 8 weeks":      "pct_3to8weeks",
    "Percentage after 3 days, within":  "pct_3to8weeks",
    "Upheld":                           "uphold_rate",
    "Percentage upheld":                "uphold_rate",
    "Context - Provision":              "context_provision",
}

KEY_TO_COL = {
    "opened":           "complaints_opened",
    "closed":           "complaints_closed",
    "pct_3days":        "pct_closed_3days",
    "pct_3to8weeks":    "pct_closed_3to8weeks",
    "uphold_rate":      "uphold_rate",
    "context_provision":"denominator",
}

FILES = [
    {"filename":"firm-level-complaints-data-2024-h1.xlsx","period_label":"2024H1",
     "period_start":"2024-01-01","period_end":"2024-06-30",
     "url":"https://www.fca.org.uk/publication/data/firm-level-complaints-data-2024-h1.xlsx"},
    {"filename":"firm-level-complaints-data-2024-h2.xlsx","period_label":"2024H2",
     "period_start":"2024-07-01","period_end":"2024-12-31",
     "url":"https://www.fca.org.uk/publication/data/firm-level-complaints-data-2024-h2.xlsx"},
    {"filename":"firm-level-complaints-data-2025-h1.xlsx","period_label":"2025H1",
     "period_start":"2025-01-01","period_end":"2025-06-30",
     "url":"https://www.fca.org.uk/publication/data/firm-level-complaints-data-2025-h1.xlsx"},
    {"filename":"firm-level-complaints-data-2025-h2.xlsx","period_label":"2025H2",
     "period_start":"2025-07-01","period_end":"2025-12-31",
     "url":"https://www.fca.org.uk/publication/data/firm-level-complaints-data-2025-h2.xlsx"},
]

ID_COLS = ["firm_name_raw","group_raw","joint_reporting","reporting_period_raw","product_group_raw"]


def read_sheet(xl, sheet_name):
    df = xl.parse(sheet_name, header=0)
    cols = list(df.columns)
    renames = {}
    if len(cols) >= 1: renames[cols[0]] = "firm_name_raw"
    if len(cols) >= 2: renames[cols[1]] = "group_raw"
    if len(cols) >= 3: renames[cols[2]] = "joint_reporting"
    if len(cols) >= 4: renames[cols[3]] = "reporting_period_raw"
    df = df.rename(columns=renames)
    return df[df["firm_name_raw"].notna()].copy()


def melt_sheet(df_wide, value_name):
    present = [c for c in PRODUCT_COLS if c in df_wide.columns]
    df_long = df_wide[["firm_name_raw","group_raw","joint_reporting",
                        "reporting_period_raw"] + present].melt(
        id_vars=["firm_name_raw","group_raw","joint_reporting","reporting_period_raw"],
        value_vars=present,
        var_name="product_group_raw",
        value_name=value_name,
    )
    return df_long.dropna(subset=[value_name]).reset_index(drop=True)


def std_firm(name):
    if pd.isna(name): return name
    words = []
    for w in str(name).strip().split():
        if w.upper() in ("PLC","LTD","LLC","LLP","UK","GB","HSBC","MBNA","RBS",
                         "TSB","CIBC","NWB","AIB","ISA","PPI","FSA","FCA"):
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    return " ".join(words)


all_frames = []
quality_notes = []

for meta in FILES:
    path = RAW / meta["filename"]
    print(f"\nProcessing {meta['period_label']} — {meta['filename']}")
    xl = pd.ExcelFile(path)

    # Map available sheets to canonical keys
    canon = {SHEET_ALIASES[sh]: sh for sh in xl.sheet_names if sh in SHEET_ALIASES}
    print(f"  Mapped: {sorted(canon.keys())}")

    # Melt each metric sheet
    melted = {}
    for key, col in KEY_TO_COL.items():
        if key not in canon:
            quality_notes.append(f"{meta['period_label']}: '{key}' sheet not found")
            continue
        df_wide = read_sheet(xl, canon[key])
        melted[key] = melt_sheet(df_wide, col)

    if "opened" not in melted:
        print("  ERROR: no opened sheet — skipping")
        continue

    # Start from opened, left-join the rest
    base = melted["opened"].copy()
    for key in ["closed","pct_3days","pct_3to8weeks","uphold_rate","context_provision"]:
        if key not in melted:
            continue
        col = KEY_TO_COL[key]
        right = melted[key][ID_COLS + [col]]
        base = base.merge(right, on=ID_COLS, how="left")

    # Add metadata columns
    base["period_label"] = meta["period_label"]
    base["source_file"]  = meta["filename"]

    # Ensure all metric columns exist
    for col in KEY_TO_COL.values():
        if col not in base.columns:
            base[col] = np.nan

    print(f"  Rows: {len(base)}")
    all_frames.append(base)


df = pd.concat(all_frames, ignore_index=True)
print(f"\nCombined rows: {len(df)}")

# ── Clean ──────────────────────────────────────────────────────────────────────
df["firm_name"]       = df["firm_name_raw"].apply(std_firm)
df["product_group"]   = df["product_group_raw"].str.strip()
df["reporting_period"]= df["period_label"]

for col in list(KEY_TO_COL.values()):
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Non-negative volumes
for col in ["complaints_opened","complaints_closed"]:
    bad = (df[col] < 0).sum()
    if bad:
        quality_notes.append(f"{bad} negative {col} set to NaN")
        df.loc[df[col] < 0, col] = np.nan

# Proportion checks
for col in ["pct_closed_3days","pct_closed_3to8weeks","uphold_rate"]:
    bad = ((df[col] < 0) | (df[col] > 1)).sum()
    if bad:
        quality_notes.append(f"{bad} out-of-range {col} set to NaN")
        df.loc[(df[col] < 0) | (df[col] > 1), col] = np.nan

# Duplicate check
dups = df.duplicated(subset=["firm_name","product_group","reporting_period"]).sum()
if dups:
    quality_notes.append(f"{dups} duplicate firm/product/period rows dropped")
    df = df.drop_duplicates(subset=["firm_name","product_group","reporting_period"])

# Final schema
df_clean = df[[
    "reporting_period","firm_name","group_raw","joint_reporting",
    "product_group","complaints_opened","complaints_closed",
    "pct_closed_3days","pct_closed_3to8weeks","uphold_rate",
    "denominator","source_file",
]].rename(columns={"group_raw":"firm_group"})
df_clean = df_clean.sort_values(["reporting_period","firm_name","product_group"]).reset_index(drop=True)

print(f"Final rows: {len(df_clean)}")
print(f"Firms: {df_clean['firm_name'].nunique()}")
print(f"Periods: {sorted(df_clean['reporting_period'].unique())}")

# ── Save ───────────────────────────────────────────────────────────────────────
df_clean.to_csv(PROC / "complaints_clean.csv", index=False)
print("Saved complaints_clean.csv")
try:
    df_clean.to_parquet(PROC / "complaints_clean.parquet", index=False)
    print("Saved complaints_clean.parquet")
except Exception as e:
    print(f"Parquet skipped: {e}")

# Source log
pd.DataFrame([{
    "source_url": m["url"], "reporting_period": m["period_label"],
    "period_start": m["period_start"], "period_end": m["period_end"],
    "download_date": str(date.today()), "filename": m["filename"],
    "file_format": "xlsx",
    "file_size_kb": round(os.path.getsize(RAW / m["filename"]) / 1024, 1),
} for m in FILES]).to_csv(DOCS / "source_log.csv", index=False)
print("Saved source_log.csv")

# Quality summary
summary = {
    "total_rows": len(df_clean),
    "unique_firms": int(df_clean["firm_name"].nunique()),
    "periods": sorted(df_clean["reporting_period"].unique().tolist()),
    "product_groups": sorted(df_clean["product_group"].unique().tolist()),
    "missing_complaints_opened": int(df_clean["complaints_opened"].isna().sum()),
    "missing_complaints_closed": int(df_clean["complaints_closed"].isna().sum()),
    "missing_uphold_rate": int(df_clean["uphold_rate"].isna().sum()),
    "missing_denominator": int(df_clean["denominator"].isna().sum()),
    "notes": quality_notes,
}
with open(DOCS / "data_quality_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("Saved data_quality_summary.json")
print("\nQuality notes:")
for n in quality_notes: print(f"  - {n}")
print("\n✓ Phase 1-3 complete")
