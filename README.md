# Dhaka Daily Price Watch — Full Mobile Consumer App

Version: 8.0.0-history-trend

## Latest update
- Adds a visible Historical trend chart in the Charts tab.
- The chart uses stored daily official snapshots, not fake historical data.
- On a new deployment, the chart may start with one day only.
- As the app runs on future days, it appends official snapshots to `cache/official_price_history.csv`.
- Keeps the Dhaka market map from v7.
- Cheapest-market ranking still requires verified market-wise rows.

## Important
Official DAM public data gives aggregate price ranges. It does not automatically provide a clean authenticated Dhaka market-wise feed inside this app. For true cheapest-market ranking, connect a verified market-wise CSV/API.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Production market-wise feed

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```

Required market-wise fields:
`date, market, area, commodity, unit, price, source, verified, latitude, longitude`
