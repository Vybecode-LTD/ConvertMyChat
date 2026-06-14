"""Playwright-based scraper for Gemini share pages.

All CSS selectors isolated here — when Google changes the DOM, fix this file only.
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

_scrape_semaphore = asyncio.Semaphore(settings.max_concurrent_scrapes)

SHARE_URL_PATTERN = re.compile(
    r"^https?://(gemini\.google\.com/share/[a-zA-Z0-9]+|g\.co/gemini/share/[a-zA-Z0-9]+)"
)


def validate_share_url(url: str) -> bool:
    return bool(SHARE_URL_PATTERN.match(url))


def normalize_share_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = f"https://{url}"
    return url


@asynccontextmanager
async def get_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu", "--single-process"],
        )
        try:
            yield browser
        finally:
            await browser.close()


async def scrape_share_page(url: str) -> tuple[str, str]:
    """Render a Gemini share URL, return (html, raw_text)."""
    acquired = await asyncio.wait_for(_scrape_semaphore.acquire(), timeout=10.0)
    if not acquired:
        from app.core.exceptions import ScraperBusy
        raise ScraperBusy()

    try:
        normalized = normalize_share_url(url)
        logger.info(f"Scraping: {normalized}")

        async with get_browser() as browser:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await context.new_page()

            try:
                await page.goto(normalized, wait_until="networkidle",
                                timeout=settings.scrape_timeout_ms)
            except Exception as e:
                from app.core.exceptions import ExtractionError
                raise ExtractionError(f"Failed to load page: {e}")

            # Wait for content to render (GHOST_DOM mitigation)
            for selector in ["[data-share-conversation]", "message-content",
                             "model-response", "main"]:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    break
                except Exception:
                    continue
            else:
                await page.wait_for_timeout(5000)

            # Check for deleted conversation
            page_text = await page.inner_text("body")
            if any(p in page_text.lower() for p in [
                "no longer available", "chat no longer exists",
                "has been deleted", "page not found"
            ]):
                from app.core.exceptions import ShareLinkExpired
                raise ShareLinkExpired()

            html = await page.content()
            raw_text = page_text
            await context.close()
            return html, raw_text
    finally:
        _scrape_semaphore.release()


async def check_playwright_available() -> bool:
    try:
        async with get_browser() as browser:
            page = await (await browser.new_context()).new_page()
            await page.goto("about:blank")
            await page.close()
            return True
    except Exception:
        return False
