# Dhaka Daily Price Watch — GitHub CSV Archive Edition

Version: 11.0.0-github-csv-archive

## What this version adds

- Historical prices are archived in `data/official_price_history.csv`.
- GitHub Actions updates this CSV every day.
- The Charts tab reads this repository CSV for historical trend charts.
- The app no longer depends only on temporary Streamlit local cache for history.
- No Google Sheets or Google Cloud setup required.

## New files

```text
scripts/fetch_dam_prices.py
.github/workflows/update_prices.yml
data/official_price_history.csv
GITHUB_ACTIONS_ARCHIVE.md
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Run the updater locally

```bash
python scripts/fetch_dam_prices.py
```

## GitHub Actions setup

In your GitHub repository:

```text
Settings → Actions → General → Workflow permissions → Read and write permissions
```

Then go to:

```text
Actions → Update official DAM price history → Run workflow
```

The workflow also runs daily automatically.

## Market-wise cheapest prices

This version still shows official aggregate prices and historical trends. True market-wise cheapest prices require verified market-wise rows.
