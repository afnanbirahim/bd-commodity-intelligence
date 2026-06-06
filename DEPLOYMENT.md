# Deployment Guide

## 1. Upload to GitHub

Do not upload the ZIP itself. Extract the ZIP and upload the contents so the repository root contains:

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
2. Connect your GitHub repository.
3. Select the repository.
4. Set main file path:

```text
app.py
```

5. Deploy.

## 3. Optional production secret

For a verified official/backend market-wise CSV feed, add this Streamlit secret:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed.csv"
```

Expected columns:

```text
date, commodity, market, area, price, price_min, price_max, unit, source, source_url, data_level, verified
```

For market comparison, use:

```text
data_level = market
verified = true
```

Recommended units:

```text
kg
litre
piece
packet
```

Egg rows should preferably be sent as `piece`. If an official/public source provides egg as hali / 4 eggs, the app normalizes it to a single-egg price.

## 4. Daily refresh

The package includes a GitHub Actions workflow under:

```text
.github/workflows/daily_refresh.yml
```

This can run a daily refresh script and commit cached data snapshots, depending on repository permissions.

## 5. Consumer data rule

The public app should not show demo prices as real prices. It should show:

- verified official price ranges when available;
- verified market-wise ranking only when verified market-wise rows exist;
- clear unavailable status when market-wise data is absent.
