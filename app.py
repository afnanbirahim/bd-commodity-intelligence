
"""
Bangladesh Commodity Intelligence Platform — Mobile First Consumer Edition
Version: 4.0.0-mobile-first

A Streamlit app for Dhaka consumers:
- Mobile-first cards instead of wide tables
- Official/verified data first
- No public data-source selector
- English/Bangla toggle
- Cheapest market and basket ranking when market-wise verified rows are available
- Official aggregate price cards when only official range data is available

Production secrets:
    OFFICIAL_MARKET_PRICE_CSV_URL = "https://...csv"
    ALLOW_PREVIEW_DATA = "false"
"""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Dhaka Price Watch",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------
# CSS — deliberately mobile-first and high contrast
# ---------------------------------------------------------------------
st.markdown(
    """
<style>
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-soft: #f1f5f9;
  --text: #0f172a;
  --muted: #475569;
  --line: #e2e8f0;
  --green: #16a34a;
  --green-bg: #dcfce7;
  --amber: #d97706;
  --amber-bg: #fef3c7;
  --red: #dc2626;
  --red-bg: #fee2e2;
  --blue: #2563eb;
  --blue-bg: #dbeafe;
}
html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text) !important;
}
.main .block-container {
  max-width: 1160px;
  padding-top: .75rem;
  padding-left: 1rem;
  padding-right: 1rem;
  padding-bottom: 2rem;
}
h1, h2, h3, h4, p, span, label, div { color: var(--text); }
[data-testid="stSidebar"] {
  background: var(--surface) !important;
}
.mobile-hero {
  background: linear-gradient(135deg, #ecfdf5 0%, #eff6ff 100%);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, .06);
}
.mobile-title {
  font-size: 1.85rem;
  line-height: 1.08;
  letter-spacing: -.045em;
  font-weight: 900;
  margin: 0;
}
.mobile-subtitle {
  color: var(--muted);
  font-size: .98rem;
  line-height: 1.55;
  margin-top: 9px;
  margin-bottom: 0;
}
.badge-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: .80rem;
  line-height: 1;
  font-weight: 800;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
}
.badge-green { background: var(--green-bg); color: #14532d; border-color: #bbf7d0; }
.badge-amber { background: var(--amber-bg); color: #78350f; border-color: #fde68a; }
.badge-red { background: var(--red-bg); color: #7f1d1d; border-color: #fecaca; }
.grid {
  display: grid;
  gap: 12px;
}
.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 14px 14px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, .045);
  overflow-wrap: anywhere;
}
.stat-label {
  font-size: .77rem;
  color: var(--muted);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.stat-value {
  font-size: 1.35rem;
  font-weight: 900;
  letter-spacing: -.025em;
  margin-top: 4px;
  color: var(--text);
}
.stat-help {
  color: var(--muted);
  font-size: .82rem;
  margin-top: 4px;
}
.item-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: start;
}
.item-name {
  font-weight: 900;
  font-size: 1.05rem;
  letter-spacing: -.02em;
  color: var(--text);
}
.item-meta {
  color: var(--muted);
  font-size: .86rem;
  margin-top: 2px;
}
.price-pill {
  background: #0f172a;
  color: #ffffff !important;
  font-weight: 900;
  border-radius: 14px;
  padding: 8px 10px;
  text-align: right;
  min-width: 82px;
}
.price-sub {
  font-size: .72rem;
  opacity: .82;
  margin-top: 2px;
  color: #e2e8f0 !important;
}
.market-card {
  border-left: 6px solid var(--green);
}
.warn-card {
  background: var(--amber-bg);
  border: 1px solid #fde68a;
  border-left: 6px solid var(--amber);
  color: #78350f;
}
.info-card {
  background: var(--blue-bg);
  border: 1px solid #bfdbfe;
  border-left: 6px solid var(--blue);
  color: #1e3a8a;
}
.danger-card {
  background: var(--red-bg);
  border: 1px solid #fecaca;
  border-left: 6px solid var(--red);
  color: #7f1d1d;
}
.section-title {
  font-size: 1.45rem;
  font-weight: 950;
  letter-spacing: -.04em;
  margin: 24px 0 6px 0;
}
.section-caption {
  color: var(--muted);
  line-height: 1.55;
  margin-bottom: 12px;
}
hr {
  margin: 1rem 0;
  border-color: var(--line);
}
[data-testid="stDataFrame"] {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--line);
}
div[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  padding: 12px;
  border-radius: 18px;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 5px;
  overflow-x: auto;
  white-space: nowrap;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 999px;
  padding: 8px 14px;
  background: var(--surface-soft);
  color: var(--text);
  font-weight: 800;
}
.stTabs [aria-selected="true"] {
  background: var(--green-bg) !important;
  color: #14532d !important;
  border: 1px solid #86efac !important;
}
.stTabs [data-baseweb="tab"]:focus,
.stTabs [data-baseweb="tab"]:active {
  background: var(--green-bg) !important;
  color: #14532d !important;
}
button[kind="secondary"] {
  border-radius: 14px !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
}
button[kind="secondary"]:active,
button[kind="secondary"]:focus {
  background: var(--green-bg) !important;
  color: #14532d !important;
  border-color: #86efac !important;
}
@media (max-width: 760px) {
  .main .block-container {
    padding-top: .45rem;
    padding-left: .75rem;
    padding-right: .75rem;
  }
  .mobile-hero {
    border-radius: 20px;
    padding: 15px;
  }
  .mobile-title {
    font-size: 1.55rem;
  }
  .mobile-subtitle {
    font-size: .90rem;
  }
  .grid-2, .grid-3, .grid-4 {
    grid-template-columns: 1fr;
  }
  .card {
    border-radius: 18px;
    padding: 13px;
  }
  .item-card {
    grid-template-columns: 1fr;
  }
  .price-pill {
    text-align: left;
    display: inline-block;
    width: fit-content;
    min-width: 0;
  }
  .section-title {
    font-size: 1.25rem;
    margin-top: 18px;
  }
  .stat-value {
    font-size: 1.18rem;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
APP_VERSION = "4.2.0-mobile-first-public-safe"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
SEED_PATH = os.path.join(DATA_DIR, "verified_dhaka_market_prices_seed.csv")
MARKETS_PATH = os.path.join(DATA_DIR, "dhaka_markets.csv")

TCB_DAILY_URL = "https://tcb.gov.bd/pages/daily-rmps"
DAM_DAILY_REPORT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_COMMODITY_PRINT_URL = "https://market.dam.gov.bd/commodity_wise_report/print"


TEXT = {
    "English": {
        "title": "Dhaka Daily Price Watch",
        "subtitle": "Consumer-friendly essential commodity prices for Dhaka. See the latest verified prices, cheapest markets, basket cost and alerts.",
        "lang": "Language",
        "verified": "Verified",
        "preview": "Preview",
        "unavailable": "Unavailable",
        "updated": "Updated",
        "today": "Today",
        "basket": "Basket",
        "markets": "Markets",
        "charts": "Charts",
        "source": "Source",
        "items": "Items",
        "market_count": "Markets",
        "date": "Date",
        "status": "Status",
        "official_prices": "Latest official prices",
        "official_caption": "Compact card view. Every card shows the price unit, such as per kg, litre, packet or piece.",
        "cheapest": "Cheapest by item",
        "cheapest_caption": "Shown only when market-wise verified rows are available.",
        "alerts": "Price alerts",
        "basket_title": "Smart shopping basket",
        "basket_caption": "Change quantities and compare estimated cost.",
        "market_ranking": "Market ranking",
        "no_market": "Verified market-wise Dhaka rows are unavailable, so the app does not show fake cheapest-market claims.",
        "source_title": "Source transparency",
        "refresh": "Refresh",
        "search": "Search item",
        "show_more": "Show more",
        "download": "Download data",
        "unit": "Unit",
        "price": "Price",
        "range": "Range",
        "mid": "Mid",
        "market": "Market",
        "area": "Area",
        "saving": "Saving",
        "coverage": "Dhaka",
        "preview_warning": "Preview data is active. For public use, connect an official/verified CSV feed and set ALLOW_PREVIEW_DATA=false.",
        "official_only": "Official aggregate data is suitable for reference prices. Cheapest-market ranking requires market-wise verified rows.",
        "footer": "The app prioritises official or verified data and avoids unsupported cheapest-market claims.",
    },
    "বাংলা": {
        "title": "ঢাকার দৈনিক বাজারদর",
        "subtitle": "ঢাকার ক্রেতাদের জন্য নিত্যপণ্যের সর্বশেষ যাচাইকৃত দাম, কম দামের বাজার, ঝুড়ির খরচ ও সতর্কতা।",
        "lang": "ভাষা",
        "verified": "যাচাইকৃত",
        "preview": "প্রিভিউ",
        "unavailable": "পাওয়া যায়নি",
        "updated": "আপডেট",
        "today": "আজ",
        "basket": "ঝুড়ি",
        "markets": "বাজার",
        "charts": "চার্ট",
        "source": "উৎস",
        "items": "পণ্য",
        "market_count": "বাজার",
        "date": "তারিখ",
        "status": "অবস্থা",
        "official_prices": "সর্বশেষ সরকারি দাম",
        "official_caption": "সহজ কার্ড ভিউ। প্রতিটি কার্ডে একক দেখানো আছে, যেমন কেজি, লিটার, প্যাকেট বা পিস।",
        "cheapest": "পণ্যভিত্তিক কম দাম",
        "cheapest_caption": "শুধু যাচাইকৃত বাজারভিত্তিক সারি থাকলে দেখানো হয়।",
        "alerts": "দাম সতর্কতা",
        "basket_title": "স্মার্ট বাজার-ঝুড়ি",
        "basket_caption": "পরিমাণ বদলে আনুমানিক খরচ তুলনা করুন।",
        "market_ranking": "বাজার র‍্যাংকিং",
        "no_market": "ঢাকার যাচাইকৃত বাজারভিত্তিক সারি পাওয়া যায়নি, তাই অ্যাপটি ভুয়া সবচেয়ে সস্তা বাজার দেখাচ্ছে না।",
        "source_title": "উৎসের স্বচ্ছতা",
        "refresh": "রিফ্রেশ",
        "search": "পণ্য খুঁজুন",
        "show_more": "আরও দেখুন",
        "download": "ডেটা ডাউনলোড",
        "unit": "একক",
        "price": "দাম",
        "range": "রেঞ্জ",
        "mid": "মাঝামাঝি",
        "market": "বাজার",
        "area": "এলাকা",
        "saving": "সাশ্রয়",
        "coverage": "ঢাকা",
        "preview_warning": "প্রিভিউ ডেটা চালু আছে। পাবলিক ব্যবহারের জন্য সরকারি/যাচাইকৃত CSV ফিড যুক্ত করুন এবং ALLOW_PREVIEW_DATA=false করুন।",
        "official_only": "সরকারি aggregate data রেফারেন্স দাম হিসেবে উপযোগী। কম দামের বাজার দেখাতে যাচাইকৃত market-wise row দরকার।",
        "footer": "অ্যাপটি সরকারি বা যাচাইকৃত ডেটাকে অগ্রাধিকার দেয় এবং অসমর্থিত cheapest-market দাবি এড়ায়।",
    },
}

BN_COMMODITY = {
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

BN_MARKET = {
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
    "Flour (atta)": 2.0,
    "Lentil (masur)": 1.0,
    "Onion": 2.0,
    "Potato": 2.0,
    "Soybean oil": 2.0,
    "Egg": 12.0,
    "Broiler chicken": 1.0,
    "Sugar": 1.0,
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def get_secret_or_env(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def now_bd() -> datetime:
    return datetime.utcnow() + timedelta(hours=6)


def fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def clean_number(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value)
    for i, d in enumerate("০১২৩৪৫৬৭৮৯"):
        text = text.replace(d, str(i))
    text = text.replace(",", "")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    vals = [float(x) for x in nums[:2]]
    return float(np.mean(vals))


def parse_date_any(value: Any) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    for i, d in enumerate("০১২৩৪৫৬৭۸৯"):
        text = text.replace(d, str(i))
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt).date())
        except Exception:
            pass
    try:
        return pd.to_datetime(text, errors="coerce", dayfirst=True)
    except Exception:
        return None


def money(value: Any, lang: str = "English", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    prefix = "৳" if lang == "বাংলা" else "Tk "
    return f"{prefix}{float(value):,.{decimals}f}"


def tr_item(value: Any, lang: str) -> str:
    value = str(value)
    return BN_COMMODITY.get(value, value) if lang == "বাংলা" else value


def tr_market(value: Any, lang: str) -> str:
    value = str(value)
    return BN_MARKET.get(value, value) if lang == "বাংলা" else value


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "product": "commodity",
        "item": "commodity",
        "commodities": "commodity",
        "commodity_name": "commodity",
        "commodities_name": "commodity",
        "bazar": "market",
        "bazaar": "market",
        "market_name": "market",
        "location": "area",
        "retail_price": "price",
        "avg_price": "price",
        "average_price": "price",
        "price_tk": "price",
        "min_price": "price_min",
        "minimum_price": "price_min",
        "max_price": "price_max",
        "maximum_price": "price_max",
        "lat": "latitude",
        "lon": "longitude",
        "lng": "longitude",
        "source_link": "source_url",
    }
    rename = {}
    for col in df.columns:
        key = re.sub(r"[^a-z0-9_]+", "", str(col).strip().lower().replace(" ", "_"))
        rename[col] = aliases.get(key, key)
    return df.rename(columns=rename)


def validate_market_df(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = normalize_columns(df.copy())

    if "commodity" not in df.columns or "market" not in df.columns:
        return pd.DataFrame()

    if "date" not in df.columns:
        df["date"] = now_bd().date()

    if "price" not in df.columns:
        if "price_min" in df.columns and "price_max" in df.columns:
            df["price"] = df[["price_min", "price_max"]].apply(
                lambda r: np.nanmean([clean_number(r.iloc[0]), clean_number(r.iloc[1])]), axis=1
            )
        elif "price_min" in df.columns:
            df["price"] = df["price_min"].apply(clean_number)
        else:
            return pd.DataFrame()

    for col in ["price", "price_min", "price_max", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)

    df["date"] = df["date"].apply(parse_date_any)
    df = df.dropna(subset=["date", "market", "commodity", "price"])
    if df.empty:
        return pd.DataFrame()

    defaults = {
        "area": "Dhaka",
        "category": "Essential",
        "unit": "kg",
        "source": source_name,
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

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["market"] = df["market"].astype(str).str.strip()
    df["commodity"] = df["commodity"].astype(str).str.strip()
    df["unit"] = df["unit"].astype(str).str.strip()

    # Merge coordinates if needed
    try:
        markets = pd.read_csv(MARKETS_PATH)
        markets = markets.drop_duplicates("market")
        df = df.merge(markets[["market", "area", "latitude", "longitude"]], on="market", how="left", suffixes=("", "_known"))
        for col in ["area", "latitude", "longitude"]:
            known = f"{col}_known"
            if known in df.columns:
                df[col] = df[col].where(df[col].notna() & (df[col].astype(str) != ""), df[known])
                df = df.drop(columns=[known])
    except Exception:
        pass

    if "verified" in df.columns:
        df = df[df["verified"].apply(lambda x: to_bool(x, True))].copy()

    cols = [
        "date", "market", "area", "commodity", "category", "unit", "price_min", "price_max", "price",
        "source", "source_url", "verified", "latitude", "longitude",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df[cols].sort_values(["date", "commodity", "price"], ascending=[False, True, True])


def official_aggregate_from_market(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    latest_date = max(df["date"])
    latest = df[df["date"] == latest_date]
    g = latest.groupby(["commodity", "unit"], as_index=False).agg(
        low=("price", "min"),
        high=("price", "max"),
        midpoint=("price", "mean"),
    )
    g["date"] = latest_date
    g["source"] = source_name
    return g[["date", "commodity", "unit", "low", "high", "midpoint", "source"]]


@st.cache_data(ttl=60 * 30, show_spinner=False)
def read_csv_url(url: str) -> Tuple[pd.DataFrame, str]:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text)), "ok"
    except Exception as exc:
        return pd.DataFrame(), str(exc)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_official_page_status() -> Dict[str, Any]:
    """Public-safe source status. Raw exceptions are hidden from consumer UI."""
    out: Dict[str, Any] = {}
    sources = {
        "TCB daily retail prices": TCB_DAILY_URL,
        "DAM daily market report": DAM_DAILY_REPORT_URL,
        "DAM commodity report": DAM_COMMODITY_PRINT_URL,
    }
    for name, url in sources.items():
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=16)
            out[name] = {
                "ok": bool(r.ok),
                "url": url,
                "status_code": int(r.status_code),
                "public_status": "Available" if r.ok else "Temporarily unavailable",
                "technical_status": str(r.status_code),
            }
        except requests.exceptions.SSLError:
            # Common with some government sites on hosted environments.
            out[name] = {
                "ok": False,
                "url": url,
                "status_code": None,
                "public_status": "Temporarily unavailable",
                "technical_status": "SSL certificate verification failed",
            }
        except Exception as exc:
            out[name] = {
                "ok": False,
                "url": url,
                "status_code": None,
                "public_status": "Temporarily unavailable",
                "technical_status": exc.__class__.__name__,
            }
    return out


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_official_aggregate_best_effort() -> pd.DataFrame:
    """Best-effort parser for DAM commodity report. If it fails, the app still works from verified CSV/seed."""
    try:
        r = requests.get(DAM_COMMODITY_PRINT_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        if not tables:
            return pd.DataFrame()

        candidates = []
        for raw in tables:
            if raw.shape[0] < 5:
                continue
            df = normalize_columns(raw)
            # Look for rows with a likely commodity column and numeric price columns.
            cols = list(df.columns)
            commodity_col = None
            for c in cols:
                if "commodity" in c or "item" in c or "product" in c or c in {"name"}:
                    commodity_col = c
                    break
            if commodity_col is None:
                commodity_col = cols[0]

            numeric_cols = []
            for c in cols[1:]:
                vals = df[c].apply(clean_number)
                if vals.notna().sum() >= max(3, len(vals) * 0.2):
                    numeric_cols.append(c)
            if not numeric_cols:
                continue

            tmp = pd.DataFrame()
            tmp["commodity"] = df[commodity_col].astype(str).str.strip()
            nums = df[numeric_cols].applymap(clean_number)
            tmp["low"] = nums.min(axis=1)
            tmp["high"] = nums.max(axis=1)
            tmp["midpoint"] = nums.mean(axis=1)
            tmp = tmp.dropna(subset=["commodity", "midpoint"])
            tmp = tmp[tmp["commodity"].str.len() > 1]
            tmp["unit"] = "per unit"
            tmp["date"] = now_bd().date()
            tmp["source"] = "Department of Agricultural Marketing (DAM)"
            if not tmp.empty:
                candidates.append(tmp)

        if not candidates:
            return pd.DataFrame()

        best = max(candidates, key=len)
        # Remove obvious serial/header rows
        best = best[~best["commodity"].str.lower().str.contains("serial|sl|commodity|বিবরণ|পণ্য", na=False)]
        return best[["date", "commodity", "unit", "low", "high", "midpoint", "source"]].head(80)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 30, show_spinner=True)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    meta = {
        "mode": "unavailable",
        "source": "",
        "source_url": "",
        "loaded_at": now_bd().strftime("%Y-%m-%d %H:%M"),
        "notes": [],
    }

    verified_url = get_secret_or_env("OFFICIAL_MARKET_PRICE_CSV_URL", "")
    allow_preview = to_bool(get_secret_or_env("ALLOW_PREVIEW_DATA", "false"), False)

    market_df = pd.DataFrame()

    if verified_url:
        raw, status = read_csv_url(verified_url)
        market_df = validate_market_df(raw, "Verified Dhaka market-wise feed")
        if not market_df.empty:
            meta.update({"mode": "verified", "source": "Verified Dhaka market-wise feed", "source_url": verified_url})
        else:
            meta["notes"].append(f"Verified feed failed: {status}")

    if market_df.empty and allow_preview and os.path.exists(SEED_PATH):
        raw = pd.read_csv(SEED_PATH)
        market_df = validate_market_df(raw, "Preview dataset — replace with official verified feed")
        if not market_df.empty:
            meta.update({"mode": "preview", "source": "Preview dataset — replace with official verified feed", "source_url": ""})

    # Official aggregate cards: first best-effort from official DAM page.
    official_df = fetch_official_aggregate_best_effort()

    # Only aggregate preview/market-wise data if explicitly allowed and no official aggregate exists.
    if official_df.empty and not market_df.empty:
        official_df = official_aggregate_from_market(market_df, meta["source"])

    if not official_df.empty:
        # Official aggregate is the public source for the consumer interface.
        if str(official_df["source"].iloc[0]).startswith("Department of Agricultural Marketing"):
            meta.update({"mode": "official_aggregate", "source": "Department of Agricultural Marketing (DAM)", "source_url": DAM_DAILY_REPORT_URL})
        elif meta["mode"] == "unavailable":
            meta.update({"mode": "official_aggregate", "source": str(official_df["source"].iloc[0]), "source_url": ""})

    return market_df, official_df, meta


def latest_market(market_df: pd.DataFrame) -> pd.DataFrame:
    if market_df.empty:
        return market_df
    latest = max(market_df["date"])
    return market_df[market_df["date"] == latest].copy()


def latest_agg(official_df: pd.DataFrame) -> pd.DataFrame:
    if official_df.empty:
        return official_df
    latest = max(pd.to_datetime(official_df["date"]).dt.date)
    out = official_df[pd.to_datetime(official_df["date"]).dt.date == latest].copy()
    return out


def cheapest_by_item(latest: pd.DataFrame) -> pd.DataFrame:
    if latest.empty:
        return pd.DataFrame()
    idx = latest.groupby("commodity")["price"].idxmin()
    c = latest.loc[idx].copy()
    spread = latest.groupby("commodity")["price"].agg(["min", "max"]).reset_index()
    c = c.merge(spread, on="commodity", how="left")
    c["saving"] = c["max"] - c["price"]
    return c.sort_values(["saving", "commodity"], ascending=[False, True])


def basket_costs(latest: pd.DataFrame, basket: Dict[str, float]) -> pd.DataFrame:
    if latest.empty:
        return pd.DataFrame()
    rows = []
    for market, g in latest.groupby("market"):
        total = 0.0
        covered = 0
        for item, qty in basket.items():
            if qty <= 0:
                continue
            sub = g[g["commodity"] == item]
            if sub.empty:
                continue
            unit = str(sub["unit"].iloc[0]).lower()
            qty_calc = float(qty)
            # In the app, Egg basket qty is individual eggs. If source unit is dozen, convert.
            if item == "Egg" and "dozen" in unit:
                qty_calc = qty_calc / 12.0
            total += float(sub["price"].iloc[0]) * qty_calc
            covered += 1
        if covered:
            first = g.iloc[0]
            rows.append({
                "market": market,
                "area": first.get("area", "Dhaka"),
                "basket_cost": total,
                "covered": covered,
                "latitude": first.get("latitude", np.nan),
                "longitude": first.get("longitude", np.nan),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    max_cost = out["basket_cost"].max()
    out["saving"] = max_cost - out["basket_cost"]
    return out.sort_values("basket_cost")


def aggregate_basket(agg: pd.DataFrame, basket: Dict[str, float]) -> Tuple[float, float, float]:
    low = mid = high = 0.0
    for item, qty in basket.items():
        sub = agg[agg["commodity"] == item]
        if sub.empty:
            continue
        unit = str(sub["unit"].iloc[0]).lower()
        qty_calc = float(qty)
        if item == "Egg" and "dozen" in unit:
            qty_calc = qty_calc / 12.0
        low += float(sub["low"].iloc[0]) * qty_calc
        mid += float(sub["midpoint"].iloc[0]) * qty_calc
        high += float(sub["high"].iloc[0]) * qty_calc
    return low, mid, high


def render_stat(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
<div class="card">
  <div class="stat-label">{label}</div>
  <div class="stat-value">{value}</div>
  <div class="stat-help">{help_text}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_item_card(name: str, price: str, unit: str, meta: str = "") -> None:
    st.markdown(
        f"""
<div class="card item-card">
  <div>
    <div class="item-name">{name}</div>
    <div class="item-meta">{meta}</div>
  </div>
  <div class="price-pill">{price}<div class="price-sub">{unit}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_notice(kind: str, text: str) -> None:
    cls = {"warn": "warn-card", "info": "info-card", "danger": "danger-card"}.get(kind, "info-card")
    st.markdown(f"<div class='card {cls}'>{text}</div>", unsafe_allow_html=True)


def render_section(title: str, caption: str = "") -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if caption:
        st.markdown(f"<div class='section-caption'>{caption}</div>", unsafe_allow_html=True)


def dataframe_download(df: pd.DataFrame, file_name: str, label: str) -> None:
    if df.empty:
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv", use_container_width=True)


def localize_official_df(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    if lang == "বাংলা":
        out["commodity"] = out["commodity"].apply(lambda x: tr_item(x, lang))
        out = out.rename(columns={
            "date": "তারিখ",
            "commodity": "পণ্য",
            "unit": "একক",
            "low": "সর্বনিম্ন",
            "high": "সর্বোচ্চ",
            "midpoint": "মধ্যমান",
            "source": "উৎস",
        })
    return out


def localize_market_df(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    if lang == "বাংলা":
        out["commodity"] = out["commodity"].apply(lambda x: tr_item(x, lang))
        out["market"] = out["market"].apply(lambda x: tr_market(x, lang))
        out = out.rename(columns={
            "date": "তারিখ",
            "market": "বাজার",
            "area": "এলাকা",
            "commodity": "পণ্য",
            "category": "ধরন",
            "unit": "একক",
            "price_min": "সর্বনিম্ন দাম",
            "price_max": "সর্বোচ্চ দাম",
            "price": "দাম",
            "source": "উৎস",
            "source_url": "উৎস লিংক",
            "verified": "যাচাইকৃত",
        })
    return out


# ---------------------------------------------------------------------
# Load + language
# ---------------------------------------------------------------------
lang = st.radio("🌐 Language / ভাষা", ["English", "বাংলা"], horizontal=True, label_visibility="collapsed")
t = TEXT[lang]

market_df, official_df, meta = load_data()
latest_m = latest_market(market_df)
latest_o = latest_agg(official_df)

if st.button(f"🔄 {t['refresh']}", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

latest_date = None
if not latest_m.empty:
    latest_date = max(latest_m["date"])
elif not latest_o.empty:
    latest_date = max(pd.to_datetime(latest_o["date"]).dt.date)

mode = meta["mode"]
if mode == "verified":
    badge = f"<span class='badge badge-green'>🟢 {t['verified']}</span>"
elif mode == "preview":
    badge = f"<span class='badge badge-amber'>🟡 {t['preview']}</span>"
elif mode == "official_aggregate":
    badge = f"<span class='badge badge-green'>🟢 {t['verified']}</span>"
else:
    badge = f"<span class='badge badge-red'>🔴 {t['unavailable']}</span>"

st.markdown(
    f"""
<div class="mobile-hero">
  <div class="mobile-title">🛒 {t['title']}</div>
  <p class="mobile-subtitle">{t['subtitle']}</p>
  <div class="badge-row">
    {badge}
    <span class="badge">📅 {t['date']}: {fmt_date(latest_date)}</span>
    <span class="badge">📍 {t['coverage']}</span>
    <span class="badge">🕒 {t['updated']}: {meta['loaded_at']}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if mode == "preview":
    render_notice("warn", f"⚠️ {t['preview_warning']}")
elif mode == "unavailable":
    render_notice(
        "danger",
        "Official price data could not be loaded at this moment. Please refresh later."
        if lang == "English"
        else "এই মুহূর্তে সরকারি বাজারদর লোড করা যায়নি। পরে আবার রিফ্রেশ করুন।"
    )
    status = fetch_official_page_status()
    rows = []
    for name, value in status.items():
        rows.append({
            "Source" if lang == "English" else "উৎস": name,
            "Status" if lang == "English" else "অবস্থা": value.get("public_status", "Unavailable"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("Technical details" if lang == "English" else "প্রযুক্তিগত বিস্তারিত"):
        tech_rows = []
        for name, value in status.items():
            tech_rows.append({
                "Source": name,
                "Technical status": value.get("technical_status", ""),
                "URL": value.get("url", ""),
            })
        st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)
    st.stop()


# ---------------------------------------------------------------------
# Top summary
# ---------------------------------------------------------------------
item_count = int(latest_m["commodity"].nunique()) if not latest_m.empty else int(latest_o["commodity"].nunique()) if not latest_o.empty else 0
market_count = int(latest_m["market"].nunique()) if not latest_m.empty else 0
best_market = "—"
best_cost = np.nan
basket_df = pd.DataFrame()
if not latest_m.empty and mode != "preview":
    basket_df = basket_costs(latest_m, DEFAULT_BASKET)
    if not basket_df.empty:
        best_market = tr_market(basket_df.iloc[0]["market"], lang)
        best_cost = basket_df.iloc[0]["basket_cost"]

st.markdown("<div class='grid grid-4'>", unsafe_allow_html=True)
render_stat(f"📦 {t['items']}", str(item_count), t["official_prices"])
render_stat(f"🏪 {t['market_count']}", str(market_count) if market_count else "—", t["cheapest_caption"])
render_stat(f"🧺 {t['basket']}", money(best_cost, lang) if pd.notna(best_cost) else "—", best_market)
render_stat(f"🧾 {t['source']}", "DAM" if "Department of Agricultural Marketing" in meta.get("source","") else (meta["source"][:26] if meta["source"] else "—"), f"v{APP_VERSION}")
st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------
tab_today, tab_basket, tab_markets, tab_charts, tab_source = st.tabs(
    [f"🏷️ {t['today']}", f"🧺 {t['basket']}", f"🏪 {t['markets']}", f"📊 {t['charts']}", f"🧾 {t['source']}"]
)

with tab_today:
    render_section(f"🏷️ {t['official_prices']}", t["official_caption"])

    q = st.text_input(t["search"], placeholder="onion, rice, egg..." if lang == "English" else "পেঁয়াজ, চাল, ডিম...")

    card_source = latest_o.copy()
    if q:
        card_source = card_source[card_source["commodity"].astype(str).str.lower().str.contains(q.lower(), na=False)]

    if card_source.empty:
        st.info("No matching item found." if lang == "English" else "মিল থাকা পণ্য পাওয়া যায়নি।")
    else:
        # Top compact official cards
        for _, row in card_source.sort_values("commodity").head(18).iterrows():
            item = tr_item(row["commodity"], lang)
            unit = str(row.get("unit", "unit"))
            low = row.get("low", np.nan)
            high = row.get("high", np.nan)
            mid = row.get("midpoint", np.nan)
            price_txt = money(mid, lang, 1 if float(mid) != int(mid) else 0) if pd.notna(mid) else "—"
            if pd.notna(low) and pd.notna(high) and float(low) != float(high):
                meta_txt = f"{t['range']}: {money(low, lang)} – {money(high, lang)}"
            else:
                meta_txt = f"{t['source']}: {row.get('source','')}"
            render_item_card(item, price_txt, unit, meta_txt)

        if len(card_source) > 18:
            with st.expander(t["show_more"]):
                more = card_source.copy()
                more["commodity"] = more["commodity"].apply(lambda x: tr_item(x, lang))
                st.dataframe(
                    more[["commodity", "unit", "low", "high", "midpoint", "source"]],
                    use_container_width=True,
                    hide_index=True,
                )

    render_section(f"🚨 {t['alerts']}", "")
    if latest_o.empty:
        render_notice("info", t["official_only"])
    else:
        spread = latest_o.copy()
        spread["spread"] = spread["high"] - spread["low"]
        alerts = spread.sort_values("spread", ascending=False).head(4)
        for _, row in alerts.iterrows():
            if pd.notna(row["spread"]) and row["spread"] > 0:
                msg = (
                    f"⚠️ <b>{tr_item(row['commodity'], lang)}</b>: {t['range']} {money(row['low'], lang)} – {money(row['high'], lang)}"
                )
                render_notice("warn", msg)

with tab_basket:
    render_section(f"🧺 {t['basket_title']}", t["basket_caption"])

    available = sorted(set(latest_o["commodity"].tolist()) | set(latest_m["commodity"].tolist()))
    basket = {}
    for item in DEFAULT_BASKET:
        if item in available:
            unit = "piece" if item == "Egg" else "kg/litre"
            basket[item] = st.number_input(
                f"{tr_item(item, lang)} ({unit})",
                min_value=0.0,
                value=float(DEFAULT_BASKET[item]),
                step=0.5,
                key=f"qty_{item}",
            )

    if not latest_m.empty and mode != "preview":
        bdf = basket_costs(latest_m, basket)
        if not bdf.empty:
            st.markdown("<div class='grid grid-3'>", unsafe_allow_html=True)
            top3 = bdf.head(3)
            for _, row in top3.iterrows():
                render_stat(
                    f"🏪 {tr_market(row['market'], lang)}",
                    money(row["basket_cost"], lang),
                    f"{t['saving']}: {money(row['saving'], lang)}"
                )
            st.markdown("</div>", unsafe_allow_html=True)

            render_section(f"🏆 {t['market_ranking']}", "")
            for i, (_, row) in enumerate(bdf.head(8).iterrows(), start=1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(
                    f"""
<div class="card market-card">
  <div class="item-card">
    <div>
      <div class="item-name">{medal} {tr_market(row['market'], lang)}</div>
      <div class="item-meta">{row.get('area','Dhaka')} · {row['covered']} items covered</div>
    </div>
    <div class="price-pill">{money(row['basket_cost'], lang)}<div class="price-sub">{t['basket']}</div></div>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )
        else:
            render_notice("info", t["official_only"])
    elif not latest_o.empty:
        low, mid, high = aggregate_basket(latest_o, basket)
        st.markdown("<div class='grid grid-3'>", unsafe_allow_html=True)
        render_stat("Low", money(low, lang), "Official low estimate")
        render_stat("Average", money(mid, lang), "Official midpoint estimate")
        render_stat("High", money(high, lang), "Official high estimate")
        st.markdown("</div>", unsafe_allow_html=True)
        render_notice("info", t["official_only"])
    else:
        render_notice("danger", t["unavailable"])

with tab_markets:
    render_section(f"🏪 {t['market_ranking']}", t["cheapest_caption"])

    if latest_m.empty or mode == "preview":
        render_notice("warn", t["no_market"])
    else:
        cb = cheapest_by_item(latest_m)
        for _, row in cb.head(15).iterrows():
            render_item_card(
                tr_item(row["commodity"], lang),
                money(row["price"], lang),
                str(row["unit"]),
                f"{tr_market(row['market'], lang)} · {row.get('area','Dhaka')} · {t['saving']}: {money(row['saving'], lang)}",
            )

        map_data = latest_m.dropna(subset=["latitude", "longitude"]).copy()
        if not map_data.empty:
            render_section("🗺️ Dhaka map" if lang == "English" else "🗺️ ঢাকার মানচিত্র", "")
            market_avg = map_data.groupby(["market", "area", "latitude", "longitude"], as_index=False).agg(
                avg_price=("price", "mean"),
                items=("commodity", "nunique"),
            )
            st.map(market_avg.rename(columns={"latitude": "lat", "longitude": "lon"}), latitude="lat", longitude="lon", size=90)

with tab_charts:
    render_section(f"📊 {t['charts']}", "")
    plot_config = {"displayModeBar": False, "responsive": True}

    if not latest_o.empty:
        plot_df = latest_o.copy().sort_values("midpoint", ascending=False).head(14)
        plot_df["item"] = plot_df["commodity"].apply(lambda x: tr_item(x, lang))
        fig = px.bar(plot_df, x="midpoint", y="item", orientation="h", labels={"midpoint": t["price"], "item": t["items"]})
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True, config=plot_config)

    if not market_df.empty and market_df["date"].nunique() > 1:
        trend_items = sorted(market_df["commodity"].unique().tolist())
        default_items = [x for x in ["Onion", "Egg", "Soybean oil", "Rice (medium)"] if x in trend_items]
        selected = st.multiselect(
            "Trend items" if lang == "English" else "প্রবণতার পণ্য",
            trend_items,
            default=default_items,
            format_func=lambda x: tr_item(x, lang),
        )
        tdf = market_df[market_df["commodity"].isin(selected)].groupby(["date", "commodity"], as_index=False)["price"].mean()
        tdf["item"] = tdf["commodity"].apply(lambda x: tr_item(x, lang))
        fig2 = px.line(tdf, x="date", y="price", color="item", markers=True, labels={"price": t["price"], "date": t["date"], "item": t["items"]})
        fig2.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True, config=plot_config)

with tab_source:
    render_section(f"🧾 {t['source_title']}", t["footer"])

    st.markdown(
        f"""
<div class="card">
  <div class="item-name">{meta.get('source') or '—'}</div>
  <div class="item-meta">
    {t['status']}: {mode}<br>
    {t['date']}: {fmt_date(latest_date)}<br>
    App version: {APP_VERSION}<br>
    {'TCB may be temporarily unreachable from Streamlit because of SSL certificate verification; DAM remains the active official source.' if lang == 'English' else 'SSL certificate verification সমস্যার কারণে Streamlit থেকে TCB সাময়িকভাবে না-ও খুলতে পারে; DAM এখন সক্রিয় সরকারি উৎস হিসেবে ব্যবহৃত হচ্ছে।'}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if meta.get("notes"):
        with st.expander("Technical notes" if lang == "English" else "প্রযুক্তিগত নোট"):
            for note in meta["notes"]:
                st.write("-", note)

    with st.expander("Official pages monitored" if lang == "English" else "যেসব সরকারি পেজ দেখা হয়"):
        status = fetch_official_page_status()
        rows = []
        for k, v in status.items():
            rows.append({
                "Page" if lang == "English" else "পেজ": k,
                "Status" if lang == "English" else "অবস্থা": v.get("public_status", "Unavailable"),
                "Used in app" if lang == "English" else "অ্যাপে ব্যবহৃত": "Yes" if ("DAM" in k and v.get("ok")) else "No",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("Technical details" if lang == "English" else "প্রযুক্তিগত বিস্তারিত"):
            tech_rows = []
            for k, v in status.items():
                tech_rows.append({
                    "Page": k,
                    "Technical status": v.get("technical_status", ""),
                    "URL": v.get("url", ""),
                })
            st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    dataframe_download(market_df, "dhaka_marketwise_prices.csv", f"⬇️ {t['download']} — market-wise")
    dataframe_download(official_df, "official_reference_prices.csv", f"⬇️ {t['download']} — official reference")

    with st.expander("Full data table" if lang == "English" else "পূর্ণ ডেটা টেবিল"):
        if not latest_o.empty:
            st.dataframe(localize_official_df(latest_o, lang), use_container_width=True, hide_index=True)
        if not latest_m.empty and meta.get("mode") != "preview":
            st.dataframe(localize_market_df(latest_m, lang), use_container_width=True, hide_index=True)
        elif meta.get("mode") == "preview":
            render_notice("info", "Preview market-wise rows are hidden from the public table. Connect a verified market-wise feed to show real market data." if lang == "English" else "প্রিভিউ market-wise row পাবলিক টেবিলে লুকানো আছে। আসল বাজারভিত্তিক ডেটা দেখাতে যাচাইকৃত ফিড যুক্ত করুন।")

st.caption(t["footer"])
