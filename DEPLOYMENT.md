# Deployment Guide

## 1. Upload to GitHub correctly

Do **not** upload the ZIP file itself.

Extract the ZIP, then upload the contents so your repository root shows:

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

## 2. Deploy on Streamlit Community Cloud

1. Go to Streamlit Community Cloud.
2. Sign in with GitHub.
3. Click **New app**.
4. Select your repository.
5. Set main file path:

```text
app.py
```

6. Deploy.

## 3. Add production secrets

In Streamlit Cloud:

**App → Settings → Secrets**

Add:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed-url.csv"
ALLOW_PREVIEW_DATA = "false"
```

## 4. Data feed recommendation

For the most authentic consumer app, do not let the public upload CSV files. Instead, maintain one verified feed from official or formally verified sources.

Recommended workflow:

1. DAM/TCB official report is checked daily.
2. Market-wise rows are entered/validated in a controlled Google Sheet or small database.
3. The sheet/database exposes a CSV/API endpoint.
4. This app consumes that endpoint automatically.
5. The app shows the latest verified date and source.

## 5. Common deployment errors

### Error: `File does not exist: app.py`

Your files are probably inside another folder or ZIP.

Fix: repository root must contain `app.py` directly.

### Error: package not found

Check `requirements.txt` is named exactly:

```text
requirements.txt
```

not `requirements` and not `requirements.txt.txt`.

### App shows preview warning

This means no verified feed URL has been configured.

Fix: add Streamlit secrets:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed-url.csv"
ALLOW_PREVIEW_DATA = "false"
```

### App says verified data unavailable

That is expected if no clean market-wise verified feed is connected. The app is strict by design and will not invent cheapest-market claims.
