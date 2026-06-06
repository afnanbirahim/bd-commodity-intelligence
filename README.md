# Dhaka Daily Price Watch — Mobile First Consumer Edition

Version: 4.1.0-mobile-first-official

## Main fixes
- Active tab/click styling no longer turns dark.
- Public default uses official DAM aggregate price ranges, not bundled preview data.
- Preview market-wise rows are hidden from the public full-data table.
- Bangla mode localizes the visible data table labels and commodity names where mappings exist.
- Cheapest-market claims are disabled unless a verified market-wise feed is connected.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud secrets

For an authentic market-wise production version, add a verified CSV/API feed:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```

Without a verified market-wise feed, the app shows official aggregate price ranges and basket estimates, but it will not claim which market is cheapest.
