# Deployment Guide

1. Extract the ZIP file locally.
2. Upload the extracted files and folders to your GitHub repository root.
3. Make sure GitHub shows `app.py` and `requirements.txt` at the repository root.
4. Deploy on Streamlit Community Cloud.
5. Set the main file path to `app.py`.

## Important

Do not upload only the ZIP file to GitHub. Streamlit cannot run the app from inside a ZIP archive.

## Data behavior

- Official DAM/TCB public-source checks run at app load.
- Cache is used only as fallback.
- Demo/preview prices are not displayed as real prices.
- Egg prices are displayed as **hali / 4 eggs** where applicable.
