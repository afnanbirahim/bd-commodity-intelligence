# Dhaka Daily Price Watch — Full Mobile Consumer App

Version: 5.0.0-full-app-resilient

## Fixes
- Full app no longer disappears when one source/parser fails.
- DAM live official data is tried first.
- If live parsing fails, the app shows a cached official DAM reference snapshot instead of stopping.
- TCB SSL errors are hidden from public UI and kept only in technical details.
- No public preview-market dataset is shown.
- Bangla table view localizes visible columns and mapped commodity names.
- Cheapest-market ranking is shown only if a verified market-wise CSV/API feed is connected.

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
