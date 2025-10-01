import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from .selectors import SEL

class Downloader:
    def __init__(self, cfg: dict, base_dir: Path):
        self.cfg = cfg
        self.base_dir = base_dir
        self.index_rows = []
        self.resume_enabled = bool(self.cfg.get("scrape", {}).get("resume"))
        self.index_path = self.base_dir / "index.csv"
        self._existing_index: Dict[str, Dict] = {}
        self._existing_rows: List[Dict] = []

        if self.resume_enabled and self.index_path.exists():
            try:
                existing_df = pd.read_csv(self.index_path)
                self._existing_rows = existing_df.to_dict("records")
                for row in self._existing_rows:
                    key = self._record_key(row)
                    if key:
                        self._existing_index[key] = row
                logger.debug(
                    f"Loaded {len(self._existing_rows)} existing downloads from {self.index_path}"
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(f"Failed to load existing index at {self.index_path}: {exc}")

    def _record_key(self, item: Dict) -> Optional[str]:
        return item.get("url") or item.get("href") or item.get("file")

    async def fetch_one(self, page, item: Dict) -> bool:
        url = item.get("href")
        if not url:
            logger.error(f"Skipping '{item.get('title','(untitled)')}' – missing detail URL")
            return False
        record_key = self._record_key(item)
        if self.resume_enabled and record_key:
            existing = self._existing_index.get(record_key)
            if existing:
                existing_path = Path(existing.get("file", ""))
                if existing_path.exists():
                    logger.info(
                        f"Skipping '{item.get('title', '(untitled)')}' – already downloaded at {existing_path}"
                    )
                    return False

        tab = await page.context.new_page()
        await tab.goto(url, timeout=self.cfg["scrape"]["navigation_timeout_ms"])
        await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)

        title = (item["title"] or "document").replace("/", "-").strip()
        year = str(item.get("date_parsed").year) if item.get("date_parsed") else "undated"
        folder = self.base_dir / year
        folder.mkdir(parents=True, exist_ok=True)

        try:
            async with tab.expect_download(timeout=self.cfg["scrape"]["download_timeout_ms"]) as dlf:
                await tab.click(SEL["download_link"])
            download = await dlf.value
            out_path = folder / f"{title}.pdf"
            await download.save_as(str(out_path))

            sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
            row = {
                "reference": item.get("reference"),
                "title": item["title"],
                "date": item["date"],
                "url": url,
                "file": str(out_path),
                "sha256": sha256,
            }
            self.index_rows.append(row)
            if record_key and self.resume_enabled:
                self._existing_index[record_key] = row
        finally:
            await tab.close()
        return True

    async def fetch_all(self, page, results: List[Dict]):
        for i, item in enumerate(results, 1):
            try:
                downloaded = await self.fetch_one(page, item)
                if downloaded:
                    logger.info(f"Downloaded {i}/{len(results)}: {item['title']}")
                else:
                    logger.info(f"Skipped {i}/{len(results)}: {item['title']}")
            except Exception as e:
                logger.error(f"Failed {item.get('title','(untitled)')}: {e}")
            await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)

        out_csv = Path(self.cfg["site"]["downloads_subdir"]) / "index.csv"
        all_rows: List[Dict] = []
        if self.resume_enabled:
            all_rows.extend(self._existing_rows)
        all_rows.extend(self.index_rows)

        if not all_rows:
            logger.warning("No documents were downloaded; index not updated.")
            return

        df = pd.DataFrame(all_rows)
        if "url" in df.columns:
            df = df.drop_duplicates(subset=["url"], keep="last")
        df.to_csv(out_csv, index=False)
        logger.success(f"Saved index to {out_csv}")
