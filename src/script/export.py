from __future__ import annotations

import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .models import CSV_FIELDS, Book


def save_to_csv(books: list[Book], filename: str | Path) -> None:
    """Write a complete, Excel-compatible UTF-8 CSV atomically."""
    if not books:
        return
    destination = Path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8-sig", dir=destination.parent, delete=False) as temp:
        writer = csv.DictWriter(temp, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(book.to_row() for book in books)
        temp_path = Path(temp.name)
    os.replace(temp_path, destination)
