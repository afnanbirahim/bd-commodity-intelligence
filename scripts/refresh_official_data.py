"""Daily refresh helper for GitHub Actions or cron.

This script fetches the Streamlit app's official data collector without running the UI,
then writes cache/latest_official_prices.csv and appends cache/history_official_prices.csv.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"

spec = importlib.util.spec_from_file_location("commodity_app", APP_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore

frames = []
statuses = []
for fetcher in [module.fetch_verified_remote_csv, module.fetch_dam_marketwise_best_effort, module.fetch_dam_official_range]:
    df, status = fetcher()
    statuses.append(status)
    if not df.empty:
        frames.append(df)
statuses.append(module.monitor_tcb_daily_page())

cache_dir = ROOT / "cache"
cache_dir.mkdir(exist_ok=True)

if frames:
    data = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()
    data.to_csv(cache_dir / "latest_official_prices.csv", index=False)
    module.append_history(data, cache_dir / "history_official_prices.csv")
    print(f"Saved {len(data)} official rows.")
else:
    print("No official rows fetched.")

for s in statuses:
    print(f"- {s.get('name')}: {s.get('message')}")
