# Dhaka Daily Price Watch — Consumer Clean Version

Version: 10.0.0-consumer-clean

## Latest change
- Removed developer-facing “connect CSV/API feed” message from the consumer Markets tab.
- Markets tab now uses consumer-friendly wording.
- Admin setup instructions are moved to the Source tab under an expander.
- App still tries DAM market-wise parser automatically.
- If market-wise rows are unavailable, it shows official reference price ranges without fake cheapest-market claims.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Optional market-wise feed

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-marketwise-feed.csv"
ALLOW_PREVIEW_DATA = "false"
```
