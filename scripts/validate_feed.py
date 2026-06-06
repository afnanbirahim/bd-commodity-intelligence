"""Validate a market-wise commodity price CSV feed for the Dhaka dashboard.

Usage:
    python scripts/validate_feed.py data/verified_dhaka_market_prices_seed.csv
"""
from __future__ import annotations

import sys
import pandas as pd

REQUIRED = {"date", "market", "commodity", "price"}
RECOMMENDED = {"area", "category", "unit", "source", "source_url", "verified", "latitude", "longitude"}


def main(path: str) -> int:
    df = pd.read_csv(path)
    cols = set(df.columns)
    missing = sorted(REQUIRED - cols)
    if missing:
        print(f"ERROR: missing required columns: {missing}")
        return 1
    recommended_missing = sorted(RECOMMENDED - cols)
    if recommended_missing:
        print(f"WARNING: missing recommended columns: {recommended_missing}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    bad = df[df["date"].isna() | df["price"].isna() | (df["price"] <= 0)]
    if not bad.empty:
        print(f"ERROR: {len(bad)} rows have invalid date or price")
        print(bad.head(10).to_string(index=False))
        return 1
    print("OK")
    print(f"Rows: {len(df)}")
    print(f"Latest date: {df['date'].max().date()}")
    print(f"Markets: {df['market'].nunique()}")
    print(f"Commodities: {df['commodity'].nunique()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_feed.py <csv_path>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
