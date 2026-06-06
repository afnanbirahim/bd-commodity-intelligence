# GitHub Actions + CSV archive

This app now stores historical official price snapshots in:

```text
data/official_price_history.csv
```

A GitHub Action runs every day and updates this file.

## Files added

```text
scripts/fetch_dam_prices.py
.github/workflows/update_prices.yml
data/official_price_history.csv
```

## What happens daily

```text
GitHub Action
  ↓
Fetch DAM official price ranges
  ↓
Append/update data/official_price_history.csv
  ↓
Commit the updated CSV back to GitHub
  ↓
Streamlit reads that CSV for trend charts
```

## Manual run

On GitHub:

1. Go to **Actions**
2. Select **Update official DAM price history**
3. Click **Run workflow**

## Required GitHub setting

Go to:

```text
Settings → Actions → General → Workflow permissions
```

Select:

```text
Read and write permissions
```

Otherwise GitHub Actions cannot commit the CSV update.

## Streamlit

After the Action updates the repository, Streamlit may need a refresh/reboot to reflect the latest committed CSV, depending on deployment caching.
