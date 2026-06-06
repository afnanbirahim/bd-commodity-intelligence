# Deployment Guide

## GitHub upload

Do not upload the ZIP itself. Extract it first, then upload the contents so the repository root contains:

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

## Streamlit Cloud

1. Go to Streamlit Community Cloud.
2. Connect your GitHub repository.
3. Select `app.py` as the main file.
4. Deploy.

## Data behavior

The app tries official/public source collection first, then uses the latest verified local cache if live fetching fails. It does not show fake market rankings. Market comparison activates only when verified Dhaka market-wise rows are present.

## Unit policy

Egg values are displayed as single-egg prices. If the official feed is hali / 4 eggs, the app divides by 4 and stores this in the unit audit table.

## Recommended production step

Keep daily refresh enabled so `cache/history_official_prices.csv` grows into a trend database.
