import argparse
import asyncio
from pathlib import Path
from loguru import logger
from .cdasia import CDAsiaClient
from .downloader import Downloader
from .utils import load_config, ensure_dirs

def parse_args():
    p = argparse.ArgumentParser("cdasia-opinion-downloader")
    p.add_argument("--year-from", type=int, help="Inclusive start year")
    p.add_argument("--year-to", type=int, help="Inclusive end year")
    p.add_argument("--division", type=str, default=None, help="Division filter (e.g., SEC-OGC)")
    p.add_argument("--keywords", type=str, nargs="*", help="Keyword terms")
    p.add_argument("--max-docs", type=int, default=None)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()

async def run():
    args = parse_args()
    cfg = load_config()

    # CLI overrides
    if args.year_from: cfg["filters"]["year_from"] = args.year_from
    if args.year_to: cfg["filters"]["year_to"] = args.year_to
    if args.division: cfg["filters"]["division"] = args.division
    if args.keywords: cfg["filters"]["keywords"] = args.keywords
    if args.max_docs is not None: cfg["filters"]["max_docs"] = args.max_docs
    if args.headless: cfg["scrape"]["headless"] = True

    downloads_dir = Path(cfg["site"]["downloads_subdir"])
    logs_dir = Path(cfg["site"]["log_dir"])
    ensure_dirs([downloads_dir, logs_dir])

    logger.add(logs_dir / "run.log", rotation="2 MB")

    async with CDAsiaClient(cfg) as client:
        await client.login(human_checkpoint=True)
        results = await client.search()
        if args.dry_run:
            for r in results:
                logger.info(f"{r['date']} | {r['title']} | {r['href']}")
            return
        downloader = Downloader(cfg, downloads_dir)
        await downloader.fetch_all(client.page, results)

if __name__ == "__main__":
    asyncio.run(run())
