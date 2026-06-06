# Deployment Guide

## Correct GitHub structure

Your repository homepage should show:

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

Do not upload only the ZIP file. Streamlit cannot run inside a ZIP.

## Streamlit Cloud

- Main file path: `app.py`
- Python version: default is fine
- Secrets: optional

Optional secret:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-official-feed.csv"
```

## Daily refresh

The included GitHub Actions workflow can run the collector daily and update the cache files. Streamlit itself also refreshes official public sources when the app loads or when the refresh button is pressed.

## Why market-wise rows may not always appear

The public DAM and TCB pages expose official price information, but not every public page returns a clean machine-readable Dhaka market-wise table without filters/session/dynamic IDs.

This app will:

- show official aggregate price ranges when available;
- show cheapest market only when verified market-level rows are available;
- never show preview/fake prices as if they were real;
- show a consumer-friendly status even when market-wise ranking is unavailable.

## Map-language note

The base map tiles come from OpenStreetMap/CARTO and their place names may appear in English. The app overlays its own Dhaka market labels/tooltips and localizes those labels in Bangla mode.
