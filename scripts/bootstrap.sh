#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-$PROJECT_ROOT/requirements.txt}"
WHEEL_DIR="${WHEEL_DIR:-$PROJECT_ROOT/vendor/wheels}"
REQ_HASH_FILE="$WHEEL_DIR/requirements.sha256"
PLAYWRIGHT_SENTINEL="$VENV_PATH/.playwright-chromium"

if [ ! -d "$VENV_PATH" ]; then
  echo "[bootstrap] Creating virtual environment at $VENV_PATH"
  "$PYTHON_BIN" -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

mkdir -p "$WHEEL_DIR"

current_hash=$(python - "$REQUIREMENTS_FILE" <<'PY'
import hashlib, sys
from pathlib import Path
req = Path(sys.argv[1])
print(hashlib.sha256(req.read_bytes()).hexdigest())
PY
)

stored_hash=""
if [ -f "$REQ_HASH_FILE" ]; then
  stored_hash=$(cat "$REQ_HASH_FILE")
fi

need_download=false
if [ -z "$stored_hash" ]; then
  need_download=true
elif [[ "$current_hash" != "$stored_hash" ]]; then
  need_download=true
elif ! find "$WHEEL_DIR" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) -print -quit | grep -q .; then
  need_download=true
fi

if [ "$need_download" = true ]; then
  echo "[bootstrap] Downloading Python requirements into $WHEEL_DIR"
  rm -f "$WHEEL_DIR"/*
  python -m pip download --dest "$WHEEL_DIR" -r "$REQUIREMENTS_FILE"
  echo "$current_hash" > "$REQ_HASH_FILE"
else
  echo "[bootstrap] Cached wheelhouse up to date"
fi

echo "[bootstrap] Installing dependencies from local wheel cache"
python -m pip install --no-index --find-links "$WHEEL_DIR" -r "$REQUIREMENTS_FILE"

if [ ! -f "$PLAYWRIGHT_SENTINEL" ]; then
  echo "[bootstrap] Installing Playwright Chromium browser"
  python -m playwright install chromium
  touch "$PLAYWRIGHT_SENTINEL"
else
  echo "[bootstrap] Playwright Chromium already installed"
fi

echo "[bootstrap] Environment ready"
