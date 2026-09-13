from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


CSV_FIELDS = [
    "title",
    "author",
    "publisher",
    "product_code",
    "series",
    "isbn",
    "edition_price",
    "sale_price",
    "fixed_book_price",
    "availability",
    "publication_year",
    "page_count",
    "dimensions",
    "release_date",
    "topic",
    "cover_image",
    "description",
    "url",
    "image_file",
]


@dataclass(slots=True)
class Book:
    title: str = ""
    author: str = ""
    publisher: str = ""
    product_code: str = ""
    series: str = ""
    isbn: str = ""
    edition_price: str = ""
    sale_price: str = ""
    fixed_book_price: str = ""
    availability: str = ""
    publication_year: str = ""
    page_count: str = ""
    dimensions: str = ""
    release_date: str = ""
    topic: str = ""
    cover_image: str = ""
    description: str = ""
    url: str = ""
    image_file: str = ""

    def to_row(self) -> dict[str, Any]:
        """Return a stable CSV-shaped mapping."""
        return asdict(self)
