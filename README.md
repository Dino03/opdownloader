# CDAsia Opinions Downloader

Automate login to CDAsia and batch-download SEC opinions (e.g., SEC-OGC) to a local archive with a CSV index.

> ⚠️ **Disclaimer**: Use only if permitted by your CDAsia license and agency policy. Runs locally with your credentials from `.env`. Throttled, and requires manual completion of CAPTCHA/2FA when shown.

## Features
- Playwright (Chromium) automation
- Filters: year range, division, keywords
- Pagination handling
- Download capture with CSV manifest (title, date, URL, file path, SHA-256)
- Conservative throttling and retries

## Quick Start
```bash
# 1) Clone and enter
git clone https://github.com/YOUR_GH_USERNAME/cdasia-opinion-downloader.git
cd cdasia-opinion-downloader

# 2) Python env + deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3) Configure
cp .env.example .env
# edit .env to put your CDAsia credentials
# edit config.yaml to set years, division, keywords

# 4) Dry-run (headed, for selector testing / login checkpoint)
./scripts/launch_debug.sh --division "SEC-OGC" --dry-run

# 5) Download (headless ok after you've confirmed login works)
./scripts/run.sh --year-from 2015 --year-to 2025 --division "SEC-OGC"
```

## Optional: run the web app

If you prefer a browser-based UI to tweak filters and launch runs, install the new web dependencies and start Uvicorn:

```bash
pip install -r requirements.txt
uvicorn src.webapp:app --reload --port 8000
```

Then open <http://localhost:8000>. The page mirrors the CLI filters, lets you choose headless vs. headed mode, supports dry-run previews, and streams task progress (including log file paths for each run).

## Notes
- Update CSS selectors in `src/selectors.py` to match CDAsia's DOM (placeholders provided).
- If your org uses SSO/2FA, run headed first (`--dry-run`) and complete steps in the visible browser.
- Respect the website's terms and your license agreements.
