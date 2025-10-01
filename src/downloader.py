import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict
import pandas as pd
from loguru import logger
from .selectors import SEL

class Downloader:
    def __init__(self, cfg: dict, base_dir: Path):
        self.cfg = cfg
        self.base_dir = base_dir
        self.index_rows = []

    async def fetch_one(self, page, item: Dict):
        url = item["href"]
        tab = await page.context.new_page()
        await tab.goto(url, timeout=self.cfg["scrape"]["navigation_timeout_ms"])
        await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)

        title = (item["title"] or "document").replace("/", "-").strip()
        year = str(item.get("date_parsed").year) if item.get("date_parsed") else "undated"
        folder = self.base_dir / year
        folder.mkdir(parents=True, exist_ok=True)

        with tab.expect_download(timeout=self.cfg["scrape"]["download_timeout_ms"]) as dlf:
            await tab.click(SEL["download_link"])
        download = await dlf.value
        out_path = folder / f"{title}.pdf"
        await download.save_as(str(out_path))

        sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
        self.index_rows.append({
            "title": item["title"],
            "date": item["date"],
            "url": url,
            "file": str(out_path),
            "sha256": sha256,
        })
        await tab.close()

    async def fetch_all(self, page, results: List[Dict]):
        for i, item in enumerate(results, 1):
            try:
                await self.fetch_one(page, item)
                logger.info(f"Downloaded {i}/{len(results)}: {item['title']}")
            except Exception as e:
                logger.error(f"Failed {item.get('title','(untitled)')}: {e}")
            await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)

        out_csv = Path(self.cfg["site"]["downloads_subdir"]) / "index.csv"
        pd.DataFrame(self.index_rows).to_csv(out_csv, index=False)
        logger.success(f"Saved index to {out_csv}")
