"""Multi-platform share URL scraper.

Routes to platform-specific scrapers:
  - Gemini  : Playwright (Angular CSR — stealth required)
  - ChatGPT : httpx (Next.js SSR — no browser needed)
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager

import httpx
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from app.core.config import settings

logger = logging.getLogger(__name__)

_scrape_semaphore = asyncio.Semaphore(settings.max_concurrent_scrapes)

_PLATFORM_PATTERNS: dict[str, re.Pattern] = {
    "gemini": re.compile(
        r"^https?://(gemini\.google\.com/share/[a-zA-Z0-9]+|g\.co/gemini/share/[a-zA-Z0-9]+)"
    ),
    "chatgpt": re.compile(
        r"^https?://(chatgpt\.com|chat\.openai\.com)/share/[a-zA-Z0-9\-]+"
    ),
}


def detect_platform(url: str) -> str | None:
    for platform, pattern in _PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return platform
    return None


def validate_share_url(url: str) -> bool:
    return detect_platform(url) is not None


def normalize_share_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = f"https://{url}"
    return url


# ─── Gemini — Playwright ────────────────────────────────────────────────────

@asynccontextmanager
async def _get_browser():
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


async def _scrape_gemini(url: str) -> tuple[str, str]:
    async with _get_browser() as browser:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        try:
            await page.goto(url, wait_until="networkidle", timeout=settings.scrape_timeout_ms)
        except Exception as e:
            from app.core.exceptions import ExtractionError
            raise ExtractionError(f"Failed to load page: {e}")

        for selector in ["[data-share-conversation]", "message-content", "model-response", "main"]:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                break
            except Exception:
                continue
        else:
            await page.wait_for_timeout(5000)

        page_text = await page.inner_text("body")
        if any(p in page_text.lower() for p in [
            "no longer available", "chat no longer exists",
            "has been deleted", "page not found",
        ]):
            from app.core.exceptions import ShareLinkExpired
            raise ShareLinkExpired()

        html = await page.content()
        await context.close()
        return html, page_text


# ─── ChatGPT — httpx (SSR) ──────────────────────────────────────────────────

_CHATGPT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def _scrape_chatgpt(url: str) -> tuple[str, str]:
    """Fetch a ChatGPT share page via httpx. No browser needed — it's SSR."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=_CHATGPT_HEADERS,
    ) as client:
        try:
            resp = await client.get(url)
        except Exception as e:
            from app.core.exceptions import ExtractionError
            raise ExtractionError(f"Failed to fetch ChatGPT share page: {e}")

        if resp.status_code == 404:
            from app.core.exceptions import ShareLinkExpired
            raise ShareLinkExpired()

        if resp.status_code != 200:
            from app.core.exceptions import ExtractionError
            raise ExtractionError(f"ChatGPT returned HTTP {resp.status_code}")

        return resp.text, ""


# ─── Dispatcher ─────────────────────────────────────────────────────────────

async def scrape_share_page(url: str) -> tuple[str, str]:
    """Scrape a share page. Platform is auto-detected from the URL."""
    acquired = await asyncio.wait_for(_scrape_semaphore.acquire(), timeout=10.0)
    if not acquired:
        from app.core.exceptions import ScraperBusy
        raise ScraperBusy()

    try:
        url = normalize_share_url(url)
        platform = detect_platform(url)
        logger.info("Scraping %s URL: %s", platform, url)
        if platform == "chatgpt":
            return await _scrape_chatgpt(url)
        return await _scrape_gemini(url)
    finally:
        _scrape_semaphore.release()


async def check_playwright_available() -> bool:
    try:
        async with _get_browser() as browser:
            page = await (await browser.new_context()).new_page()
            await page.goto("about:blank")
            await page.close()
            return True
    except Exception:
        return False
