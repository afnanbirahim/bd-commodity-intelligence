"""
Bangladesh Commodity Intelligence Platform (Dhaka Consumer Edition)
-------------------------------------------------------------------
A consumer-facing Streamlit dashboard for Dhaka essential commodity prices.

Design principles:
- No public data-source selector.
- Official / verified source first.
- If market-wise verified data is unavailable, the app says so clearly instead of inventing prices.
- Bangla / English interface.
- Cheapest market, basket ranking, trends, maps, alerts.

Expected market-wise feed schema:
    date, market, area, commodity, category, unit, price_min, price_max, price,
    source, source_url, verified, latitude, longitude

Recommended production source:
    A verified CSV/API generated from official DAM/TCB data, set through Streamlit secrets:
        OFFICIAL_MARKET_PRICE_CSV_URL = "https://.../export?format=csv"
        ALLOW_PREVIEW_DATA = "false"
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Dhaka Price Watch | Bangladesh Commodity Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    :root {
        --card-bg: rgba(255,255,255,0.80);
        --card-border: rgba(49, 51, 63, 0.12);
        --muted: #64748b;
        --good: #16a34a;
        --warn: #f59e0b;
        --bad: #dc2626;
    }
    .main .block-container {padding-top: 1.0rem; padding-bottom: 2rem; max-width: 1200px;}
    .hero {
        border: 1px solid rgba(49,51,63,0.12);
        border-radius: 24px;
        padding: 24px 26px;
        background: linear-gradient(135deg, rgba(240,253,244,.92), rgba(239,246,255,.86));
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }
    .hero-title {font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; margin:0;}
    .hero-subtitle {font-size: 1.02rem; color: var(--muted); margin-top: 8px; margin-bottom: 0;}
    .pill {
        display: inline-block;
        border-radius: 999px;
        padding: 6px 11px;
        margin-right: 7px;
        margin-top: 8px;
        font-size: .86rem;
        font-weight: 650;
        border: 1px solid rgba(49,51,63,.12);
        background: rgba(255,255,255,.75);
    }
    .pill-good {color: #166534; background: rgba(220,252,231,.9);}
    .pill-warn {color: #92400e; background: rgba(254,243,199,.9);}
    .pill-bad {color: #991b1b; background: rgba(254,226,226,.9);}
    .metric-card {
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 16px 16px 14px 16px;
        background: var(--card-bg);
        min-height: 116px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045);
        color: #0f172a;
    }
    .metric-label {font-size:.88rem;color:#475569;font-weight:650;margin-bottom:7px;}
    .metric-value {font-size:1.55rem;font-weight:800;line-height:1.15;color:#0f172a;}
    .metric-help {font-size:.80rem;color:#475569;margin-top:8px;}
    .section-title {font-size:1.35rem;font-weight:800;letter-spacing:-0.02em;margin-top:24px;margin-bottom:6px;}
    .section-caption {color:var(--muted);font-size:.95rem;margin-bottom:12px;}
    .source-box {
        border: 1px solid rgba(49,51,63,.12);
        border-radius: 18px;
        padding: 14px 16px;
        background: rgba(248,250,252,.86);
        margin-top: 6px;
        margin-bottom: 12px;
    }
    .small-muted {color:var(--muted);font-size:.86rem;}
    .alert-card {
        border-left: 6px solid #f59e0b;
        background: rgba(255, 251, 235, .88);
        padding: 13px 15px;
        border-radius: 14px;
        margin-bottom: 8px;
    }
    .ok-card {
        border-left: 6px solid #16a34a;
        background: rgba(240, 253, 244, .9);
        padding: 13px 15px;
        border-radius: 14px;
        margin-bottom: 8px;
    }
    div[data-testid="stDataFrame"] {border-radius: 16px; overflow:hidden;}
    .compact-note {font-size:.88rem;color:var(--muted); margin-bottom:10px;}
    @media (max-width: 768px) {
        .main .block-container {padding-top: .6rem !important; padding-left: .9rem !important; padding-right: .9rem !important; padding-bottom: 1rem !important;}
        .hero {padding: 16px 16px 14px 16px; border-radius: 18px;}
        .hero-title {font-size: 1.55rem;}
        .hero-subtitle {font-size: .92rem;}
        .metric-card {min-height: 92px; padding: 12px 12px 10px 12px; border-radius: 16px;}
        .metric-label {font-size: .8rem;}
        .metric-value {font-size: 1.12rem; line-height: 1.2;}
        .metric-help {font-size: .74rem; margin-top: 5px;}
        .section-title {font-size: 1.15rem; margin-top: 18px;}
        .section-caption, .small-muted {font-size: .86rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Constants
# -----------------------------
TCB_DAILY_URL = "https://tcb.gov.bd/pages/daily-rmps"
DAM_DAILY_REPORT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_DAILY_PRINT_URL = "https://market.dam.gov.bd/market_daily_price_report/print?L=E"
DAM_RECENT_URL = "https://market.dam.gov.bd/commodity_wise_report/print"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
CACHE_DIR = os.path.join(APP_DIR, "cache")
SEED_PATH = os.path.join(DATA_DIR, "verified_dhaka_market_prices_seed.csv")
MARKETS_PATH = os.path.join(DATA_DIR, "dhaka_markets.csv")


# -----------------------------
# Translation
# -----------------------------
TEXT = {
    "English": {
        "app_title": "Dhaka Daily Price Watch",
        "app_subtitle": "Latest verified essential commodity prices, cheapest markets, basket cost and price alerts for Dhaka consumers.",
        "language": "Language",
        "verified": "Verified source",
        "partial": "Partial update",
        "preview": "Preview data",
        "unavailable": "Live verified data unavailable",
        "updated": "Updated",
        "source": "Source",
        "coverage": "Coverage",
        "latest_date": "Latest date",
        "commodities": "Commodities",
        "markets": "Markets",
        "best_basket": "Cheapest basket",
        "highest_spread": "Highest price spread",
        "todays_cheapest": "Cheapest market by commodity",
        "todays_cheapest_caption": "For each commodity, this shows the lowest verified price available in the latest dataset.",
        "basket_title": "Cheapest household basket today",
        "basket_caption": "A simple family basket based on common daily essentials. You can adjust it below.",
        "map_title": "Dhaka market map",
        "trend_title": "Price trends and spreads",
        "alerts_title": "Consumer alerts",
        "source_title": "Source transparency",
        "commodity": "Commodity",
        "market": "Market",
        "area": "Area",
        "unit": "Unit",
        "price": "Price",
        "lowest_price": "Lowest price",
        "basket_cost": "Basket cost",
        "saving": "Saving vs most expensive",
        "date": "Date",
        "price_range": "Price range",
        "search": "Search commodity",
        "basket_settings": "Basket settings",
        "select_commodities": "Choose basket items",
        "no_verified": "No market-wise verified data could be loaded. The app will not show cheapest-market claims until an official/verified feed is connected.",
        "no_market_level": "Official source was reached, but market-wise rows were not available in a clean machine-readable format.",
        "latest_button": "Refresh latest data",
        "last_verified": "Last verified update",
        "official_links": "Official pages monitored",
        "footer": "This app prioritises official/verified data. If today's official data is unavailable, it shows a warning instead of pretending to be live.",
        "price_unit": "Tk",
        "data_age": "Data age",
        "fresh": "Fresh",
        "stale": "Stale",
        "filters": "Filters",
        "all": "All",
        "source_note": "Rows are accepted only when they have date, commodity, market, price and source fields.",
    },
    "বাংলা": {
        "app_title": "ঢাকার দৈনিক বাজারদর",
        "app_subtitle": "ঢাকার ক্রেতাদের জন্য সর্বশেষ যাচাইকৃত নিত্যপণ্যের দাম, সবচেয়ে কম দামের বাজার, বাজার-ঝুড়ির খরচ ও সতর্কতা।",
        "language": "ভাষা",
        "verified": "যাচাইকৃত উৎস",
        "partial": "আংশিক আপডেট",
        "preview": "প্রিভিউ ডেটা",
        "unavailable": "লাইভ যাচাইকৃত ডেটা পাওয়া যায়নি",
        "updated": "আপডেট",
        "source": "উৎস",
        "coverage": "কভারেজ",
        "latest_date": "সর্বশেষ তারিখ",
        "commodities": "পণ্য",
        "markets": "বাজার",
        "best_basket": "সবচেয়ে সস্তা ঝুড়ি",
        "highest_spread": "সর্বোচ্চ দাম-ফারাক",
        "todays_cheapest": "পণ্যভিত্তিক সবচেয়ে সস্তা বাজার",
        "todays_cheapest_caption": "সর্বশেষ যাচাইকৃত ডেটায় প্রতিটি পণ্যের সবচেয়ে কম দাম দেখানো হয়েছে।",
        "basket_title": "আজকের সবচেয়ে সস্তা পারিবারিক বাজার-ঝুড়ি",
        "basket_caption": "সাধারণ নিত্যপ্রয়োজনীয় পণ্যের একটি নমুনা পারিবারিক ঝুড়ি। নিচে এটি বদলানো যাবে।",
        "map_title": "ঢাকার বাজার মানচিত্র",
        "trend_title": "দামের প্রবণতা ও ফারাক",
        "alerts_title": "ক্রেতা সতর্কতা",
        "source_title": "উৎসের স্বচ্ছতা",
        "commodity": "পণ্য",
        "market": "বাজার",
        "area": "এলাকা",
        "unit": "একক",
        "price": "দাম",
        "lowest_price": "সর্বনিম্ন দাম",
        "basket_cost": "ঝুড়ির খরচ",
        "saving": "সর্বোচ্চ দামের তুলনায় সাশ্রয়",
        "date": "তারিখ",
        "price_range": "দাম-ফারাক",
        "search": "পণ্য খুঁজুন",
        "basket_settings": "ঝুড়ি সেটিংস",
        "select_commodities": "ঝুড়ির পণ্য নির্বাচন করুন",
        "no_verified": "মার্কেটভিত্তিক যাচাইকৃত ডেটা লোড করা যায়নি। সরকারি/যাচাইকৃত ফিড যুক্ত না হওয়া পর্যন্ত অ্যাপটি সবচেয়ে সস্তা বাজারের দাবি দেখাবে না।",
        "no_market_level": "সরকারি উৎস পাওয়া গেছে, কিন্তু বাজারভিত্তিক সারিগুলো পরিষ্কার মেশিন-পঠনযোগ্য ফরম্যাটে পাওয়া যায়নি।",
        "latest_button": "সর্বশেষ ডেটা রিফ্রেশ করুন",
        "last_verified": "সর্বশেষ যাচাইকৃত আপডেট",
        "official_links": "পর্যবেক্ষণ করা সরকারি পেজ",
        "footer": "এই অ্যাপ সরকারি/যাচাইকৃত ডেটাকে অগ্রাধিকার দেয়। আজকের সরকারি ডেটা না পেলে এটি লাইভ বলে ভান না করে সতর্কতা দেখায়।",
        "price_unit": "৳",
        "data_age": "ডেটার বয়স",
        "fresh": "সাম্প্রতিক",
        "stale": "পুরোনো",
        "filters": "ফিল্টার",
        "all": "সব",
        "source_note": "তারিখ, পণ্য, বাজার, দাম ও উৎস থাকা সারিগুলোই গ্রহণ করা হয়।",
    },
}

COMMODITY_BN = {
    "Rice (coarse)": "চাল (মোটা)",
    "Rice (medium)": "চাল (মাঝারি)",
    "Rice (fine)": "চাল (সরু)",
    "Lentil (masur)": "মসুর ডাল",
    "Soybean oil": "সয়াবিন তেল",
    "Onion": "পেঁয়াজ",
    "Potato": "আলু",
    "Egg": "ডিম",
    "Broiler chicken": "ব্রয়লার মুরগি",
    "Sugar": "চিনি",
    "Garlic": "রসুন",
    "Ginger": "আদা",
    "Flour (atta)": "আটা",
}

MARKET_BN = {
    "Karwan Bazar": "কারওয়ান বাজার",
    "Shyambazar": "শ্যামবাজার",
    "Jatrabari Bazar": "যাত্রাবাড়ী বাজার",
    "Mohammadpur Krishi Market": "মোহাম্মদপুর কৃষি মার্কেট",
    "Mirpur-1 Kitchen Market": "মিরপুর-১ কাঁচাবাজার",
    "New Market Kitchen Bazar": "নিউ মার্কেট কাঁচাবাজার",
    "Uttara Sector 6 Market": "উত্তরা সেক্টর ৬ বাজার",
    "Rampura Bazar": "রামপুরা বাজার",
}

DEFAULT_BASKET = {
    "Rice (medium)": 5.0,
    "Lentil (masur)": 1.0,
    "Soybean oil": 2.0,
    "Onion": 2.0,
    "Potato": 3.0,
    "Egg": 1.0,  # dozen
    "Broiler chicken": 1.5,
    "Sugar": 1.0,
}


# -----------------------------
# Utility functions
# -----------------------------

def get_secret_or_env(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def str_to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def now_bd() -> datetime:
    # Bangladesh Standard Time = UTC+6. Avoids needing pytz/zoneinfo edge cases.
    return datetime.utcnow() + timedelta(hours=6)


def detect_mobile() -> bool:
    """Best-effort mobile detection from request headers."""
    ua = ""
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:
        try:
            ua = st.context.headers.get("user-agent", "")
        except Exception:
            ua = ""
    ua = str(ua).lower()
    mobile_tokens = ["android", "iphone", "ipad", "mobile", "opera mini", "windows phone"]
    return any(token in ua for token in mobile_tokens)


def parse_date_any(value: Any) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    # Bangla digits to English digits
    bn_digits = "০১২৩৪৫৬৭৮৯"
    for i, d in enumerate(bn_digits):
        text = text.replace(d, str(i))
    # Common formats
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %B, %Y", "%d %b, %Y", "%d %B %Y", "%d %b %Y"]:
        try:
            return pd.Timestamp(datetime.strptime(text, fmt).date())
        except Exception:
            pass
    try:
        return pd.to_datetime(text, errors="coerce", dayfirst=True)
    except Exception:
        return None


def clean_price(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value)
    bn_digits = "০১২৩৪৫৬৭৮۹"
    # includes Arabic/Persian ۹ if accidentally present
    for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    for i, d in enumerate("০۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    text = text.replace(",", "")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    # If a range like 60-70, use mid-point for a single comparable price.
    vals = [float(x) for x in nums[:2]]
    return float(np.mean(vals))


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in df.columns:
        c = str(col).strip().lower().replace(" ", "_")
        c = re.sub(r"[^a-z0-9_]+", "", c)
        aliases = {
            "commodities_name": "commodity",
            "commodity_name": "commodity",
            "commodities": "commodity",
            "product": "commodity",
            "item": "commodity",
            "bazaar": "market",
            "bazar": "market",
            "market_name": "market",
            "marketplace": "market",
            "location": "area",
            "price_tk": "price",
            "retail_price": "price",
            "average_price": "price",
            "avg_price": "price",
            "min_price": "price_min",
            "max_price": "price_max",
            "maximum_price": "price_max",
            "minimum_price": "price_min",
            "lat": "latitude",
            "lon": "longitude",
            "lng": "longitude",
            "verified_status": "verified",
            "source_link": "source_url",
            "url": "source_url",
        }
        rename_map[col] = aliases.get(c, c)
    return df.rename(columns=rename_map)


def validate_market_price_df(df: pd.DataFrame, source_name: str = "") -> Tuple[pd.DataFrame, List[str]]:
    warnings: List[str] = []
    if df is None or df.empty:
        return pd.DataFrame(), ["Empty dataset"]

    df = normalise_columns(df.copy())

    required = {"date", "market", "commodity"}
    missing = sorted(required - set(df.columns))
    if missing:
        warnings.append(f"Missing required columns: {', '.join(missing)}")
        return pd.DataFrame(), warnings

    if "price" not in df.columns:
        if "price_min" in df.columns and "price_max" in df.columns:
            df["price"] = df[["price_min", "price_max"]].apply(lambda r: np.nanmean([clean_price(r.iloc[0]), clean_price(r.iloc[1])]), axis=1)
        elif "price_min" in df.columns:
            df["price"] = df["price_min"].apply(clean_price)
        elif "price_max" in df.columns:
            df["price"] = df["price_max"].apply(clean_price)
        else:
            warnings.append("Missing price column")
            return pd.DataFrame(), warnings

    for col in ["price", "price_min", "price_max", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_price)

    df["date"] = df["date"].apply(parse_date_any)
    df = df.dropna(subset=["date", "market", "commodity", "price"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["market"] = df["market"].astype(str).str.strip()
    df["commodity"] = df["commodity"].astype(str).str.strip()

    defaults = {
        "area": "Dhaka",
        "category": "Essential",
        "unit": "kg",
        "source": source_name or "Verified feed",
        "source_url": "",
        "verified": True,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    if "price_min" not in df.columns:
        df["price_min"] = df["price"]
    if "price_max" not in df.columns:
        df["price_max"] = df["price"]

    # Merge known coordinates if missing
    markets = load_markets()
    if not markets.empty:
        coord_cols = ["market", "latitude", "longitude", "area"]
        markets_small = markets[[c for c in coord_cols if c in markets.columns]].drop_duplicates("market")
        df = df.merge(markets_small, on="market", how="left", suffixes=("", "_known"))
        for col in ["latitude", "longitude", "area"]:
            known = f"{col}_known"
            if known in df.columns:
                df[col] = df[col].where(df[col].notna() & (df[col].astype(str) != ""), df[known])
                df = df.drop(columns=[known])

    df["verified"] = df["verified"].apply(lambda x: str_to_bool(x, default=True))
    df = df[df["verified"] == True].copy()
    df = df[df["price"] > 0]

    ordered = [
        "date", "market", "area", "commodity", "category", "unit", "price_min", "price_max", "price",
        "source", "source_url", "verified", "latitude", "longitude",
    ]
    for col in ordered:
        if col not in df.columns:
            df[col] = np.nan
    return df[ordered].sort_values(["date", "commodity", "price", "market"], ascending=[False, True, True, True]), warnings


@st.cache_data(ttl=60 * 60 * 24)
def load_markets() -> pd.DataFrame:
    try:
        return pd.read_csv(MARKETS_PATH)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 30, show_spinner=False)
def read_url_text(url: str, timeout: int = 20) -> Tuple[Optional[str], str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BangladeshCommodityDashboard/1.0; +https://streamlit.io)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text, "ok"
    except Exception as exc:
        return None, str(exc)


@st.cache_data(ttl=60 * 30, show_spinner=False)
def read_csv_url(url: str) -> Tuple[pd.DataFrame, str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BangladeshCommodityDashboard/1.0)"}
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        return df, "ok"
    except Exception as exc:
        return pd.DataFrame(), str(exc)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_official_monitors() -> Dict[str, Any]:
    monitors: Dict[str, Any] = {
        "tcb": {"url": TCB_DAILY_URL, "ok": False, "latest_date": None, "title": "TCB daily retail market prices", "error": None},
        "dam_daily": {"url": DAM_DAILY_REPORT_URL, "ok": False, "latest_date": None, "title": "DAM Market Daily Price Report", "error": None},
        "dam_print": {"url": DAM_DAILY_PRINT_URL, "ok": False, "latest_date": None, "title": "DAM print report", "error": None},
    }
    # TCB page
    text, status = read_url_text(TCB_DAILY_URL)
    if text:
        monitors["tcb"]["ok"] = True
        # extract likely dates in Bangla/English from page
        for i, d in enumerate("০১২৩৪৫۶۷۸۹"):
            text = text.replace(d, str(i))
        dates = re.findall(r"\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)
        parsed = [parse_date_any(d) for d in dates]
        parsed = [p for p in parsed if p is not None and not pd.isna(p)]
        if parsed:
            monitors["tcb"]["latest_date"] = str(max(parsed).date())
    else:
        monitors["tcb"]["error"] = status

    # DAM report page
    for key, url in [("dam_daily", DAM_DAILY_REPORT_URL), ("dam_print", DAM_DAILY_PRINT_URL)]:
        text, status = read_url_text(url)
        if text:
            monitors[key]["ok"] = True
            m = re.search(r"Report Date:\s*([^|<]+)", text, flags=re.I)
            if m:
                p = parse_date_any(m.group(1).strip())
                if p is not None and not pd.isna(p):
                    monitors[key]["latest_date"] = str(p.date())
        else:
            monitors[key]["error"] = status

    return monitors


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_dam_print_table() -> Tuple[pd.DataFrame, str]:
    """Best-effort parser for DAM print report. It may be aggregate, not market-wise."""
    try:
        html, status = read_url_text(DAM_DAILY_PRINT_URL)
        if not html:
            return pd.DataFrame(), status
        tables = pd.read_html(io.StringIO(html))
        if not tables:
            return pd.DataFrame(), "No tables found"
        # Choose the largest table
        raw = max(tables, key=lambda x: x.shape[0] * x.shape[1])
        raw = normalise_columns(raw)
        # Only accept if it contains market-wise essentials.
        useful_cols = set(raw.columns)
        has_market = any(c in useful_cols for c in ["market", "market_name", "bazar", "bazaar"])
        has_commodity = any(c in useful_cols for c in ["commodity", "commodities_name", "commodity_name"])
        has_price = any("price" in c for c in useful_cols)
        if has_market and has_commodity and has_price:
            raw["source"] = "Department of Agricultural Marketing (DAM)"
            raw["source_url"] = DAM_DAILY_PRINT_URL
            raw["verified"] = True
            df, warnings = validate_market_price_df(raw, "Department of Agricultural Marketing (DAM)")
            return df, "; ".join(warnings) if warnings else "ok"
        return pd.DataFrame(), "DAM page reached, but table is not a complete market-wise price feed"
    except Exception as exc:
        return pd.DataFrame(), str(exc)


@st.cache_data(ttl=60 * 30, show_spinner=True)
def load_verified_data() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load market-wise data without exposing source selection to consumers."""
    meta: Dict[str, Any] = {
        "mode": "unavailable",
        "source_name": "",
        "source_url": "",
        "warnings": [],
        "monitors": {},
        "loaded_at": now_bd().strftime("%Y-%m-%d %H:%M"),
    }

    official_csv_url = get_secret_or_env("OFFICIAL_MARKET_PRICE_CSV_URL", "")
    allow_preview = str_to_bool(get_secret_or_env("ALLOW_PREVIEW_DATA", "true"), default=True)

    # 1) Production verified feed URL (CSV/API export) - hidden from public UI.
    if official_csv_url:
        raw, status = read_csv_url(official_csv_url)
        df, warnings = validate_market_price_df(raw, "Verified Dhaka market-wise feed")
        if not df.empty:
            meta.update({
                "mode": "verified_feed",
                "source_name": "Verified Dhaka market-wise feed",
                "source_url": official_csv_url,
                "warnings": warnings,
            })
            return df, meta
        meta["warnings"].append(f"Verified feed could not be used: {status}; {'; '.join(warnings)}")

    # 2) Official DAM print parser, if market-wise rows are available.
    dam_df, dam_status = fetch_dam_print_table()
    if not dam_df.empty:
        meta.update({
            "mode": "official_dam",
            "source_name": "Department of Agricultural Marketing (DAM)",
            "source_url": DAM_DAILY_PRINT_URL,
            "warnings": [] if dam_status == "ok" else [dam_status],
        })
        return dam_df, meta
    meta["warnings"].append(dam_status)

    # 3) Official monitors are shown, but not used for market-wise cheapest claims.
    meta["monitors"] = fetch_official_monitors()

    # 4) Preview seed only for local/demo deployments. It is clearly marked in UI.
    if allow_preview and os.path.exists(SEED_PATH):
        raw = pd.read_csv(SEED_PATH)
        df, warnings = validate_market_price_df(raw, "Bundled preview dataset")
        if not df.empty:
            meta.update({
                "mode": "preview_seed",
                "source_name": "Bundled preview dataset — replace with verified official feed",
                "source_url": "",
                "warnings": meta["warnings"] + warnings,
            })
            return df, meta

    return pd.DataFrame(), meta


def latest_slice(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    latest = max(df["date"])
    return df[df["date"] == latest].copy()


def translate_value(value: Any, lang: str, kind: str = "commodity") -> Any:
    if lang != "বাংলা":
        return value
    if kind == "commodity":
        return COMMODITY_BN.get(str(value), value)
    if kind == "market":
        return MARKET_BN.get(str(value), value)
    return value


def display_df(df: pd.DataFrame, lang: str, max_rows: int = 30) -> pd.DataFrame:
    out = df.copy()
    if "commodity" in out.columns:
        out["commodity"] = out["commodity"].apply(lambda x: translate_value(x, lang, "commodity"))
    if "market" in out.columns:
        out["market"] = out["market"].apply(lambda x: translate_value(x, lang, "market"))
    return out.head(max_rows)


def fmt_tk(value: Any, lang: str = "English") -> str:
    if value is None or pd.isna(value):
        return "—"
    prefix = TEXT[lang]["price_unit"]
    return f"{prefix}{float(value):,.0f}"


def status_badge(meta: Dict[str, Any], latest_date: Optional[date], lang: str) -> str:
    t = TEXT[lang]
    mode = meta.get("mode")
    today = now_bd().date()
    age_days = None
    if latest_date:
        age_days = (today - latest_date).days

    if mode in {"verified_feed", "official_dam"}:
        cls = "pill-good" if age_days is not None and age_days <= 1 else "pill-warn"
        label = f"🟢 {t['verified']}" if age_days is not None and age_days <= 1 else f"🟡 {t['partial']}"
    elif mode == "preview_seed":
        cls = "pill-warn"
        label = f"🟡 {t['preview']}"
    else:
        cls = "pill-bad"
        label = f"🔴 {t['unavailable']}"
    return f"<span class='pill {cls}'>{label}</span>"


def build_cheapest_by_commodity(df_latest: pd.DataFrame) -> pd.DataFrame:
    if df_latest.empty:
        return pd.DataFrame()
    idx = df_latest.groupby("commodity")["price"].idxmin()
    cheapest = df_latest.loc[idx].copy()
    spread = df_latest.groupby("commodity")["price"].agg(["min", "max"]).reset_index()
    spread["spread"] = spread["max"] - spread["min"]
    cheapest = cheapest.merge(spread[["commodity", "spread", "max"]], on="commodity", how="left")
    cheapest["saving_vs_highest"] = cheapest["max"] - cheapest["price"]
    return cheapest.sort_values(["saving_vs_highest", "commodity"], ascending=[False, True])


def compute_basket(df_latest: pd.DataFrame, basket: Dict[str, float]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    if df_latest.empty or not basket:
        return pd.DataFrame()
    basket_items = {k: v for k, v in basket.items() if v and v > 0}
    for market, g in df_latest.groupby("market"):
        total = 0.0
        covered = 0
        missing: List[str] = []
        for commodity, qty in basket_items.items():
            sub = g[g["commodity"] == commodity]
            if sub.empty:
                missing.append(commodity)
                continue
            total += float(sub["price"].iloc[0]) * float(qty)
            covered += 1
        if covered > 0:
            first = g.iloc[0]
            rows.append({
                "market": market,
                "area": first.get("area", "Dhaka"),
                "basket_cost": total,
                "items_covered": covered,
                "items_total": len(basket_items),
                "missing_items": ", ".join(missing),
                "latitude": first.get("latitude", np.nan),
                "longitude": first.get("longitude", np.nan),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    max_cost = out["basket_cost"].max()
    out["saving_vs_most_expensive"] = max_cost - out["basket_cost"]
    return out.sort_values("basket_cost")


def make_alerts(df: pd.DataFrame, df_latest: pd.DataFrame, lang: str) -> List[str]:
    alerts: List[str] = []
    if df_latest.empty:
        return alerts
    # Spread alerts
    spread = df_latest.groupby("commodity")["price"].agg(["min", "max"]).reset_index()
    spread["pct_spread"] = (spread["max"] - spread["min"]) / spread["min"].replace(0, np.nan) * 100
    high_spread = spread.sort_values("pct_spread", ascending=False).head(3)
    for _, r in high_spread.iterrows():
        if pd.notna(r["pct_spread"]) and r["pct_spread"] >= 8:
            name = translate_value(r["commodity"], lang, "commodity")
            if lang == "বাংলা":
                alerts.append(f"⚠️ {name}: বাজারভেদে দামের ফারাক প্রায় {r['pct_spread']:.0f}%। কেনার আগে বাজার তুলনা করুন।")
            else:
                alerts.append(f"⚠️ {name}: market-to-market price spread is about {r['pct_spread']:.0f}%. Compare before buying.")
    # 7-day trend alerts
    if df["date"].nunique() >= 2:
        latest_date = max(df["date"])
        prev_date = max([d for d in df["date"].unique() if d < latest_date], default=None)
        if prev_date:
            latest_avg = df[df["date"] == latest_date].groupby("commodity")["price"].mean()
            prev_avg = df[df["date"] == prev_date].groupby("commodity")["price"].mean()
            common = latest_avg.index.intersection(prev_avg.index)
            changes = ((latest_avg[common] - prev_avg[common]) / prev_avg[common].replace(0, np.nan) * 100).sort_values(ascending=False)
            for commodity, pct in changes.head(2).items():
                if pd.notna(pct) and abs(pct) >= 4:
                    name = translate_value(commodity, lang, "commodity")
                    arrow = "increased" if pct > 0 else "decreased"
                    if lang == "বাংলা":
                        word = "বেড়েছে" if pct > 0 else "কমেছে"
                        alerts.append(f"📈 {name}: আগের আপডেটের তুলনায় গড় দাম {abs(pct):.1f}% {word}।")
                    else:
                        alerts.append(f"📈 {name}: average price {arrow} by {abs(pct):.1f}% compared with the previous update.")
    return alerts[:5]


# -----------------------------
# Sidebar: language only + refresh
# -----------------------------
with st.sidebar:
    lang = st.radio("🌐 Language / ভাষা", ["English", "বাংলা"], horizontal=True)
    t = TEXT[lang]
    st.markdown("---")
    if st.button(f"🔄 {t['latest_button']}", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(t["footer"])


# -----------------------------
# Load data
# -----------------------------
with st.spinner("Loading latest verified market data..." if lang == "English" else "সর্বশেষ যাচাইকৃত বাজারদর লোড হচ্ছে..."):
    df, meta = load_verified_data()

latest = latest_slice(df)
latest_date = max(df["date"]) if not df.empty else None
source_name = meta.get("source_name", "")
source_url = meta.get("source_url", "")
is_mobile = detect_mobile()
plotly_config = {"displayModeBar": False, "responsive": True, "scrollZoom": False}
chart_height_small = 320 if is_mobile else 390
map_height = 360 if is_mobile else 520

# -----------------------------
# Hero
# -----------------------------
status_html = status_badge(meta, latest_date, lang)
updated_text = meta.get("loaded_at", now_bd().strftime("%Y-%m-%d %H:%M"))
coverage_text = "Dhaka metropolitan markets" if lang == "English" else "ঢাকা মহানগরীর বাজারসমূহ"
source_display = source_name or ("Official DAM/TCB monitor" if lang == "English" else "সরকারি DAM/TCB মনিটর")

st.markdown(
    f"""
    <div class="hero">
        <p class="hero-title">🛒 {t['app_title']}</p>
        <p class="hero-subtitle">{t['app_subtitle']}</p>
        <div style="margin-top:10px;">
            {status_html}
            <span class="pill">🕒 {t['updated']}: {updated_text}</span>
            <span class="pill">📍 {t['coverage']}: {coverage_text}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if is_mobile:
    st.markdown(f"<div class='compact-note'>📱 {'Compact mobile layout is active for easier reading.' if lang == 'English' else 'সহজে দেখার জন্য মোবাইল লেআউট চালু আছে।'}</div>", unsafe_allow_html=True)

# -----------------------------
# Empty / unavailable state
# -----------------------------
if df.empty:
    st.error(t["no_verified"])
    monitors = meta.get("monitors") or fetch_official_monitors()
    st.markdown(f"<div class='section-title'>🔎 {t['official_links']}</div>", unsafe_allow_html=True)
    monitor_rows = []
    for key, value in monitors.items():
        monitor_rows.append({
            "Source": value.get("title"),
            "Status": "Reached" if value.get("ok") else "Unavailable",
            "Latest date found": value.get("latest_date") or "—",
            "URL": value.get("url"),
        })
    st.dataframe(pd.DataFrame(monitor_rows), use_container_width=True, hide_index=True)
    st.info(t["no_market_level"])
    st.stop()

# -----------------------------
# Freshness
# -----------------------------
today_bd = now_bd().date()
age_days = (today_bd - latest_date).days if latest_date else None
if meta.get("mode") == "preview_seed":
    st.warning(
        "This deployment is showing bundled preview data because no verified market-wise feed URL is configured. For public use, set OFFICIAL_MARKET_PRICE_CSV_URL and set ALLOW_PREVIEW_DATA=false."
        if lang == "English"
        else "এই ডিপ্লয়মেন্টে যাচাইকৃত মার্কেটভিত্তিক ফিড সেট করা না থাকায় প্রিভিউ ডেটা দেখানো হচ্ছে। পাবলিক ব্যবহারের জন্য OFFICIAL_MARKET_PRICE_CSV_URL সেট করুন এবং ALLOW_PREVIEW_DATA=false করুন।"
    )
elif age_days is not None and age_days > 1:
    st.warning(
        f"The latest verified market-wise dataset is {age_days} days old. Check source freshness before making buying decisions."
        if lang == "English"
        else f"সর্বশেষ যাচাইকৃত মার্কেটভিত্তিক ডেটা {age_days} দিন পুরোনো। কেনাকাটার সিদ্ধান্তের আগে উৎসের আপডেট যাচাই করুন।"
    )

# -----------------------------
# Metrics
# -----------------------------
cheapest = build_cheapest_by_commodity(latest)
basket = compute_basket(latest, DEFAULT_BASKET)

best_basket_market = basket.iloc[0]["market"] if not basket.empty else "—"
best_basket_cost = basket.iloc[0]["basket_cost"] if not basket.empty else np.nan
highest_spread_value = cheapest["saving_vs_highest"].max() if not cheapest.empty else np.nan
highest_spread_item = cheapest.sort_values("saving_vs_highest", ascending=False).iloc[0]["commodity"] if not cheapest.empty else "—"

cols = st.columns(2) if is_mobile else st.columns(5)
metrics = [
    ("📅", t["latest_date"], str(latest_date), f"{t['data_age']}: {age_days} day(s)" if lang == "English" else f"{t['data_age']}: {age_days} দিন"),
    ("🥬", t["commodities"], f"{latest['commodity'].nunique()}", "Essential items tracked" if lang == "English" else "নিত্যপণ্য ট্র্যাক করা হচ্ছে"),
    ("🏪", t["markets"], f"{latest['market'].nunique()}", "Dhaka market locations" if lang == "English" else "ঢাকার বাজার লোকেশন"),
    ("🧺", t["best_basket"], translate_value(best_basket_market, lang, "market"), fmt_tk(best_basket_cost, lang)),
    ("↕️", t["highest_spread"], translate_value(highest_spread_item, lang, "commodity"), fmt_tk(highest_spread_value, lang)),
]
for col, (emoji, label, value, help_text) in zip(cols, metrics):
    col.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{emoji} {label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Filters/search
# -----------------------------
st.markdown(f"<div class='section-title'>🔍 {t['filters']}</div>", unsafe_allow_html=True)

if is_mobile:
    f1 = st.container()
    f2 = st.container()
else:
    f1, f2 = st.columns([1.2, 1])
search_text = f1.text_input(t["search"], placeholder="onion, rice, egg..." if lang == "English" else "পেঁয়াজ, চাল, ডিম...")
category_options = [t["all"]] + sorted(latest["category"].dropna().astype(str).unique().tolist())
category_filter = f2.selectbox("Category" if lang == "English" else "ধরন", category_options)

filtered_latest = latest.copy()
if search_text:
    q = search_text.strip().lower()
    filtered_latest = filtered_latest[
        filtered_latest["commodity"].str.lower().str.contains(q, na=False)
        | filtered_latest["market"].str.lower().str.contains(q, na=False)
        | filtered_latest["area"].str.lower().str.contains(q, na=False)
    ]
if category_filter != t["all"]:
    filtered_latest = filtered_latest[filtered_latest["category"].astype(str) == category_filter]

# -----------------------------
# Cheapest by commodity table
# -----------------------------
st.markdown(f"<div class='section-title'>🏷️ {t['todays_cheapest']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='section-caption'>{t['todays_cheapest_caption']}</div>", unsafe_allow_html=True)
cheapest_filtered = build_cheapest_by_commodity(filtered_latest)
if cheapest_filtered.empty:
    st.info("No matching commodity found." if lang == "English" else "মিল থাকা পণ্য পাওয়া যায়নি।")
else:
    table_cols = ["commodity", "market", "area", "unit", "price", "saving_vs_highest", "source"]
    if is_mobile:
        table_cols = ["commodity", "price", "unit", "market"]
    table = cheapest_filtered[table_cols].rename(columns={
        "commodity": t["commodity"],
        "market": t["market"],
        "area": t["area"],
        "unit": t["unit"],
        "price": t["lowest_price"],
        "saving_vs_highest": t["saving"],
        "source": t["source"],
    })
    if lang == "বাংলা":
        table[t["commodity"]] = table[t["commodity"]].map(lambda x: translate_value(x, lang, "commodity"))
        table[t["market"]] = table[t["market"]].map(lambda x: translate_value(x, lang, "market"))
    column_cfg = {t["lowest_price"]: st.column_config.NumberColumn(format="৳ %.0f")}
    if t["saving"] in table.columns:
        column_cfg[t["saving"]] = st.column_config.NumberColumn(format="৳ %.0f")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config=column_cfg,
    )
    if is_mobile and len(cheapest_filtered) > len(table):
        with st.expander("More details" if lang == "English" else "আরও বিস্তারিত"):
            full_table = cheapest_filtered[["commodity", "market", "area", "unit", "price", "saving_vs_highest", "source"]].rename(columns={
                "commodity": t["commodity"],
                "market": t["market"],
                "area": t["area"],
                "unit": t["unit"],
                "price": t["lowest_price"],
                "saving_vs_highest": t["saving"],
                "source": t["source"],
            })
            if lang == "বাংলা":
                full_table[t["commodity"]] = full_table[t["commodity"]].map(lambda x: translate_value(x, lang, "commodity"))
                full_table[t["market"]] = full_table[t["market"]].map(lambda x: translate_value(x, lang, "market"))
            st.dataframe(full_table, use_container_width=True, hide_index=True, column_config={t["lowest_price"]: st.column_config.NumberColumn(format="৳ %.0f"), t["saving"]: st.column_config.NumberColumn(format="৳ %.0f")})

# -----------------------------
# Basket calculator
# -----------------------------
st.markdown(f"<div class='section-title'>🧺 {t['basket_title']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='section-caption'>{t['basket_caption']}</div>", unsafe_allow_html=True)

with st.expander(f"⚙️ {t['basket_settings']}", expanded=False):
    available_items = sorted(latest["commodity"].unique().tolist())
    default_items = [x for x in DEFAULT_BASKET.keys() if x in available_items]
    selected_items = st.multiselect(
        t["select_commodities"],
        options=available_items,
        default=default_items,
        format_func=lambda x: translate_value(x, lang, "commodity"),
    )
    custom_basket: Dict[str, float] = {}
    bcols = st.columns(1) if is_mobile else st.columns(4)
    for i, item in enumerate(selected_items):
        default_qty = DEFAULT_BASKET.get(item, 1.0)
        custom_basket[item] = bcols[i % 4].number_input(
            f"{translate_value(item, lang, 'commodity')} ({latest[latest['commodity']==item]['unit'].iloc[0]})",
            min_value=0.0,
            value=float(default_qty),
            step=0.5,
        )

basket_df = compute_basket(latest, custom_basket if 'custom_basket' in locals() and custom_basket else DEFAULT_BASKET)
if not basket_df.empty:
    if is_mobile:
        b1 = st.container()
        b2 = st.container()
    else:
        b1, b2 = st.columns([1.1, 1])
    basket_cols = ["market", "area", "basket_cost", "saving_vs_most_expensive", "items_covered", "items_total"]
    if is_mobile:
        basket_cols = ["market", "basket_cost", "saving_vs_most_expensive"]
    basket_table = basket_df[basket_cols].rename(columns={
        "market": t["market"],
        "area": t["area"],
        "basket_cost": t["basket_cost"],
        "saving_vs_most_expensive": t["saving"],
        "items_covered": "Items covered" if lang == "English" else "কভার করা পণ্য",
        "items_total": "Total items" if lang == "English" else "মোট পণ্য",
    })
    if lang == "বাংলা":
        basket_table[t["market"]] = basket_table[t["market"]].map(lambda x: translate_value(x, lang, "market"))
    basket_cfg = {t["basket_cost"]: st.column_config.NumberColumn(format="৳ %.0f")}
    if t["saving"] in basket_table.columns:
        basket_cfg[t["saving"]] = st.column_config.NumberColumn(format="৳ %.0f")
    b1.dataframe(
        basket_table,
        use_container_width=True,
        hide_index=True,
        column_config=basket_cfg,
    )
    fig_basket = px.bar(
        basket_df.sort_values("basket_cost"),
        x="market",
        y="basket_cost",
        hover_data=["area", "saving_vs_most_expensive"],
        labels={"market": t["market"], "basket_cost": t["basket_cost"]},
        title="",
    )
    fig_basket.update_layout(height=chart_height_small, xaxis_tickangle=-30, margin=dict(l=5, r=5, t=15, b=5))
    b2.plotly_chart(fig_basket, use_container_width=True, config=plotly_config)
else:
    st.info("Basket cannot be calculated with the current data." if lang == "English" else "বর্তমান ডেটা দিয়ে ঝুড়ির খরচ হিসাব করা যাচ্ছে না।")

# -----------------------------
# Map
# -----------------------------
st.markdown(f"<div class='section-title'>🗺️ {t['map_title']}</div>", unsafe_allow_html=True)
map_data = latest.dropna(subset=["latitude", "longitude"]).copy()
if map_data.empty:
    st.info("Market coordinates are not available in the current feed." if lang == "English" else "বর্তমান ফিডে বাজারের স্থানাঙ্ক পাওয়া যায়নি।")
else:
    market_avg = map_data.groupby(["market", "area", "latitude", "longitude"], as_index=False).agg(
        avg_price=("price", "mean"),
        items=("commodity", "nunique"),
    )
    if not basket_df.empty:
        market_avg = market_avg.merge(basket_df[["market", "basket_cost"]], on="market", how="left")
    fig_map = px.scatter_mapbox(
        market_avg,
        lat="latitude",
        lon="longitude",
        size="items",
        color="basket_cost" if "basket_cost" in market_avg.columns else "avg_price",
        hover_name="market",
        hover_data={"area": True, "items": True, "avg_price": ":.0f", "latitude": False, "longitude": False},
        zoom=10.5,
        height=map_height,
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True, config=plotly_config)

# -----------------------------
# Trends and graphics
# -----------------------------
st.markdown(f"<div class='section-title'>📊 {t['trend_title']}</div>", unsafe_allow_html=True)
if is_mobile:
    trend_col1 = st.container()
    trend_col2 = st.container()
else:
    trend_col1, trend_col2 = st.columns(2)

# Price spread by commodity
spread_df = latest.groupby("commodity")["price"].agg(["min", "max", "mean"]).reset_index()
spread_df["spread"] = spread_df["max"] - spread_df["min"]
spread_df = spread_df.sort_values("spread", ascending=False).head(12)
fig_spread = px.bar(
    spread_df,
    x="commodity",
    y="spread",
    hover_data=["min", "max", "mean"],
    labels={"commodity": t["commodity"], "spread": t["price_range"]},
)
fig_spread.update_layout(height=chart_height_small, xaxis_tickangle=-35, margin=dict(l=5, r=5, t=15, b=5))
trend_col1.plotly_chart(fig_spread, use_container_width=True, config=plotly_config)

# Multi-date trend chart for selected commodities
trend_items = sorted(df["commodity"].unique().tolist())
default_trend = [x for x in ["Onion", "Potato", "Egg", "Broiler chicken", "Rice (medium)"] if x in trend_items]
selected_trend = trend_col2.multiselect(
    "Trend items" if lang == "English" else "প্রবণতার পণ্য",
    trend_items,
    default=default_trend[:4],
    format_func=lambda x: translate_value(x, lang, "commodity"),
)
trend_data = df[df["commodity"].isin(selected_trend)].groupby(["date", "commodity"], as_index=False)["price"].mean()
fig_trend = px.line(
    trend_data,
    x="date",
    y="price",
    color="commodity",
    markers=True,
    labels={"date": t["date"], "price": t["price"], "commodity": t["commodity"]},
)
fig_trend.update_layout(height=300 if is_mobile else 340, margin=dict(l=5, r=5, t=15, b=5))
trend_col2.plotly_chart(fig_trend, use_container_width=True, config=plotly_config)

# -----------------------------
# Alerts
# -----------------------------
st.markdown(f"<div class='section-title'>🚨 {t['alerts_title']}</div>", unsafe_allow_html=True)
alerts = make_alerts(df, latest, lang)
if alerts:
    for alert in alerts:
        st.markdown(f"<div class='alert-card'>{alert}</div>", unsafe_allow_html=True)
else:
    st.markdown(
        f"<div class='ok-card'>✅ {'No major price-spread alert detected in the latest verified dataset.' if lang == 'English' else 'সর্বশেষ যাচাইকৃত ডেটায় বড় ধরনের দাম-ফারাক সতর্কতা পাওয়া যায়নি।'}</div>",
        unsafe_allow_html=True,
    )

# -----------------------------
# Source transparency
# -----------------------------
st.markdown(f"<div class='section-title'>🧾 {t['source_title']}</div>", unsafe_allow_html=True)
source_lines = [
    f"<b>{t['source']}:</b> {source_display}",
    f"<b>{t['last_verified']}:</b> {latest_date}",
    f"<b>{t['coverage']}:</b> {coverage_text}",
    f"<span class='small-muted'>{t['source_note']}</span>",
]
if source_url:
    source_lines.append(f"<b>Feed URL:</b> {source_url}")
source_lines.append(f"<b>{t['official_links']}:</b> <a href='{TCB_DAILY_URL}' target='_blank'>TCB daily retail prices</a> · <a href='{DAM_DAILY_REPORT_URL}' target='_blank'>DAM daily market report</a>")
st.markdown("<div class='source-box'>" + "<br>".join(source_lines) + "</div>", unsafe_allow_html=True)

if meta.get("warnings"):
    with st.expander("Technical data notes" if lang == "English" else "প্রযুক্তিগত ডেটা নোট"):
        for w in meta.get("warnings", []):
            st.write("-", w)

# Download latest verified dataset for transparency
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download verified dataset" if lang == "English" else "⬇️ যাচাইকৃত ডেটাসেট ডাউনলোড করুন",
    data=csv,
    file_name=f"dhaka_verified_market_prices_{latest_date}.csv",
    mime="text/csv",
)

st.caption(t["footer"])
