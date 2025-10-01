from pathlib import Path
from typing import Any, Dict

import yaml

_DEFAULT_CFG = {
    "site": {
        "base_url": "https://www.cdasia.com",
        "login_path": "/login",
        "search_path": "/search",
        "downloads_subdir": "data/downloads",
        "log_dir": "data/logs",
    },
    "filters": {
        "division": "SEC-OGC",
        "keywords": ["SEC-OGC Opinion"],
        "year_from": 2010,
        "year_to": 2025,
        "max_docs": 0,
    },
    "scrape": {
        "headless": True,
        "timeout_ms": 45000,
        "navigation_timeout_ms": 60000,
        "throttle_ms": 1500,
        "batch_size": 5,
        "download_timeout_ms": 120000,
        "retries": 3,
        "resume": True,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
    }
}

def _deep_merge(target: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in defaults.items():
        if isinstance(value, dict):
            target[key] = _deep_merge(target.get(key, {}), value)
        else:
            target.setdefault(key, value)
    return target


def load_config() -> dict:
    path = Path("config.yaml")
    if path.exists():
        cfg = yaml.safe_load(path.read_text()) or {}
    else:
        cfg = {}

    return _deep_merge(cfg, _DEFAULT_CFG.copy())


def save_config(cfg: Dict[str, Any], path: Path | str = "config.yaml") -> None:
    path = Path(path)
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))

def ensure_dirs(paths):
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)
