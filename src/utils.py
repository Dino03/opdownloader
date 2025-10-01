import yaml
from pathlib import Path

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

def load_config() -> dict:
    path = Path("config.yaml")
    if path.exists():
        cfg = yaml.safe_load(path.read_text()) or {}
    else:
        cfg = {}

    def deep_merge(a, b):
        for k, v in b.items():
            if isinstance(v, dict):
                a[k] = deep_merge(a.get(k, {}), v)
            else:
                a[k] = a.get(k, v)
        return a

    return deep_merge(cfg, _DEFAULT_CFG.copy())

def ensure_dirs(paths):
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)
