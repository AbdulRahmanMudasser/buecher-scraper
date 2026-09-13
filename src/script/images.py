from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page


def download_cover(page: Page, image_url: str, destination: Path, delay: float = 0.0) -> str:
    """Download an image through the browser session and return its file path."""
    if not image_url:
        return ""
    if delay:
        time.sleep(delay)
    try:
        response = page.request.get(image_url, timeout=30_000)
        if not response.ok:
            return ""
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        extension = mimetypes.guess_extension(content_type) or Path(urlsplit(image_url).path).suffix or ".jpg"
        if extension.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            extension = ".jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = destination.with_suffix(extension)
        target.write_bytes(response.body())
        return str(target)
    except Exception:
        return ""
