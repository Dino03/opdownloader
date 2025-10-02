import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional
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

    async def login(
        self,
        human_checkpoint: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        load_dotenv()

        auth_cfg = self.cfg.get("auth", {}) if isinstance(self.cfg, dict) else {}
        user = (
            username
            or auth_cfg.get("username")
            or os.getenv("CDASIA_USERNAME")
        )
        pwd = (
            password
            or auth_cfg.get("password")
            or os.getenv("CDASIA_PASSWORD")
        )
        if not user or not pwd:
            raise RuntimeError(
                "Missing CDAsia credentials. Provide them via .env (CDASIA_USERNAME/"
                "CDASIA_PASSWORD), config auth.username/auth.password, or CLI overrides."
            )

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

        throttle = self.cfg["scrape"]["throttle_ms"] / 1000

        library = self.cfg["filters"].get("library")
        if library:
            await self.page.wait_for_selector(SEL["search_library_button"], timeout=60000)
            await self.page.click(SEL["search_library_button"])
            await self.page.wait_for_selector(SEL["search_library_menu"], timeout=15000)
            option_selector = SEL["search_library_option"].format(library=library)
            await self.page.click(option_selector)
            await asyncio.sleep(throttle)
            try:
                await self.page.wait_for_selector(SEL["search_backdrop"], timeout=2000)
                await self.page.click(SEL["search_backdrop"])
            except PlaywrightTimeout:
                await self.page.keyboard.press("Escape")
            finally:
                try:
                    await self.page.wait_for_selector(SEL["search_library_menu"], state="hidden", timeout=15000)
                except PlaywrightTimeout:
                    logger.warning("Library menu did not close after selection.")

        sections = self.cfg["filters"].get("sections", [])
        for section in sections:
            section_selector = SEL["search_section_chip"].format(section=section)
            locator = self.page.locator(section_selector)
            if await locator.count():
                await locator.first.click()
                await asyncio.sleep(throttle)
            else:
                logger.warning(f"Section chip '{section}' not found")

        division = self.cfg["filters"].get("division")
        if division:
            division_selector = SEL["search_division_chip"].format(division=division)
            locator = self.page.locator(division_selector)
            if await locator.count():
                await locator.first.click()
                await asyncio.sleep(throttle)
            else:
                logger.warning(f"Division chip '{division}' not found")

        await self.page.click(SEL["search_submit"])
        await self.page.wait_for_selector(SEL["results_container"], timeout=60000)
        await self.page.wait_for_selector(SEL["result_row"], timeout=60000)

        results = []
        max_docs = int(self.cfg["filters"].get("max_docs", 0))

        async def capture_detail_url(click_target):
            try:
                async with self.context.expect_page(timeout=self.cfg["scrape"]["navigation_timeout_ms"]) as popup_info:
                    await click_target.click()
                popup = await popup_info.value
            except PlaywrightTimeout:
                logger.warning("Timed out waiting for detail tab to open")
                return None
            else:
                try:
                    await popup.wait_for_load_state("domcontentloaded", timeout=self.cfg["scrape"]["navigation_timeout_ms"])
                except PlaywrightTimeout:
                    logger.warning("Detail tab opened but did not finish loading in time")
                href = popup.url
                await popup.close()
                await asyncio.sleep(throttle)
                await self.page.bring_to_front()
                return href

        while True:
            rows = await self.page.query_selector_all(SEL["result_row"])
            for row in rows:
                ref_el = await row.query_selector(SEL["result_ref"])
                title_el = await row.query_selector(SEL["result_title"])
                date_el = await row.query_selector(SEL["result_date"])
                if not (ref_el and title_el):
                    continue

                ref_text = (await ref_el.inner_text()).strip()
                title_text = (await title_el.inner_text()).strip()
                date_text = (await date_el.inner_text()).strip() if date_el else ""

                link_el = await title_el.query_selector("a")
                href = None
                if link_el:
                    href = await link_el.get_attribute("href")
                if not href:
                    href = await title_el.get_attribute("data-href")
                if not href:
                    href = await row.get_attribute("data-href")

                if not href:
                    href = await capture_detail_url(title_el)
                if not href:
                    href = await capture_detail_url(row)
                if not href:
                    logger.warning(f"Skipping '{title_text}' because no detail URL could be captured.")
                    continue

                date_parsed = None
                for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d"]:
                    try:
                        date_parsed = datetime.strptime(date_text, fmt).date()
                        break
                    except Exception:
                        continue

                results.append({
                    "reference": ref_text,
                    "title": title_text,
                    "href": href,
                    "date": date_text,
                    "date_parsed": date_parsed,
                })

                if max_docs and len(results) >= max_docs:
                    logger.info(f"Reached max_docs={max_docs}; stopping pagination.")
                    return results

            next_btn = self.page.locator(SEL["pagination_next"])
            if await next_btn.count() and await next_btn.first.is_enabled():
                await next_btn.first.click()
                await asyncio.sleep(throttle)
                await self.page.wait_for_selector(SEL["result_row"], timeout=60000)
            else:
                break

        logger.info(f"Collected {len(results)} results.")
        return results
