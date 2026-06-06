# Bangladesh Commodity Intelligence

A consumer-facing Streamlit app for Bangladesh essential commodity prices.

## Final consumer version: 2.3.0

This version is designed for a public consumer website. It shows only verified official/public-source prices and never displays demo or preview prices as real market data.

## What this version fixes

- Replaced the confusing `Partial / আংশিক` status with a consumer-friendly status: **Prices available / মূল্যতথ্য পাওয়া গেছে**.
- Keeps Dhaka market-wise availability as a separate card, so users clearly see whether true market ranking is available today.
- Added full Bangla localization for commodity names, basket item names, table columns, dates, numbers, charts, and source-monitor messages.
- Added localized Dhaka market marker labels/tooltips on the map. Base map labels still come from OpenStreetMap/CARTO tiles, but the app’s own market labels appear in Bangla when Bangla mode is selected.
- Removed raw technical errors from consumer-facing areas.
- Added cleaner data transparency messages.
- Improved weekly household basket summary cards.

## Main features

- Latest official price-range view from DAM public pages
- Best-effort official DAM market-wise report parser
- TCB daily retail-price page monitor
- Optional backend-only verified CSV/API feed
- Dhaka cheapest-market logic when verified market-wise rows are available
- Household weekly basket estimate
- English/Bangla toggle
- Localized Dhaka market coverage map
- Price level and spread charts
- Local cache and historical snapshot files
- GitHub Actions daily refresh workflow

## Important data rule

The app distinguishes between:

1. **Market-level rows** — can support cheapest-market ranking.
2. **Official aggregate/range rows** — can support price reference and basket estimates, but not true market ranking.

If the official source does not return market-level rows, the app will not invent market rankings. It clearly shows aggregate official prices instead.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Extract the ZIP.
2. Upload the extracted contents to GitHub so `app.py` and `requirements.txt` are in the repository root.
3. Go to Streamlit Community Cloud.
4. Select the repository.
5. Main file path: `app.py`.
6. Deploy.

## Optional verified market-wise feed

If you obtain a formal DAM/TCB/official Google Sheet CSV or API, add this to Streamlit secrets:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-official-feed.csv"
```

Required CSV columns:

```csv
date,commodity,market,price
```

Recommended columns:

```csv
date,commodity,market,area,unit,price,price_min,price_max,source,source_url,verified,data_level
```

Verification rule:

- `verified` must be `true`, `yes`, `1`, or `verified`; or
- `source` must contain words like `DAM`, `TCB`, `Official`, `Government`, or `Govt`.

Unverified rows are rejected.

## Data honesty

Prices may vary by quality, brand, package size, shop, and time of day. The app is a verified reference, not a bargaining guarantee.
