"""
Fetch official DAM commodity price ranges and append them to data/official_price_history.csv.

Designed for GitHub Actions daily runs.
This script is intentionally independent from Streamlit.
"""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HISTORY_PATH = DATA_DIR / "official_price_history.csv"
DAM_DAILY_REPORT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_COMMODITY_PRINT_URL = "https://market.dam.gov.bd/commodity_wise_report/print"


def now_bd() -> datetime:
    return datetime.utcnow() + timedelta(hours=6)


def parse_date_any(value: Any):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    for i, d in enumerate("০১২۳৪৫۶۷۸۹"):
        text = text.replace(d, str(i))
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %B, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt).date())
        except Exception:
            pass
    try:
        return pd.to_datetime(text, errors="coerce", dayfirst=True)
    except Exception:
        return None


def clean_number(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value)
    for i, d in enumerate("০۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    text = text.replace(",", "")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    vals = [float(x) for x in nums[:2]]
    return float(np.mean(vals))


def infer_unit(name: str) -> str:
    n = str(name).lower()
    if "egg" in n:
        return "per piece"
    if "soybean" in n:
        return "per litre"
    if "salt" in n and "packed" in n:
        return "per packet"
    return "per kg"


def parse_dam_text(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    for i, d in enumerate("০১২۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))

    report_date = now_bd().date()
    mdate = re.search(
        r"Report Date:\s*([0-9]{1,2}\s+[A-Za-z]+,?\s+[0-9]{4}|[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4}|[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})",
        text,
        re.I,
    )
    if mdate:
        parsed = parse_date_any(mdate.group(1))
        if parsed is not None and not pd.isna(parsed):
            report_date = parsed.date()

    zone = text.split("Daily Price List Report", 1)[0] if "Daily Price List Report" in text else text
    pattern = re.compile(
        r"([A-Za-z][A-Za-z0-9()\\-/ ]{2,45}?):\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)",
        re.I,
    )

    rows = []
    seen = set()
    for name, low, high in pattern.findall(zone):
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"^(Price Reports|Recent Prices|Market Prices)\s+", "", name, flags=re.I).strip()
        if any(bad in name.lower() for bad in ["report date", "select", "from date", "to date", "division", "district"]):
            continue
        low_f, high_f = float(low), float(high)
        if len(name) < 2 or name.lower() in seen or high_f <= 0 or low_f <= 0:
            continue
        seen.add(name.lower())
        rows.append(
            {
                "date": report_date,
                "commodity": name,
                "unit": infer_unit(name),
                "low": low_f,
                "high": high_f,
                "midpoint": (low_f + high_f) / 2,
                "source": "Department of Agricultural Marketing (DAM)",
                "snapshot_saved_at": now_bd().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return pd.DataFrame(rows)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = re.sub(r"[^a-z0-9_]+", "", str(col).strip().lower().replace(" ", "_"))
        rename[col] = key
    return df.rename(columns=rename)


def fetch_dam_live() -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (GitHubActions; bd-commodity-intelligence)"})

    for url in [DAM_DAILY_REPORT_URL, DAM_COMMODITY_PRINT_URL]:
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()

            parsed = parse_dam_text(response.text)
            if not parsed.empty and len(parsed) >= 5:
                return parsed

            # table fallback
            tables = pd.read_html(io.StringIO(response.text))
            for raw in tables:
                if raw.shape[0] < 5:
                    continue
                df = normalize_columns(raw)
                cols = list(df.columns)
                commodity_col = cols[0]
                numeric_cols = []
                for c in cols[1:]:
                    vals = df[c].apply(clean_number)
                    if vals.notna().sum() >= max(3, len(vals) * 0.2):
                        numeric_cols.append(c)
                if not numeric_cols:
                    continue

                nums = df[numeric_cols].apply(lambda s: s.map(clean_number))
                out = pd.DataFrame()
                out["date"] = now_bd().date()
                out["commodity"] = df[commodity_col].astype(str).str.strip()
                out["unit"] = out["commodity"].apply(infer_unit)
                out["low"] = nums.min(axis=1)
                out["high"] = nums.max(axis=1)
                out["midpoint"] = nums.mean(axis=1)
                out["source"] = "Department of Agricultural Marketing (DAM)"
                out["snapshot_saved_at"] = now_bd().strftime("%Y-%m-%d %H:%M:%S")
                out = out.dropna(subset=["commodity", "midpoint"])
                out = out[~out["commodity"].str.lower().str.contains("serial|commodity|select|date", na=False)]
                if len(out) >= 5:
                    return out[["date", "commodity", "unit", "low", "high", "midpoint", "source", "snapshot_saved_at"]]
        except Exception as exc:
            print(f"Fetch failed for {url}: {exc}")

    return pd.DataFrame()


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    new_rows = fetch_dam_live()

    if new_rows.empty:
        print("No new DAM rows fetched. Keeping existing history unchanged.")
        # Still ensure file exists.
        if not HISTORY_PATH.exists():
            pd.DataFrame(columns=["date", "commodity", "unit", "low", "high", "midpoint", "source", "snapshot_saved_at"]).to_csv(HISTORY_PATH, index=False)
        return

    if HISTORY_PATH.exists():
        history = pd.read_csv(HISTORY_PATH)
    else:
        history = pd.DataFrame()

    new_rows["date"] = pd.to_datetime(new_rows["date"]).dt.date.astype(str)
    combined = pd.concat([history, new_rows], ignore_index=True) if not history.empty else new_rows

    for col in ["low", "high", "midpoint"]:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.date.astype(str)
    combined = combined.dropna(subset=["date", "commodity", "midpoint"])
    combined = combined.drop_duplicates(subset=["date", "commodity", "unit"], keep="last")
    combined = combined.sort_values(["date", "commodity"])

    combined.to_csv(HISTORY_PATH, index=False)
    print(f"Updated {HISTORY_PATH} with {len(new_rows)} rows. Total rows: {len(combined)}")


if __name__ == "__main__":
    main()
