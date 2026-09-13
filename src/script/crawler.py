from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .export import save_to_csv
from .images import download_cover
from .models import Book
from .parser import extract_product_urls, parse_book_html


DEFAULT_CATEGORY_URL = "https://www.politeianet.gr/el/categories/thema-logotexnia-efhbikh-logotexnia?page={}"


def print_progress(message: str) -> None:
    """Print progress immediately, even in a non-Unicode Windows console."""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        print(message.encode("ascii", "backslashreplace").decode("ascii"), flush=True)


@dataclass(slots=True)
class ScraperConfig:
    category_url: str = DEFAULT_CATEGORY_URL
    output: Path = Path("data/books.csv")
    max_pages: int | None = None
    max_books: int | None = None
    retries: int = 3
    request_delay: float = 0.5
    download_images: Path = Path("data/covers")


def handle_cookie_banner(page: Page) -> None:
    for selector in ("text=Αποδοχή όλων", "text=Αποδοχή", "text=Συμφωνώ", "#accept-cookies", ".cookie-accept"):
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=500):
                button.click(timeout=1_000)
                return
        except Exception:
            continue


def _goto_with_retries(page: Page, url: str, retries: int) -> bool:
    for attempt in range(max(1, retries)):
        try:
            # The current site renders the catalogue through an API after the
            # initial document is committed; waiting for DOMContentLoaded can
            # therefore time out even though the page is usable.
            page.goto(url, wait_until="commit", timeout=30_000)
            return True
        except PlaywrightTimeoutError:
            if attempt == retries - 1:
                return False
            time.sleep(1 + attempt)
    return False


def extract_book_details(page: Page, book_url: str, retries: int = 3) -> Book | None:
    if not _goto_with_retries(page, book_url, retries):
        return None
    try:
        page.wait_for_selector("h1", timeout=20_000)
    except Exception:
        return None
    try:
        page.wait_for_selector(".formatted-price", timeout=20_000)
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except Exception:
        pass
    try:
        return parse_book_html(page.content(), book_url, page.locator("body").inner_text())
    except Exception:
        return None


def _load_category_urls(page: Page, category_url: str, retries: int) -> list[str]:
    """Load a dynamic category, retrying a React/API loading shell."""
    for attempt in range(max(1, retries)):
        if not _goto_with_retries(page, category_url, 1):
            continue
        handle_cookie_banner(page)
        try:
            page.wait_for_selector('a[href*="/products/"]', state="attached", timeout=60_000)
        except Exception:
            pass
        urls = extract_product_urls(page.content(), category_url)
        if urls:
            return urls
        if attempt + 1 < retries:
            time.sleep(1 + attempt)
    return []


def scrape_politeia(config: ScraperConfig, progress: Callable[[str], None] = print_progress) -> list[Book]:
    books: list[Book] = []
    seen_urls: set[str] = set()
    empty_pages = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context: BrowserContext = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="el-GR",
        )
        category_page = context.new_page()
        detail_page = context.new_page()
        page_number = 1
        try:
            while config.max_pages is None or page_number <= config.max_pages:
                category_url = config.category_url.format(page_number)
                progress(f"Processing category page {page_number}: {category_url}")
                urls = [url for url in _load_category_urls(category_page, category_url, config.retries) if url not in seen_urls]
                if not urls:
                    empty_pages += 1
                    if empty_pages >= 2:
                        break
                    page_number += 1
                    continue
                empty_pages = 0
                for attempt_number, url in enumerate(urls, start=1):
                    if config.max_books is not None and len(books) >= config.max_books:
                        break
                    seen_urls.add(url)
                    progress(f"  [{attempt_number}/{len(urls)}] START book: {url}")
                    book = extract_book_details(detail_page, url, config.retries)
                    if not book or not book.title:
                        progress(f"  [{attempt_number}/{len(urls)}] FAILED metadata: {url}")
                        continue
                    book.image_file = download_cover(
                        detail_page,
                        book.cover_image,
                        config.download_images / f"{len(books) + 1:06d}",
                        config.request_delay,
                    )
                    books.append(book)
                    cover_status = "cover downloaded" if book.image_file else "cover unavailable"
                    progress(f"  [{attempt_number}/{len(urls)}] DONE #{len(books)}: {book.title} ({cover_status})")
                    save_to_csv(books, config.output)
                    time.sleep(config.request_delay)
                save_to_csv(books, config.output)
                if config.max_books is not None and len(books) >= config.max_books:
                    break
                page_number += 1
        finally:
            context.close()
            browser.close()
    return books
