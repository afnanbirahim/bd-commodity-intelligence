
"""
Dhaka Daily Price Watch — Mobile First Consumer Edition
Version: 5.0.0-full-app-resilient

Main behavior:
- Full app always loads.
- DAM live official data first.
- If live parsing fails, use cached official DAM reference snapshot.
- No public raw JSON/SSL error.
- No fake cheapest-market claim unless a verified market-wise feed is connected.
"""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(
    page_title="Dhaka Price Watch",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_VERSION = "11.0.0-github-csv-archive"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
OFFICIAL_CACHE_PATH = os.path.join(DATA_DIR, "official_reference_cache.csv")
HISTORY_PATH = os.path.join(DATA_DIR, "official_price_history.csv")
MARKETS_PATH = os.path.join(DATA_DIR, "dhaka_markets.csv")

TCB_DAILY_URL = "https://tcb.gov.bd/pages/daily-rmps"
DAM_DAILY_REPORT_URL = "https://market.dam.gov.bd/market_daily_price_report?L=E"
DAM_COMMODITY_PRINT_URL = "https://market.dam.gov.bd/commodity_wise_report/print"


st.markdown(
    """
<style>
:root {
  --bg:#f8fafc; --surface:#ffffff; --surface-soft:#f1f5f9; --text:#0f172a;
  --muted:#475569; --line:#e2e8f0; --green:#16a34a; --green-bg:#dcfce7;
  --amber:#d97706; --amber-bg:#fef3c7; --red:#dc2626; --red-bg:#fee2e2;
  --blue:#2563eb; --blue-bg:#dbeafe;
}
html, body, [data-testid="stAppViewContainer"] {background:var(--bg)!important;color:var(--text)!important;}
.main .block-container {max-width:1160px;padding-top:.7rem;padding-left:1rem;padding-right:1rem;padding-bottom:2rem;}
h1,h2,h3,h4,p,span,label,div {color:var(--text);}
.mobile-hero{background:linear-gradient(135deg,#ecfdf5 0%,#eff6ff 100%);border:1px solid var(--line);border-radius:24px;padding:18px;margin-bottom:14px;box-shadow:0 10px 24px rgba(15,23,42,.06);}
.mobile-title{font-size:1.85rem;line-height:1.08;letter-spacing:-.045em;font-weight:900;margin:0;}
.mobile-subtitle{color:var(--muted);font-size:.98rem;line-height:1.55;margin-top:9px;margin-bottom:0;}
.badge-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
.badge{display:inline-flex;align-items:center;gap:5px;padding:6px 10px;border-radius:999px;font-size:.80rem;line-height:1;font-weight:800;border:1px solid var(--line);background:var(--surface);color:var(--text);}
.badge-green{background:var(--green-bg);color:#14532d;border-color:#bbf7d0;}
.badge-amber{background:var(--amber-bg);color:#78350f;border-color:#fde68a;}
.badge-red{background:var(--red-bg);color:#7f1d1d;border-color:#fecaca;}
.grid{display:grid;gap:12px}.grid-2{grid-template-columns:repeat(2,minmax(0,1fr));}.grid-3{grid-template-columns:repeat(3,minmax(0,1fr));}.grid-4{grid-template-columns:repeat(4,minmax(0,1fr));}
.card{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:14px;box-shadow:0 8px 18px rgba(15,23,42,.045);overflow-wrap:anywhere;margin-bottom:10px;}
.stat-label{font-size:.77rem;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.04em;}
.stat-value{font-size:1.35rem;font-weight:900;letter-spacing:-.025em;margin-top:4px;color:var(--text);}
.stat-help{color:var(--muted);font-size:.82rem;margin-top:4px;}
.item-card{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;}
.item-name{font-weight:900;font-size:1.05rem;letter-spacing:-.02em;color:var(--text);}
.item-meta{color:var(--muted);font-size:.86rem;margin-top:2px;line-height:1.5;}
.price-pill{background:#14532d;color:#fff!important;font-weight:900;border-radius:14px;padding:8px 10px;text-align:right;min-width:82px;}
.price-sub{font-size:.72rem;opacity:.88;margin-top:2px;color:#dcfce7!important;}
.market-card{border-left:6px solid var(--green);}
.warn-card{background:var(--amber-bg);border:1px solid #fde68a;border-left:6px solid var(--amber);color:#78350f;}
.info-card{background:var(--blue-bg);border:1px solid #bfdbfe;border-left:6px solid var(--blue);color:#1e3a8a;}
.danger-card{background:var(--red-bg);border:1px solid #fecaca;border-left:6px solid var(--red);color:#7f1d1d;}
.section-title{font-size:1.45rem;font-weight:950;letter-spacing:-.04em;margin:24px 0 6px 0;}
.section-caption{color:var(--muted);line-height:1.55;margin-bottom:12px;}
[data-testid="stDataFrame"]{border-radius:16px;overflow:hidden;border:1px solid var(--line);}
.stTabs [data-baseweb="tab-list"]{gap:5px;overflow-x:auto;white-space:nowrap;}
.stTabs [data-baseweb="tab"]{border-radius:999px;padding:8px 14px;background:var(--surface-soft);color:var(--text);font-weight:800;}
.stTabs [aria-selected="true"]{background:var(--green-bg)!important;color:#14532d!important;border:1px solid #86efac!important;}
.stTabs [data-baseweb="tab"]:focus,.stTabs [data-baseweb="tab"]:active{background:var(--green-bg)!important;color:#14532d!important;}
button[kind="secondary"]{border-radius:14px!important;background:var(--surface)!important;color:var(--text)!important;border:1px solid var(--line)!important;}
button[kind="secondary"]:active,button[kind="secondary"]:focus{background:var(--green-bg)!important;color:#14532d!important;border-color:#86efac!important;}
@media(max-width:760px){
 .main .block-container{padding-top:.45rem;padding-left:.75rem;padding-right:.75rem;}
 .mobile-hero{border-radius:20px;padding:15px}.mobile-title{font-size:1.55rem}.mobile-subtitle{font-size:.90rem}
 .grid-2,.grid-3,.grid-4{grid-template-columns:1fr}.card{border-radius:18px;padding:13px}
 .item-card{grid-template-columns:1fr}.price-pill{text-align:left;display:inline-block;width:fit-content;min-width:0}
 .section-title{font-size:1.25rem;margin-top:18px}.stat-value{font-size:1.18rem}
}
</style>
""",
    unsafe_allow_html=True,
)


TEXT = {
    "English": {
        "title":"Dhaka Daily Price Watch",
        "subtitle":"Consumer-friendly official commodity prices for Dhaka. See latest price ranges, basket estimates, alerts and source status.",
        "verified":"Official data", "cached":"Cached official snapshot", "unavailable":"Unavailable",
        "updated":"Updated", "date":"Date", "coverage":"Dhaka", "items":"Items", "markets":"Markets",
        "basket":"Basket", "source":"Source", "today":"Today", "basket_tab":"Basket", "markets_tab":"Markets",
        "charts":"Charts", "source_tab":"Source", "trend_title":"Historical trend", "trend_caption":"Uses stored daily official snapshots. On a new deployment, the chart starts with today and becomes richer as the app collects future days.", "official_prices":"Latest official price ranges",
        "official_caption":"Cards are easier to read on mobile. Every item shows unit and low-high range.",
        "search":"Search item", "range":"Range", "price":"Price", "alerts":"Price alerts",
        "basket_title":"Smart shopping basket", "basket_caption":"Change quantities and see an official low-average-high estimate.",
        "market_title":"Market comparison", "map_title":"Dhaka market map", "map_caption":"All listed Dhaka market locations are shown. Cheapest item per market appears only with verified market-wise rows.", "cheapest_item":"Cheapest listed item", "no_market":"Market-wise verified Dhaka prices are not available from the current official public response.",
        "connect_market":"The official public response currently provides reference price ranges. Market-by-market cheapest prices will appear here when verified market-wise rows are available.",
        "source_title":"Source transparency", "download":"Download data", "status":"Status", "footer":"The app uses official DAM data when available and avoids unsupported cheapest-market claims.",
        "technical":"Technical details", "available":"Available", "temp_unavailable":"Temporarily unavailable",
        "cached_note":"Live DAM parsing was not available, so the app is showing the latest bundled official reference snapshot instead of stopping.",
        "official_note":"Official aggregate ranges are shown. Market-level cheapest ranking requires verified market-wise rows.",
    },
    "বাংলা": {
        "title":"ঢাকার দৈনিক বাজারদর",
        "subtitle":"ঢাকার ক্রেতাদের জন্য সরকারি নিত্যপণ্যের দাম। সর্বশেষ রেঞ্জ, ঝুড়ির হিসাব, সতর্কতা ও উৎসের অবস্থা দেখুন।",
        "verified":"সরকারি ডেটা", "cached":"ক্যাশড সরকারি স্ন্যাপশট", "unavailable":"পাওয়া যায়নি",
        "updated":"আপডেট", "date":"তারিখ", "coverage":"ঢাকা", "items":"পণ্য", "markets":"বাজার",
        "basket":"ঝুড়ি", "source":"উৎস", "today":"আজ", "basket_tab":"ঝুড়ি", "markets_tab":"বাজার",
        "charts":"চার্ট", "source_tab":"উৎস", "trend_title":"ঐতিহাসিক প্রবণতা", "trend_caption":"সংরক্ষিত দৈনিক সরকারি snapshot দিয়ে তৈরি। নতুন deployment-এ আজকের ডেটা দিয়ে শুরু হয় এবং পরের দিনগুলো জমলে সমৃদ্ধ হবে।", "official_prices":"সর্বশেষ সরকারি দাম-রেঞ্জ",
        "official_caption":"মোবাইলে সহজে পড়ার জন্য কার্ড ভিউ। প্রতিটি পণ্যে একক ও কম-বেশি রেঞ্জ দেখানো হয়েছে।",
        "search":"পণ্য খুঁজুন", "range":"রেঞ্জ", "price":"দাম", "alerts":"দাম সতর্কতা",
        "basket_title":"স্মার্ট বাজার-ঝুড়ি", "basket_caption":"পরিমাণ বদলে সরকারি কম-গড়-বেশি আনুমানিক হিসাব দেখুন।",
        "market_title":"বাজার তুলনা", "map_title":"ঢাকার বাজার মানচিত্র", "map_caption":"ঢাকার তালিকাভুক্ত বাজারগুলো মানচিত্রে দেখানো হয়েছে। যাচাইকৃত market-wise row থাকলেই প্রতি বাজারের সবচেয়ে কম দামের পণ্য দেখাবে।", "cheapest_item":"সবচেয়ে কম দামের তালিকাভুক্ত পণ্য", "no_market":"বর্তমান সরকারি public response থেকে ঢাকার যাচাইকৃত বাজারভিত্তিক দাম পাওয়া যাচ্ছে না।",
        "connect_market":"সরকারি public response বর্তমানে reference price range দেয়। যাচাইকৃত market-wise row পাওয়া গেলে এখানে বাজারভিত্তিক সবচেয়ে কম দাম দেখাবে।",
        "source_title":"উৎসের স্বচ্ছতা", "download":"ডেটা ডাউনলোড", "status":"অবস্থা", "footer":"অ্যাপটি DAM সরকারি ডেটা ব্যবহার করে এবং অসমর্থিত cheapest-market দাবি এড়ায়।",
        "technical":"প্রযুক্তিগত বিস্তারিত", "available":"চালু", "temp_unavailable":"সাময়িকভাবে পাওয়া যায়নি",
        "cached_note":"লাইভ DAM parsing পাওয়া যায়নি, তাই অ্যাপ বন্ধ না করে সর্বশেষ bundled official reference snapshot দেখাচ্ছে।",
        "official_note":"সরকারি aggregate range দেখানো হচ্ছে। বাজারভিত্তিক cheapest ranking-এর জন্য যাচাইকৃত market-wise row দরকার।",
    },
}

BN_COMMODITY = {
    "Ata (packet)":"আটা (প্যাকেট)", "Beef":"গরুর মাংস", "Boro-Coarse":"বোরো চাল (মোটা)",
    "Boro-Fine":"বোরো চাল (সরু)", "Boro-Medium":"বোরো চাল (মাঝারি)",
    "Egg Farm-Red":"লাল ফার্ম ডিম", "Farm-raised Hen":"ফার্মের মুরগি",
    "Garlic-Imported":"রসুন (আমদানি)", "Garlic-local":"রসুন (দেশি)",
    "Ginger-Imported":"আদা (আমদানি)", "Ginger-local":"আদা (দেশি)",
    "Gram-Whole":"ছোলা", "Green Chili":"কাঁচা মরিচ", "Iodized Salt (Packed)":"আয়োডিনযুক্ত লবণ (প্যাকেট)",
    "Mung":"মুগ ডাল", "Mutton":"খাসির মাংস", "Onion-local":"পেঁয়াজ (দেশি)",
    "Potato":"আলু", "Soybean":"সয়াবিন তেল", "Sugar (Local)":"চিনি (দেশি)",
    "Rice (medium)":"চাল (মাঝারি)", "Rice (coarse)":"চাল (মোটা)", "Rice (fine)":"চাল (সরু)",
    "Flour (atta)":"আটা", "Lentil (masur)":"মসুর ডাল", "Soybean oil":"সয়াবিন তেল",
    "Onion":"পেঁয়াজ", "Egg":"ডিম", "Broiler chicken":"ব্রয়লার মুরগি", "Sugar":"চিনি",
    "Garlic":"রসুন", "Ginger":"আদা",
}

BN_MARKET = {
    "Karwan Bazar":"কারওয়ান বাজার", "Shyambazar":"শ্যামবাজার", "Jatrabari Bazar":"যাত্রাবাড়ী বাজার",
    "Mohammadpur Krishi Market":"মোহাম্মদপুর কৃষি মার্কেট", "Mirpur-1 Kitchen Market":"মিরপুর-১ কাঁচাবাজার",
    "New Market Kitchen Bazar":"নিউ মার্কেট কাঁচাবাজার", "Uttara Sector 6 Market":"উত্তরা সেক্টর ৬ বাজার", "Rampura Bazar":"রামপুরা বাজার",
}

DEFAULT_BASKET_MATCH = {
    "Boro-Coarse": 5.0,
    "Ata (packet)": 2.0,
    "Gram-Whole": 1.0,
    "Onion-local": 2.0,
    "Potato": 2.0,
    "Soybean": 2.0,
    "Egg Farm-Red": 12.0,
    "Farm-raised Hen": 1.0,
    "Sugar (Local)": 1.0,
    "Iodized Salt (Packed)": 1.0,
}

def now_bd() -> datetime:
    return datetime.utcnow() + timedelta(hours=6)

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
    return str(value).strip().lower() in {"1","true","yes","y","on"}

def parse_date_any(value: Any):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    for i, d in enumerate("০১২৩৪৫৬۷۸۹"):
        text = text.replace(d, str(i))
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%d %B, %Y","%d %B %Y","%d %b %Y"):
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

def fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "—"
    return pd.to_datetime(value).strftime("%Y-%m-%d")

def infer_unit(name: str) -> str:
    n = str(name).lower()
    if "egg" in n:
        return "per piece"
    if "soybean" in n:
        return "per litre"
    if "salt" in n and "packed" in n:
        return "per packet"
    return "per kg"

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "product":"commodity", "item":"commodity", "commodities":"commodity", "commodity_name":"commodity",
        "bazar":"market", "bazaar":"market", "market_name":"market", "retail_price":"price",
        "avg_price":"price", "average_price":"price", "min_price":"price_min", "max_price":"price_max",
        "lat":"latitude", "lon":"longitude", "lng":"longitude",
    }
    rename = {}
    for col in df.columns:
        key = re.sub(r"[^a-z0-9_]+", "", str(col).strip().lower().replace(" ","_"))
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
            df["price"] = df[["price_min","price_max"]].apply(lambda r: np.nanmean([clean_number(r.iloc[0]), clean_number(r.iloc[1])]), axis=1)
        else:
            return pd.DataFrame()
    for col in ["price","price_min","price_max","latitude","longitude"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
    df["date"] = df["date"].apply(parse_date_any)
    df = df.dropna(subset=["date","market","commodity","price"])
    if df.empty:
        return pd.DataFrame()
    for col, val in {"area":"Dhaka","category":"Essential","unit":"kg","source":source_name,"source_url":"","verified":True}.items():
        if col not in df.columns:
            df[col] = val
    if "price_min" not in df.columns:
        df["price_min"] = df["price"]
    if "price_max" not in df.columns:
        df["price_max"] = df["price"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df[df["price"] > 0].copy()


@st.cache_data(ttl=60*60*24, show_spinner=False)
def load_market_locations() -> pd.DataFrame:
    """Load known Dhaka market coordinates for the public map."""
    try:
        df = pd.read_csv(MARKETS_PATH)
        needed = {"market", "area", "latitude", "longitude"}
        if not needed.issubset(set(df.columns)):
            return pd.DataFrame()
        df["latitude"] = df["latitude"].apply(clean_number)
        df["longitude"] = df["longitude"].apply(clean_number)
        df = df.dropna(subset=["market", "latitude", "longitude"])
        # Keep plausible Bangladesh/Dhaka coordinates only.
        df = df[(df["latitude"].between(20, 27)) & (df["longitude"].between(88, 93))]
        return df.drop_duplicates("market")
    except Exception:
        return pd.DataFrame()


def market_cheapest_items(latest_m: pd.DataFrame) -> pd.DataFrame:
    """For each market, return the lowest listed item from verified market-wise data."""
    if latest_m.empty:
        return pd.DataFrame()
    df = latest_m.dropna(subset=["market", "commodity", "price"]).copy()
    if df.empty:
        return pd.DataFrame()
    idx = df.groupby("market")["price"].idxmin()
    out = df.loc[idx, ["market", "commodity", "unit", "price", "area", "latitude", "longitude"]].copy()
    out = out.rename(columns={"commodity": "cheapest_item", "price": "cheapest_price"})
    return out

@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_source_status() -> Dict[str, Dict[str, Any]]:
    sources = {
        "TCB daily retail prices": TCB_DAILY_URL,
        "DAM daily market report": DAM_DAILY_REPORT_URL,
        "DAM commodity report": DAM_COMMODITY_PRINT_URL,
    }
    out = {}
    for name, url in sources.items():
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=14)
            out[name] = {"ok": bool(r.ok), "url": url, "public": "Available" if r.ok else "Temporarily unavailable", "technical": str(r.status_code)}
        except requests.exceptions.SSLError:
            out[name] = {"ok": False, "url": url, "public": "Temporarily unavailable", "technical": "SSL certificate verification failed"}
        except Exception as exc:
            out[name] = {"ok": False, "url": url, "public": "Temporarily unavailable", "technical": exc.__class__.__name__}
    return out

def parse_dam_text(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    for i, d in enumerate("০۱۲۳۴۵۶۷۸۹"):
        text = text.replace(d, str(i))
    report_date = now_bd().date()
    mdate = re.search(r"Report Date:\s*([0-9]{1,2}\s+[A-Za-z]+,?\s+[0-9]{4}|[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4}|[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})", text, re.I)
    if mdate:
        parsed = parse_date_any(mdate.group(1))
        if parsed is not None and not pd.isna(parsed):
            report_date = parsed.date()
    zone = text.split("Daily Price List Report", 1)[0] if "Daily Price List Report" in text else text
    pattern = re.compile(r"([A-Za-z][A-Za-z0-9()\\-/ ]{2,45}?):\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)", re.I)
    rows = []
    seen = set()
    for name, low, high in pattern.findall(zone):
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"^(Price Reports|Recent Prices|Market Prices)\s+", "", name, flags=re.I).strip()
        low_f, high_f = float(low), float(high)
        if len(name) < 2 or name.lower() in seen or high_f <= 0 or low_f <= 0:
            continue
        # Avoid dates being treated as prices by checking plausible commodity name.
        if any(bad in name.lower() for bad in ["report date", "select", "from date", "to date", "division", "district"]):
            continue
        seen.add(name.lower())
        rows.append({
            "date": report_date,
            "commodity": name,
            "unit": infer_unit(name),
            "low": low_f,
            "high": high_f,
            "midpoint": (low_f + high_f) / 2,
            "source": "Department of Agricultural Marketing (DAM)",
        })
    return pd.DataFrame(rows)


def parse_marketwise_price_table(html: str, source_url: str) -> pd.DataFrame:
    """
    Best-effort parser for DAM market daily price print result.
    It looks for rows containing market, commodity and price columns.
    If the page only contains aggregate ticker ranges, returns empty.
    """
    try:
        tables = pd.read_html(io.StringIO(html))
    except Exception:
        return pd.DataFrame()

    candidates = []
    for raw in tables:
        if raw is None or raw.empty or raw.shape[0] < 2:
            continue
        df = normalize_columns(raw)
        cols = list(df.columns)

        # Flatten multi-index columns if needed.
        df.columns = [re.sub(r"[^a-z0-9_]+", "", str(c).strip().lower().replace(" ", "_")) for c in df.columns]
        cols = list(df.columns)

        market_col = next((c for c in cols if "market" in c or "bazar" in c or "bazaar" in c), None)
        commodity_col = next((c for c in cols if "commodity" in c or "commodities" in c or "product" in c or "item" in c), None)
        price_col = next((c for c in cols if c in {"price", "retail_price", "wholesale_price", "average_price", "avg_price"} or ("price" in c and "type" not in c)), None)

        # Some DAM tables use positional columns. Try inference.
        if commodity_col is None and len(cols) >= 2:
            commodity_col = cols[1] if "market" in cols[0] else cols[0]
        if market_col is None:
            # Market might be in filter header, not row; then this is not truly market-wise.
            continue
        if price_col is None:
            numeric_cols = []
            for c in cols:
                vals = df[c].apply(clean_number)
                if vals.notna().sum() >= max(2, len(vals) * 0.25):
                    numeric_cols.append(c)
            if numeric_cols:
                price_col = numeric_cols[-1]
        if not market_col or not commodity_col or not price_col:
            continue

        tmp = pd.DataFrame()
        tmp["date"] = now_bd().date()
        tmp["market"] = df[market_col].astype(str).str.strip()
        tmp["commodity"] = df[commodity_col].astype(str).str.strip()
        tmp["price"] = df[price_col].apply(clean_number)
        tmp["unit"] = tmp["commodity"].apply(infer_unit)
        tmp["area"] = "Dhaka"
        tmp["source"] = "Department of Agricultural Marketing (DAM) market-wise parser"
        tmp["source_url"] = source_url
        tmp["verified"] = True
        tmp = tmp.dropna(subset=["market", "commodity", "price"])
        tmp = tmp[~tmp["market"].str.lower().str.contains("market|select|total|nan", na=False)]
        tmp = tmp[~tmp["commodity"].str.lower().str.contains("commodity|select|total|nan", na=False)]
        if not tmp.empty and tmp["market"].nunique() >= 1 and tmp["commodity"].nunique() >= 2:
            candidates.append(tmp)

    if not candidates:
        return pd.DataFrame()

    out = max(candidates, key=len)
    # Add coordinates if market matches known map file.
    try:
        loc = load_market_locations()
        if not loc.empty:
            out = out.merge(loc[["market", "area", "latitude", "longitude"]], on="market", how="left", suffixes=("", "_loc"))
            for col in ["area", "latitude", "longitude"]:
                loc_col = f"{col}_loc"
                if loc_col in out.columns:
                    out[col] = out[col].where(out[col].notna() & (out[col].astype(str) != ""), out[loc_col])
                    out = out.drop(columns=[loc_col])
    except Exception:
        pass

    return validate_market_df(out, "Department of Agricultural Marketing (DAM) market-wise parser")


@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_dam_marketwise_experimental() -> pd.DataFrame:
    """
    Experimental DAM market-wise connector.

    It tries:
    1) a user-provided direct print/export URL in secrets;
    2) DAM form discovery + POST/GET submission;
    3) common print endpoint parameter names.

    If DAM does not expose market-wise rows cleanly, returns empty.
    """
    direct_url = get_secret_or_env("DAM_MARKETWISE_PRINT_URL", "")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    urls_to_try = []
    if direct_url:
        urls_to_try.append(direct_url)

    today = now_bd().strftime("%Y-%m-%d")
    date_alt = now_bd().strftime("%d-%m-%Y")
    common_payloads = [
        {"division": "Dhaka", "district": "Dhaka", "price_type": "Retail", "date": today, "L": "E"},
        {"division_id": "Dhaka", "district_id": "Dhaka", "price_type": "Retail", "date": today, "L": "E"},
        {"division": "Dhaka", "district": "Dhaka", "price_type": "Retail", "report_date": today, "L": "E"},
        {"division": "Dhaka", "district": "Dhaka", "price_type": "Retail", "date": date_alt, "L": "E"},
    ]
    print_endpoint = DAM_DAILY_REPORT_URL.replace("market_daily_price_report?L=E", "market_daily_price_report/print")

    # Direct URLs / common GET params.
    for payload in common_payloads:
        try:
            r = session.get(print_endpoint, params=payload, timeout=22)
            if r.ok:
                parsed = parse_marketwise_price_table(r.text, r.url)
                if not parsed.empty:
                    return parsed
        except Exception:
            pass

    for url in urls_to_try:
        try:
            r = session.get(url, timeout=22)
            if r.ok:
                parsed = parse_marketwise_price_table(r.text, r.url)
                if not parsed.empty:
                    return parsed
        except Exception:
            pass

    # Form discovery and submit.
    try:
        form_page = session.get(DAM_DAILY_REPORT_URL, timeout=22)
        form_page.raise_for_status()
        soup = BeautifulSoup(form_page.text, "html.parser")
        forms = soup.find_all("form")
        for form in forms:
            form_text = form.get_text(" ", strip=True).lower()
            if "daily price" not in form_text and "market" not in form_text:
                continue

            action = form.get("action") or print_endpoint
            if action.startswith("/"):
                action = "https://market.dam.gov.bd" + action
            elif not action.startswith("http"):
                action = print_endpoint

            payload = {}
            selects = form.find_all("select")
            # Infer select order from DAM page: Division, District, Upazila, Market, Price Type
            desired_by_order = ["Dhaka", "Dhaka", "", "", "Retail"]
            for i, sel in enumerate(selects):
                name = sel.get("name")
                if not name:
                    continue
                desired = desired_by_order[i] if i < len(desired_by_order) else ""
                chosen = ""
                for opt in sel.find_all("option"):
                    opt_text = opt.get_text(" ", strip=True)
                    opt_val = opt.get("value", "")
                    if desired and desired.lower() in opt_text.lower():
                        chosen = opt_val or opt_text
                        break
                if not chosen:
                    # choose blank/all/default if available
                    opt = sel.find("option")
                    chosen = opt.get("value", "") if opt else ""
                payload[name] = chosen

            for inp in form.find_all("input"):
                name = inp.get("name")
                if not name:
                    continue
                typ = (inp.get("type") or "").lower()
                val = inp.get("value", "")
                if "date" in name.lower():
                    val = today
                if typ not in {"submit", "button", "reset", "file"}:
                    payload[name] = val

            # Force likely date/price fields if absent.
            for k in ["date", "report_date", "price_date"]:
                payload.setdefault(k, today)
            for k in ["price_type", "priceType", "price_type_id"]:
                payload.setdefault(k, "Retail")

            for method in ["post", "get"]:
                try:
                    if method == "post":
                        resp = session.post(action, data=payload, timeout=25)
                    else:
                        resp = session.get(action, params=payload, timeout=25)
                    if resp.ok:
                        parsed = parse_marketwise_price_table(resp.text, resp.url)
                        if not parsed.empty:
                            return parsed
                except Exception:
                    continue
    except Exception:
        pass

    return pd.DataFrame()

@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_dam_live_aggregate() -> pd.DataFrame:
    for url in [DAM_DAILY_REPORT_URL, DAM_COMMODITY_PRINT_URL]:
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
            r.raise_for_status()
            parsed = parse_dam_text(r.text)
            if not parsed.empty and len(parsed) >= 5:
                return parsed[["date","commodity","unit","low","high","midpoint","source"]]
            # Table fallback
            tables = pd.read_html(io.StringIO(r.text))
            for raw in tables:
                if raw.shape[0] < 5:
                    continue
                df = normalize_columns(raw)
                cols = list(df.columns)
                commodity_col = cols[0]
                numeric_cols = []
                for c in cols[1:]:
                    vals = df[c].apply(clean_number)
                    if vals.notna().sum() >= max(3, len(vals)*.2):
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
                out = out.dropna(subset=["commodity","midpoint"])
                out = out[~out["commodity"].str.lower().str.contains("serial|commodity|select|date", na=False)]
                if len(out) >= 5:
                    return out[["date","commodity","unit","low","high","midpoint","source"]]
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data(ttl=60*30, show_spinner=True)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    meta = {"mode":"unavailable","source":"","source_url":"","loaded_at":now_bd().strftime("%Y-%m-%d %H:%M"),"notes":[]}
    market_df = pd.DataFrame()
    verified_url = get_secret_or_env("OFFICIAL_MARKET_PRICE_CSV_URL", "")
    if verified_url:
        try:
            r = requests.get(verified_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=25)
            r.raise_for_status()
            raw = pd.read_csv(io.StringIO(r.text))
            market_df = validate_market_df(raw, "Verified Dhaka market-wise feed")
            if not market_df.empty:
                meta.update({"mode":"verified_marketwise","source":"Verified Dhaka market-wise feed","source_url":verified_url})
        except Exception as exc:
            meta["notes"].append(f"Verified market-wise feed unavailable: {exc.__class__.__name__}")

    if market_df.empty:
        market_df = fetch_dam_marketwise_experimental()
        if not market_df.empty:
            meta.update({"mode":"dam_marketwise_experimental","source":"DAM experimental market-wise parser","source_url":DAM_DAILY_REPORT_URL})
        else:
            meta["notes"].append("DAM experimental market-wise parser did not return clean market-wise rows.")

    official_df = fetch_dam_live_aggregate()
    if not official_df.empty:
        meta.update({"mode":"official_live","source":"Department of Agricultural Marketing (DAM)","source_url":DAM_DAILY_REPORT_URL})
    else:
        try:
            official_df = pd.read_csv(OFFICIAL_CACHE_PATH)
            official_df["date"] = pd.to_datetime(official_df["date"]).dt.date
            meta.update({"mode":"official_cache","source":"DAM cached official reference snapshot","source_url":DAM_DAILY_REPORT_URL})
            meta["notes"].append("Live DAM parsing failed; cached official reference snapshot loaded.")
        except Exception as exc:
            meta["notes"].append(f"Official cache failed: {exc.__class__.__name__}")

    return market_df, official_df, meta

def latest_market(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["date"] == max(df["date"])].copy()

def latest_official(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    dd = pd.to_datetime(df["date"]).dt.date
    return df[dd == max(dd)].copy()


def load_and_update_history(official_df: pd.DataFrame) -> pd.DataFrame:
    """
    Read historical official price snapshots from the GitHub-tracked CSV archive.

    The Streamlit app itself does not commit to GitHub.
    A GitHub Action updates data/official_price_history.csv daily.
    For immediate display, today's fetched official_df is merged in memory.
    """
    try:
        history = pd.DataFrame()
        if os.path.exists(HISTORY_PATH):
            history = pd.read_csv(HISTORY_PATH)

        current = official_df.copy()
        if not current.empty:
            current["date"] = pd.to_datetime(current["date"]).dt.date.astype(str)
            if "snapshot_saved_at" not in current.columns:
                current["snapshot_saved_at"] = now_bd().strftime("%Y-%m-%d %H:%M:%S")

        if history.empty:
            combined = current
        elif current.empty:
            combined = history
        else:
            combined = pd.concat([history, current], ignore_index=True)

        if combined.empty:
            return pd.DataFrame()

        for col in ["low", "high", "midpoint"]:
            if col in combined.columns:
                combined[col] = pd.to_numeric(combined[col], errors="coerce")

        combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.date.astype(str)
        combined = combined.dropna(subset=["date", "commodity", "midpoint"])
        combined = combined.drop_duplicates(subset=["date", "commodity", "unit"], keep="last")
        return combined.sort_values(["commodity", "date"])
    except Exception:
        return official_df.copy() if not official_df.empty else pd.DataFrame()

def basket_estimate(official_df: pd.DataFrame, basket: Dict[str, float]):
    low = mid = high = 0.0
    used = []
    for item, qty in basket.items():
        sub = official_df[official_df["commodity"] == item]
        if sub.empty:
            continue
        unit = str(sub["unit"].iloc[0]).lower()
        q = float(qty)
        # Egg is already per piece in this app cache/normalization.
        low += float(sub["low"].iloc[0]) * q
        mid += float(sub["midpoint"].iloc[0]) * q
        high += float(sub["high"].iloc[0]) * q
        used.append(item)
    return low, mid, high, used

def cheapest_market_basket(latest_m: pd.DataFrame, basket: Dict[str, float]) -> pd.DataFrame:
    if latest_m.empty:
        return pd.DataFrame()
    rows = []
    for market, g in latest_m.groupby("market"):
        total = 0; covered = 0
        for item, qty in basket.items():
            sub = g[g["commodity"] == item]
            if sub.empty:
                continue
            total += float(sub["price"].iloc[0]) * float(qty)
            covered += 1
        if covered:
            first = g.iloc[0]
            rows.append({"market":market,"area":first.get("area","Dhaka"),"basket_cost":total,"covered":covered})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["saving"] = out["basket_cost"].max() - out["basket_cost"]
    return out.sort_values("basket_cost")

def localize_official(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    out = df.copy()
    if lang == "বাংলা":
        out["commodity"] = out["commodity"].apply(lambda x: tr_item(x, lang))
        out = out.rename(columns={"date":"তারিখ","commodity":"পণ্য","unit":"একক","low":"সর্বনিম্ন","high":"সর্বোচ্চ","midpoint":"মধ্যমান","source":"উৎস"})
    return out

def localize_market(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    out = df.copy()
    if lang == "বাংলা":
        out["commodity"] = out["commodity"].apply(lambda x: tr_item(x, lang))
        if "market" in out.columns:
            out["market"] = out["market"].apply(lambda x: tr_market(x, lang))
        out = out.rename(columns={"date":"তারিখ","market":"বাজার","area":"এলাকা","commodity":"পণ্য","category":"ধরন","unit":"একক","price_min":"সর্বনিম্ন দাম","price_max":"সর্বোচ্চ দাম","price":"দাম","source":"উৎস","source_url":"উৎস লিংক","verified":"যাচাইকৃত"})
    return out

def render_stat(label: str, value: str, help_text: str = ""):
    st.markdown(f"""<div class="card"><div class="stat-label">{label}</div><div class="stat-value">{value}</div><div class="stat-help">{help_text}</div></div>""", unsafe_allow_html=True)

def render_card(name: str, price: str, unit: str, meta: str = ""):
    st.markdown(f"""<div class="card item-card"><div><div class="item-name">{name}</div><div class="item-meta">{meta}</div></div><div class="price-pill">{price}<div class="price-sub">{unit}</div></div></div>""", unsafe_allow_html=True)

def notice(kind: str, text: str):
    cls = {"warn":"warn-card","info":"info-card","danger":"danger-card"}.get(kind,"info-card")
    st.markdown(f"<div class='card {cls}'>{text}</div>", unsafe_allow_html=True)

def section(title: str, caption: str = ""):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if caption:
        st.markdown(f"<div class='section-caption'>{caption}</div>", unsafe_allow_html=True)


lang = st.radio("🌐 Language / ভাষা", ["English","বাংলা"], horizontal=True, label_visibility="collapsed")
t = TEXT[lang]

if st.button(f"🔄 {t['updated']}", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

market_df, official_df, meta = load_data()
latest_m = latest_market(market_df)
latest_o = latest_official(official_df)
history_df = load_and_update_history(official_df)

latest_date = None
if not latest_o.empty:
    latest_date = max(pd.to_datetime(latest_o["date"]).dt.date)
elif not latest_m.empty:
    latest_date = max(latest_m["date"])

if meta["mode"] in {"official_live", "verified_marketwise", "dam_marketwise_experimental"}:
    badge = f"<span class='badge badge-green'>🟢 {t['verified']}</span>"
elif meta["mode"] == "official_cache":
    badge = f"<span class='badge badge-amber'>🟡 {t['cached']}</span>"
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
""", unsafe_allow_html=True)

if meta["mode"] == "official_cache":
    notice("warn", f"⚠️ {t['cached_note']}")
elif meta["mode"] == "unavailable":
    notice("danger", "Official data is unavailable now, but the app interface remains active." if lang == "English" else "সরকারি ডেটা এখন পাওয়া যায়নি, তবে অ্যাপ ইন্টারফেস চালু আছে।")

item_count = int(latest_o["commodity"].nunique()) if not latest_o.empty else int(latest_m["commodity"].nunique()) if not latest_m.empty else 0
market_count = int(latest_m["market"].nunique()) if not latest_m.empty else 0
low, mid, high, used = basket_estimate(latest_o, DEFAULT_BASKET_MATCH) if not latest_o.empty else (np.nan, np.nan, np.nan, [])

st.markdown("<div class='grid grid-4'>", unsafe_allow_html=True)
render_stat(f"📦 {t['items']}", str(item_count), t["official_prices"])
render_stat(f"🏪 {t['markets']}", str(market_count) if market_count else "—", t["official_note"])
render_stat(f"🧺 {t['basket']}", money(mid, lang) if pd.notna(mid) and mid > 0 else "—", "Official midpoint estimate")
render_stat(f"🧾 {t['source']}", "DAM" if "DAM" in meta.get("source","") or "Agricultural" in meta.get("source","") else (meta.get("source") or "—"), f"v{APP_VERSION}")
st.markdown("</div>", unsafe_allow_html=True)

tab_today, tab_basket, tab_markets, tab_charts, tab_source = st.tabs([f"🏷️ {t['today']}", f"🧺 {t['basket_tab']}", f"🏪 {t['markets_tab']}", f"📊 {t['charts']}", f"🧾 {t['source_tab']}"])

with tab_today:
    section(f"🏷️ {t['official_prices']}", t["official_caption"])
    q = st.text_input(t["search"], placeholder="onion, rice, egg..." if lang=="English" else "পেঁয়াজ, চাল, ডিম...")
    cards = latest_o.copy()
    if q and not cards.empty:
        cards = cards[cards["commodity"].astype(str).str.lower().str.contains(q.lower(), na=False)]
    if cards.empty:
        notice("danger", t["unavailable"])
    else:
        for _, row in cards.sort_values("commodity").head(24).iterrows():
            item = tr_item(row["commodity"], lang)
            midv = row.get("midpoint", np.nan)
            decimals = 1 if pd.notna(midv) and abs(float(midv)-round(float(midv))) > .01 else 0
            meta_txt = f"{t['range']}: {money(row['low'], lang)} – {money(row['high'], lang)} · {t['source']}: DAM"
            render_card(item, money(midv, lang, decimals), str(row.get("unit","unit")), meta_txt)
    section(f"🚨 {t['alerts']}")
    if not latest_o.empty:
        alerts = latest_o.copy()
        alerts["spread"] = alerts["high"] - alerts["low"]
        for _, row in alerts.sort_values("spread", ascending=False).head(5).iterrows():
            if pd.notna(row["spread"]) and row["spread"] > 0:
                notice("warn", f"⚠️ <b>{tr_item(row['commodity'], lang)}</b>: {t['range']} {money(row['low'], lang)} – {money(row['high'], lang)}")
    else:
        notice("info", t["official_note"])

with tab_basket:
    section(f"🧺 {t['basket_title']}", t["basket_caption"])
    basket = {}
    for item, qty in DEFAULT_BASKET_MATCH.items():
        if latest_o.empty or item in set(latest_o["commodity"]):
            unit = str(latest_o[latest_o["commodity"] == item]["unit"].iloc[0]) if not latest_o.empty and item in set(latest_o["commodity"]) else "unit"
            basket[item] = st.number_input(f"{tr_item(item, lang)} ({unit})", min_value=0.0, value=float(qty), step=0.5, key=f"qty_{item}")
    if not latest_o.empty:
        low, mid, high, used = basket_estimate(latest_o, basket)
        st.markdown("<div class='grid grid-3'>", unsafe_allow_html=True)
        render_stat("Low" if lang=="English" else "কম", money(low, lang), "Official low estimate")
        render_stat("Average" if lang=="English" else "গড়", money(mid, lang), "Official midpoint estimate")
        render_stat("High" if lang=="English" else "বেশি", money(high, lang), "Official high estimate")
        st.markdown("</div>", unsafe_allow_html=True)
        rows = []
        for item, qty in basket.items():
            if qty <= 0:
                continue
            sub = latest_o[latest_o["commodity"] == item]
            if sub.empty:
                continue
            rows.append({
                "Item" if lang=="English" else "পণ্য": tr_item(item, lang),
                "Quantity" if lang=="English" else "পরিমাণ": qty,
                "Unit" if lang=="English" else "একক": sub["unit"].iloc[0],
                "Average price" if lang=="English" else "গড় দাম": sub["midpoint"].iloc[0],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        notice("info", t["official_note"])
    else:
        notice("danger", t["unavailable"])

with tab_markets:
    section(f"🗺️ {t['map_title']}", t["map_caption"])

    market_locations = load_market_locations()
    cheapest_items = market_cheapest_items(latest_m)

    if market_locations.empty:
        notice("warn", "Market coordinates are missing." if lang == "English" else "বাজারের লোকেশন ডেটা পাওয়া যায়নি।")
    else:
        map_df = market_locations.copy()
        map_df["display_market"] = map_df["market"].apply(lambda x: tr_market(x, lang))
        map_df["display_area"] = map_df["area"]

        if not cheapest_items.empty:
            map_df = map_df.merge(
                cheapest_items[["market", "cheapest_item", "cheapest_price", "unit"]],
                on="market",
                how="left",
            )
            map_df["tooltip"] = map_df.apply(
                lambda r: (
                    f"{r['display_market']}<br>{r['display_area']}<br>{t['cheapest_item']}: "
                    f"{tr_item(r['cheapest_item'], lang)} · {money(r['cheapest_price'], lang)} / {r['unit']}"
                    if pd.notna(r.get("cheapest_item")) else f"{r['display_market']}<br>{r['display_area']}"
                ),
                axis=1,
            )
            color_col = "cheapest_price"
        else:
            map_df["tooltip"] = map_df.apply(lambda r: f"{r['display_market']}<br>{r['display_area']}", axis=1)
            map_df["cheapest_price"] = 1
            color_col = "cheapest_price"

        # Safe map rendering:
        # Do not pass missing columns to Plotly hover_data. That caused Streamlit Cloud errors.
        hover_cols = {
            "display_area": True,
            "latitude": False,
            "longitude": False,
        }
        if "cheapest_item" in map_df.columns:
            map_df["cheapest_item_display"] = map_df["cheapest_item"].apply(
                lambda x: tr_item(x, lang) if pd.notna(x) else ("Not available yet" if lang == "English" else "এখনো পাওয়া যায়নি")
            )
            hover_cols["cheapest_item_display"] = True
        if "unit" in map_df.columns:
            hover_cols["unit"] = True

        try:
            fig_map = px.scatter_mapbox(
                map_df,
                lat="latitude",
                lon="longitude",
                hover_name="display_market",
                hover_data=hover_cols,
                zoom=10.4,
                height=430,
            )
            fig_map.update_traces(marker={"size": 14})
            fig_map.update_layout(
                mapbox_style="open-street-map",
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        except Exception:
            # Fallback that should never crash the app.
            fallback_map = map_df.rename(columns={"latitude": "lat", "longitude": "lon"})
            st.map(fallback_map, latitude="lat", longitude="lon", size=80)

        if cheapest_items.empty:
            notice("info", t["no_market"])
            section(f"🏪 {t['markets_tab']}", "")
            for _, row in market_locations.sort_values("market").iterrows():
                st.markdown(
                    f"""<div class="card"><div class="item-name">📍 {tr_market(row['market'], lang)}</div><div class="item-meta">{row.get('area','Dhaka')} · {t['cheapest_item']}: {'Not available yet' if lang == 'English' else 'এখনো পাওয়া যায়নি'}</div></div>""",
                    unsafe_allow_html=True,
                )
        else:
            section(f"🏷️ {t['cheapest_item']}", "")
            for _, row in cheapest_items.sort_values("market").iterrows():
                render_card(
                    tr_market(row["market"], lang),
                    money(row["cheapest_price"], lang),
                    str(row["unit"]),
                    f"{tr_item(row['cheapest_item'], lang)} · {row.get('area','Dhaka')}",
                )

    section(f"🏪 {t['market_title']}", t["connect_market"])
    if latest_m.empty:
        notice("warn", t["no_market"])
    else:
        bdf = cheapest_market_basket(latest_m, DEFAULT_BASKET_MATCH)
        if not bdf.empty:
            for i, (_, row) in enumerate(bdf.head(10).iterrows(), start=1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f"""<div class="card market-card"><div class="item-card"><div><div class="item-name">{medal} {tr_market(row['market'], lang)}</div><div class="item-meta">{row.get('area','Dhaka')} · {row['covered']} items covered</div></div><div class="price-pill">{money(row['basket_cost'], lang)}<div class="price-sub">{t['basket']}</div></div></div></div>""", unsafe_allow_html=True)

with tab_charts:
    section(f"📈 {t['trend_title']}", t["trend_caption"])
    plot_config = {"displayModeBar": False, "responsive": True}

    if not history_df.empty:
        hdf = history_df.copy()
        hdf["date"] = pd.to_datetime(hdf["date"], errors="coerce")
        hdf = hdf.dropna(subset=["date", "commodity", "midpoint"])
        commodities = sorted(hdf["commodity"].dropna().unique().tolist())
        preferred = [x for x in ["Onion-local", "Potato", "Egg Farm-Red", "Soybean", "Boro-Coarse"] if x in commodities]
        selected = st.multiselect(
            "Trend items" if lang == "English" else "প্রবণতার পণ্য",
            commodities,
            default=preferred[:4] if preferred else commodities[:4],
            format_func=lambda x: tr_item(x, lang),
        )
        trend = hdf[hdf["commodity"].isin(selected)].copy()
        trend["item"] = trend["commodity"].apply(lambda x: tr_item(x, lang))
        if trend.empty:
            notice("info", "Select at least one item." if lang == "English" else "কমপক্ষে একটি পণ্য নির্বাচন করুন।")
        else:
            fig_trend = px.line(
                trend.sort_values("date"),
                x="date",
                y="midpoint",
                color="item",
                markers=True,
                labels={"date": t["date"], "midpoint": t["price"], "item": t["items"]},
            )
            fig_trend.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_trend, use_container_width=True, config=plot_config)
            if trend["date"].nunique() < 2:
                notice("info", "Only one official snapshot is stored so far. The line will become a real historical trend after daily snapshots accumulate." if lang == "English" else "এখনো শুধু এক দিনের সরকারি snapshot আছে। প্রতিদিন snapshot জমলে এটি আসল historical trend হবে।")
    else:
        notice("info", "Historical data is not available yet." if lang == "English" else "ঐতিহাসিক ডেটা এখনো পাওয়া যায়নি।")

    section(f"📊 {t['charts']}")
    if not latest_o.empty:
        plot_df = latest_o.copy()
        plot_df["item"] = plot_df["commodity"].apply(lambda x: tr_item(x, lang))
        fig = px.bar(plot_df.sort_values("midpoint", ascending=False).head(16), x="midpoint", y="item", orientation="h", labels={"midpoint":t["price"],"item":t["items"]})
        fig.update_layout(height=430, margin=dict(l=0,r=0,t=10,b=0), yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig, use_container_width=True, config=plot_config)
        spread = latest_o.copy()
        spread["spread"] = spread["high"] - spread["low"]
        spread["item"] = spread["commodity"].apply(lambda x: tr_item(x, lang))
        fig2 = px.bar(spread.sort_values("spread", ascending=False).head(12), x="spread", y="item", orientation="h", labels={"spread":t["range"],"item":t["items"]})
        fig2.update_layout(height=360, margin=dict(l=0,r=0,t=10,b=0), yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig2, use_container_width=True, config=plot_config)
    else:
        notice("danger", t["unavailable"])

with tab_source:
    section(f"🧾 {t['source_title']}", t["footer"])
    st.markdown(f"""<div class="card"><div class="item-name">{meta.get('source') or '—'}</div><div class="item-meta">{t['status']}: {meta.get('mode')}<br>{t['date']}: {fmt_date(latest_date)}<br>App version: {APP_VERSION}<br>{"Market-wise data: available" if not latest_m.empty else "Market-wise data: not available in public official response"}</div></div>""", unsafe_allow_html=True)
    statuses = fetch_source_status()
    source_rows = []
    for name, value in statuses.items():
        source_rows.append({
            "Source" if lang=="English" else "উৎস": name,
            "Status" if lang=="English" else "অবস্থা": t["available"] if value.get("ok") else t["temp_unavailable"],
            "Used" if lang=="English" else "ব্যবহৃত": "Yes" if ("DAM" in name and value.get("ok")) else "No",
        })
    st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)
    with st.expander(t["technical"]):
        tech = [{"Source":k, "Technical status":v["technical"], "URL":v["url"]} for k, v in statuses.items()]
        st.dataframe(pd.DataFrame(tech), use_container_width=True, hide_index=True)
        if meta.get("notes"):
            for n in meta["notes"]:
                st.write("-", n)

    with st.expander("Admin setup for market-wise cheapest prices" if lang=="English" else "বাজারভিত্তিক কম দাম দেখানোর অ্যাডমিন সেটআপ"):
        st.markdown(
            """
To show true cheapest markets, provide a verified market-wise CSV/API with columns:

`date, market, area, commodity, unit, price, source, verified, latitude, longitude`

Then add this in Streamlit secrets:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```

The public app will keep showing official reference prices even without this feed.
"""
            if lang=="English"
            else
            """
সত্যিকারের বাজারভিত্তিক সবচেয়ে কম দাম দেখাতে একটি যাচাইকৃত market-wise CSV/API দরকার:

`date, market, area, commodity, unit, price, source, verified, latitude, longitude`

তারপর Streamlit secrets-এ দিন:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```

এই feed না থাকলেও public app সরকারি reference price দেখাবে।
"""
        )
    st.download_button(f"⬇️ {t['download']} — official", latest_o.to_csv(index=False).encode("utf-8"), "official_reference_prices.csv", "text/csv", use_container_width=True)
    if not history_df.empty:
        st.download_button(f"⬇️ {t['download']} — history", history_df.to_csv(index=False).encode("utf-8"), "official_price_history.csv", "text/csv", use_container_width=True)
    if not latest_m.empty:
        st.download_button(f"⬇️ {t['download']} — market-wise", latest_m.to_csv(index=False).encode("utf-8"), "marketwise_prices.csv", "text/csv", use_container_width=True)
    with st.expander("Full data table" if lang=="English" else "পূর্ণ ডেটা টেবিল"):
        if not latest_o.empty:
            st.dataframe(localize_official(latest_o, lang), use_container_width=True, hide_index=True)
        if not latest_m.empty:
            st.dataframe(localize_market(latest_m, lang), use_container_width=True, hide_index=True)

st.caption(t["footer"])
