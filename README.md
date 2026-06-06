# Dhaka Realtime Commodity Price Intelligence

A Streamlit dashboard for Bangladesh/Dhaka daily necessities. It is designed to answer:

- What is the latest price of essential commodities?
- In Dhaka, which market has the minimum price for each commodity?
- Which market is cheapest for a full household basket?
- How large is the price spread between markets?
- Are official public TCB/DAM sources reachable today?
- Can users switch the interface between English and Bangla?

## Main features

- English / Bangla translation toggle
- Live CSV/API connector
- Google Sheets CSV connector
- CSV upload option
- Official DAM public recent-price snapshot parser
- TCB daily retail-price page monitor
- Local cache fallback if the live CSV/API fails
- Cheapest market by commodity
- Basket-cost optimizer
- Market price index
- Dhaka market map
- Multi-date trend chart
- Downloadable CSV outputs
- Daily cache refresh script and GitHub Actions workflow

## Important truth about “realtime”

The app is **live-ready**, but true market-wise realtime results require a market-level data source.

Official public pages may show aggregate daily prices or reports, but they do not always expose clean machine-readable rows for every Dhaka market. Therefore:

- Official DAM/TCB monitoring is included.
- Market-wise “which market is cheapest?” uses a live CSV/API/Google Sheet feed.
- The included CSV is only a demo/template and is clearly marked as demo data.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Connect live daily-changing data

### Option A — Google Sheets CSV, fastest prototype

1. Open `data/dhaka_market_prices_template.csv`.
2. Copy the headers to Google Sheets.
3. Update prices daily from enumerators, TCB/DAM reports, or verified market collectors.
4. Publish the sheet as CSV.
5. Paste the CSV URL in the app sidebar.

Google Sheets CSV format:

```text
https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>
```

### Option B — Streamlit secrets

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`:

```toml
MARKET_PRICE_CSV_URL = "https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>"
```

Then run:

```bash
streamlit run app.py
```

### Option C — API endpoint

Use any public/private API endpoint that returns CSV with the required columns.

## Required columns

Minimum useful columns:

```text
date,district,market,commodity,unit,price_mid,source,lat,lon
```

Full recommended schema:

```text
date,division,district,city_area,market,market_bn,commodity,commodity_bn,variety,variety_bn,unit,unit_bn,price_min,price_max,price_mid,currency,source,source_url,confidence,lat,lon
```

## Daily auto-update using GitHub Actions

1. Put this project in a GitHub repository.
2. Add a repository secret named `MARKET_PRICE_CSV_URL`.
3. The included workflow `.github/workflows/daily_refresh.yml` runs daily.
4. It saves the latest live CSV/API result into `cache/latest_market_prices_cache.csv`.

## Files

- `app.py` — main Streamlit app
- `requirements.txt` — Python dependencies
- `data/dhaka_market_prices_template.csv` — demo/template market-wise data
- `data/basket_template.csv` — default household basket
- `data/dhaka_market_locations.csv` — sample market coordinates
- `scripts/update_cache.py` — daily cache update script
- `.github/workflows/daily_refresh.yml` — optional scheduled daily refresh
- `.streamlit/secrets.toml.example` — example live source config

## Recommended production model

For a real public civic-tech deployment, use this workflow:

1. Data collector submits daily prices by market.
2. Supervisor checks anomalies.
3. Approved data goes to Google Sheet/API.
4. Streamlit dashboard reads the source every few minutes.
5. Dashboard displays cheapest market, basket cost, map, and trend.

A formal TCB/DAM data-sharing arrangement would be much better than scraping because scraping can break when government pages change layout.
