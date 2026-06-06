# Dhaka Daily Price Watch — Mobile First Consumer Edition

Version: 4.2.0-mobile-first-public-safe

## Fixes in this version
- Raw SSL/JSON errors are no longer shown to consumers.
- If TCB fails because of SSL certificate verification, the app shows a clean public message.
- DAM remains the active official source when DAM is reachable.
- Source status is shown as Available / Temporarily unavailable.
- Technical details are hidden inside an expander for debugging only.
- Public UI avoids fake cheapest-market claims unless a verified market-wise feed is connected.

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
