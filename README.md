# Books scraper

This project scrapes book records from Politeia category pages, downloads each
available cover automatically, and exports a UTF-8 CSV. It has no built-in
book or page limit.

## Setup (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

## Run

The default category is the one from the supplied script. Start with a small
run to verify access and selectors:

```powershell
.\.venv\Scripts\python.exe -m script --max-pages 1 --max-books 5
```

Run the full category without those caps:

```powershell
.\.venv\Scripts\python.exe -m script
```

Cover downloads are automatic and are stored in `data\covers`; the CSV also
contains the source URL and local image path. Respect the source site's terms,
robots guidance, and rate limits when running a large crawl.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The parser tests use saved HTML-shaped fixtures and do not require a browser
or network connection. Browser crawling is kept in `crawler.py` so it can be
run separately from deterministic extraction and CSV tests.
