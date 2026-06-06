# Deployment Guide

## 1. Extract the ZIP

Do not upload the ZIP file itself to GitHub. Extract it first.

## 2. Upload project contents

Upload the files and folders inside the extracted folder so GitHub shows:

```text
app.py
requirements.txt
README.md
DEPLOYMENT.md
data/
scripts/
.streamlit/
.github/
cache/
```

## 3. Streamlit Cloud

- Connect GitHub.
- Choose your repository.
- Main file: `app.py`.
- Deploy.

## 4. Optional production feed

In Streamlit Cloud secrets, add:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-official-marketwise-feed.csv"
```

The app will use this feed as a verified backend source if available.

## 5. Important data rule

The public app should not claim a cheapest Dhaka market unless verified market-wise rows are loaded. Aggregate official ranges are authentic reference prices, but they are not the same as market-by-market shopping prices.

## 6. Daily history

The app stores daily snapshots in:

```text
cache/history_official_prices.csv
```

If deployed with the included GitHub Actions workflow or opened daily, the historical trend section becomes richer over time.

## 7. Consumer features included

- Smart Shopping Basket
- Price Alerts
- Historical Trends
- Dhaka Map
- Verified-only Market Comparison
- Bangla/English UI
- Egg unit correction: hali / 4 eggs
