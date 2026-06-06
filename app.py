import os
import io
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import streamlit as st

APP_NAME = "Dhaka Realtime Commodity Price Intelligence"
DAM_RECENT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_PRINT_URL = "https://market.dam.gov.bd/market_daily_price_report/print"
TCB_DAILY_URL = "https://tcb.gov.bd/pages/daily-rmps"
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CACHE_DIR = APP_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
MARKET_TEMPLATE = DATA_DIR / "dhaka_market_prices_template.csv"
BASKET_TEMPLATE = DATA_DIR / "basket_template.csv"
LOCAL_CACHE = CACHE_DIR / "latest_market_prices_cache.csv"

REQUIRED_COLUMNS = [
    "date", "division", "district", "city_area", "market", "market_bn",
    "commodity", "commodity_bn", "variety", "variety_bn", "unit", "unit_bn",
    "price_min", "price_max", "price_mid", "currency", "source", "source_url",
    "confidence", "lat", "lon"
]

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
EN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

TEXT = {
    "en": {
        "language": "Language",
        "app_title": "🧺 Dhaka Realtime Commodity Price Intelligence",
        "subtitle": "Daily essentials dashboard: latest price, cheapest market, basket-cost ranking, map, trend, and official-source monitor.",
        "data_connection": "Data connection",
        "mode": "Choose price data source",
        "auto_mode": "Auto: live CSV/API + official snapshot + local cache",
        "remote_only": "Remote CSV/API only",
        "upload": "Upload CSV",
        "official_only": "Official DAM/TCB monitor only",
        "demo": "Demo template only",
        "remote_url": "Remote CSV / Google Sheet / API URL",
        "remote_help": "For real daily changes, connect a published Google Sheet CSV, API endpoint, or official data feed with market-wise Dhaka rows.",
        "upload_csv": "Upload market-level CSV",
        "include_official": "Include official aggregate snapshot in raw data",
        "auto_refresh": "Browser auto-refresh every 30 minutes",
        "clear_cache": "Clear cache and refetch",
        "latest_date": "Latest market date",
        "dhaka_markets": "Dhaka markets",
        "commodities": "Commodities",
        "rows_loaded": "Rows loaded",
        "stale_warning": "The latest market-level data is not for today. Check source update timing before using it as today's price.",
        "no_market_data": "No Dhaka market-level rows are loaded. To show which market is cheapest, connect a live market-wise CSV/API or upload daily market data.",
        "tab_cheapest": "Cheapest today",
        "tab_basket": "Basket optimizer",
        "tab_map": "Market map",
        "tab_trends": "Trends & spread",
        "tab_sources": "Data sources",
        "tab_template": "Live data template",
        "cheapest_title": "Cheapest market by commodity — Dhaka",
        "search_commodity": "Search commodity",
        "download_cheapest": "Download cheapest-market table",
        "saving_chart": "Potential saving per unit vs highest observed market",
        "basket_title": "Best basket market today",
        "basket_caption": "Edit quantities to match a household basket. The app ranks markets by total basket cost and item coverage.",
        "best_basket": "Best basket market",
        "download_basket": "Download basket ranking",
        "map_title": "Dhaka market map",
        "map_caption": "Map uses market-level rows with latitude/longitude. Verify coordinates before publication.",
        "map_metric": "Map metric",
        "price_index": "Price index",
        "basket_cost": "Basket cost",
        "trends_title": "Price spread and market pressure",
        "select_commodity": "Commodity",
        "trend_hint": "Add multiple dates to the live CSV/API to enable trend lines.",
        "sources_title": "Data-source status",
        "raw_data": "Raw loaded data",
        "download_all": "Download all loaded rows",
        "limitation_title": "Important data honesty rule",
        "limitation": "The app only says 'cheapest market' from market-level rows. Official aggregate prices are shown separately and are not treated as market-wise evidence.",
        "template_title": "CSV/API schema for live market-level data",
        "template_intro": "Use this schema for Google Sheets, Airtable, a government API, a field-enumerator app, or daily uploaded CSV.",
        "production_options": "Production connection options",
        "market_level_required": "Market-level data is required for this table.",
        "source_official_aggregate": "Official aggregate; not market-level",
        "demo_warning": "The included template contains demonstration rows so the dashboard can run immediately. Replace it with a live market-level feed for real use.",
        "status_ok": "Connected",
        "status_warn": "Not connected",
    },
    "bn": {
        "language": "ভাষা",
        "app_title": "🧺 ঢাকা রিয়েলটাইম নিত্যপণ্যের দাম ড্যাশবোর্ড",
        "subtitle": "নিত্যপ্রয়োজনীয় পণ্যের সর্বশেষ দাম, সবচেয়ে কম দামের বাজার, বাস্কেট খরচ, মানচিত্র, ট্রেন্ড ও সরকারি উৎস মনিটর।",
        "data_connection": "ডেটা সংযোগ",
        "mode": "দামের ডেটা উৎস নির্বাচন করুন",
        "auto_mode": "অটো: লাইভ CSV/API + সরকারি স্ন্যাপশট + লোকাল ক্যাশ",
        "remote_only": "শুধু রিমোট CSV/API",
        "upload": "CSV আপলোড",
        "official_only": "শুধু সরকারি DAM/TCB মনিটর",
        "demo": "শুধু ডেমো টেমপ্লেট",
        "remote_url": "রিমোট CSV / Google Sheet / API URL",
        "remote_help": "প্রতিদিন নিজে নিজে পরিবর্তনের জন্য বাজারভিত্তিক ঢাকা ডেটাসহ Google Sheet CSV, API endpoint বা সরকারি ডেটা ফিড যুক্ত করুন।",
        "upload_csv": "বাজারভিত্তিক CSV আপলোড করুন",
        "include_official": "র' ডেটায় সরকারি aggregate snapshot যুক্ত রাখুন",
        "auto_refresh": "প্রতি ৩০ মিনিটে ব্রাউজার অটো-রিফ্রেশ",
        "clear_cache": "ক্যাশ মুছে নতুন করে আনুন",
        "latest_date": "সর্বশেষ বাজার তারিখ",
        "dhaka_markets": "ঢাকার বাজার",
        "commodities": "পণ্য",
        "rows_loaded": "লোড হওয়া সারি",
        "stale_warning": "সর্বশেষ বাজারভিত্তিক ডেটা আজকের নয়। আজকের দাম হিসেবে ব্যবহারের আগে উৎস আপডেট সময় যাচাই করুন।",
        "no_market_data": "ঢাকার বাজারভিত্তিক সারি পাওয়া যায়নি। কোন বাজারে দাম কম তা দেখাতে লাইভ market-wise CSV/API বা দৈনিক বাজার ডেটা দিন।",
        "tab_cheapest": "আজ সবচেয়ে কম",
        "tab_basket": "বাস্কেট অপ্টিমাইজার",
        "tab_map": "বাজার মানচিত্র",
        "tab_trends": "ট্রেন্ড ও পার্থক্য",
        "tab_sources": "ডেটা উৎস",
        "tab_template": "লাইভ ডেটা টেমপ্লেট",
        "cheapest_title": "পণ্যভিত্তিক সবচেয়ে কম দামের বাজার — ঢাকা",
        "search_commodity": "পণ্য খুঁজুন",
        "download_cheapest": "কম দামের বাজার টেবিল ডাউনলোড",
        "saving_chart": "সর্বোচ্চ দেখা দামের তুলনায় সম্ভাব্য সাশ্রয়/ইউনিট",
        "basket_title": "আজকের সেরা বাস্কেট বাজার",
        "basket_caption": "পরিবারের বাজার তালিকা অনুযায়ী পরিমাণ বদলান। অ্যাপ বাজারভেদে মোট খরচ ও কাভারেজ দেখাবে।",
        "best_basket": "সেরা বাস্কেট বাজার",
        "download_basket": "বাস্কেট র‍্যাঙ্কিং ডাউনলোড",
        "map_title": "ঢাকার বাজার মানচিত্র",
        "map_caption": "মানচিত্রে latitude/longitude সহ বাজারভিত্তিক সারি ব্যবহার করা হয়। প্রকাশের আগে স্থানাঙ্ক যাচাই করুন।",
        "map_metric": "মানচিত্র সূচক",
        "price_index": "দাম সূচক",
        "basket_cost": "বাস্কেট খরচ",
        "trends_title": "দামের পার্থক্য ও বাজার চাপ",
        "select_commodity": "পণ্য",
        "trend_hint": "ট্রেন্ড দেখতে লাইভ CSV/API-তে একাধিক তারিখের ডেটা যুক্ত করুন।",
        "sources_title": "ডেটা উৎসের অবস্থা",
        "raw_data": "লোড হওয়া র' ডেটা",
        "download_all": "সব ডেটা ডাউনলোড",
        "limitation_title": "গুরুত্বপূর্ণ ডেটা সততা নিয়ম",
        "limitation": "অ্যাপ শুধু বাজারভিত্তিক সারি থেকে 'সবচেয়ে কম দামের বাজার' দেখায়। সরকারি aggregate price আলাদা দেখানো হয়, market-wise evidence হিসেবে ধরা হয় না।",
        "template_title": "লাইভ বাজারভিত্তিক CSV/API স্কিমা",
        "template_intro": "Google Sheets, Airtable, সরকারি API, field-enumerator app বা দৈনিক CSV আপলোডের জন্য এই স্কিমা ব্যবহার করুন।",
        "production_options": "প্রোডাকশন সংযোগের পথ",
        "market_level_required": "এই টেবিলের জন্য বাজারভিত্তিক ডেটা দরকার।",
        "source_official_aggregate": "সরকারি aggregate; বাজারভিত্তিক নয়",
        "demo_warning": "অ্যাপ চালু দেখানোর জন্য টেমপ্লেটে ডেমো সারি আছে। বাস্তব ব্যবহারের জন্য লাইভ market-level feed বসান।",
        "status_ok": "সংযুক্ত",
        "status_warn": "সংযুক্ত নয়",
    }
}

COMMODITY_BN = {
    "Onion-local": "পেঁয়াজ-দেশি",
    "Onion": "পেঁয়াজ",
    "Potato": "আলু",
    "Green Chili": "কাঁচা মরিচ",
    "Garlic-local": "রসুন-দেশি",
    "Garlic-Imported": "রসুন-আমদানি",
    "Ginger-local": "আদা-দেশি",
    "Ginger-Imported": "আদা-আমদানি",
    "Farm-raised Hen": "ব্রয়লার/ফার্ম মুরগি",
    "Broiler Chicken": "ব্রয়লার মুরগি",
    "Beef": "গরুর মাংস",
    "Mutton": "খাসির মাংস",
    "Egg Farm-Red": "ডিম-ফার্ম লাল",
    "Egg": "ডিম",
    "Soybean": "সয়াবিন তেল",
    "Sugar (Local)": "চিনি-দেশি",
    "Sugar": "চিনি",
    "Iodized Salt (Packed)": "আয়োডিনযুক্ত লবণ-প্যাকেট",
    "Mung": "মুগ ডাল",
    "Masur Dal": "মসুর ডাল",
    "Gram-Whole": "ছোলা",
    "Aman-Fine": "আমন-চিকন চাল",
    "Aman-Medium": "আমন-মাঝারি চাল",
    "Aman-Coarse": "আমন-মোটা চাল",
    "Boro-Fine": "বোরো-চিকন চাল",
    "Boro-Medium": "বোরো-মাঝারি চাল",
    "Boro-Coarse": "বোরো-মোটা চাল",
    "Ata (packet)": "আটা-প্যাকেট",
}

MARKET_BN = {
    "Karwan Bazar": "কারওয়ান বাজার",
    "Shyambazar": "শ্যামবাজার",
    "Jatrabari Bazar": "যাত্রাবাড়ী বাজার",
    "Mirpur-1 Kitchen Market": "মিরপুর-১ কাঁচাবাজার",
    "Mohammadpur Krishi Market": "মোহাম্মদপুর কৃষি মার্কেট",
    "Uttara Sector 6 Market": "উত্তরা সেক্টর ৬ বাজার",
    "New Market Kitchen Market": "নিউ মার্কেট কাঁচাবাজার",
    "Rampura Bazar": "রামপুরা বাজার",
}

UNIT_BN = {"kg": "কেজি", "litre": "লিটার", "dozen": "ডজন", "4 pcs": "৪টি", "piece": "টি", "packet": "প্যাকেট"}

st.set_page_config(page_title=APP_NAME, page_icon="🧺", layout="wide")


def t(key: str, lang: str) -> str:
    return TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"].get(key, key))


def bn_digits(value):
    return str(value).translate(EN_DIGITS)


def normalize_digits(text: str) -> str:
    return str(text).translate(BENGALI_DIGITS)


def safe_float(x):
    if pd.isna(x):
        return np.nan
    s = normalize_digits(str(x))
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return np.nan


def clean_name(name: str) -> str:
    name = str(name).strip()
    return re.sub(r"\s+", " ", name)


def classify_source(row):
    source = str(row.get("source", "")).lower()
    market = str(row.get("market", "")).lower()
    confidence = str(row.get("confidence", "")).lower()
    if "demo" in source or "sample" in source or "demo" in confidence:
        return "Demo / replaceable"
    if "manual" in source or "google" in source or "csv" in source or "api" in source or "enumerator" in source:
        return "Market-level feed"
    if "dam" in source and ("snapshot" in market or "aggregate" in confidence):
        return "Official aggregate"
    if "tcb" in source:
        return "TCB metadata/report"
    if market and "snapshot" not in market:
        return "Market-level feed"
    return "Unknown"


def coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[REQUIRED_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    text_cols = ["division", "district", "city_area", "market", "market_bn", "commodity", "commodity_bn", "variety", "variety_bn", "unit", "unit_bn", "currency", "source", "source_url", "confidence"]
    for c in text_cols:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for c in ["price_min", "price_max", "price_mid", "lat", "lon"]:
        df[c] = df[c].map(safe_float)
    df["commodity"] = df["commodity"].map(clean_name)
    df.loc[df["commodity_bn"].eq(""), "commodity_bn"] = df.loc[df["commodity_bn"].eq(""), "commodity"].map(COMMODITY_BN).fillna("")
    df.loc[df["market_bn"].eq(""), "market_bn"] = df.loc[df["market_bn"].eq(""), "market"].map(MARKET_BN).fillna("")
    df.loc[df["unit_bn"].eq(""), "unit_bn"] = df.loc[df["unit_bn"].eq(""), "unit"].map(UNIT_BN).fillna("")
    df.loc[df["currency"].eq(""), "currency"] = "BDT"
    df.loc[df["price_mid"].isna() & df["price_min"].notna() & df["price_max"].notna(), "price_mid"] = (df["price_min"] + df["price_max"]) / 2
    df.loc[df["price_min"].isna() & df["price_mid"].notna(), "price_min"] = df["price_mid"]
    df.loc[df["price_max"].isna() & df["price_mid"].notna(), "price_max"] = df["price_mid"]
    df["source_type"] = df.apply(classify_source, axis=1)
    df = df.dropna(subset=["price_mid"])
    return df


def read_csv_any(source):
    if source is None:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    if hasattr(source, "read"):
        return pd.read_csv(source)
    source = str(source)
    if source.startswith("http://") or source.startswith("https://"):
        return pd.read_csv(source)
    return pd.read_csv(source)


def cache_market_rows(df: pd.DataFrame):
    try:
        if df is not None and not df.empty:
            df.to_csv(LOCAL_CACHE, index=False)
    except Exception:
        pass


def load_cached_rows() -> pd.DataFrame:
    if LOCAL_CACHE.exists():
        try:
            return coerce_schema(pd.read_csv(LOCAL_CACHE))
        except Exception:
            return pd.DataFrame(columns=REQUIRED_COLUMNS + ["source_type"])
    return pd.DataFrame(columns=REQUIRED_COLUMNS + ["source_type"])


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_dam_recent_snapshot() -> Tuple[pd.DataFrame, Dict]:
    meta = {
        "ok": False,
        "source": "DAM official public recent-price snapshot",
        "url": DAM_RECENT_URL,
        "message": "Not attempted",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DhakaCommodityDashboard/1.0)"}
    try:
        res = requests.get(DAM_RECENT_URL, headers=headers, timeout=25)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        text = normalize_digits(soup.get_text(" ", strip=True))
        pairs = re.findall(r"([A-Za-z][A-Za-z0-9()\-/ .]+?):\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)", text)
        rows = []
        today = date.today()
        for name, pmin, pmax in pairs:
            name = clean_name(name)
            pmin_f, pmax_f = float(pmin), float(pmax)
            unit = "kg"
            unit_bn = "কেজি"
            if "egg" in name.lower():
                unit, unit_bn = "4 pcs", "৪টি"
            elif "soybean" in name.lower():
                unit, unit_bn = "litre", "লিটার"
            rows.append({
                "date": today,
                "division": "",
                "district": "",
                "city_area": "Bangladesh",
                "market": "DAM public recent-price snapshot",
                "market_bn": "ডিএএম পাবলিক সাম্প্রতিক দামের স্ন্যাপশট",
                "commodity": name,
                "commodity_bn": COMMODITY_BN.get(name, ""),
                "variety": "",
                "variety_bn": "",
                "unit": unit,
                "unit_bn": unit_bn,
                "price_min": pmin_f,
                "price_max": pmax_f,
                "price_mid": (pmin_f + pmax_f) / 2,
                "currency": "BDT",
                "source": "DAM official public page",
                "source_url": DAM_RECENT_URL,
                "confidence": "official aggregate; not market-level",
                "lat": np.nan,
                "lon": np.nan,
            })
        df = coerce_schema(pd.DataFrame(rows))
        meta["ok"] = len(df) > 0
        meta["message"] = f"Parsed {len(df)} official aggregate price ranges from DAM." if len(df) else "DAM reached, but no price ranges were parsed."
        return df, meta
    except Exception as e:
        meta["message"] = f"DAM fetch failed: {e}"
        return pd.DataFrame(columns=REQUIRED_COLUMNS + ["source_type"]), meta


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_tcb_metadata() -> Dict:
    meta = {
        "ok": False,
        "source": "TCB daily retail price page monitor",
        "url": TCB_DAILY_URL,
        "message": "Not attempted",
        "latest_dates_seen": [],
        "download_links_seen": [],
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DhakaCommodityDashboard/1.0)"}
    try:
        res = requests.get(TCB_DAILY_URL, headers=headers, timeout=25)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        text = normalize_digits(soup.get_text(" ", strip=True))
        dates = sorted(set(re.findall(r"\b\d{2}-\d{2}-\d{4}\b", text)), reverse=True)
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            label = a.get_text(" ", strip=True)
            if any(term in href.lower() for term in ["pdf", "download", "daily-rmps", "uploads"]) or "দেখুন" in label:
                if href.startswith("/"):
                    href = "https://tcb.gov.bd" + href
                links.append(href)
        meta["ok"] = True
        meta["latest_dates_seen"] = dates[:10]
        meta["download_links_seen"] = links[:10]
        meta["message"] = f"TCB page reached. Dates parsed: {', '.join(dates[:3]) if dates else 'none'}."
        return meta
    except Exception as e:
        meta["message"] = f"TCB fetch failed/timed out: {e}"
        return meta


@st.cache_data(ttl=60 * 5, show_spinner=False)
def load_market_csv(path_or_url: str) -> pd.DataFrame:
    df = coerce_schema(read_csv_any(path_or_url))
    cache_market_rows(df[df["source_type"] != "Official aggregate"])
    return df


@st.cache_data(ttl=60 * 5, show_spinner=False)
def load_basket_csv(path_or_url: str) -> pd.DataFrame:
    return pd.read_csv(path_or_url)


def latest_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df.dropna(subset=["date"]).copy()
    if d.empty:
        return df
    max_date = d["date"].max()
    return d[d["date"] == max_date].copy()


def filter_dhaka_market_level(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df.copy()
    is_dhaka = d["district"].str.contains("Dhaka", case=False, na=False) | d["city_area"].str.contains("Dhaka", case=False, na=False)
    is_market = ~d["source_type"].eq("Official aggregate")
    return d[is_dhaka & is_market].copy()


def cheapest_by_commodity(df: pd.DataFrame) -> pd.DataFrame:
    d = latest_only(filter_dhaka_market_level(df))
    if d.empty:
        return d
    grp_cols = ["commodity", "commodity_bn", "variety", "variety_bn", "unit", "unit_bn"]
    idx = d.groupby(grp_cols, dropna=False)["price_mid"].idxmin()
    out = d.loc[idx, grp_cols + ["market", "market_bn", "price_mid", "price_min", "price_max", "date", "confidence", "source"]].copy()
    max_price = d.groupby(grp_cols, dropna=False)["price_mid"].max().reset_index(name="highest_seen")
    market_count = d.groupby(grp_cols, dropna=False)["market"].nunique().reset_index(name="markets_compared")
    out = out.merge(max_price, on=grp_cols, how="left").merge(market_count, on=grp_cols, how="left")
    out["saving_per_unit"] = out["highest_seen"] - out["price_mid"]
    out["saving_pct_vs_highest"] = np.where(out["highest_seen"] > 0, out["saving_per_unit"] / out["highest_seen"] * 100, np.nan)
    return out.sort_values(["commodity", "price_mid"])


def market_basket_cost(df: pd.DataFrame, basket: pd.DataFrame) -> pd.DataFrame:
    d = latest_only(filter_dhaka_market_level(df))
    if d.empty or basket is None or basket.empty:
        return pd.DataFrame()
    basket = basket.copy()
    for col in ["commodity", "variety", "unit"]:
        if col not in basket.columns:
            basket[col] = ""
    if "quantity" not in basket.columns:
        basket["quantity"] = 1
    basket["commodity"] = basket["commodity"].map(clean_name)
    basket["quantity"] = basket["quantity"].map(safe_float).fillna(0)
    basket = basket[basket["quantity"] > 0]
    if basket.empty:
        return pd.DataFrame()
    merged_rows = []
    for _, b in basket.iterrows():
        commodity, variety, unit, q = b["commodity"], str(b.get("variety", "")).strip(), str(b.get("unit", "")).strip(), float(b["quantity"])
        subset = d[d["commodity"].str.lower() == commodity.lower()].copy()
        if variety:
            subset = subset[subset["variety"].str.lower() == variety.lower()]
        if unit:
            subset = subset[subset["unit"].str.lower() == unit.lower()]
        if subset.empty:
            continue
        subset = subset.sort_values("price_mid").groupby("market", as_index=False).first()
        subset["basket_commodity"] = commodity
        subset["basket_quantity"] = q
        subset["line_cost"] = subset["price_mid"] * q
        merged_rows.append(subset)
    if not merged_rows:
        return pd.DataFrame()
    m = pd.concat(merged_rows, ignore_index=True)
    needed_count = basket["commodity"].nunique()
    out = m.groupby("market").agg(
        market_bn=("market_bn", "first"),
        total_cost=("line_cost", "sum"),
        items_available=("basket_commodity", "nunique"),
        avg_price=("price_mid", "mean"),
        lat=("lat", "first"),
        lon=("lon", "first"),
        date=("date", "max"),
        source=("source", lambda x: "; ".join(sorted(set(map(str, x)))[:3])),
    ).reset_index()
    out["basket_items_requested"] = needed_count
    out["coverage_pct"] = out["items_available"] / max(needed_count, 1) * 100
    out["rank_cost"] = out["total_cost"] / np.maximum(out["coverage_pct"] / 100, 0.01)
    return out.sort_values(["coverage_pct", "total_cost"], ascending=[False, True])


def price_index_by_market(df: pd.DataFrame) -> pd.DataFrame:
    d = latest_only(filter_dhaka_market_level(df))
    if d.empty:
        return pd.DataFrame()
    med = d.groupby(["commodity", "variety", "unit"], dropna=False)["price_mid"].median().reset_index(name="median_price")
    m = d.merge(med, on=["commodity", "variety", "unit"], how="left")
    m["relative_price"] = m["price_mid"] / m["median_price"] * 100
    out = m.groupby("market").agg(
        market_bn=("market_bn", "first"),
        price_index=("relative_price", "mean"),
        items=("commodity", "nunique"),
        lat=("lat", "first"),
        lon=("lon", "first"),
        date=("date", "max"),
    ).reset_index()
    return out.sort_values("price_index")


def money(x, lang):
    if pd.isna(x):
        return "—"
    s = f"৳{x:,.2f}"
    return bn_digits(s) if lang == "bn" else s


def display_df(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    d = df.copy()
    if lang == "bn":
        if "commodity_bn" in d.columns:
            d["commodity_display"] = np.where(d["commodity_bn"].ne(""), d["commodity_bn"], d.get("commodity", ""))
        if "market_bn" in d.columns:
            d["market_display"] = np.where(d["market_bn"].ne(""), d["market_bn"], d.get("market", ""))
        if "unit_bn" in d.columns:
            d["unit_display"] = np.where(d["unit_bn"].ne(""), d["unit_bn"], d.get("unit", ""))
    else:
        if "commodity" in d.columns:
            d["commodity_display"] = d["commodity"]
        if "market" in d.columns:
            d["market_display"] = d["market"]
        if "unit" in d.columns:
            d["unit_display"] = d["unit"]
    return d


def source_status_card(meta: Dict, lang: str):
    ok = meta.get("ok")
    label = t("status_ok", lang) if ok else t("status_warn", lang)
    st.markdown(f"**{'✅' if ok else '⚠️'} {meta.get('source', 'Source')} — {label}**")
    st.write(meta.get("message", ""))
    st.caption(meta.get("url", ""))
    st.caption(f"Fetched: {meta.get('fetched_at', '')}")
    if meta.get("latest_dates_seen"):
        st.caption("TCB dates: " + ", ".join(meta.get("latest_dates_seen", [])[:5]))


# Sidebar
lang_label = "English / বাংলা"
with st.sidebar:
    lang_choice = st.radio("Language / ভাষা", ["English", "বাংলা"], index=0, horizontal=True)
    lang = "bn" if lang_choice == "বাংলা" else "en"

st.title(t("app_title", lang))
st.caption(t("subtitle", lang))

with st.sidebar:
    st.header(t("data_connection", lang))
    modes = {
        t("auto_mode", lang): "auto",
        t("remote_only", lang): "remote",
        t("upload", lang): "upload",
        t("official_only", lang): "official",
        t("demo", lang): "demo",
    }
    selected_mode_label = st.radio(t("mode", lang), list(modes.keys()), index=0)
    mode = modes[selected_mode_label]

    default_remote = ""
    try:
        default_remote = st.secrets.get("MARKET_PRICE_CSV_URL", "")
    except Exception:
        default_remote = os.getenv("MARKET_PRICE_CSV_URL", "")

    remote_url = st.text_input(t("remote_url", lang), value=default_remote, help=t("remote_help", lang))
    uploaded_file = st.file_uploader(t("upload_csv", lang), type=["csv"])
    include_official = st.checkbox(t("include_official", lang), value=True)
    auto_refresh = st.checkbox(t("auto_refresh", lang), value=False)
    if st.button(t("clear_cache", lang)):
        st.cache_data.clear()
        if LOCAL_CACHE.exists():
            try:
                LOCAL_CACHE.unlink()
            except Exception:
                pass
        st.rerun()

if auto_refresh:
    st.markdown("<meta http-equiv='refresh' content='1800'>", unsafe_allow_html=True)

status_cards: List[Dict] = []
data_parts: List[pd.DataFrame] = []

# Load market-level data by priority
if mode in ["auto", "remote"]:
    if remote_url.strip():
        try:
            df_remote = load_market_csv(remote_url.strip())
            data_parts.append(df_remote)
            status_cards.append({"ok": True, "source": "Remote live market-level CSV/API", "url": remote_url.strip(), "message": f"Loaded {len(df_remote)} market rows.", "fetched_at": datetime.now().isoformat(timespec="seconds")})
        except Exception as e:
            status_cards.append({"ok": False, "source": "Remote live market-level CSV/API", "url": remote_url.strip(), "message": str(e), "fetched_at": datetime.now().isoformat(timespec="seconds")})
            cached = load_cached_rows()
            if not cached.empty:
                data_parts.append(cached)
                status_cards.append({"ok": True, "source": "Local cached market-level rows", "url": str(LOCAL_CACHE), "message": f"Remote failed, loaded {len(cached)} cached rows.", "fetched_at": datetime.now().isoformat(timespec="seconds")})
    elif mode == "auto":
        try:
            df_demo = load_market_csv(str(MARKET_TEMPLATE))
            data_parts.append(df_demo)
            status_cards.append({"ok": True, "source": "Included demo/template market rows", "url": str(MARKET_TEMPLATE), "message": f"Loaded {len(df_demo)} demo rows. Replace with a live feed for real publication.", "fetched_at": datetime.now().isoformat(timespec="seconds")})
        except Exception as e:
            status_cards.append({"ok": False, "source": "Included demo/template market rows", "url": str(MARKET_TEMPLATE), "message": str(e), "fetched_at": datetime.now().isoformat(timespec="seconds")})
    else:
        status_cards.append({"ok": False, "source": "Remote live market-level CSV/API", "url": "", "message": "No remote URL was provided.", "fetched_at": datetime.now().isoformat(timespec="seconds")})

elif mode == "upload":
    if uploaded_file is not None:
        try:
            df_upload = coerce_schema(read_csv_any(uploaded_file))
            data_parts.append(df_upload)
            cache_market_rows(df_upload)
            status_cards.append({"ok": True, "source": "Uploaded market-level CSV", "url": "local upload", "message": f"Loaded {len(df_upload)} rows.", "fetched_at": datetime.now().isoformat(timespec="seconds")})
        except Exception as e:
            status_cards.append({"ok": False, "source": "Uploaded market-level CSV", "url": "local upload", "message": str(e), "fetched_at": datetime.now().isoformat(timespec="seconds")})
    else:
        status_cards.append({"ok": False, "source": "Uploaded market-level CSV", "url": "local upload", "message": "No CSV uploaded.", "fetched_at": datetime.now().isoformat(timespec="seconds")})

elif mode == "demo":
    try:
        df_demo = load_market_csv(str(MARKET_TEMPLATE))
        data_parts.append(df_demo)
        status_cards.append({"ok": True, "source": "Included demo/template market rows", "url": str(MARKET_TEMPLATE), "message": f"Loaded {len(df_demo)} demo rows.", "fetched_at": datetime.now().isoformat(timespec="seconds")})
    except Exception as e:
        status_cards.append({"ok": False, "source": "Included demo/template market rows", "url": str(MARKET_TEMPLATE), "message": str(e), "fetched_at": datetime.now().isoformat(timespec="seconds")})

# Official monitor/snapshot
if include_official or mode == "official":
    with st.spinner("Fetching official public sources..." if lang == "en" else "সরকারি পাবলিক উৎস থেকে ডেটা আনা হচ্ছে..."):
        dam_df, dam_meta = fetch_dam_recent_snapshot()
        tcb_meta = fetch_tcb_metadata()
    status_cards.extend([dam_meta, tcb_meta])
    if include_official:
        data_parts.append(dam_df)

if data_parts:
    data = coerce_schema(pd.concat(data_parts, ignore_index=True))
else:
    data = pd.DataFrame(columns=REQUIRED_COLUMNS + ["source_type"])

if not include_official:
    data = data[data["source_type"] != "Official aggregate"].copy()

market_level = filter_dhaka_market_level(data)
latest_market = latest_only(market_level)
cheapest = cheapest_by_commodity(data)
price_index = price_index_by_market(data)
latest_date = latest_market["date"].max() if not latest_market.empty else None

# Summary metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric(t("latest_date", lang), str(latest_date) if latest_date else "—")
c2.metric(t("dhaka_markets", lang), int(latest_market["market"].nunique()) if not latest_market.empty else 0)
c3.metric(t("commodities", lang), int(latest_market["commodity"].nunique()) if not latest_market.empty else 0)
c4.metric(t("rows_loaded", lang), len(data))

if mode in ["auto", "demo"] and (not data.empty) and (data["source_type"].eq("Demo / replaceable").any()):
    st.warning(t("demo_warning", lang))

if latest_date and latest_date != date.today():
    st.warning(t("stale_warning", lang))

if latest_market.empty:
    st.warning(t("no_market_data", lang))

# Tabs
tabs = st.tabs([t("tab_cheapest", lang), t("tab_basket", lang), t("tab_map", lang), t("tab_trends", lang), t("tab_sources", lang), t("tab_template", lang)])

with tabs[0]:
    st.subheader(t("cheapest_title", lang))
    if cheapest.empty:
        st.info(t("market_level_required", lang))
    else:
        d = display_df(cheapest, lang)
        query = st.text_input(t("search_commodity", lang), "")
        if query.strip():
            q = query.strip()
            d = d[d["commodity"].str.contains(q, case=False, na=False) | d["commodity_display"].str.contains(q, case=False, na=False)]
        if lang == "bn":
            view = d.rename(columns={
                "commodity_display": "পণ্য", "variety_bn": "ধরন", "unit_display": "একক", "market_display": "সবচেয়ে কম দামের বাজার",
                "price_mid": "সেরা দাম", "highest_seen": "সর্বোচ্চ দেখা দাম", "saving_per_unit": "সম্ভাব্য সাশ্রয়/একক",
                "saving_pct_vs_highest": "সাশ্রয় %", "markets_compared": "তুলনাকৃত বাজার", "date": "তারিখ", "confidence": "বিশ্বাসযোগ্যতা"
            })
            cols = ["পণ্য", "ধরন", "একক", "সবচেয়ে কম দামের বাজার", "সেরা দাম", "সর্বোচ্চ দেখা দাম", "সম্ভাব্য সাশ্রয়/একক", "সাশ্রয় %", "তুলনাকৃত বাজার", "তারিখ", "বিশ্বাসযোগ্যতা"]
        else:
            view = d.rename(columns={
                "commodity_display": "Commodity", "variety": "Variety", "unit_display": "Unit", "market_display": "Cheapest market",
                "price_mid": "Best price", "highest_seen": "Highest seen", "saving_per_unit": "Possible saving/unit",
                "saving_pct_vs_highest": "Saving %", "markets_compared": "Markets compared", "date": "Date", "confidence": "Confidence"
            })
            cols = ["Commodity", "Variety", "Unit", "Cheapest market", "Best price", "Highest seen", "Possible saving/unit", "Saving %", "Markets compared", "Date", "Confidence"]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
        st.download_button(t("download_cheapest", lang), cheapest.to_csv(index=False).encode("utf-8-sig"), "dhaka_cheapest_market_by_commodity.csv", "text/csv")
        chart_df = d.sort_values("saving_per_unit", ascending=False).head(20)
        if not chart_df.empty:
            fig = px.bar(chart_df, x="commodity_display", y="saving_per_unit", hover_data=["market_display", "price_mid", "highest_seen", "markets_compared"], title=t("saving_chart", lang))
            st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader(t("basket_title", lang))
    st.caption(t("basket_caption", lang))
    try:
        default_basket = load_basket_csv(str(BASKET_TEMPLATE))
    except Exception:
        default_basket = pd.DataFrame({"commodity": [], "variety": [], "unit": [], "quantity": []})
    edited_basket = st.data_editor(default_basket, num_rows="dynamic", use_container_width=True)
    basket_rank = market_basket_cost(data, edited_basket)
    if basket_rank.empty:
        st.info("No basket ranking yet. Check commodity names." if lang == "en" else "এখনও বাস্কেট র‍্যাঙ্কিং নেই। পণ্যের নাম মিলছে কি না দেখুন।")
    else:
        best = basket_rank.iloc[0]
        best_name = best["market_bn"] if lang == "bn" and str(best.get("market_bn", "")).strip() else best["market"]
        st.success(f"{t('best_basket', lang)}: {best_name} — {money(best['total_cost'], lang)} ({best['coverage_pct']:.0f}% coverage)")
        d = display_df(basket_rank, lang)
        if lang == "bn":
            view = d.rename(columns={"market_display": "বাজার", "total_cost": "মোট বাস্কেট খরচ", "items_available": "পাওয়া পণ্য", "basket_items_requested": "চাওয়া পণ্য", "coverage_pct": "কভারেজ %", "date": "তারিখ", "source": "উৎস"})
            cols = ["বাজার", "মোট বাস্কেট খরচ", "পাওয়া পণ্য", "চাওয়া পণ্য", "কভারেজ %", "তারিখ", "উৎস"]
        else:
            view = d.rename(columns={"market_display": "Market", "total_cost": "Total basket cost", "items_available": "Items available", "basket_items_requested": "Items requested", "coverage_pct": "Coverage %", "date": "Date", "source": "Source"})
            cols = ["Market", "Total basket cost", "Items available", "Items requested", "Coverage %", "Date", "Source"]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
        chart_df = d.head(15)
        fig = px.bar(chart_df, x="market_display", y="total_cost", hover_data=["coverage_pct", "items_available"], title=t("basket_cost", lang))
        st.plotly_chart(fig, use_container_width=True)
        st.download_button(t("download_basket", lang), basket_rank.to_csv(index=False).encode("utf-8-sig"), "dhaka_basket_market_ranking.csv", "text/csv")

with tabs[2]:
    st.subheader(t("map_title", lang))
    st.caption(t("map_caption", lang))
    metric_options = {t("price_index", lang): "price_index", t("basket_cost", lang): "basket_cost"}
    selected_metric = st.selectbox(t("map_metric", lang), list(metric_options.keys()))
    if metric_options[selected_metric] == "basket_cost":
        map_df = basket_rank if "basket_rank" in locals() else pd.DataFrame()
        value_col = "total_cost"
    else:
        map_df = price_index
        value_col = "price_index"
    map_df = display_df(map_df, lang).dropna(subset=["lat", "lon"]) if not map_df.empty else pd.DataFrame()
    if map_df.empty:
        st.info("No coordinate-ready market data available." if lang == "en" else "স্থানাঙ্কসহ বাজার ডেটা নেই।")
    else:
        st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}), latitude="latitude", longitude="longitude", size=70)
        st.dataframe(map_df, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader(t("trends_title", lang))
    if latest_market.empty:
        st.info(t("market_level_required", lang))
    else:
        dmarket = display_df(latest_market, lang)
        options_df = dmarket[["commodity", "commodity_display"]].drop_duplicates().sort_values("commodity_display")
        label_to_value = dict(zip(options_df["commodity_display"], options_df["commodity"]))
        selected_label = st.selectbox(t("select_commodity", lang), list(label_to_value.keys()))
        selected_commodity = label_to_value[selected_label]
        d = display_df(latest_market[latest_market["commodity"] == selected_commodity].sort_values("price_mid"), lang)
        if lang == "bn":
            view = d.rename(columns={"market_display": "বাজার", "variety_bn": "ধরন", "unit_display": "একক", "price_min": "সর্বনিম্ন", "price_max": "সর্বোচ্চ", "price_mid": "মধ্য দাম", "date": "তারিখ", "confidence": "বিশ্বাসযোগ্যতা"})
            cols = ["বাজার", "ধরন", "একক", "সর্বনিম্ন", "সর্বোচ্চ", "মধ্য দাম", "তারিখ", "বিশ্বাসযোগ্যতা"]
        else:
            view = d.rename(columns={"market_display": "Market", "variety": "Variety", "unit_display": "Unit", "price_min": "Low", "price_max": "High", "price_mid": "Mid", "date": "Date", "confidence": "Confidence"})
            cols = ["Market", "Variety", "Unit", "Low", "High", "Mid", "Date", "Confidence"]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
        fig = px.bar(d, x="market_display", y="price_mid", color="variety" if d["variety"].nunique() > 1 else None, title=selected_label)
        st.plotly_chart(fig, use_container_width=True)
        hist = display_df(market_level[market_level["commodity"] == selected_commodity].sort_values("date"), lang)
        if hist["date"].nunique() > 1:
            fig2 = px.line(hist, x="date", y="price_mid", color="market_display", title=f"{selected_label}: trend")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption(t("trend_hint", lang))

with tabs[4]:
    st.subheader(t("sources_title", lang))
    if status_cards:
        cols = st.columns(2)
        for i, meta in enumerate(status_cards):
            with cols[i % 2]:
                source_status_card(meta, lang)
    st.markdown(f"### {t('raw_data', lang)}")
    st.dataframe(data, use_container_width=True, hide_index=True)
    st.download_button(t("download_all", lang), data.to_csv(index=False).encode("utf-8-sig"), "all_loaded_price_rows.csv", "text/csv")
    st.markdown(f"### {t('limitation_title', lang)}")
    st.info(t("limitation", lang))

with tabs[5]:
    st.subheader(t("template_title", lang))
    st.write(t("template_intro", lang))
    try:
        template = coerce_schema(pd.read_csv(MARKET_TEMPLATE))
    except Exception:
        template = pd.DataFrame(columns=REQUIRED_COLUMNS)
    st.dataframe(template.head(50), use_container_width=True, hide_index=True)
    st.download_button("Download CSV template" if lang == "en" else "CSV টেমপ্লেট ডাউনলোড", template.to_csv(index=False).encode("utf-8-sig"), "dhaka_market_prices_template.csv", "text/csv")
    st.markdown(f"### {t('production_options', lang)}")
    if lang == "en":
        st.markdown(
            "1. **Best:** formal TCB/DAM/ministry API or data-sharing feed.\n"
            "2. **Fastest prototype:** Google Sheet published as CSV, updated daily by enumerators.\n"
            "3. **Operational civic-tech model:** field enumerator form + approval workflow + public dashboard.\n"
            "4. **Scraping:** possible for official snapshot monitoring, but fragile for production because government page structure can change."
        )
    else:
        st.markdown(
            "1. **সেরা পথ:** TCB/DAM/মন্ত্রণালয়ের formal API বা data-sharing feed।\n"
            "2. **দ্রুত প্রোটোটাইপ:** Google Sheet published CSV, enumerator প্রতিদিন আপডেট করবে।\n"
            "3. **বাস্তব civic-tech মডেল:** field enumerator form + approval workflow + public dashboard।\n"
            "4. **Scraping:** সরকারি স্ন্যাপশট মনিটরের জন্য সম্ভব, কিন্তু প্রোডাকশনে ভঙ্গুর।"
        )
