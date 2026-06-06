from __future__ import annotations

import io
import os
import re
import time
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from bs4 import BeautifulSoup

APP_NAME = "Bangladesh Commodity Intelligence"
APP_VERSION = "2.0.0-official-only"
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

DAM_HOME_URL = "https://market.dam.gov.bd/?L=E"
DAM_MARKET_REPORT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_MARKET_PRINT_URL = "https://market.dam.gov.bd/market_daily_price_report/print"
DAM_SUBDISTRICT_PRINT_URL = "https://market.dam.gov.bd/subdistrict_retail_price_report/print"
TCB_DAILY_RMPS_URL = "https://tcb.gov.bd/pages/daily-rmps"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
}

ESSENTIAL_KEYWORDS = [
    "rice", "aman", "boro", "ata", "flour", "oil", "soybean", "lentil", "mung", "gram",
    "sugar", "salt", "onion", "garlic", "ginger", "potato", "egg", "hen", "chicken",
    "beef", "mutton", "fish", "chili", "chilli",
]

DHAKA_MARKETS = pd.DataFrame([
    {"market": "Karwan Bazar", "area": "Tejgaon", "lat": 23.7509, "lon": 90.3935},
    {"market": "Shyambazar", "area": "Old Dhaka", "lat": 23.7104, "lon": 90.4092},
    {"market": "Jatrabari Bazar", "area": "Jatrabari", "lat": 23.7109, "lon": 90.4347},
    {"market": "Mohammadpur Krishi Market", "area": "Mohammadpur", "lat": 23.7665, "lon": 90.3586},
    {"market": "Mirpur-1 Kitchen Market", "area": "Mirpur", "lat": 23.8044, "lon": 90.3533},
    {"market": "Uttara Bazar", "area": "Uttara", "lat": 23.8759, "lon": 90.3795},
    {"market": "New Market", "area": "New Market", "lat": 23.7335, "lon": 90.3854},
    {"market": "Rampura Bazar", "area": "Rampura", "lat": 23.7630, "lon": 90.4200},
    {"market": "Malibagh Bazar", "area": "Malibagh", "lat": 23.7481, "lon": 90.4186},
    {"market": "Khilgaon Bazar", "area": "Khilgaon", "lat": 23.7508, "lon": 90.4261},
])

TRANSLATIONS = {
    "English": {
        "title": "🛒 Bangladesh Commodity Intelligence",
        "subtitle": "Latest verified essential commodity prices for consumers. No demo prices. No fake market ranking.",
        "language": "Language",
        "source_ok": "Verified official data loaded",
        "source_partial": "Official data partially available",
        "source_fail": "Official data unavailable right now",
        "last_updated": "Last updated",
        "data_date": "Data date",
        "source": "Source",
        "official_ranges": "📌 Latest official price ranges",
        "official_ranges_help": "This section uses the latest price ranges visible from official DAM public pages.",
        "cheapest_market": "🏷️ Cheapest Dhaka market by commodity",
        "cheapest_market_help": "This appears only when official/verified market-wise Dhaka rows are available.",
        "no_marketwise": "Official market-wise Dhaka rows are not available to this deployment today. Showing official aggregate/range prices instead of fake cheapest-market results.",
        "basket": "🧺 Household basket estimate",
        "basket_help": "If market-wise rows are available, this ranks markets. Otherwise it estimates the basket using official aggregate ranges.",
        "map": "🗺️ Dhaka market coverage map",
        "charts": "📊 Price spread and trend view",
        "transparency": "🔎 Data transparency",
        "consumer_note": "Consumer note",
        "consumer_note_text": "Prices can vary by quality, brand, package size, retail shop, and time of day. Use this as a verified reference, not a bargaining guarantee.",
        "tcb_monitor": "TCB monitor",
        "dam_monitor": "DAM monitor",
        "reload": "Refresh official data",
        "download": "Download current data",
        "market_unavailable": "Market-wise ranking is unavailable until the official source returns market-level rows.",
        "verified": "Verified",
        "partial": "Partial",
        "unavailable": "Unavailable",
        "kg_or_unit": "Official unit/as reported",
    },
    "বাংলা": {
        "title": "🛒 বাংলাদেশ কমোডিটি ইন্টেলিজেন্স",
        "subtitle": "ভোক্তাদের জন্য সর্বশেষ যাচাইকৃত নিত্যপ্রয়োজনীয় পণ্যের বাজারদর। ডেমো দাম নয়, ভুয়া র‍্যাঙ্কিং নয়।",
        "language": "ভাষা",
        "source_ok": "যাচাইকৃত সরকারি তথ্য পাওয়া গেছে",
        "source_partial": "সরকারি তথ্য আংশিক পাওয়া গেছে",
        "source_fail": "এই মুহূর্তে সরকারি তথ্য পাওয়া যাচ্ছে না",
        "last_updated": "সর্বশেষ হালনাগাদ",
        "data_date": "তথ্যের তারিখ",
        "source": "উৎস",
        "official_ranges": "📌 সর্বশেষ সরকারি মূল্যসীমা",
        "official_ranges_help": "এই অংশে DAM-এর সরকারি পাবলিক পেইজে পাওয়া সর্বশেষ মূল্যসীমা দেখানো হয়।",
        "cheapest_market": "🏷️ পণ্যভিত্তিক ঢাকার সবচেয়ে কমদামের বাজার",
        "cheapest_market_help": "শুধু যাচাইকৃত/সরকারি বাজারভিত্তিক ঢাকার তথ্য পাওয়া গেলে এটি দেখাবে।",
        "no_marketwise": "আজ এই ডেপ্লয়মেন্টে সরকারি বাজারভিত্তিক ঢাকার সারি পাওয়া যায়নি। তাই ভুয়া কমদামের বাজার না দেখিয়ে সরকারি সামগ্রিক মূল্যসীমা দেখানো হচ্ছে।",
        "basket": "🧺 পরিবারের বাজার ঝুড়ির হিসাব",
        "basket_help": "বাজারভিত্তিক তথ্য থাকলে বাজার র‍্যাঙ্ক করবে; না থাকলে সরকারি সামগ্রিক মূল্যসীমা দিয়ে আনুমানিক হিসাব দেখাবে।",
        "map": "🗺️ ঢাকার বাজার কাভারেজ ম্যাপ",
        "charts": "📊 মূল্য পার্থক্য ও ট্রেন্ড",
        "transparency": "🔎 তথ্যের স্বচ্ছতা",
        "consumer_note": "ভোক্তা নোট",
        "consumer_note_text": "মান, ব্র্যান্ড, প্যাকেট সাইজ, দোকান ও দিনের সময় অনুযায়ী দাম বদলাতে পারে। এটিকে যাচাইকৃত রেফারেন্স হিসেবে ব্যবহার করুন, দর-কষাকষির নিশ্চয়তা হিসেবে নয়।",
        "tcb_monitor": "TCB মনিটর",
        "dam_monitor": "DAM মনিটর",
        "reload": "সরকারি তথ্য রিফ্রেশ করুন",
        "download": "বর্তমান তথ্য ডাউনলোড",
        "market_unavailable": "সরকারি উৎস বাজারভিত্তিক সারি না দেওয়া পর্যন্ত বাজার র‍্যাঙ্কিং পাওয়া যাবে না।",
        "verified": "যাচাইকৃত",
        "partial": "আংশিক",
        "unavailable": "পাওয়া যায়নি",
        "kg_or_unit": "সরকারি ইউনিট/যেভাবে প্রকাশিত",
    },
}


def tr(key: str) -> str:
    lang = st.session_state.get("lang", "English")
    return TRANSLATIONS.get(lang, TRANSLATIONS["English"]).get(key, key)


def safe_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_url(url: str, *, params: Optional[dict] = None, timeout: int = 20) -> Tuple[Optional[str], Optional[str]]:
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, params=params, timeout=timeout)
        res.raise_for_status()
        # Government pages may not always declare encoding cleanly.
        if not res.encoding or res.encoding.lower() == "iso-8859-1":
            res.encoding = res.apparent_encoding or "utf-8"
        return res.text, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def commodity_is_essential(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in ESSENTIAL_KEYWORDS)


def infer_unit(name: str) -> str:
    low = name.lower()
    if "egg" in low:
        return "as reported"
    if "soybean" in low or "oil" in low:
        return "as reported"
    return "as reported"


def parse_dam_recent_prices(html: str) -> pd.DataFrame:
    """Parse the DAM homepage/report ticker into official aggregate price ranges.

    DAM's public pages include recent price ticker text like:
    Aman-Fine: 72.00 - 75.00 ▲0.00% ... Onion-local: 60.00 - 64.00 ▲0.00%
    This is official data, but it is not market-wise. We therefore classify it as
    data_level='official_range', not as market-level prices.
    """
    soup = BeautifulSoup(html, "html.parser")
    raw = clean_text(soup.get_text(" "))
    pattern = re.compile(
        r"([A-Za-z][A-Za-z0-9\s\-()/.&]+?):\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*"
        r"(?:[▲▼]?\s*([+-]?[0-9]+(?:\.[0-9]+)?)%)?"
    )
    rows = []
    seen = set()
    for match in pattern.finditer(raw):
        commodity = clean_text(match.group(1))
        # Guard against menu/footer text accidentally being captured.
        if len(commodity) > 45 or not commodity_is_essential(commodity):
            continue
        low_price = float(match.group(2))
        high_price = float(match.group(3))
        change_pct = float(match.group(4)) if match.group(4) is not None else np.nan
        key = (commodity.lower(), low_price, high_price)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "date": date.today().isoformat(),
            "commodity": commodity,
            "market": "Official aggregate range",
            "area": "Official public source",
            "unit": infer_unit(commodity),
            "price": round((low_price + high_price) / 2, 2),
            "price_min": low_price,
            "price_max": high_price,
            "change_pct": change_pct,
            "source": "Department of Agricultural Marketing (DAM)",
            "source_url": DAM_HOME_URL,
            "verified": True,
            "data_level": "official_range",
            "fetched_at": now_iso(),
        })
    return pd.DataFrame(rows)


def parse_tables_to_marketwise(html: str, source_url: str, source_name: str) -> pd.DataFrame:
    """Best-effort parser for official printable reports.

    It intentionally refuses to manufacture market rows. It only returns rows if
    the official HTML contains a recognizable commodity/market/price table.
    """
    try:
        tables = pd.read_html(io.StringIO(html))
    except Exception:
        return pd.DataFrame()

    out = []
    for table in tables:
        if table.empty or table.shape[1] < 3:
            continue
        df = table.copy()
        df.columns = [clean_text(c).lower() for c in df.columns]
        joined_cols = " ".join(df.columns)
        # Try flexible column discovery.
        commodity_col = next((c for c in df.columns if "commodity" in c or "commodities" in c or "পণ্য" in c), None)
        market_col = next((c for c in df.columns if "market" in c or "বাজার" in c), None)
        unit_col = next((c for c in df.columns if "unit" in c or "একক" in c), None)
        price_col = next((c for c in df.columns if "retail" in c or "rate" in c or "price" in c or "দর" in c or "মূল্য" in c), None)
        if commodity_col is None or price_col is None:
            # Some DAM printable pages flatten headers. Attempt positional parsing.
            if df.shape[1] >= 4:
                commodity_col = df.columns[1]
                unit_col = df.columns[2]
                price_col = df.columns[-1]
            else:
                continue
        for _, row in df.iterrows():
            commodity = clean_text(row.get(commodity_col, ""))
            if not commodity or commodity.lower() in {"commodities name", "commodity", "nan"}:
                continue
            if not commodity_is_essential(commodity):
                continue
            market = clean_text(row.get(market_col, "")) if market_col else "Official market report"
            unit = clean_text(row.get(unit_col, "")) if unit_col else "as reported"
            price_raw = clean_text(row.get(price_col, ""))
            nums = re.findall(r"\d+(?:\.\d+)?", price_raw)
            if not nums:
                continue
            nums = [float(x) for x in nums]
            price_min = min(nums)
            price_max = max(nums)
            price = float(np.mean(nums))
            data_level = "market" if market and market.lower() not in {"official market report", "nan"} else "official_range"
            out.append({
                "date": date.today().isoformat(),
                "commodity": commodity,
                "market": market or "Official market report",
                "area": "Dhaka" if "dhaka" in market.lower() or "sadar" in market.lower() else "Official report",
                "unit": unit or "as reported",
                "price": round(price, 2),
                "price_min": round(price_min, 2),
                "price_max": round(price_max, 2),
                "change_pct": np.nan,
                "source": source_name,
                "source_url": source_url,
                "verified": True,
                "data_level": data_level,
                "fetched_at": now_iso(),
            })
    return pd.DataFrame(out).drop_duplicates() if out else pd.DataFrame()


def fetch_dam_official_range() -> Tuple[pd.DataFrame, Dict[str, str]]:
    status = {"name": "DAM recent prices", "url": DAM_HOME_URL, "ok": "false", "message": "Not attempted"}
    html, err = fetch_url(DAM_HOME_URL)
    if err or not html:
        status.update({"ok": "false", "message": err or "Empty response"})
        return pd.DataFrame(), status
    df = parse_dam_recent_prices(html)
    if df.empty:
        status.update({"ok": "false", "message": "DAM page loaded but no price ticker was parsed."})
        return df, status
    status.update({"ok": "true", "message": f"Parsed {len(df)} official price ranges from DAM."})
    return df, status


def fetch_dam_marketwise_best_effort() -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Attempt official market-wise reports without inventing data.

    The public DAM form uses filters for Division/District/Upazila/Market/Price Type/Date.
    Some installations require dynamic IDs or session state. This collector tries the
    printable endpoints and returns rows only if a recognizable official table appears.
    """
    status = {"name": "DAM market-wise report", "url": DAM_MARKET_PRINT_URL, "ok": "false", "message": "Not attempted"}
    urls = [DAM_MARKET_PRINT_URL, DAM_SUBDISTRICT_PRINT_URL]
    frames = []
    for url in urls:
        html, err = fetch_url(url, timeout=25)
        if err or not html:
            continue
        parsed = parse_tables_to_marketwise(html, url, "Department of Agricultural Marketing (DAM)")
        if not parsed.empty:
            frames.append(parsed)
    if not frames:
        status.update({
            "ok": "false",
            "message": "Official report endpoints loaded no usable market-wise Dhaka rows without filters/API access.",
        })
        return pd.DataFrame(), status
    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    # Keep Dhaka-ish rows if present. If not, keep all official rows but mark as official_range.
    dhaka_mask = df["market"].astype(str).str.contains("dhaka|karwan|kawran|shyam|jatra|mirpur|uttara|mohammad", case=False, regex=True, na=False)
    if dhaka_mask.any():
        df = df[dhaka_mask].copy()
    status.update({"ok": "true", "message": f"Parsed {len(df)} official report rows."})
    return df, status


def fetch_verified_remote_csv() -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Optional backend-only source for a verified CSV/API feed.

    This is not visible as a consumer selector. It allows you to connect a formal DAM/TCB
    CSV, Google Sheet CSV, or verified internal feed later. Rows must include verified=true
    or source containing DAM/TCB/Government/Official; otherwise they are rejected.
    """
    url = safe_secret("OFFICIAL_MARKET_PRICE_CSV_URL", os.getenv("OFFICIAL_MARKET_PRICE_CSV_URL", ""))
    status = {"name": "Verified CSV/API feed", "url": url or "not configured", "ok": "false", "message": "No backend feed configured."}
    if not url:
        return pd.DataFrame(), status
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        res.raise_for_status()
        df = pd.read_csv(io.StringIO(res.text))
    except Exception as exc:
        status.update({"ok": "false", "message": f"Could not read verified CSV/API feed: {type(exc).__name__}: {exc}"})
        return pd.DataFrame(), status

    required = {"date", "commodity", "market", "price"}
    lower_map = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=lower_map)
    if not required.issubset(set(df.columns)):
        status.update({"ok": "false", "message": "Feed rejected: required columns missing: date, commodity, market, price."})
        return pd.DataFrame(), status
    if "source" not in df.columns:
        df["source"] = "Configured verified feed"
    if "verified" not in df.columns:
        df["verified"] = df["source"].astype(str).str.contains("dam|tcb|official|government|govt", case=False, regex=True, na=False)
    else:
        df["verified"] = df["verified"].astype(str).str.lower().isin(["true", "1", "yes", "y", "verified"])
    df = df[df["verified"]].copy()
    if df.empty:
        status.update({"ok": "false", "message": "Feed rejected: no rows passed verification rule."})
        return pd.DataFrame(), status
    for col, default in {
        "area": "Dhaka", "unit": "as reported", "price_min": np.nan, "price_max": np.nan,
        "change_pct": np.nan, "source_url": url, "data_level": "market", "fetched_at": now_iso()
    }.items():
        if col not in df.columns:
            df[col] = default
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    df["price_min"] = pd.to_numeric(df["price_min"], errors="coerce").fillna(df["price"])
    df["price_max"] = pd.to_numeric(df["price_max"], errors="coerce").fillna(df["price"])
    status.update({"ok": "true", "message": f"Loaded {len(df)} verified rows from backend feed."})
    return df, status


def monitor_tcb_daily_page() -> Dict[str, str]:
    status = {"name": "TCB daily retail prices", "url": TCB_DAILY_RMPS_URL, "ok": "false", "message": "Not attempted"}
    html, err = fetch_url(TCB_DAILY_RMPS_URL, timeout=20)
    if err or not html:
        status.update({"ok": "false", "message": err or "Empty response"})
        return status
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = clean_text(a.get_text(" "))
        if any(ext in href.lower() for ext in [".pdf", ".xls", ".xlsx", ".csv", ".doc", ".docx"]) or "download" in label.lower() or "ডাউনলোড" in label:
            links.append(href)
    msg = "TCB page loaded. "
    if links:
        msg += f"Found {len(links)} possible report/download links."
    elif "দৈনিক" in text or "খুচরা" in text or "retail" in text.lower():
        msg += "Daily retail price content was visible, but no direct machine-readable table was parsed."
    else:
        msg += "No machine-readable price table found."
    status.update({"ok": "true", "message": msg})
    return status


def load_cache(path: Path) -> pd.DataFrame:
    try:
        if path.exists() and path.stat().st_size > 0:
            return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()


def save_cache(df: pd.DataFrame, path: Path) -> None:
    try:
        if not df.empty:
            df.to_csv(path, index=False)
    except Exception:
        pass


def append_history(df: pd.DataFrame, path: Path) -> None:
    try:
        if df.empty:
            return
        keep = df.copy()
        keep["snapshot_saved_at"] = now_iso()
        if path.exists() and path.stat().st_size > 0:
            old = pd.read_csv(path)
            all_df = pd.concat([old, keep], ignore_index=True)
        else:
            all_df = keep
        subset = [c for c in ["date", "commodity", "market", "price", "price_min", "price_max", "source"] if c in all_df.columns]
        all_df = all_df.drop_duplicates(subset=subset, keep="last")
        all_df.to_csv(path, index=False)
    except Exception:
        pass


@st.cache_data(ttl=60 * 30, show_spinner=False)
def load_official_data(force_key: int = 0) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    statuses: List[Dict[str, str]] = []
    frames: List[pd.DataFrame] = []

    remote_df, remote_status = fetch_verified_remote_csv()
    statuses.append(remote_status)
    if not remote_df.empty:
        frames.append(remote_df)

    market_df, market_status = fetch_dam_marketwise_best_effort()
    statuses.append(market_status)
    if not market_df.empty:
        frames.append(market_df)

    dam_df, dam_status = fetch_dam_official_range()
    statuses.append(dam_status)
    if not dam_df.empty:
        frames.append(dam_df)

    statuses.append(monitor_tcb_daily_page())

    if frames:
        data = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()
        # Prefer market-level rows for market views, but retain official ranges.
        data["price"] = pd.to_numeric(data["price"], errors="coerce")
        data["price_min"] = pd.to_numeric(data.get("price_min", data["price"]), errors="coerce").fillna(data["price"])
        data["price_max"] = pd.to_numeric(data.get("price_max", data["price"]), errors="coerce").fillna(data["price"])
        data = data.dropna(subset=["price"])
        save_cache(data, CACHE_DIR / "latest_official_prices.csv")
        append_history(data, CACHE_DIR / "history_official_prices.csv")
        return data, statuses

    cached = load_cache(CACHE_DIR / "latest_official_prices.csv")
    if not cached.empty:
        cached["data_level"] = cached.get("data_level", "cached_official")
        statuses.append({"name": "Local cache", "url": str(CACHE_DIR / "latest_official_prices.csv"), "ok": "true", "message": "Loaded last verified local cache because live official fetch failed."})
        return cached, statuses

    return pd.DataFrame(), statuses


def build_cheapest_market(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "data_level" not in df.columns:
        return pd.DataFrame()
    market_df = df[(df["data_level"] == "market") & (df["verified"] == True)].copy()
    if market_df.empty:
        return pd.DataFrame()
    market_df["price"] = pd.to_numeric(market_df["price"], errors="coerce")
    market_df = market_df.dropna(subset=["price"])
    if market_df.empty:
        return pd.DataFrame()
    idx = market_df.groupby("commodity")["price"].idxmin()
    cheapest = market_df.loc[idx].copy().sort_values("price")
    # Savings vs most expensive market for same commodity.
    max_prices = market_df.groupby("commodity")["price"].max().rename("max_price").reset_index()
    cheapest = cheapest.merge(max_prices, on="commodity", how="left")
    cheapest["saving_vs_highest"] = (cheapest["max_price"] - cheapest["price"]).round(2)
    return cheapest


def build_basket(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    basket_path = DATA_DIR / "basket.csv"
    if basket_path.exists():
        basket = pd.read_csv(basket_path)
    else:
        basket = pd.DataFrame([
            {"commodity_keyword": "Rice", "quantity": 5, "unit_note": "kg"},
            {"commodity_keyword": "Onion", "quantity": 2, "unit_note": "kg"},
            {"commodity_keyword": "Potato", "quantity": 2, "unit_note": "kg"},
            {"commodity_keyword": "Soybean", "quantity": 2, "unit_note": "litre/as reported"},
            {"commodity_keyword": "Egg", "quantity": 1, "unit_note": "dozen/as reported"},
            {"commodity_keyword": "Lentil", "quantity": 1, "unit_note": "kg"},
            {"commodity_keyword": "Sugar", "quantity": 1, "unit_note": "kg"},
        ])
    if df.empty:
        return pd.DataFrame(), "none"
    market_df = df[(df.get("data_level") == "market") & (df.get("verified") == True)].copy()
    if not market_df.empty:
        rows = []
        for market, g in market_df.groupby("market"):
            total = 0.0
            matched = 0
            details = []
            for _, b in basket.iterrows():
                keyword = str(b["commodity_keyword"])
                qty = float(b["quantity"])
                matches = g[g["commodity"].astype(str).str.contains(keyword, case=False, na=False)]
                if matches.empty:
                    continue
                selected = matches.sort_values("price").iloc[0]
                cost = float(selected["price"]) * qty
                total += cost
                matched += 1
                details.append(f"{keyword}: {qty} × {selected['price']}")
            if matched:
                rows.append({"market": market, "basket_cost": round(total, 2), "items_matched": matched, "details": "; ".join(details)})
        if rows:
            return pd.DataFrame(rows).sort_values("basket_cost"), "market"
    # Aggregate estimate using official ranges/midpoints.
    range_df = df[df.get("data_level").astype(str).str.contains("official_range|cached", regex=True, na=False)].copy()
    if range_df.empty:
        range_df = df.copy()
    total_low = total_mid = total_high = 0.0
    matched = 0
    rows = []
    for _, b in basket.iterrows():
        keyword = str(b["commodity_keyword"])
        qty = float(b["quantity"])
        matches = range_df[range_df["commodity"].astype(str).str.contains(keyword, case=False, na=False)]
        if matches.empty:
            continue
        selected = matches.sort_values("price").iloc[0]
        low = float(selected.get("price_min", selected["price"])) * qty
        mid = float(selected.get("price", selected["price"])) * qty
        high = float(selected.get("price_max", selected["price"])) * qty
        rows.append({
            "item": selected["commodity"], "quantity": qty, "unit": selected.get("unit", "as reported"),
            "low_estimate": round(low, 2), "mid_estimate": round(mid, 2), "high_estimate": round(high, 2)
        })
        total_low += low; total_mid += mid; total_high += high; matched += 1
    if not rows:
        return pd.DataFrame(), "none"
    result = pd.DataFrame(rows)
    result.loc[len(result)] = {"item": "TOTAL", "quantity": np.nan, "unit": "", "low_estimate": round(total_low, 2), "mid_estimate": round(total_mid, 2), "high_estimate": round(total_high, 2)}
    return result, "range"


def status_badge(statuses: List[Dict[str, str]]) -> Tuple[str, str]:
    any_ok = any(s.get("ok") == "true" for s in statuses)
    market_ok = any(s.get("ok") == "true" and "market" in s.get("name", "").lower() for s in statuses)
    if market_ok:
        return "🟢", tr("source_ok")
    if any_ok:
        return "🟡", tr("source_partial")
    return "🔴", tr("source_fail")


def display_metric_cards(df: pd.DataFrame, statuses: List[Dict[str, str]]) -> None:
    badge, msg = status_badge(statuses)
    latest_time = df["fetched_at"].max() if not df.empty and "fetched_at" in df.columns else now_iso()
    data_date = df["date"].max() if not df.empty and "date" in df.columns else "—"
    verified_rows = int(df["verified"].astype(bool).sum()) if not df.empty and "verified" in df.columns else 0
    market_rows = int((df.get("data_level", pd.Series(dtype=str)) == "market").sum()) if not df.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{badge} {tr('verified')}", msg)
    c2.metric(tr("data_date"), data_date)
    c3.metric("Verified rows", f"{verified_rows}")
    c4.metric("Market rows", f"{market_rows}")
    st.caption(f"{tr('last_updated')}: {latest_time} · App version: {APP_VERSION}")


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="🛒", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e9edf3; padding: 14px; border-radius: 18px; box-shadow: 0 1px 6px rgba(0,0,0,.04);}
        .hero {padding: 1.2rem 1.4rem; border-radius: 22px; background: linear-gradient(135deg, #f8fafc 0%, #eef7ff 55%, #fff8ec 100%); border: 1px solid #e8eef7; margin-bottom: 1rem;}
        .hero h1 {margin-bottom: .25rem;}
        .soft-card {padding: 1rem; border: 1px solid #e9edf3; border-radius: 16px; background: #fff;}
        .tiny {font-size: 0.85rem; color: #64748b;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "lang" not in st.session_state:
        st.session_state.lang = "English"
    top_l, top_r = st.columns([3, 1])
    with top_r:
        st.session_state.lang = st.selectbox(tr("language"), ["English", "বাংলা"], index=0 if st.session_state.lang == "English" else 1)

    with top_l:
        st.markdown(f"<div class='hero'><h1>{tr('title')}</h1><p>{tr('subtitle')}</p></div>", unsafe_allow_html=True)

    refresh_key = 0
    if st.button(f"🔄 {tr('reload')}"):
        st.cache_data.clear()
        refresh_key = int(time.time())

    with st.spinner("Fetching official public sources..."):
        df, statuses = load_official_data(refresh_key)

    display_metric_cards(df, statuses)

    if df.empty:
        st.error("No verified official price data could be loaded and no cache exists yet. Please check internet access or official source availability.")
        with st.expander(tr("transparency"), expanded=True):
            for s in statuses:
                st.write(f"**{s['name']}** — {s['message']}")
                st.caption(s.get("url", ""))
        return

    # Download data
    st.download_button(
        f"⬇️ {tr('download')}",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"official_commodity_prices_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

    market_df = df[df.get("data_level") == "market"].copy() if "data_level" in df.columns else pd.DataFrame()
    official_range_df = df[df.get("data_level").astype(str).str.contains("official_range|cached", regex=True, na=False)].copy() if "data_level" in df.columns else df.copy()

    st.subheader(tr("cheapest_market"))
    st.caption(tr("cheapest_market_help"))
    cheapest = build_cheapest_market(df)
    if cheapest.empty:
        st.warning(tr("no_marketwise"))
    else:
        show = cheapest[["commodity", "market", "area", "unit", "price", "saving_vs_highest", "source"]].copy()
        show = show.rename(columns={
            "commodity": "Commodity", "market": "Market", "area": "Area", "unit": "Unit",
            "price": "Lowest price", "saving_vs_highest": "Saving vs highest", "source": "Source",
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.subheader(tr("official_ranges"))
    st.caption(tr("official_ranges_help"))
    if official_range_df.empty:
        st.info("No aggregate official range data parsed from DAM today.")
    else:
        display_cols = [c for c in ["commodity", "price_min", "price_max", "price", "unit", "change_pct", "source"] if c in official_range_df.columns]
        table = official_range_df[display_cols].copy()
        table = table.rename(columns={
            "commodity": "Commodity", "price_min": "Low", "price_max": "High", "price": "Midpoint", "unit": "Unit", "change_pct": "Change %", "source": "Source",
        })
        st.dataframe(table.sort_values("Commodity"), use_container_width=True, hide_index=True)

    st.subheader(tr("basket"))
    st.caption(tr("basket_help"))
    basket_df, basket_mode = build_basket(df)
    if basket_df.empty:
        st.info("Basket could not be calculated because matching official commodity rows were not found.")
    elif basket_mode == "market":
        st.success("Market-wise basket ranking available from verified market rows.")
        st.dataframe(basket_df, use_container_width=True, hide_index=True)
    else:
        st.info("Market-wise basket ranking is not shown because market-level data was not available. This is an official aggregate basket estimate.")
        st.dataframe(basket_df, use_container_width=True, hide_index=True)

    st.subheader(tr("charts"))
    chart_df = official_range_df.copy() if not official_range_df.empty else df.copy()
    if not chart_df.empty:
        chart_df["spread"] = pd.to_numeric(chart_df.get("price_max", chart_df["price"]), errors="coerce") - pd.to_numeric(chart_df.get("price_min", chart_df["price"]), errors="coerce")
        chart_df = chart_df.dropna(subset=["price"])
        c1, c2 = st.columns(2)
        with c1:
            top = chart_df.sort_values("price", ascending=False).head(15)
            fig = px.bar(top, x="price", y="commodity", orientation="h", title="Higher-price essentials / উচ্চমূল্যের পণ্য", labels={"price": "Price", "commodity": "Commodity"})
            fig.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            sp = chart_df.sort_values("spread", ascending=False).head(15)
            fig2 = px.bar(sp, x="spread", y="commodity", orientation="h", title="Official low-high spread / মূল্যসীমার পার্থক্য", labels={"spread": "Spread", "commodity": "Commodity"})
            fig2.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader(tr("map"))
    map_df = DHAKA_MARKETS.copy()
    if not market_df.empty:
        # Add average price count by market when available.
        avg = market_df.groupby("market", as_index=False).agg(avg_price=("price", "mean"), rows=("price", "size"))
        map_df = map_df.merge(avg, on="market", how="left")
    st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}), latitude="latitude", longitude="longitude", zoom=11)
    if market_df.empty:
        st.caption(tr("market_unavailable"))

    st.subheader(tr("transparency"))
    with st.expander("Official source monitor", expanded=True):
        for s in statuses:
            icon = "🟢" if s.get("ok") == "true" else "🟡"
            st.markdown(f"{icon} **{s.get('name','Source')}** — {s.get('message','')}")
            if s.get("url"):
                st.caption(s["url"])
        st.info(f"{tr('consumer_note')}: {tr('consumer_note_text')}")
        st.markdown(
            "This app uses only verified official/public-source data or a backend-configured verified official feed. "
            "It no longer displays 'PREVIEW ONLY' fake prices. If official market-wise data is not available, the app clearly says so."
        )


if __name__ == "__main__":
    main()
