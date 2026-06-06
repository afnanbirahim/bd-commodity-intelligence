# Bangladesh Commodity Intelligence — Consumer Final

A consumer-facing Streamlit app for latest verified Bangladesh essential commodity prices.

## Final fixes in this version

- Uses short consumer status labels: **Verified / যাচাইকৃত**.
- Shows Dhaka market-wise coverage as **Unavailable / তথ্য অনুপলব্ধ** when official market rows are not available.
- Treats **Egg Farm-Red / Egg Farm-White** prices as **hali / 4 eggs (হালি / ৪টি)**, not per single egg.
- Bangla/English UI, commodity names, basket items, numbers, dates, chart labels, and market marker labels.
- Does not show demo prices as real prices.
- Shows official aggregate/range prices from public DAM data when available.
- Shows cheapest Dhaka market ranking only when verified market-wise rows are available.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Upload the extracted contents to GitHub, not the ZIP itself. Your repository root should show:

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

Then deploy on Streamlit Cloud with main file:

```text
app.py
```

## Authenticity note

The app is intentionally conservative. If official market-wise Dhaka rows are not found, it will not invent cheapest-market rankings. It will show official aggregate/range prices and say market-wise data is unavailable.
