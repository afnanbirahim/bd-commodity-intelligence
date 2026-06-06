# Dhaka Daily Price Watch — Full Mobile Consumer App

Version: 9.0.0-dam-marketwise-parser

## Latest update
- Added an experimental DAM market-wise parser.
- The app now tries DAM form/print endpoints automatically.
- If DAM returns clean market-wise rows, the Markets tab will show cheapest markets and cheapest listed item per market.
- If DAM only returns aggregate ranges, the app keeps using official aggregate prices and clearly avoids fake cheapest-market claims.
- You can also provide `DAM_MARKETWISE_PRINT_URL` in Streamlit secrets if you discover a working DAM print URL for a selected Dhaka market/report.

## Optional Streamlit secrets

```toml
# Best production option:
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"

# Optional experimental DAM direct print/export URL:
DAM_MARKETWISE_PRINT_URL = "https://market.dam.gov.bd/market_daily_price_report/print?..."

ALLOW_PREVIEW_DATA = "false"
```

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Required market-wise fields for verified feed:
`date, market, area, commodity, unit, price, source, verified, latitude, longitude`
