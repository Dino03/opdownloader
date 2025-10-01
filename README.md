# CDAsia Opinions Downloader

Automate login to CDAsia and batch-download SEC opinions (e.g., SEC-OGC) to a local archive with a CSV index.

> ⚠️ **Disclaimer**: Use only if permitted by your CDAsia license and agency policy. Runs locally with your credentials from `.env`. Throttled, and requires manual completion of CAPTCHA/2FA when shown.

## Features
- Playwright (Chromium) automation
- Filters: year range, division, keywords
- Pagination handling
- Download capture with CSV manifest (title, date, URL, file path, SHA-256)
- Conservative throttling and retries

## Beginner Setup (Step by Step)

If you are brand new to command-line tools, follow these instructions slowly and in order. When you get stuck, search for the exact error message or ask a teammate for help.

### 0. Install the prerequisites

1. **Python 3.9 or later** – Download from the [official Python website](https://www.python.org/downloads/) (Windows/macOS) or install via your package manager (for example, `brew install python@3.11` on macOS or `sudo apt install python3 python3-venv python3-pip` on Ubuntu/Linux). During installation on Windows, check the box that adds Python to your PATH.
2. **Git** – Download from [git-scm.com](https://git-scm.com/downloads) (Windows/macOS) or install with your package manager on Linux (`sudo apt install git`, `brew install git`, etc.).
3. **Playwright CLI** – Installed automatically later via `playwright install chromium`. No separate download is required, but Playwright will ask to download the browser the first time you run the command.

### 1. Open a terminal window

- **macOS** – Press `Cmd + Space`, type `Terminal`, and press Enter.
- **Windows** – Press the Windows key, type `Command Prompt` (or `PowerShell`), and press Enter.
- **Linux** – Use your desktop launcher and search for “Terminal,” or press `Ctrl + Alt + T`.

Keep this window open for the rest of the steps. Everything below happens inside the terminal.

### 2. Download (clone) the project

Type the following command and press Enter. Replace `YOUR_GH_USERNAME` with your own GitHub username if you forked the repo:

```bash
git clone https://github.com/YOUR_GH_USERNAME/cdasia-opinion-downloader.git
```

When it finishes, move into the project folder:

```bash
cd cdasia-opinion-downloader
```

### 3. Create and activate a virtual environment

Using a virtual environment keeps the project’s Python packages separate from the rest of your computer.

```bash
python -m venv .venv
```

- If you get `command not found: python` on macOS/Linux, try `python3` instead.
- On Windows Command Prompt, use `python`; on PowerShell, use `py -3`.

Activate the environment:

```bash
source .venv/bin/activate
```

On Windows Command Prompt the command is:

```cmd
.venv\Scripts\activate
```

If you see `(.venv)` at the beginning of your terminal prompt, activation worked. When you are finished working, type `deactivate` to exit the environment.

### 4. Install Python packages and Playwright browser

With the virtual environment active, run:

```bash
pip install -r requirements.txt
playwright install chromium
```

- If you see `command not found: pip`, use `pip3`.
- The Playwright install command downloads the Chromium browser that powers the automation. Allow it to finish completely.

### 5. Copy the environment template and fill in credentials

```bash
cp .env.example .env
```

Open `.env` in any text editor (VS Code, Notepad, nano, etc.) and add your CDAsia username and password. Do the same for `config.yaml`, setting the year range, division, and keywords you want to download.

### 6. Run the downloader

For a first run, use the debug script so you can watch the browser and solve any CAPTCHA or 2FA prompts:

```bash
./scripts/launch_debug.sh --division "SEC-OGC" --dry-run
```

- If you get `permission denied`, run `chmod +x scripts/*.sh` once and retry.
- On Windows, run these scripts from Git Bash or WSL. Alternatively, run the Python module directly:

  ```bash
  python -m src.main --division "SEC-OGC" --dry-run
  ```

When everything works in debug mode, start the headless downloader:

```bash
./scripts/run.sh --year-from 2015 --year-to 2025 --division "SEC-OGC"
```

Your downloaded files and CSV manifest will appear inside the `data/` folder the scripts create.

### 7. Need a faster summary?

Once you are comfortable with the basics, you can skip to the [Quick Start](#quick-start) section below for the condensed command list.

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
