# Dhaka Daily Price Watch — Full Mobile Consumer App

Version: 7.0.0-map-safe

## Latest fix
- Fixed Streamlit Cloud map crash.
- Plotly map no longer receives missing hover fields when market-wise data is absent.
- Map has a safe fallback using `st.map`, so the app should not crash even if Plotly fails.
- Dhaka market locations still show from `data/dhaka_markets.csv`.
- Cheapest item per market appears only after a verified market-wise feed is connected.

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

Required feed fields:
`date, market, area, commodity, unit, price, source, verified, latitude, longitude`
