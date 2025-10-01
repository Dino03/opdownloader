import asyncio
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from .selectors import SEL

class CDAsiaClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        headless = self.cfg["scrape"]["headless"]
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(user_agent=self.cfg["scrape"].get("user_agent"))
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def goto(self, url: str):
        logger.debug(f"Navigating to {url}")
        await self.page.goto(url, timeout=self.cfg["scrape"]["navigation_timeout_ms"])

    async def login(self, human_checkpoint: bool = True):
        load_dotenv()
        user = os.getenv("CDASIA_USERNAME")
        pwd = os.getenv("CDASIA_PASSWORD")
        if not user or not pwd:
            raise RuntimeError("Missing CDASIA_USERNAME or CDASIA_PASSWORD in .env")

        await self.goto(self.cfg["site"]["base_url"] + self.cfg["site"]["login_path"])
        await self.page.fill(SEL["login_user"], user)
        await asyncio.sleep(0.5)
        await self.page.fill(SEL["login_pass"], pwd)
        await asyncio.sleep(0.5)
        await self.page.click(SEL["login_submit"])
        await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)

        if human_checkpoint:
            logger.info("If a CAPTCHA or 2FA appears, complete it in the browser window. Waiting up to 60s…")
            try:
                await self.page.wait_for_selector(SEL["post_login_marker"], timeout=60000)
            except PlaywrightTimeout:
                logger.warning("Post-login marker not found yet. Increase timeout if needed.")
        else:
            await self.page.wait_for_selector(SEL["post_login_marker"], timeout=60000)

    async def search(self) -> List[Dict]:
        url = self.cfg["site"]["base_url"] + self.cfg["site"]["search_path"]
        await self.goto(url)

        division = self.cfg["filters"].get("division")
        if division:
            await self.page.fill(SEL["search_division"], division)
            await asyncio.sleep(0.3)

        keywords = self.cfg["filters"].get("keywords") or []
        if keywords:
            await self.page.fill(SEL["search_keywords"], " ".join(keywords))
            await asyncio.sleep(0.3)

        yfrom = str(self.cfg["filters"].get("year_from", ""))
        yto = str(self.cfg["filters"].get("year_to", ""))
        if yfrom:
            await self.page.fill(SEL["search_year_from"], yfrom)
        if yto:
            await self.page.fill(SEL["search_year_to"], yto)

        await asyncio.sleep(0.3)
        await self.page.click(SEL["search_submit"])
        await self.page.wait_for_selector(SEL["results_container"], timeout=60000)

        results = []
        max_docs = int(self.cfg["filters"].get("max_docs", 0))

        while True:
            cards = await self.page.query_selector_all(SEL["result_card"])
            for card in cards:
                title_el = await card.query_selector(SEL["card_title"])
                link_el = await card.query_selector(SEL["card_link"])
                date_el = await card.query_selector(SEL["card_date"])
                if not (title_el and link_el):
                    continue
                title = (await title_el.inner_text()).strip()
                href = await link_el.get_attribute("href")
                date_text = (await date_el.inner_text()).strip() if date_el else ""
                # Adjust date format as needed
                date_parsed = None
                for fmt in ["%d %B %Y", "%B %d, %Y", "%Y-%m-%d"]:
                    try:
                        date_parsed = datetime.strptime(date_text, fmt).date()
                        break
                    except Exception:
                        continue
                results.append({
                    "title": title,
                    "href": href,
                    "date": date_text,
                    "date_parsed": date_parsed
                })
                if max_docs and len(results) >= max_docs:
                    return results

            next_btn = await self.page.query_selector(SEL["pagination_next"])
            if next_btn and (await next_btn.is_enabled()):
                await next_btn.click()
                await self.page.wait_for_selector(SEL["results_container"], timeout=60000)
                await asyncio.sleep(self.cfg["scrape"]["throttle_ms"]/1000)
            else:
                break

        logger.info(f"Collected {len(results)} results.")
        return results
