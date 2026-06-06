# Bangladesh Commodity Intelligence

A consumer-facing Streamlit website for Bangladesh essential commodity prices.

## What this app does

- Shows the latest verified official/public commodity price ranges where available.
- Shows the **price unit everywhere**: per kg, per litre, per piece, per packet, or official unit.
- Supports English and Bangla UI, including commodity names, numbers, dates, table labels, chart labels, map markers, and unit labels.
- Treats egg prices as **single egg / ১টি ডিম** everywhere. If the official source gives egg price as **hali / 4 eggs**, the app divides by 4 and shows the per-egg value.
- Shows a ready-made weekly household basket estimate.
- Adds a **Smart Shopping Basket** where users can enter quantities such as 5 kg rice, 2 kg onion, 30 eggs, and 2 litres oil.
- Shows **price alert cards** when official data indicates notable increases, decreases, or wide low-high spreads.
- Stores daily snapshots for **historical trend charts** as the app runs over time.
- Shows charts, price spreads, high-price essentials, and a Dhaka market coverage map.
- Shows **Dhaka market comparison / cheapest market** only if verified market-wise Dhaka rows are available.
- Never displays demo/preview prices as real prices.

## Unit policy

The app makes units explicit because commodity prices are meaningless without the quantity basis.

Typical normalized units:

| Commodity type | Displayed unit |
|---|---|
| Rice, flour/ata, dal, onion, potato, chicken, beef, mutton, sugar, salt | per kg / প্রতি কেজি |
| Soybean oil / edible oil | per litre / প্রতি লিটার |
| Egg | per piece / প্রতি পিস |
| Packeted items where applicable | per packet / প্রতি প্যাকেট |

If an official page does not expose a clean machine-readable unit column, the app infers the usual consumer unit from the commodity name and explains this in the transparency note.

## Existing Bangladesh systems

Bangladesh already has official price-report systems, especially TCB and DAM. This app does not replace them. It repackages verified public data into a simpler consumer interface with clearer cards, Bangla localization, smart basket estimates, trend storage, alerts, map labels, explicit units, and source transparency.

## Authenticity rule

Official aggregate prices are shown as verified reference ranges. Market-wise “cheapest market” results are displayed only when verified market-level Dhaka data is available. If market-wise data is unavailable, the app clearly says so instead of inventing a ranking.

## Best features added

### Smart Shopping Basket
Users choose their own quantities and the app calculates low, average, and high estimated cost from verified official price ranges.

### Historical Trends
The app saves daily snapshots into `cache/history_official_prices.csv`. As the app runs every day, the trend section becomes more useful.

### Price Alerts
The app highlights notable official price changes and wide price spreads.

### Market Comparison
If verified Dhaka market-wise rows are available from DAM/TCB or a backend official feed, the app compares markets and shows the cheapest market by commodity. If not available, it does not fake it.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

Upload the extracted project contents to GitHub so the repository root contains:

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

Then select `app.py` as the main file in Streamlit Cloud.

## Optional verified backend feed

For production use, you can configure a verified CSV/API source through Streamlit secrets:

```toml
OFFICIAL_MARKET_PRICE_CSV_URL = "https://your-verified-feed.csv"
```

Expected columns can include:

```text
date, commodity, market, area, price, price_min, price_max, unit, source, source_url, data_level
```

For market comparison, set:

```text
data_level = market
```

Recommended unit values for backend rows:

```text
kg, litre, piece, packet
```

## Disclaimer

Prices can vary by quality, brand, package size, shop, and time of day. This app is a verified reference dashboard, not a purchase-price guarantee.
