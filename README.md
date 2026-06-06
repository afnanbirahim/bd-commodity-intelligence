# Dhaka Daily Price Watch — Mobile First Consumer Edition

A Streamlit consumer app for Bangladesh/Dhaka commodity prices.

## Version
4.0.0-mobile-first

## What changed
- Mobile-first app layout with tabs and cards
- No public data-source selector
- High-contrast light theme to avoid unreadable mobile cards
- Compact official price cards instead of wide tables
- Basket estimator and market ranking when verified market-wise rows exist
- English/Bangla toggle

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Production secrets
Set these in Streamlit Cloud secrets:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```

If no verified market-wise CSV is connected, the app will not make unsupported cheapest-market claims.
