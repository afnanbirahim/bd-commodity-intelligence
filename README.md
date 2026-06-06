# Dhaka Daily Price Watch — Full Mobile Consumer App

Version: 6.0.0-market-map

## Latest update
- Added a Dhaka market map in the Markets tab.
- The map always shows known Dhaka market locations from `data/dhaka_markets.csv`.
- If a verified market-wise feed is connected, each market card shows the cheapest listed item for that market.
- If no verified market-wise feed is connected, the map still shows market locations but clearly says cheapest item is not available yet.
- No fake market-wise prices are invented from aggregate official DAM price ranges.

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
