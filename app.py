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
APP_VERSION = "3.1.0-unit-clear-consumer-final"
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
        "source_partial": "Official price data loaded; market ranking requires market-wise rows.",
        "source_fail": "Official data unavailable right now",
        "last_updated": "Last updated",
        "data_date": "Data date",
        "status": "Status",
        "coverage": "Dhaka market data",
        "covered": "Commodities covered",
        "available": "Available",
        "not_available": "Unavailable",
        "official_ranges": "📌 Latest official price ranges",
        "official_ranges_help": "Official aggregate/range prices parsed from public DAM data. Every row shows the price unit, such as per kg, per litre, or per piece. Egg prices are normalized from hali / 4 eggs to single egg price where applicable.",
        "key_prices": "💳 Today's key official prices",
        "key_prices_help": "Consumer-friendly view of essential items from the latest verified official data. Check the price unit column beside every price.",
        "cheapest_market": "🏷️ Cheapest Dhaka market by commodity",
        "cheapest_market_help": "This appears only when official/verified market-wise Dhaka rows are available.",
        "no_marketwise": "Official market-wise Dhaka rows are not available to this deployment today. Showing official aggregate/range prices instead of fake cheapest-market results.",
        "basket": "🧺 Household basket estimate",
        "basket_help": "If market-wise rows are available, this ranks markets. Otherwise it estimates a weekly basket using official aggregate ranges.",
        "map": "🗺️ Dhaka market coverage map",
        "charts": "📊 Price spread and trend view",
        "transparency": "🔎 Data transparency",
        "consumer_note": "Consumer note",
        "consumer_note_text": "Prices can vary by quality, brand, package size, retail shop, and time of day. Each row shows the price unit: per kg, per litre, per piece, or official unit. Egg prices are normalized from hali / 4 eggs to single egg price where applicable. Use this as a verified reference, not a bargaining guarantee.",
        "reload": "Refresh official data",
        "download": "Download current data",
        "market_unavailable": "Market-wise ranking is unavailable until the official source returns market-level Dhaka rows.",
        "verified": "Verified",
        "partial": "Verified",
        "unavailable": "Unavailable",
        "unit_published": "Official unit",
        "unit_kg": "per kg",
        "unit_litre": "per litre",
        "unit_piece": "per piece",
        "unit_packet": "per packet",
        "unit_hali": "per piece",
        "unit_single_egg": "per piece",
        "qty_kg": "kg",
        "qty_litre": "litre",
        "qty_piece": "piece",
        "qty_packet": "packet",
        "price_unit": "Price unit",
        "unit_published_note": "Unit inferred from commodity name when the official page does not expose a separate unit column.",
        "egg_unit_note": "Egg prices are converted from official hali / 4 eggs values into a single-egg estimate. So 30 eggs means 30 individual eggs, not 30 hali.",
        "source_monitor": "Official source monitor",
        "smart_basket": "🛒 Smart shopping basket",
        "smart_basket_help": "Choose your own quantities. The app calculates low, average, and high cost using the latest verified official prices.",
        "basket_item": "Item",
        "qty": "Quantity",
        "calc_cost": "Calculate basket cost",
        "custom_basket_total": "Custom basket total",
        "alerts": "🔔 Price alerts",
        "alerts_help": "Automatic alerts based on official change percentages and price spread. These are signals, not forecasts.",
        "no_alerts": "No major official price alert detected today.",
        "alert_increase": "Price increased",
        "alert_decrease": "Price decreased",
        "alert_spread": "Large low-high market spread",
        "history": "📈 Historical trends",
        "history_help": "Trend view from saved daily snapshots. It becomes richer as the app runs every day.",
        "history_empty": "No historical snapshots yet. After daily refreshes, this section will show trend lines.",
        "market_comparison": "📍 Market comparison",
        "market_comparison_help": "Activates only when verified Dhaka market-wise rows are available from the official/backend feed.",
        "market_comparison_unavailable": "Verified Dhaka market-wise rows are unavailable today, so the app does not show market comparison or fake cheapest-market claims.",
        "perfect_features": "What this app adds beyond official portals",
        "perfect_features_text": "Smart custom basket, historical trend storage, alert cards, localized Bangla/English UI, consumer-friendly charts, map labels, source transparency, and verified-only market comparison when official market-level rows exist.",
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
        "positioning": "How this app differs",
        "positioning_text": "Bangladesh already has official TCB and DAM price-report portals. This app does not replace them; it repackages verified public data into a mobile-friendly consumer view with Bangla/English UI, basket estimates, charts, map labels, and clear source transparency.",
        "official_not_marketwise": "Official prices are authentic as reference price ranges. Cheapest-market claims are shown only when verified market-wise Dhaka rows are available.",
    },
    "বাংলা": {
        "title": "🛒 বাংলাদেশ কমোডিটি ইন্টেলিজেন্স",
        "subtitle": "ভোক্তাদের জন্য সর্বশেষ যাচাইকৃত নিত্যপ্রয়োজনীয় পণ্যের বাজারদর। শুধু সরকারি তথ্য; ডেমো দাম নয়, ভুয়া র‍্যাঙ্কিং নয়।",
        "language": "ভাষা",
        "source_ok": "সরকারি তথ্য লোড হয়েছে",
        "source_partial": "সরকারি দাম লোড হয়েছে; বাজার র‍্যাঙ্কিংয়ের জন্য বাজারভিত্তিক তথ্য দরকার।",
        "source_fail": "এই মুহূর্তে সরকারি তথ্য পাওয়া যাচ্ছে না",
        "last_updated": "সর্বশেষ হালনাগাদ",
        "data_date": "তথ্যের তারিখ",
        "status": "অবস্থা",
        "coverage": "ঢাকার বাজারভিত্তিক তথ্য",
        "covered": "পণ্যের সংখ্যা",
        "available": "উপলব্ধ",
        "not_available": "অনুপলব্ধ",
        "official_ranges": "📌 সর্বশেষ সরকারি মূল্যসীমা",
        "official_ranges_help": "DAM-এর পাবলিক সরকারি তথ্য থেকে পাওয়া সামগ্রিক/মূল্যসীমা। প্রতিটি সারিতে দামের একক দেখানো হয়—প্রতি কেজি, প্রতি লিটার, প্রতি পিস বা সরকারি একক। ডিমের দাম প্রযোজ্য ক্ষেত্রে হালি / ৪টি থেকে ১টি ডিমের আনুমানিক দামে রূপান্তর করা হয়েছে।",
        "key_prices": "💳 আজকের গুরুত্বপূর্ণ সরকারি দাম",
        "key_prices_help": "সর্বশেষ যাচাইকৃত সরকারি তথ্য থেকে ভোক্তাবান্ধব নিত্যপণ্যের তালিকা। প্রতিটি দামের পাশে দামের একক দেখুন।",
        "cheapest_market": "🏷️ পণ্যভিত্তিক ঢাকার সবচেয়ে কমদামের বাজার",
        "cheapest_market_help": "শুধু যাচাইকৃত/সরকারি বাজারভিত্তিক ঢাকার তথ্য পাওয়া গেলে এটি দেখাবে।",
        "no_marketwise": "আজ এই ডেপ্লয়মেন্টে সরকারি বাজারভিত্তিক ঢাকার সারি পাওয়া যায়নি। তাই ভুয়া কমদামের বাজার না দেখিয়ে সরকারি সামগ্রিক মূল্যসীমা দেখানো হচ্ছে।",
        "basket": "🧺 পরিবারের সাপ্তাহিক বাজার ঝুড়ির হিসাব",
        "basket_help": "বাজারভিত্তিক তথ্য থাকলে বাজার র‍্যাঙ্ক করবে; না থাকলে সরকারি সামগ্রিক মূল্যসীমা দিয়ে আনুমানিক সাপ্তাহিক হিসাব দেখাবে।",
        "map": "🗺️ ঢাকার বাজার কাভারেজ ম্যাপ",
        "charts": "📊 মূল্য পার্থক্য ও ট্রেন্ড",
        "transparency": "🔎 তথ্যের স্বচ্ছতা",
        "consumer_note": "ভোক্তা নোট",
        "consumer_note_text": "মান, ব্র্যান্ড, প্যাকেট সাইজ, দোকান ও দিনের সময় অনুযায়ী দাম বদলাতে পারে। প্রতিটি সারিতে দামের একক দেখানো হয়—প্রতি কেজি, প্রতি লিটার, প্রতি পিস বা সরকারি একক। ডিমের দাম প্রযোজ্য ক্ষেত্রে হালি / ৪টি থেকে ১টি ডিমের আনুমানিক দামে রূপান্তর করা হয়েছে। এটিকে যাচাইকৃত রেফারেন্স হিসেবে ব্যবহার করুন, দর-কষাকষির নিশ্চয়তা হিসেবে নয়।",
        "reload": "সরকারি তথ্য রিফ্রেশ করুন",
        "download": "বর্তমান তথ্য ডাউনলোড",
        "market_unavailable": "সরকারি উৎস বাজারভিত্তিক ঢাকার সারি না দেওয়া পর্যন্ত বাজার র‍্যাঙ্কিং পাওয়া যাবে না।",
        "verified": "যাচাইকৃত",
        "partial": "যাচাইকৃত",
        "unavailable": "পাওয়া যায়নি",
        "unit_published": "সরকারি একক",
        "unit_kg": "প্রতি কেজি",
        "unit_litre": "প্রতি লিটার",
        "unit_piece": "প্রতি পিস",
        "unit_packet": "প্রতি প্যাকেট",
        "unit_hali": "প্রতি পিস",
        "unit_single_egg": "প্রতি পিস",
        "qty_kg": "কেজি",
        "qty_litre": "লিটার",
        "qty_piece": "টি",
        "qty_packet": "প্যাকেট",
        "price_unit": "দামের একক",
        "unit_published_note": "সরকারি পেজ আলাদা একক না দিলে পণ্যের নাম থেকে একক অনুমান করে দেখানো হয়েছে।",
        "egg_unit_note": "সরকারি উৎসে ডিমের দাম হালি / ৪টি হলে সেটি ১টি ডিমের আনুমানিক দামে রূপান্তর করা হয়েছে। তাই ৩০ ডিম মানে ৩০টি ডিম, ৩০ হালি নয়।",
        "source_monitor": "সরকারি উৎস মনিটর",
        "smart_basket": "🛒 স্মার্ট বাজার ঝুড়ি",
        "smart_basket_help": "নিজের প্রয়োজনমতো পরিমাণ দিন। সর্বশেষ যাচাইকৃত সরকারি দামের ভিত্তিতে কম, গড় ও বেশি খরচ হিসাব করা হবে।",
        "basket_item": "পণ্য",
        "qty": "পরিমাণ",
        "calc_cost": "বাজার খরচ হিসাব করুন",
        "custom_basket_total": "নিজস্ব বাজার ঝুড়ির মোট খরচ",
        "alerts": "🔔 মূল্য সতর্কতা",
        "alerts_help": "সরকারি পরিবর্তন হার ও মূল্যসীমার পার্থক্যের ভিত্তিতে স্বয়ংক্রিয় সতর্কতা। এগুলো সংকেত, পূর্বাভাস নয়।",
        "no_alerts": "আজ বড় কোনো সরকারি মূল্য সতর্কতা পাওয়া যায়নি।",
        "alert_increase": "দাম বেড়েছে",
        "alert_decrease": "দাম কমেছে",
        "alert_spread": "নিম্ন-উচ্চ দামের বড় পার্থক্য",
        "history": "📈 ঐতিহাসিক ট্রেন্ড",
        "history_help": "সংরক্ষিত দৈনিক স্ন্যাপশট থেকে ট্রেন্ড ভিউ। অ্যাপ প্রতিদিন চললে এই অংশ আরও সমৃদ্ধ হবে।",
        "history_empty": "এখনও ঐতিহাসিক স্ন্যাপশট নেই। দৈনিক রিফ্রেশের পর এখানে ট্রেন্ড লাইন দেখা যাবে।",
        "market_comparison": "📍 বাজার তুলনা",
        "market_comparison_help": "শুধু যাচাইকৃত ঢাকার বাজারভিত্তিক সারি সরকারি/ব্যাকএন্ড ফিডে পাওয়া গেলে সক্রিয় হবে।",
        "market_comparison_unavailable": "আজ যাচাইকৃত ঢাকার বাজারভিত্তিক সারি পাওয়া যায়নি, তাই অ্যাপ বাজার তুলনা বা ভুয়া সর্বনিম্ন বাজার দেখাচ্ছে না।",
        "perfect_features": "সরকারি পোর্টালের বাইরে এই অ্যাপ যা যোগ করে",
        "perfect_features_text": "স্মার্ট কাস্টম বাজার ঝুড়ি, ঐতিহাসিক ট্রেন্ড সংরক্ষণ, সতর্কতা কার্ড, বাংলা/ইংরেজি UI, ভোক্তাবান্ধব চার্ট, ম্যাপ লেবেল, উৎস স্বচ্ছতা, এবং সরকারি বাজারভিত্তিক সারি থাকলে যাচাইকৃত বাজার তুলনা।",
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
        "positioning": "এই অ্যাপের পার্থক্য",
        "positioning_text": "বাংলাদেশে TCB ও DAM-এর সরকারি মূল্যতথ্য পোর্টাল আগে থেকেই আছে। এই অ্যাপ সেগুলোর বিকল্প নয়; যাচাইকৃত পাবলিক তথ্যকে ভোক্তাবান্ধব মোবাইল ভিউ, বাংলা/ইংরেজি UI, বাজার ঝুড়ির হিসাব, চার্ট, ম্যাপ লেবেল ও উৎস-স্বচ্ছতার মাধ্যমে সহজ করে দেখায়।",
        "official_not_marketwise": "সরকারি দামগুলো রেফারেন্স মূল্যসীমা হিসেবে প্রামাণ্য। যাচাইকৃত ঢাকার বাজারভিত্তিক সারি পাওয়া গেলেই শুধু সবচেয়ে কমদামের বাজার দেখানো হবে।",
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
    "Unit": "দামের একক",
    "Price unit": "দামের একক",
    "Quantity used": "ব্যবহৃত পরিমাণ",
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


def is_egg_name(value: object) -> bool:
    return "egg" in clean_text(value).lower() or "ডিম" in clean_text(value)


def unit_key_for(commodity: object = "", item: object = "", unit: object = "") -> str:
    """Return a consumer-facing normalized unit key.

    DAM public recent-price snippets do not always expose a separate machine-readable
    unit column. For consumer clarity, we infer the common Bangladesh retail unit
    from the commodity name while preserving explicit official units when present.
    """
    text = f"{clean_text(commodity)} {clean_text(item)} {clean_text(unit)}".lower()
    raw_unit = clean_text(unit).lower()

    if is_egg_name(commodity) or is_egg_name(item) or "egg" in text or "ডিম" in text:
        return "piece"
    if "soybean" in text or "oil" in text or "তেল" in text:
        return "litre"
    if "packet" in text or "packed" in text or "প্যাকেট" in text:
        # Packeted salt/ata is usually sold by packet, often a kg packet.
        return "packet" if "salt" in text or "লবণ" in text else "kg"
    kg_words = [
        "rice", "boro", "aman", "ata", "flour", "lentil", "masur", "mung",
        "gram", "onion", "potato", "garlic", "ginger", "chili", "chilli",
        "hen", "chicken", "beef", "mutton", "fish", "sugar", "salt",
        "চাল", "আটা", "ডাল", "পেঁয়াজ", "পেঁয়াজ", "আলু", "রসুন", "আদা",
        "মরিচ", "মুরগি", "মাংস", "মাছ", "চিনি", "লবণ", "ছোলা",
    ]
    if any(w in text for w in kg_words):
        return "kg"
    if any(w in raw_unit for w in ["kg", "kilogram", "কেজি"]):
        return "kg"
    if any(w in raw_unit for w in ["litre", "liter", "ltr", "লিটার"]):
        return "litre"
    if any(w in raw_unit for w in ["piece", "pcs", "pc", "টি", "পিস"]):
        return "piece"
    if any(w in raw_unit for w in ["packet", "pack", "প্যাকেট"]):
        return "packet"
    return "published"


def display_unit(unit: object, commodity: object = "", item: object = "") -> str:
    key = unit_key_for(commodity, item, unit)
    if key == "kg":
        return tr("unit_kg")
    if key == "litre":
        return tr("unit_litre")
    if key == "piece":
        return tr("unit_piece")
    if key == "packet":
        return tr("unit_packet")
    raw = clean_text(unit)
    if raw.lower() in {"as published", "", "nan", "none"}:
        return tr("unit_published")
    return bn_digits(raw) if is_bn() else raw


def display_quantity(qty: object, commodity: object = "", item: object = "", unit: object = "") -> str:
    key = unit_key_for(commodity, item, unit)
    q = fmt_num(qty)
    if key == "kg":
        return f"{q} {tr('qty_kg')}"
    if key == "litre":
        return f"{q} {tr('qty_litre')}"
    if key == "piece":
        return f"{q} {tr('qty_piece')}"
    if key == "packet":
        return f"{q} {tr('qty_packet')}"
    return q


def quantity_unit_name(commodity: object = "", item: object = "", unit: object = "") -> str:
    key = unit_key_for(commodity, item, unit)
    if key == "kg":
        return tr("qty_kg")
    if key == "litre":
        return tr("qty_litre")
    if key == "piece":
        return tr("qty_piece")
    if key == "packet":
        return tr("qty_packet")
    return tr("unit_published")


def input_label_with_unit(item: object, commodity: object = "", unit: object = "") -> str:
    return f"{display_item(item)} ({quantity_unit_name(commodity, item, unit)})"



def normalize_egg_prices_to_single(df: pd.DataFrame) -> pd.DataFrame:
    """Convert official egg prices from hali / 4 eggs into single-egg prices.

    DAM-style Bangladesh egg rows are commonly published as a hali (4 eggs).
    For consumer clarity, this app displays and calculates eggs as a single unit.
    To avoid accidental repeated conversion, rows already marked as single egg are skipped.
    """
    if df.empty or "commodity" not in df.columns:
        return df
    out = df.copy()
    unit_text = out.get("unit", pd.Series([""] * len(out))).astype(str).str.lower()
    egg_mask = out["commodity"].astype(str).str.contains("egg|ডিম", case=False, regex=True, na=False)
    already_single = unit_text.str.contains("single|১টি|1 egg|per egg", case=False, regex=True, na=False)
    # Official hali values are usually above Tk 20. Per-egg rows around Tk 10-15 should not be divided again.
    numeric_price = pd.to_numeric(out.get("price", pd.Series([np.nan] * len(out))), errors="coerce")
    needs_conversion = egg_mask & (~already_single) & (numeric_price > 20)
    for col in ["price", "price_min", "price_max"]:
        if col in out.columns:
            vals = pd.to_numeric(out[col], errors="coerce")
            out.loc[needs_conversion, col] = (vals.loc[needs_conversion] / 4.0).round(2)
    if "unit" not in out.columns:
        out["unit"] = "As published"
    out.loc[egg_mask, "unit"] = "Single egg"
    return out

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
        data = normalize_egg_prices_to_single(data)
        save_cache(data, CACHE_DIR / "latest_official_prices.csv")
        append_history(data, CACHE_DIR / "history_official_prices.csv")
        return data, statuses

    cached = load_cache(CACHE_DIR / "latest_official_prices.csv")
    if not cached.empty:
        if "data_level" not in cached.columns:
            cached["data_level"] = "cached_official"
        statuses.append({"name": "Local cache", "url": str(CACHE_DIR / "latest_official_prices.csv"), "ok": "true", "message": "Loaded last verified local cache because live official fetch failed."})
        return normalize_egg_prices_to_single(cached), statuses

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
            {"item_label": "Rice", "commodity_pattern": "rice|boro|aman", "quantity": 5, "unit_note": "kg"},
            {"item_label": "Flour/Ata", "commodity_pattern": "ata|flour", "quantity": 2, "unit_note": "kg"},
            {"item_label": "Lentil/Dal", "commodity_pattern": "lentil|masur|mung|gram", "quantity": 1, "unit_note": "kg"},
            {"item_label": "Onion", "commodity_pattern": "onion", "quantity": 2, "unit_note": "kg"},
            {"item_label": "Potato", "commodity_pattern": "potato", "quantity": 2, "unit_note": "kg"},
            {"item_label": "Soybean oil", "commodity_pattern": "soybean|oil", "quantity": 2, "unit_note": "litre"},
            {"item_label": "Egg", "commodity_pattern": "egg", "quantity": 12, "unit_note": "piece"},
            {"item_label": "Chicken/Hen", "commodity_pattern": "chicken|hen", "quantity": 1, "unit_note": "kg"},
            {"item_label": "Sugar", "commodity_pattern": "sugar", "quantity": 1, "unit_note": "kg"},
            {"item_label": "Salt", "commodity_pattern": "salt", "quantity": 1, "unit_note": "kg"},
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
                details.append(f"{display_item(label)}: {display_quantity(qty, selected.get('commodity', ''), label, selected.get('unit', 'As published'))} × {fmt_tk(selected['price'])} {display_unit(selected.get('unit', 'As published'), selected.get('commodity', ''), label)}")
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
            "Quantity used": display_quantity(qty, selected.get("commodity", ""), label, selected.get("unit", "As published")),
            "Price unit": display_unit(selected.get("unit", "As published"), selected.get("commodity", ""), label),
            "Low estimate": fmt_tk(low),
            "Mid estimate": fmt_tk(mid),
            "High estimate": fmt_tk(high),
        })
        total_low += low; total_mid += mid; total_high += high
    if not rows:
        return pd.DataFrame(), "none"
    result = pd.DataFrame(rows)
    result.loc[len(result)] = {
        "Item": display_item("TOTAL"), "Matched official item": "", "Quantity used": "", "Price unit": "",
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
        "Price unit": [display_unit(u, c) for u, c in zip(key_df.get("unit", "As published"), key_df["commodity"].astype(str))],
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



def build_alerts(official_range_df: pd.DataFrame) -> List[str]:
    alerts: List[str] = []
    if official_range_df.empty:
        return alerts
    work = official_range_df.copy()
    work["change_pct"] = pd.to_numeric(work.get("change_pct", 0), errors="coerce").fillna(0)
    work["spread"] = pd.to_numeric(work.get("price_max", work.get("price", 0)), errors="coerce") - pd.to_numeric(work.get("price_min", work.get("price", 0)), errors="coerce")
    work["price"] = pd.to_numeric(work.get("price", 0), errors="coerce")
    inc = work[work["change_pct"] >= 5].sort_values("change_pct", ascending=False).head(4)
    dec = work[work["change_pct"] <= -5].sort_values("change_pct", ascending=True).head(4)
    for _, r in inc.iterrows():
        alerts.append(f"🔺 {display_commodity(r['commodity'])}: {tr('alert_increase')} {fmt_num(r['change_pct'])}%")
    for _, r in dec.iterrows():
        alerts.append(f"🔻 {display_commodity(r['commodity'])}: {tr('alert_decrease')} {fmt_num(abs(r['change_pct']))}%")
    # Spread alert: show only if spread is meaningfully large relative to midpoint or over Tk 20
    work["spread_ratio"] = np.where(work["price"] > 0, work["spread"] / work["price"], 0)
    spr = work[(work["spread"] >= 20) | (work["spread_ratio"] >= 0.15)].sort_values("spread", ascending=False).head(4)
    for _, r in spr.iterrows():
        alerts.append(f"⚠️ {display_commodity(r['commodity'])}: {tr('alert_spread')} ({fmt_range(r.get('price_min'), r.get('price_max'), r.get('price'))})")
    # Deduplicate while preserving order
    seen=set(); out=[]
    for a in alerts:
        if a not in seen:
            out.append(a); seen.add(a)
    return out[:6]


def render_alerts(official_range_df: pd.DataFrame) -> None:
    st.subheader(tr("alerts"))
    st.caption(tr("alerts_help"))
    alerts = build_alerts(official_range_df)
    if not alerts:
        st.success(tr("no_alerts"))
    else:
        for a in alerts:
            st.warning(a)


def basket_match_price(official_range_df: pd.DataFrame, pattern: str):
    if official_range_df.empty:
        return None
    matches = official_range_df[match_commodity(official_range_df["commodity"], pattern)]
    if matches.empty:
        return None
    return matches.sort_values("price").iloc[0]


def render_smart_basket(official_range_df: pd.DataFrame) -> None:
    st.subheader(tr("smart_basket"))
    st.caption(tr("smart_basket_help"))
    presets = [
        ("Rice", "rice|boro|aman", 5.0),
        ("Flour/Ata", "ata|flour", 1.0),
        ("Lentil/Dal", "lentil|mung|gram", 1.0),
        ("Onion", "onion", 2.0),
        ("Potato", "potato", 2.0),
        ("Soybean oil", "soybean|oil", 2.0),
        ("Egg", "egg", 30.0),
        ("Chicken/Hen", "hen|chicken", 1.0),
        ("Sugar", "sugar", 1.0),
        ("Salt", "salt", 1.0),
    ]
    cols = st.columns(2)
    rows=[]; total_low=total_mid=total_high=0.0
    for i,(label,pattern,default_qty) in enumerate(presets):
        with cols[i % 2]:
            step = 1.0 if unit_key_for(label, label) == "piece" else 0.5
            qty = st.number_input(input_label_with_unit(label, label), min_value=0.0, max_value=100.0, value=float(default_qty), step=step, key=f"smart_qty_{label}")
        if qty <= 0:
            continue
        r = basket_match_price(official_range_df, pattern)
        if r is None:
            continue
        low = float(r.get("price_min", r["price"])) * qty
        mid = float(r.get("price", r["price"])) * qty
        high = float(r.get("price_max", r["price"])) * qty
        total_low += low; total_mid += mid; total_high += high
        rows.append({
            "Item": display_item(label),
            "Matched official item": display_commodity(r["commodity"]),
            "Quantity used": display_quantity(qty, r.get("commodity", ""), label, r.get("unit", "As published")),
            "Price unit": display_unit(r.get("unit", "As published"), r.get("commodity", ""), label),
            "Low estimate": fmt_tk(low),
            "Mid estimate": fmt_tk(mid),
            "High estimate": fmt_tk(high),
        })
    if rows:
        st.markdown(f"### {tr('custom_basket_total')}")
        x1,x2,x3=st.columns(3)
        x1.metric(tr("low"), fmt_tk(total_low))
        x2.metric(tr("mid"), fmt_tk(total_mid))
        x3.metric(tr("high"), fmt_tk(total_high))
        st.caption(tr("egg_unit_note"))
        st.dataframe(localize_columns(pd.DataFrame(rows)), use_container_width=True, hide_index=True)
    else:
        st.info(tr("basket_fail"))


def render_history() -> None:
    st.subheader(tr("history"))
    st.caption(tr("history_help"))
    hist_path = CACHE_DIR / "history_official_prices.csv"
    hist = load_cache(hist_path)
    if hist.empty or "date" not in hist.columns or "commodity" not in hist.columns or "price" not in hist.columns:
        st.info(tr("history_empty"))
        return
    hist = hist.copy()
    hist["price"] = pd.to_numeric(hist["price"], errors="coerce")
    hist = hist.dropna(subset=["price"])
    if hist.empty or hist["date"].nunique() < 2:
        st.info(tr("history_empty"))
        return
    choices = sorted(hist["commodity"].astype(str).unique())
    default = choices[:5]
    selected = st.multiselect(tr("axis_commodity"), choices, default=default, format_func=display_commodity)
    if not selected:
        st.info(tr("history_empty"))
        return
    show = hist[hist["commodity"].astype(str).isin(selected)].copy()
    show["commodity_display"] = [display_commodity(x) for x in show["commodity"]]
    fig = px.line(show, x="date", y="price", color="commodity_display", markers=True, labels={"date": tr("data_date"), "price": tr("axis_price"), "commodity_display": tr("axis_commodity")})
    fig.update_layout(height=460)
    st.plotly_chart(fig, use_container_width=True)


def render_market_comparison(df: pd.DataFrame, market_df: pd.DataFrame) -> None:
    st.subheader(tr("market_comparison"))
    st.caption(tr("market_comparison_help"))
    if market_df.empty:
        st.markdown(f"<div class='warnbox'>{tr('market_comparison_unavailable')}</div>", unsafe_allow_html=True)
        return
    cheapest = build_cheapest_market(df)
    if cheapest.empty:
        st.markdown(f"<div class='warnbox'>{tr('market_comparison_unavailable')}</div>", unsafe_allow_html=True)
        return
    show = pd.DataFrame({
        "Commodity": [display_commodity(x) for x in cheapest["commodity"]],
        "Cheapest market": [display_market(x) for x in cheapest["market"]],
        "Area": [display_area(x) for x in cheapest["area"]],
        "Price unit": [display_unit(u, c) for u, c in zip(cheapest.get("unit", "As published"), cheapest["commodity"])],
        "Lowest price": [fmt_tk(x) for x in cheapest["price"]],
        "Saving vs highest": [fmt_tk(x) for x in cheapest["saving_vs_highest"]],
        "Source": [source_short(x) for x in cheapest["source"]],
    })
    st.dataframe(localize_columns(show), use_container_width=True, hide_index=True)


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

    render_alerts(official_range_df)

    render_smart_basket(official_range_df)

    render_market_comparison(df, market_df)
    st.caption(tr("official_not_marketwise"))

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
        st.caption(tr("egg_unit_note"))
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
            "Price unit": [display_unit(u, c) for u, c in zip(table.get("unit", "As published"), table["commodity"].astype(str))],
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

    render_history()

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
    with st.expander(tr("positioning"), expanded=False):
        st.markdown(tr("positioning_text"))
    with st.expander(tr("perfect_features"), expanded=False):
        st.markdown(tr("perfect_features_text"))


if __name__ == "__main__":
    main()
