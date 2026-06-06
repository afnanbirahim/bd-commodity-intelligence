# Bangladesh Commodity Intelligence

A consumer-facing Streamlit app for Bangladesh essential commodity prices.

## What this final version fixes

This version removes the misleading placeholder rows such as:

`PREVIEW ONLY - replace with verified DAM/TCB market-wise feed`

The app now follows a strict rule:

> Show only verified official/public-source data. If official market-wise Dhaka rows are not available, say that clearly instead of showing fake cheapest-market results.

## Main features

- Latest official price-range view from DAM public pages
- Best-effort official DAM market-wise report parser
- TCB daily retail-price page monitor
- Optional backend-only verified CSV/API feed
- Dhaka cheapest-market logic when market-wise verified rows are available
- Household basket estimate
- Bangla/English toggle
- Dhaka market coverage map
- Charts for price level and price spread
- Local cache and history snapshots
- GitHub Actions daily refresh script

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

The app distinguishes between:

1. **Market-level rows** — can support cheapest-market ranking.
2. **Official aggregate/range rows** — can support price reference and basket estimates, but not true market ranking.

If the official source does not return market-level rows, the app will not invent market rankings.

## Important official sources

- DAM market portal: https://market.dam.gov.bd/?L=E
- DAM market daily price report: https://market.dam.gov.bd/market_daily_price_report?L=E
- TCB daily retail market prices: https://tcb.gov.bd/pages/daily-rmps
