# Deployment Guide

## Streamlit Community Cloud

1. Push the folder to GitHub.
2. Go to Streamlit Community Cloud.
3. Choose the repository and set `app.py` as the entry point.
4. In Streamlit secrets, add:

```toml
MARKET_PRICE_CSV_URL = "https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>"
```

5. Deploy.

## Local/VPS deployment

```bash
pip install -r requirements.txt
export MARKET_PRICE_CSV_URL="https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>"
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## Making it properly daily-changing

The key is not the Streamlit code. The key is the source data.

Use one of these:

1. A Google Sheet updated daily by enumerators.
2. A custom admin panel where market officers submit price rows.
3. A formal TCB/DAM API/data feed.
4. A scheduled scraper only as a temporary prototype.

The dashboard updates whenever the CSV/API updates and the Streamlit cache expires.
