# Bangladesh Commodity Intelligence Platform — Dhaka Consumer Edition

A consumer-facing Streamlit app for Dhaka essential commodity prices.

The app is designed for **latest verified data only**. Consumers do not choose data sources. The app automatically tries to use a verified market-wise feed and monitors official Bangladesh public sources such as TCB and DAM.

## Main features

- 🛒 Latest Dhaka essential commodity prices
- 🏷️ Cheapest market by commodity
- 🧺 Cheapest household basket calculator
- 🗺️ Dhaka market map
- 📊 Price trends and market-to-market spread charts
- 🚨 Consumer price-spread alerts
- 🌐 English / Bangla interface
- 🧾 Source transparency panel
- 🔒 No public data-source selector

## Important data policy

This app is intentionally strict:

- It should use **official or verified market-wise data**.
- If verified data is missing, it warns users instead of pretending prices are live.
- The bundled seed data is for local preview only and must not be used as public live data.

## Expected production CSV/API schema

Set a CSV/API URL in Streamlit secrets using this schema:

```csv
date,market,area,commodity,category,unit,price_min,price_max,price,source,source_url,verified,latitude,longitude
2026-06-06,Karwan Bazar,Tejgaon,Onion,Vegetable,kg,66,70,68,Department of Agricultural Marketing,https://market.dam.gov.bd/,true,23.7516,90.3935
```

Required columns:

- `date`
- `market`
- `commodity`
- `price`

Strongly recommended columns:

- `area`
- `unit`
- `source`
- `source_url`
- `verified`
- `latitude`
- `longitude`

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Production configuration

Create `.streamlit/secrets.toml` from the example:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed-url.csv"
ALLOW_PREVIEW_DATA = "false"
```

For Streamlit Community Cloud, add these in:

**App → Settings → Secrets**

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed-url.csv"
ALLOW_PREVIEW_DATA = "false"
```

## Official public sources monitored

- TCB daily retail market price page: `https://tcb.gov.bd/pages/daily-rmps`
- DAM market daily price report: `https://market.dam.gov.bd/market_daily_price_report?L=E`
- DAM print report endpoint: `https://market.dam.gov.bd/market_daily_price_report/print?L=E`

Because government pages may be forms, PDFs, or dynamically generated reports, the most reliable production setup is:

1. collect/verify the official market-wise rows,  
2. publish them as a structured CSV/API,  
3. connect that feed to this app using `OFFICIAL_MARKET_PRICE_CSV_URL`.

## Repository structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── DEPLOYMENT.md
├── data/
│   ├── dhaka_markets.csv
│   └── verified_dhaka_market_prices_seed.csv
├── scripts/
│   └── validate_feed.py
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
└── .github/
    └── workflows/
        └── validate.yml
```

## Public use checklist

Before sharing the app publicly:

- [ ] Set `OFFICIAL_MARKET_PRICE_CSV_URL`
- [ ] Set `ALLOW_PREVIEW_DATA = "false"`
- [ ] Confirm latest date is today or yesterday
- [ ] Confirm each row has a source/source URL
- [ ] Confirm coordinates for market map
- [ ] Confirm no preview warning appears on the homepage
