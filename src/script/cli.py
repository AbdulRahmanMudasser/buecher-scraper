from __future__ import annotations

import argparse
from pathlib import Path

from .crawler import DEFAULT_CATEGORY_URL, ScraperConfig, scrape_politeia


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape book metadata and cover images.")
    parser.add_argument("--category-url", default=DEFAULT_CATEGORY_URL, help="URL template containing {} for the page number")
    parser.add_argument("--output", type=Path, default=Path("data/books.csv"))
    parser.add_argument("--max-pages", type=int, default=None, help="Optional page cap; omitted means continue until pagination ends")
    parser.add_argument("--max-books", type=int, default=None, help="Optional book cap; omitted means scrape all discovered books")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    books = scrape_politeia(ScraperConfig(
        category_url=args.category_url,
        output=args.output,
        max_pages=args.max_pages,
        max_books=args.max_books,
        retries=args.retries,
        request_delay=args.delay,
    ))
    print(f"Completed: {len(books)} books written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
