"""Daily cache updater for Dhaka commodity dashboard.

Usage:
    MARKET_PRICE_CSV_URL="https://.../export?format=csv" python scripts/update_cache.py

This script is intended for GitHub Actions, a server cron job, or a small VPS.
It downloads the live market-level CSV/API output and stores it in cache/latest_market_prices_cache.csv.
"""
import os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "latest_market_prices_cache.csv"
TEMPLATE = ROOT / "data" / "dhaka_market_prices_template.csv"

url = os.getenv("MARKET_PRICE_CSV_URL", "").strip()
if not url:
    raise SystemExit("MARKET_PRICE_CSV_URL is not set. Add a Google Sheet CSV/API URL.")

print(f"Fetching live market CSV/API: {url}")
df = pd.read_csv(url)
if df.empty:
    raise SystemExit("Fetched CSV/API returned zero rows; cache not updated.")

required_min = {"date", "district", "market", "commodity", "unit", "price_mid"}
missing = required_min - set(df.columns)
if missing:
    raise SystemExit(f"Fetched data is missing required columns: {sorted(missing)}")

df.to_csv(CACHE_FILE, index=False, encoding="utf-8")
print(f"Updated {CACHE_FILE} with {len(df)} rows.")
