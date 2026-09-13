import csv

from script.export import save_to_csv
from script.models import Book, CSV_FIELDS


def test_save_to_csv_creates_parent_and_writes_all_columns(tmp_path):
    output = tmp_path / "nested" / "books.csv"
    save_to_csv([Book(title="Δοκιμή", url="https://example.test/book")], output)

    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["title"] == "Δοκιμή"
    assert rows[0]["url"] == "https://example.test/book"
    assert list(rows[0]) == CSV_FIELDS
