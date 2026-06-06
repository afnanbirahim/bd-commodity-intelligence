from __future__ import annotations

import io
import os
import re
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import urllib3
import streamlit as st
import plotly.express as px
import pydeck as pdk
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

APP_NAME = "Bangladesh Commodity Intelligence"
APP_VERSION = "2.3.0-consumer-final"
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
    "rice", "aman", "boro", "ata", "flour", "oil", "soybean", "lentil", "masur", "mung", "gram",
    "sugar", "salt", "onion", "garlic", "ginger", "potato", "egg", "hen", "chicken",
    "beef", "mutton", "fish", "chili", "chilli",
]

KEY_PRICE_ORDER = [
    "rice", "boro", "aman", "ata", "flour", "onion", "potato", "soybean", "oil",
    "egg", "hen", "chicken", "lentil", "mung", "gram", "sugar", "salt", "beef", "mutton",
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
        "subtitle": "Latest verified essential commodity prices for consumers. Official data only. No demo prices. No fake market ranking.",
        "language": "Language",
        "source_ok": "Official data loaded",
        "source_partial": "Official price ranges are available; Dhaka market ranking is unavailable today.",
        "source_fail": "Official data unavailable right now",
        "last_updated": "Last updated",
        "data_date": "Data date",
        "status": "Status",
        "coverage": "Dhaka market data",
        "covered": "Commodities covered",
        "available": "Available",
        "not_available": "Unavailable today",
        "official_ranges": "📌 Latest official price ranges",
        "official_ranges_help": "Official aggregate/range prices parsed from public DAM data. Units are shown exactly as published when machine-readable unit detail is unavailable.",
        "key_prices": "💳 Today's key official prices",
        "key_prices_help": "Consumer-friendly view of essential items from the latest verified official data.",
        "cheapest_market": "🏷️ Cheapest Dhaka market by commodity",
        "cheapest_market_help": "This appears only when official/verified market-wise Dhaka rows are available.",
        "no_marketwise": "Official market-wise Dhaka rows are not available to this deployment today. Showing official aggregate/range prices instead of fake cheapest-market results.",
        "basket": "🧺 Household basket estimate",
        "basket_help": "If market-wise rows are available, this ranks markets. Otherwise it estimates a weekly basket using official aggregate ranges.",
        "map": "🗺️ Dhaka market coverage map",
        "charts": "📊 Price spread and trend view",
        "transparency": "🔎 Data transparency",
        "consumer_note": "Consumer note",
        "consumer_note_text": "Prices can vary by quality, brand, package size, retail shop, and time of day. Use this as a verified reference, not a bargaining guarantee.",
        "reload": "Refresh official data",
        "download": "Download current data",
        "market_unavailable": "Market-wise ranking is unavailable until the official source returns market-level Dhaka rows.",
        "verified": "Verified",
        "partial": "Prices available",
        "unavailable": "Unavailable",
        "unit_published": "As published",
        "source_monitor": "Official source monitor",
        "technical_details": "Technical details",
        "basket_summary": "🛒 Estimated weekly household basket",
        "low": "Low",
        "mid": "Average",
        "high": "High",
        "spinner": "Fetching official public sources...",
        "no_data_error": "No verified official price data could be loaded and no cache exists yet. Please check internet access or official source availability.",
        "key_prices_fail": "Key official prices could not be summarized today.",
        "basket_fail": "Basket could not be calculated because matching official commodity rows were not found.",
        "basket_market_ok": "Market-wise basket ranking is available from verified market rows.",
        "basket_no_market": "Market-wise basket ranking is not shown because market-level data was not available. This is an official aggregate weekly basket estimate.",
        "official_ranges_none": "No aggregate official range data parsed from DAM today.",
        "chart_price_title": "Higher-price essentials",
        "chart_spread_title": "Official low-high spread",
        "axis_price": "Price",
        "axis_spread": "Spread",
        "axis_commodity": "Commodity",
        "map_note": "Base map place names come from OpenStreetMap tiles. Market marker labels/tooltips are localized by the app.",
        "covered_markets": "Covered Dhaka markets",
        "source_policy": "This app uses only verified official/public-source data or a backend-configured verified official feed. It does not display demo prices as real prices. If official market-wise data is not available, the app clearly says so.",
    },
    "বাংলা": {
        "title": "🛒 বাংলাদেশ কমোডিটি ইন্টেলিজেন্স",
        "subtitle": "ভোক্তাদের জন্য সর্বশেষ যাচাইকৃত নিত্যপ্রয়োজনীয় পণ্যের বাজারদর। শুধু সরকারি তথ্য; ডেমো দাম নয়, ভুয়া র‍্যাঙ্কিং নয়।",
        "language": "ভাষা",
        "source_ok": "সরকারি তথ্য পাওয়া গেছে",
        "source_partial": "সরকারি মূল্যসীমা পাওয়া গেছে; ঢাকার বাজারভিত্তিক র‍্যাঙ্কিং আজ পাওয়া যায়নি।",
        "source_fail": "এই মুহূর্তে সরকারি তথ্য পাওয়া যাচ্ছে না",
        "last_updated": "সর্বশেষ হালনাগাদ",
        "data_date": "তথ্যের তারিখ",
        "status": "অবস্থা",
        "coverage": "ঢাকার বাজারভিত্তিক তথ্য",
        "covered": "পণ্যের সংখ্যা",
        "available": "পাওয়া গেছে",
        "not_available": "আজ পাওয়া যায়নি",
        "official_ranges": "📌 সর্বশেষ সরকারি মূল্যসীমা",
        "official_ranges_help": "DAM-এর পাবলিক সরকারি তথ্য থেকে পাওয়া সামগ্রিক/মূল্যসীমা। মেশিন-রিডেবল ইউনিট না থাকলে প্রকাশিত রূপেই দেখানো হয়।",
        "key_prices": "💳 আজকের গুরুত্বপূর্ণ সরকারি দাম",
        "key_prices_help": "সর্বশেষ যাচাইকৃত সরকারি তথ্য থেকে ভোক্তাবান্ধব নিত্যপণ্যের তালিকা।",
        "cheapest_market": "🏷️ পণ্যভিত্তিক ঢাকার সবচেয়ে কমদামের বাজার",
        "cheapest_market_help": "শুধু যাচাইকৃত/সরকারি বাজারভিত্তিক ঢাকার তথ্য পাওয়া গেলে এটি দেখাবে।",
        "no_marketwise": "আজ এই ডেপ্লয়মেন্টে সরকারি বাজারভিত্তিক ঢাকার সারি পাওয়া যায়নি। তাই ভুয়া কমদামের বাজার না দেখিয়ে সরকারি সামগ্রিক মূল্যসীমা দেখানো হচ্ছে।",
        "basket": "🧺 পরিবারের সাপ্তাহিক বাজার ঝুড়ির হিসাব",
        "basket_help": "বাজারভিত্তিক তথ্য থাকলে বাজার র‍্যাঙ্ক করবে; না থাকলে সরকারি সামগ্রিক মূল্যসীমা দিয়ে আনুমানিক সাপ্তাহিক হিসাব দেখাবে।",
        "map": "🗺️ ঢাকার বাজার কাভারেজ ম্যাপ",
        "charts": "📊 মূল্য পার্থক্য ও ট্রেন্ড",
        "transparency": "🔎 তথ্যের স্বচ্ছতা",
        "consumer_note": "ভোক্তা নোট",
        "consumer_note_text": "মান, ব্র্যান্ড, প্যাকেট সাইজ, দোকান ও দিনের সময় অনুযায়ী দাম বদলাতে পারে। এটিকে যাচাইকৃত রেফারেন্স হিসেবে ব্যবহার করুন, দর-কষাকষির নিশ্চয়তা হিসেবে নয়।",
        "reload": "সরকারি তথ্য রিফ্রেশ করুন",
        "download": "বর্তমান তথ্য ডাউনলোড",
        "market_unavailable": "সরকারি উৎস বাজারভিত্তিক ঢাকার সারি না দেওয়া পর্যন্ত বাজার র‍্যাঙ্কিং পাওয়া যাবে না।",
        "verified": "যাচাইকৃত",
        "partial": "মূল্যতথ্য পাওয়া গেছে",
        "unavailable": "পাওয়া যায়নি",
        "unit_published": "প্রকাশিত রূপে",
        "source_monitor": "সরকারি উৎস মনিটর",
        "technical_details": "টেকনিক্যাল বিস্তারিত",
        "basket_summary": "🛒 আনুমানিক সাপ্তাহিক বাজার",
        "low": "কম",
        "mid": "গড়",
        "high": "বেশি",
        "spinner": "সরকারি পাবলিক উৎস থেকে তথ্য আনা হচ্ছে...",
        "no_data_error": "যাচাইকৃত সরকারি মূল্যতথ্য লোড করা যায়নি এবং কোনো ক্যাশও নেই। ইন্টারনেট সংযোগ বা সরকারি উৎসের প্রাপ্যতা পরীক্ষা করুন।",
        "key_prices_fail": "আজ গুরুত্বপূর্ণ সরকারি দামের সারাংশ তৈরি করা যায়নি।",
        "basket_fail": "মিল পাওয়া সরকারি পণ্য না থাকায় বাজার ঝুড়ির হিসাব করা যায়নি।",
        "basket_market_ok": "যাচাইকৃত বাজারভিত্তিক তথ্য থেকে বাজার র‍্যাঙ্কিং পাওয়া গেছে।",
        "basket_no_market": "বাজারভিত্তিক তথ্য না থাকায় বাজার র‍্যাঙ্কিং দেখানো হয়নি। এটি সরকারি সামগ্রিক মূল্যসীমা দিয়ে আনুমানিক সাপ্তাহিক হিসাব।",
        "official_ranges_none": "আজ DAM থেকে সামগ্রিক সরকারি মূল্যসীমা পাওয়া যায়নি।",
        "chart_price_title": "উচ্চমূল্যের পণ্য",
        "chart_spread_title": "সরকারি নিম্ন-উচ্চ মূল্যসীমার পার্থক্য",
        "axis_price": "দাম",
        "axis_spread": "পার্থক্য",
        "axis_commodity": "পণ্য",
        "map_note": "বেস ম্যাপের জায়গার নাম OpenStreetMap টাইল থেকে আসে। বাজারের মার্কার/টুলটিপের নাম অ্যাপ নিজে বাংলায় দেখায়।",
        "covered_markets": "কভার করা ঢাকার বাজার",
        "source_policy": "এই অ্যাপ শুধু যাচাইকৃত সরকারি/পাবলিক উৎসের তথ্য বা ব্যাকএন্ডে সংযুক্ত যাচাইকৃত সরকারি ফিড ব্যবহার করে। ডেমো দামকে বাস্তব দাম হিসেবে দেখায় না। সরকারি বাজারভিত্তিক তথ্য না পাওয়া গেলে অ্যাপ তা স্পষ্টভাবে জানায়।",
    },
}


COMMODITY_BN = {
    "Boro-Fine": "বোরো চাল (সরু)",
    "Boro-Coarse": "বোরো চাল (মোটা)",
    "Aman-Medium": "আমন চাল (মাঝারি)",
    "Ata (packet)": "আটা (প্যাকেট)",
    "Flour": "ময়দা",
    "Onion-local": "পেঁয়াজ (দেশি)",
    "Onion-Imported": "পেঁয়াজ (আমদানিকৃত)",
    "Potato": "আলু",
    "Soybean": "সয়াবিন তেল",
    "Egg Farm-Red": "ডিম (ফার্ম লাল)",
    "Egg Farm-White": "ডিম (ফার্ম সাদা)",
    "Farm-raised Hen": "ব্রয়লার/ফার্ম মুরগি",
    "Chicken": "মুরগি",
    "Beef": "গরুর মাংস",
    "Mutton": "খাসির মাংস",
    "Mung": "মুগ ডাল",
    "Gram-Whole": "ছোলা",
    "Lentil": "মসুর ডাল",
    "Sugar (Local)": "চিনি (দেশি)",
    "Iodized Salt (Packed)": "আয়োডিনযুক্ত লবণ (প্যাকেট)",
    "Ginger-local": "আদা (দেশি)",
    "Ginger-Imported": "আদা (আমদানিকৃত)",
    "Garlic-local": "রসুন (দেশি)",
    "Garlic-Imported": "রসুন (আমদানিকৃত)",
    "Green Chili": "কাঁচা মরিচ",
    "Green Chilli": "কাঁচা মরিচ",
}

ITEM_BN = {
    "Rice": "চাল",
    "Flour/Ata": "আটা",
    "Lentil/Dal": "ডাল",
    "Onion": "পেঁয়াজ",
    "Potato": "আলু",
    "Soybean oil": "সয়াবিন তেল",
    "Egg": "ডিম",
    "Chicken/Hen": "মুরগি",
    "Sugar": "চিনি",
    "Salt": "লবণ",
    "TOTAL": "মোট",
}

MARKET_BN = {
    "Karwan Bazar": "কারওয়ান বাজার",
    "Shyambazar": "শ্যামবাজার",
    "Jatrabari Bazar": "যাত্রাবাড়ী বাজার",
    "Mohammadpur Krishi Market": "মোহাম্মদপুর কৃষি মার্কেট",
    "Mirpur-1 Kitchen Market": "মিরপুর-১ কাঁচাবাজার",
    "Uttara Bazar": "উত্তরা বাজার",
    "New Market": "নিউ মার্কেট",
    "Rampura Bazar": "রামপুরা বাজার",
    "Malibagh Bazar": "মালিবাগ বাজার",
    "Khilgaon Bazar": "খিলগাঁও বাজার",
}

AREA_BN = {
    "Tejgaon": "তেজগাঁও",
    "Old Dhaka": "পুরান ঢাকা",
    "Jatrabari": "যাত্রাবাড়ী",
    "Mohammadpur": "মোহাম্মদপুর",
    "Mirpur": "মিরপুর",
    "Uttara": "উত্তরা",
    "New Market": "নিউ মার্কেট",
    "Rampura": "রামপুরা",
    "Malibagh": "মালিবাগ",
    "Khilgaon": "খিলগাঁও",
}

COLUMN_BN = {
    "Commodity": "পণ্য",
    "Official price range": "সরকারি মূল্যসীমা",
    "Midpoint": "মধ্যমান",
    "Unit": "একক",
    "Source": "উৎস",
    "Low": "সর্বনিম্ন",
    "High": "সর্বোচ্চ",
    "Change %": "পরিবর্তন %",
    "Item": "পণ্য",
    "Matched official item": "মিল পাওয়া সরকারি পণ্য",
    "Quantity": "পরিমাণ",
    "Low estimate": "কম হিসাব",
    "Mid estimate": "গড় হিসাব",
    "High estimate": "বেশি হিসাব",
    "Cheapest market": "সর্বনিম্ন দামের বাজার",
    "Area": "এলাকা",
    "Lowest price": "সর্বনিম্ন দাম",
    "Saving vs highest": "সর্বোচ্চ দামের তুলনায় সাশ্রয়",
    "Market": "বাজার",
    "Basket estimate": "বাজার ঝুড়ির আনুমানিক খরচ",
    "Items matched": "মিল পাওয়া পণ্য",
    "Details": "বিস্তারিত",
}

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = {
    "01": "জানুয়ারি", "02": "ফেব্রুয়ারি", "03": "মার্চ", "04": "এপ্রিল",
    "05": "মে", "06": "জুন", "07": "জুলাই", "08": "আগস্ট",
    "09": "সেপ্টেম্বর", "10": "অক্টোবর", "11": "নভেম্বর", "12": "ডিসেম্বর",
}

def is_bn() -> bool:
    return st.session_state.get("lang", "English") == "বাংলা"


def bn_digits(text: object) -> str:
    return str(text).translate(BN_DIGITS) if is_bn() else str(text)


def display_commodity(name: object) -> str:
    txt = clean_text(name)
    return COMMODITY_BN.get(txt, txt) if is_bn() else txt


def display_item(name: object) -> str:
    txt = clean_text(name)
    return ITEM_BN.get(txt, txt) if is_bn() else txt


def display_market(name: object) -> str:
    txt = clean_text(name)
    return MARKET_BN.get(txt, txt) if is_bn() else txt


def display_area(name: object) -> str:
    txt = clean_text(name)
    return AREA_BN.get(txt, txt) if is_bn() else txt


def localize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not is_bn() or df.empty:
        return df
    return df.rename(columns={c: COLUMN_BN.get(c, c) for c in df.columns})


def display_date(value: object) -> str:
    raw = clean_text(value)
    if not is_bn():
        return raw
    try:
        dt = datetime.fromisoformat(raw[:10])
        return f"{str(dt.day).translate(BN_DIGITS)} {BN_MONTHS.get(f'{dt.month:02d}', f'{dt.month:02d}')} {str(dt.year).translate(BN_DIGITS)}"
    except Exception:
        return raw.translate(BN_DIGITS)


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
    """Fetch a public official page.

    Some Bangladesh government pages have certificate-chain issues in hosted Python
    environments. For public read-only pages only, the function retries once with
    certificate verification disabled and returns a friendly status message instead
    of exposing raw stack traces to consumers.
    """
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, params=params, timeout=timeout)
        res.raise_for_status()
        if not res.encoding or res.encoding.lower() == "iso-8859-1":
            res.encoding = res.apparent_encoding or "utf-8"
        return res.text, None
    except requests.exceptions.SSLError:
        try:
            res = requests.get(url, headers=REQUEST_HEADERS, params=params, timeout=timeout, verify=False)
            res.raise_for_status()
            if not res.encoding or res.encoding.lower() == "iso-8859-1":
                res.encoding = res.apparent_encoding or "utf-8"
            return res.text, "Loaded with certificate fallback"
        except Exception:
            return None, "Source temporarily unavailable to the app"
    except requests.exceptions.Timeout:
        return None, "Source timed out"
    except requests.exceptions.ConnectionError:
        return None, "Source connection failed"
    except requests.exceptions.HTTPError as exc:
        return None, f"Source returned HTTP {getattr(exc.response, 'status_code', 'error')}"
    except Exception:
        return None, "Source temporarily unavailable to the app"


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
    return tr("unit_published") if "lang" in st.session_state else "As published"


def fmt_num(value: object) -> str:
    try:
        x = float(value)
    except Exception:
        return "—"
    if np.isnan(x):
        return "—"
    if abs(x - round(x)) < 0.001:
        out = f"{int(round(x))}"
    else:
        out = f"{x:.1f}".rstrip("0").rstrip(".")
    return bn_digits(out)


def fmt_tk(value: object) -> str:
    n = fmt_num(value)
    return "—" if n == "—" else f"৳ {n}"


def fmt_range(low: object, high: object, mid: object | None = None) -> str:
    low_s, high_s = fmt_num(low), fmt_num(high)
    if low_s != "—" and high_s != "—":
        if low_s == high_s:
            return f"৳ {low_s}"
        return f"৳ {low_s}–{high_s}"
    if mid is not None:
        return fmt_tk(mid)
    return "—"


def source_short(source: str) -> str:
    s = str(source)
    if "Agricultural" in s or "DAM" in s:
        return "DAM"
    if "TCB" in s or "Trading" in s:
        return "TCB"
    if "official" in s.lower() or "government" in s.lower():
        return "Official"
    return s[:40]


def match_commodity(series: pd.Series, pattern: str) -> pd.Series:
    try:
        return series.astype(str).str.contains(pattern, case=False, regex=True, na=False)
    except re.error:
        return series.astype(str).str.contains(re.escape(pattern), case=False, regex=True, na=False)


def parse_dam_recent_prices(html: str) -> pd.DataFrame:
    """Parse DAM public page aggregate price ranges.

    This returns official aggregate/range data, not market-wise prices.
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
        if len(commodity) > 45 or not commodity_is_essential(commodity):
            continue
        low_price = float(match.group(2))
        high_price = float(match.group(3))
        change_pct = float(match.group(4)) if match.group(4) is not None else 0.0
        key = (commodity.lower(), low_price, high_price)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "date": date.today().isoformat(),
            "commodity": commodity,
            "market": "Official aggregate range",
            "area": "Official public source",
            "unit": "As published",
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
    """Best-effort official table parser. Never fabricates market rows."""
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
        commodity_col = next((c for c in df.columns if "commodity" in c or "commodities" in c or "পণ্য" in c), None)
        market_col = next((c for c in df.columns if "market" in c or "বাজার" in c), None)
        unit_col = next((c for c in df.columns if "unit" in c or "একক" in c), None)
        price_col = next((c for c in df.columns if "retail" in c or "rate" in c or "price" in c or "দর" in c or "মূল্য" in c), None)
        if commodity_col is None or price_col is None:
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
            unit = clean_text(row.get(unit_col, "")) if unit_col else "As published"
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
                "unit": unit or "As published",
                "price": round(price, 2),
                "price_min": round(price_min, 2),
                "price_max": round(price_max, 2),
                "change_pct": 0.0,
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
    if not html:
        status.update({"ok": "false", "message": err or "Empty response"})
        return pd.DataFrame(), status
    df = parse_dam_recent_prices(html)
    if df.empty:
        status.update({"ok": "false", "message": "DAM page loaded but no official price ranges were parsed."})
        return df, status
    msg = f"Parsed {len(df)} official price ranges from DAM."
    if err:
        msg += f" ({err}.)"
    status.update({"ok": "true", "message": msg})
    return df, status


def fetch_dam_marketwise_best_effort() -> Tuple[pd.DataFrame, Dict[str, str]]:
    status = {"name": "DAM market-wise report", "url": DAM_MARKET_PRINT_URL, "ok": "false", "message": "Not attempted"}
    urls = [DAM_MARKET_PRINT_URL, DAM_SUBDISTRICT_PRINT_URL]
    frames = []
    for url in urls:
        html, _ = fetch_url(url, timeout=25)
        if not html:
            continue
        parsed = parse_tables_to_marketwise(html, url, "Department of Agricultural Marketing (DAM)")
        if not parsed.empty:
            frames.append(parsed)
    if not frames:
        status.update({
            "ok": "false",
            "message": "No usable official market-wise Dhaka rows were found from the public report endpoint today.",
        })
        return pd.DataFrame(), status
    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    dhaka_mask = df["market"].astype(str).str.contains("dhaka|karwan|kawran|shyam|jatra|mirpur|uttara|mohammad", case=False, regex=True, na=False)
    if dhaka_mask.any():
        df = df[dhaka_mask].copy()
    status.update({"ok": "true", "message": f"Parsed {len(df)} official market/report rows."})
    return df, status


def fetch_verified_remote_csv() -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Optional backend-only official/verified CSV feed."""
    url = safe_secret("OFFICIAL_MARKET_PRICE_CSV_URL", os.getenv("OFFICIAL_MARKET_PRICE_CSV_URL", ""))
    status = {"name": "Verified backend feed", "url": url or "not configured", "ok": "false", "message": "No backend feed configured."}
    if not url:
        return pd.DataFrame(), status
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        res.raise_for_status()
        df = pd.read_csv(io.StringIO(res.text))
    except Exception:
        status.update({"ok": "false", "message": "Configured verified feed could not be read today."})
        return pd.DataFrame(), status

    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    required = {"date", "commodity", "market", "price"}
    if not required.issubset(set(df.columns)):
        status.update({"ok": "false", "message": "Feed rejected: required columns missing."})
        return pd.DataFrame(), status
    if "source" not in df.columns:
        df["source"] = "Configured verified official feed"
    if "verified" not in df.columns:
        df["verified"] = df["source"].astype(str).str.contains("dam|tcb|official|government|govt", case=False, regex=True, na=False)
    else:
        df["verified"] = df["verified"].astype(str).str.lower().isin(["true", "1", "yes", "y", "verified"])
    df = df[df["verified"]].copy()
    if df.empty:
        status.update({"ok": "false", "message": "Feed rejected: no rows passed verification rule."})
        return pd.DataFrame(), status
    for col, default in {
        "area": "Dhaka", "unit": "As published", "price_min": np.nan, "price_max": np.nan,
        "change_pct": 0.0, "source_url": url, "data_level": "market", "fetched_at": now_iso()
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
    if not html:
        status.update({"ok": "false", "message": err or "TCB page could not be checked today."})
        return status
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = clean_text(a.get_text(" "))
        if any(ext in href.lower() for ext in [".pdf", ".xls", ".xlsx", ".csv", ".doc", ".docx"]) or "download" in label.lower() or "ডাউনলোড" in label:
            links.append(href)
    if links:
        msg = f"TCB page loaded. Found {len(links)} possible official report/download links."
    elif "দৈনিক" in text or "খুচরা" in text or "retail" in text.lower():
        msg = "TCB page loaded. Daily retail content is visible, but no machine-readable table was parsed."
    else:
        msg = "TCB page loaded, but no machine-readable price table was found."
    if err:
        msg += f" ({err}.)"
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
        data["price"] = pd.to_numeric(data["price"], errors="coerce")
        data["price_min"] = pd.to_numeric(data.get("price_min", data["price"]), errors="coerce").fillna(data["price"])
        data["price_max"] = pd.to_numeric(data.get("price_max", data["price"]), errors="coerce").fillna(data["price"])
        data = data.dropna(subset=["price"])
        save_cache(data, CACHE_DIR / "latest_official_prices.csv")
        append_history(data, CACHE_DIR / "history_official_prices.csv")
        return data, statuses

    cached = load_cache(CACHE_DIR / "latest_official_prices.csv")
    if not cached.empty:
        if "data_level" not in cached.columns:
            cached["data_level"] = "cached_official"
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
    max_prices = market_df.groupby("commodity")["price"].max().rename("max_price").reset_index()
    cheapest = cheapest.merge(max_prices, on="commodity", how="left")
    cheapest["saving_vs_highest"] = (cheapest["max_price"] - cheapest["price"]).round(2)
    return cheapest


def load_basket() -> pd.DataFrame:
    basket_path = DATA_DIR / "basket.csv"
    if basket_path.exists():
        basket = pd.read_csv(basket_path)
    else:
        basket = pd.DataFrame([
            {"item_label": "Rice", "commodity_pattern": "rice|boro|aman", "quantity": 5, "unit_note": "kg/as published"},
            {"item_label": "Flour/Ata", "commodity_pattern": "ata|flour", "quantity": 2, "unit_note": "kg/as published"},
            {"item_label": "Lentil/Dal", "commodity_pattern": "lentil|masur|mung|gram", "quantity": 1, "unit_note": "kg/as published"},
            {"item_label": "Onion", "commodity_pattern": "onion", "quantity": 2, "unit_note": "kg/as published"},
            {"item_label": "Potato", "commodity_pattern": "potato", "quantity": 2, "unit_note": "kg/as published"},
            {"item_label": "Soybean oil", "commodity_pattern": "soybean|oil", "quantity": 2, "unit_note": "litre/as published"},
            {"item_label": "Egg", "commodity_pattern": "egg", "quantity": 1, "unit_note": "dozen/as published"},
            {"item_label": "Chicken/Hen", "commodity_pattern": "chicken|hen", "quantity": 1, "unit_note": "kg/as published"},
            {"item_label": "Sugar", "commodity_pattern": "sugar", "quantity": 1, "unit_note": "kg/as published"},
            {"item_label": "Salt", "commodity_pattern": "salt", "quantity": 1, "unit_note": "kg/as published"},
        ])
    if "commodity_pattern" not in basket.columns and "commodity_keyword" in basket.columns:
        basket["commodity_pattern"] = basket["commodity_keyword"]
    if "item_label" not in basket.columns:
        basket["item_label"] = basket.get("commodity_keyword", basket.get("commodity_pattern", "Item"))
    return basket


def build_basket(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    basket = load_basket()
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
                pattern = str(b["commodity_pattern"])
                label = str(b["item_label"])
                qty = float(b["quantity"])
                matches = g[match_commodity(g["commodity"], pattern)]
                if matches.empty:
                    continue
                selected = matches.sort_values("price").iloc[0]
                cost = float(selected["price"]) * qty
                total += cost
                matched += 1
                details.append(f"{display_item(label)}: {bn_digits(f'{qty:g}')} × {fmt_tk(selected['price'])}")
            if matched:
                rows.append({"Market": market, "Basket estimate": fmt_tk(total), "Items matched": bn_digits(matched), "Details": "; ".join(details)})
        if rows:
            raw = pd.DataFrame(rows)
            raw["_sort"] = raw["Basket estimate"].str.replace("৳", "", regex=False).astype(float)
            return raw.sort_values("_sort").drop(columns="_sort"), "market"
    range_df = df[df.get("data_level").astype(str).str.contains("official_range|cached", regex=True, na=False)].copy()
    if range_df.empty:
        range_df = df.copy()
    total_low = total_mid = total_high = 0.0
    rows = []
    for _, b in basket.iterrows():
        pattern = str(b["commodity_pattern"])
        label = str(b["item_label"])
        qty = float(b["quantity"])
        matches = range_df[match_commodity(range_df["commodity"], pattern)]
        if matches.empty:
            continue
        selected = matches.sort_values("price").iloc[0]
        low = float(selected.get("price_min", selected["price"])) * qty
        mid = float(selected.get("price", selected["price"])) * qty
        high = float(selected.get("price_max", selected["price"])) * qty
        rows.append({
            "Item": display_item(label),
            "Matched official item": display_commodity(selected["commodity"]),
            "Quantity": bn_digits(f"{qty:g}"),
            "Unit": tr("unit_published") if str(selected.get("unit", "As published")).lower() == "as published" else str(selected.get("unit", "As published")),
            "Low estimate": fmt_tk(low),
            "Mid estimate": fmt_tk(mid),
            "High estimate": fmt_tk(high),
        })
        total_low += low; total_mid += mid; total_high += high
    if not rows:
        return pd.DataFrame(), "none"
    result = pd.DataFrame(rows)
    result.loc[len(result)] = {
        "Item": display_item("TOTAL"), "Matched official item": "", "Quantity": "", "Unit": "",
        "Low estimate": fmt_tk(total_low), "Mid estimate": fmt_tk(total_mid), "High estimate": fmt_tk(total_high),
    }
    return result, "range"


def status_badge(statuses: List[Dict[str, str]]) -> Tuple[str, str, str]:
    any_ok = any(s.get("ok") == "true" for s in statuses)
    market_ok = any(s.get("ok") == "true" and "market" in s.get("name", "").lower() for s in statuses)
    if market_ok:
        return "🟢", tr("verified"), tr("source_ok")
    if any_ok:
        return "🟢", tr("partial"), tr("source_partial")
    return "🔴", tr("unavailable"), tr("source_fail")


def display_metric_cards(df: pd.DataFrame, statuses: List[Dict[str, str]]) -> None:
    badge, short_status, long_status = status_badge(statuses)
    latest_time = df["fetched_at"].max() if not df.empty and "fetched_at" in df.columns else now_iso()
    data_date = df["date"].max() if not df.empty and "date" in df.columns else "—"
    covered = int(df["commodity"].nunique()) if not df.empty and "commodity" in df.columns else 0
    market_rows = int((df.get("data_level", pd.Series(dtype=str)) == "market").sum()) if not df.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("status"), f"{badge} {short_status}")
    c2.metric(tr("data_date"), display_date(data_date))
    c3.metric(tr("covered"), bn_digits(covered))
    c4.metric(tr("coverage"), tr("available") if market_rows else tr("not_available"))
    st.caption(f"{tr('last_updated')}: {bn_digits(latest_time)} · {long_status} · App version: {APP_VERSION}")


def build_key_price_table(official_range_df: pd.DataFrame) -> pd.DataFrame:
    if official_range_df.empty:
        return pd.DataFrame()
    rows = []
    used = set()
    for key in KEY_PRICE_ORDER:
        matches = official_range_df[official_range_df["commodity"].astype(str).str.contains(key, case=False, regex=False, na=False)]
        for _, r in matches.iterrows():
            commodity = str(r["commodity"])
            if commodity.lower() in used:
                continue
            used.add(commodity.lower())
            rows.append(r)
            break
    if len(rows) < 12:
        for _, r in official_range_df.sort_values("commodity").iterrows():
            commodity = str(r["commodity"])
            if commodity.lower() not in used:
                rows.append(r)
                used.add(commodity.lower())
            if len(rows) >= 14:
                break
    if not rows:
        return pd.DataFrame()
    key_df = pd.DataFrame(rows)
    return pd.DataFrame({
        "Commodity": [display_commodity(x) for x in key_df["commodity"].astype(str)],
        "Official price range": [fmt_range(a, b, c) for a, b, c in zip(key_df["price_min"], key_df["price_max"], key_df["price"])],
        "Midpoint": [fmt_tk(x) for x in key_df["price"]],
        "Unit": [tr("unit_published") if str(x).lower() == "as published" else str(x) for x in key_df.get("unit", "As published")],
        "Source": [source_short(x) for x in key_df.get("source", "Official")],
    })


def localized_status_name(name: object) -> str:
    raw = clean_text(name)
    if not is_bn():
        return raw
    mapping = {
        "Verified backend feed": "যাচাইকৃত ব্যাকএন্ড ফিড",
        "DAM market-wise report": "DAM বাজারভিত্তিক রিপোর্ট",
        "DAM recent prices": "DAM সাম্প্রতিক মূল্যসীমা",
        "TCB daily retail prices": "TCB দৈনিক খুচরা দাম",
        "Local cache": "লোকাল ক্যাশ",
    }
    return mapping.get(raw, raw)


def localized_status_message(status: Dict[str, str]) -> str:
    msg = clean_text(status.get("message", ""))
    name = clean_text(status.get("name", ""))
    if not is_bn():
        return msg
    if name == "Verified backend feed":
        if "No backend" in msg or "not configured" in msg.lower():
            return "অতিরিক্ত যাচাইকৃত ব্যাকএন্ড ফিড সংযুক্ত নয়।"
        if "Loaded" in msg:
            m = re.search(r"Loaded\s+(\d+)", msg)
            n = bn_digits(m.group(1)) if m else ""
            return f"ব্যাকএন্ড ফিড থেকে {n}টি যাচাইকৃত সারি পাওয়া গেছে।" if n else "ব্যাকএন্ড ফিড থেকে যাচাইকৃত তথ্য পাওয়া গেছে।"
        return "যাচাইকৃত ব্যাকএন্ড ফিড আজ পড়া যায়নি।"
    if name == "DAM market-wise report":
        if status.get("ok") == "true":
            m = re.search(r"Parsed\s+(\d+)", msg)
            n = bn_digits(m.group(1)) if m else ""
            return f"DAM বাজারভিত্তিক রিপোর্ট থেকে {n}টি সরকারি সারি পাওয়া গেছে।" if n else "DAM বাজারভিত্তিক রিপোর্ট থেকে সরকারি সারি পাওয়া গেছে।"
        return "আজ পাবলিক রিপোর্ট এন্ডপয়েন্ট থেকে ব্যবহারযোগ্য ঢাকার বাজারভিত্তিক সরকারি সারি পাওয়া যায়নি।"
    if name == "DAM recent prices":
        m = re.search(r"Parsed\s+(\d+)", msg)
        n = bn_digits(m.group(1)) if m else ""
        return f"DAM থেকে {n}টি সরকারি মূল্যসীমা পাওয়া গেছে।" if n else "DAM থেকে সরকারি মূল্যসীমা পাওয়া গেছে।"
    if name == "TCB daily retail prices":
        if status.get("ok") == "true":
            m = re.search(r"Found\s+(\d+)", msg)
            n = bn_digits(m.group(1)) if m else ""
            return f"TCB পেজ লোড হয়েছে; {n}টি সম্ভাব্য অফিসিয়াল রিপোর্ট/ডাউনলোড লিংক পাওয়া গেছে।" if n else "TCB পেজ লোড হয়েছে; দৈনিক খুচরা দামের কনটেন্ট দেখা যাচ্ছে।"
        return "TCB পেজ আজ অ্যাপ থেকে যাচাই করা যায়নি।"
    if name == "Local cache":
        return "লাইভ সরকারি উৎস ব্যর্থ হওয়ায় সর্বশেষ যাচাইকৃত লোকাল ক্যাশ ব্যবহার করা হয়েছে।"
    return msg.translate(BN_DIGITS)


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="🛒", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e9edf3; padding: 14px; border-radius: 18px; box-shadow: 0 1px 6px rgba(0,0,0,.04);}
        .hero {padding: 1.2rem 1.4rem; border-radius: 22px; background: linear-gradient(135deg, #f8fafc 0%, #eef7ff 55%, #fff8ec 100%); border: 1px solid #e8eef7; margin-bottom: 1rem;}
        .hero h1 {margin-bottom: .25rem; font-size: 2.4rem;}
        .soft-card {padding: 1rem; border: 1px solid #e9edf3; border-radius: 16px; background: #fff;}
        .tiny {font-size: 0.85rem; color: #64748b;}
        .goodbox {padding: .95rem 1rem; border-radius: 14px; background: #eef8f2; border: 1px solid #caead5; color: #14532d;}
        .warnbox {padding: .95rem 1rem; border-radius: 14px; background: #fff8db; border: 1px solid #f6e7a7; color: #7a4b00;}
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

    with st.spinner(tr("spinner")):
        df, statuses = load_official_data(refresh_key)

    display_metric_cards(df, statuses)

    if df.empty:
        st.error(tr("no_data_error"))
        with st.expander(tr("transparency"), expanded=True):
            for s in statuses:
                st.write(f"**{localized_status_name(s['name'])}** — {localized_status_message(s)}")
                st.caption(s.get("url", ""))
        return

    st.download_button(
        f"⬇️ {tr('download')}",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"official_commodity_prices_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

    market_df = df[df.get("data_level") == "market"].copy() if "data_level" in df.columns else pd.DataFrame()
    official_range_df = df[df.get("data_level").astype(str).str.contains("official_range|cached", regex=True, na=False)].copy() if "data_level" in df.columns else df.copy()

    st.subheader(tr("key_prices"))
    st.caption(tr("key_prices_help"))
    key_table = build_key_price_table(official_range_df)
    if key_table.empty:
        st.info(tr("key_prices_fail"))
    else:
        st.dataframe(localize_columns(key_table), use_container_width=True, hide_index=True)

    st.subheader(tr("cheapest_market"))
    st.caption(tr("cheapest_market_help"))
    cheapest = build_cheapest_market(df)
    if cheapest.empty:
        st.markdown(f"<div class='warnbox'>{tr('no_marketwise')}</div>", unsafe_allow_html=True)
    else:
        show = cheapest[["commodity", "market", "area", "unit", "price", "saving_vs_highest", "source"]].copy()
        show = pd.DataFrame({
            "Commodity": [display_commodity(x) for x in show["commodity"]],
            "Cheapest market": [display_market(x) for x in show["market"]],
            "Area": [display_area(x) for x in show["area"]],
            "Unit": show["unit"],
            "Lowest price": [fmt_tk(x) for x in show["price"]],
            "Saving vs highest": [fmt_tk(x) for x in show["saving_vs_highest"]],
            "Source": [source_short(x) for x in show["source"]],
        })
        st.dataframe(localize_columns(show), use_container_width=True, hide_index=True)

    st.subheader(tr("basket"))
    st.caption(tr("basket_help"))
    basket_df, basket_mode = build_basket(df)
    if basket_df.empty:
        st.info(tr("basket_fail"))
    elif basket_mode == "market":
        st.success(tr("basket_market_ok"))
        st.dataframe(localize_columns(basket_df), use_container_width=True, hide_index=True)
    else:
        st.info(tr("basket_no_market"))
        total_row = basket_df[basket_df["Item"].astype(str).isin([display_item("TOTAL"), "TOTAL"])]
        if not total_row.empty:
            st.markdown(f"### {tr('basket_summary')}")
            b1, b2, b3 = st.columns(3)
            b1.metric(tr("low"), str(total_row.iloc[0].get("Low estimate", "—")))
            b2.metric(tr("mid"), str(total_row.iloc[0].get("Mid estimate", "—")))
            b3.metric(tr("high"), str(total_row.iloc[0].get("High estimate", "—")))
        st.dataframe(localize_columns(basket_df), use_container_width=True, hide_index=True)

    st.subheader(tr("official_ranges"))
    st.caption(tr("official_ranges_help"))
    if official_range_df.empty:
        st.info(tr("official_ranges_none"))
    else:
        table = official_range_df.copy()
        table = pd.DataFrame({
            "Commodity": [display_commodity(x) for x in table["commodity"].astype(str)],
            "Low": [fmt_tk(x) for x in table["price_min"]],
            "High": [fmt_tk(x) for x in table["price_max"]],
            "Midpoint": [fmt_tk(x) for x in table["price"]],
            "Unit": [tr("unit_published") if str(x).lower() == "as published" else str(x) for x in table.get("unit", "As published")],
            "Change %": [fmt_num(x) for x in table.get("change_pct", 0)],
            "Source": [source_short(x) for x in table.get("source", "Official")],
        }).sort_values("Commodity")
        st.dataframe(localize_columns(table), use_container_width=True, hide_index=True)

    st.subheader(tr("charts"))
    chart_df = official_range_df.copy() if not official_range_df.empty else df.copy()
    if not chart_df.empty:
        chart_df["spread"] = pd.to_numeric(chart_df.get("price_max", chart_df["price"]), errors="coerce") - pd.to_numeric(chart_df.get("price_min", chart_df["price"]), errors="coerce")
        chart_df = chart_df.dropna(subset=["price"])
        chart_df["commodity_display"] = [display_commodity(x) for x in chart_df["commodity"]]
        c1, c2 = st.columns(2)
        with c1:
            top = chart_df.sort_values("price", ascending=False).head(15)
            fig = px.bar(top, x="price", y="commodity_display", orientation="h", title=tr("chart_price_title"), labels={"price": tr("axis_price"), "commodity_display": tr("axis_commodity")})
            fig.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            sp = chart_df.sort_values("spread", ascending=False).head(15)
            fig2 = px.bar(sp, x="spread", y="commodity_display", orientation="h", title=tr("chart_spread_title"), labels={"spread": tr("axis_spread"), "commodity_display": tr("axis_commodity")})
            fig2.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader(tr("map"))
    map_df = DHAKA_MARKETS.copy()
    if not market_df.empty:
        avg = market_df.groupby("market", as_index=False).agg(avg_price=("price", "mean"), rows=("price", "size"))
        map_df = map_df.merge(avg, on="market", how="left")
    map_df["market_label"] = [display_market(x) for x in map_df["market"]]
    map_df["area_label"] = [display_area(x) for x in map_df["area"]]
    view_state = pdk.ViewState(latitude=23.7600, longitude=90.4050, zoom=10.7, pitch=0)
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_radius=120,
        get_fill_color=[205, 88, 73, 180],
        pickable=True,
    )
    labels = pdk.Layer(
        "TextLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_text="market_label",
        get_size=14,
        get_color=[20, 36, 64, 230],
        get_text_anchor="middle",
        get_alignment_baseline="bottom",
        pickable=True,
    )
    st.pydeck_chart(
        pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=view_state,
            layers=[scatter, labels],
            tooltip={"html": "<b>{market_label}</b><br/>{area_label}", "style": {"backgroundColor": "white", "color": "#111827"}},
        ),
        use_container_width=True,
    )
    st.caption(tr("map_note"))
    with st.expander(tr("covered_markets"), expanded=False):
        market_list = pd.DataFrame({
            "Market": [display_market(x) for x in map_df["market"]],
            "Area": [display_area(x) for x in map_df["area"]],
        })
        st.dataframe(localize_columns(market_list), use_container_width=True, hide_index=True)
    if market_df.empty:
        st.caption(tr("market_unavailable"))

    st.subheader(tr("transparency"))
    st.info(f"{tr('consumer_note')}: {tr('consumer_note_text')}")
    with st.expander(tr("source_monitor"), expanded=False):
        for s in statuses:
            icon = "🟢" if s.get("ok") == "true" else "🟡"
            st.markdown(f"{icon} **{localized_status_name(s.get('name','Source'))}** — {localized_status_message(s)}")
            if s.get("url"):
                st.caption(s["url"])
        st.markdown(tr("source_policy"))


if __name__ == "__main__":
    main()
