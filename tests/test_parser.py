from script.parser import extract_isbn, extract_product_urls, parse_book_html


BOOK_HTML = """
<html><head>
  <meta property="og:image" content="/images/book-original.jpg">
  <meta property="og:description" content="A short description.">
</head><body>
  <h1> Το βιβλίο της δοκιμής </h1>
  <table>
    <tr><th>Συγγραφέας</th><td>Άννα Παπαδοπούλου</td></tr>
    <tr><th>Εκδότης</th><td>Δοκιμαστικές Εκδόσεις</td></tr>
    <tr><th>Σειρά</th><td>Μικρή σειρά</td></tr>
    <tr><th>Σελίδες</th><td>320</td></tr>
    <tr><th>Ημερομηνία έκδοσης</th><td>12/03/2024</td></tr>
  </table>
  <div class="product-price">Κωδ. Πολιτείας: 1234-5678</div>
  <div class="product-price">Τιμή: 19,90 €</div>
  <div class="description">Αναλυτική περιγραφή του βιβλίου.</div>
  <div>Άμεσα διαθέσιμο</div>
</body></html>
"""


def test_parse_book_html_extracts_metadata_and_normalizes_values():
    book = parse_book_html(BOOK_HTML, "https://example.test/el/products/book-9781234567890")

    assert book.title == "Το βιβλίο της δοκιμής"
    assert book.author == "Άννα Παπαδοπούλου"
    assert book.publisher == "Δοκιμαστικές Εκδόσεις"
    assert book.series == "Μικρή σειρά"
    assert book.product_code == "1234-5678"
    assert book.page_count == "320"
    assert book.fixed_book_price == "19.90"
    assert book.sale_price == "19.90"
    assert book.publication_year == "2024"
    assert book.availability == "Άμεσα διαθέσιμο"
    assert book.cover_image == "https://example.test/images/book-original.jpg"
    assert book.isbn == "9781234567890"


def test_parser_tolerates_missing_optional_fields_and_uses_image_fallback():
    html = '<h1>Minimal</h1><img class="product-main-image" src="/cover-large.jpg">'
    book = parse_book_html(html, "https://example.test/products/minimal")

    assert book.title == "Minimal"
    assert book.cover_image == "https://example.test/cover-large.jpg"
    assert book.author == ""
    assert book.description == ""


def test_parse_current_politeia_detail_markup_uses_author_price_and_status_classes():
    html = """
    <h1>Current title</h1>
    <h2 class="author"><a>AUTHOR NAME</a></h2>
    <div class="final-price"><span class="formatted-price">21.96�</span></div>
    <div class="availability-container"><div class="status available">Διαθέσιμο</div></div>
    """
    book = parse_book_html(html, "https://example.test/el/products/current")

    assert book.author == "AUTHOR NAME"
    assert book.fixed_book_price == "21.96"
    assert book.availability == "Διαθέσιμο"


def test_extract_product_urls_deduplicates_and_discards_non_products():
    html = """
    <a href="/el/products/one?utm_source=x">One</a>
    <a href="https://example.test/el/products/one#details">Again</a>
    <a href="/categories/other">Other</a>
    <a href="/products/two/">Two</a>
    """
    assert extract_product_urls(html, "https://example.test/el/categories/books?page=1") == [
        "https://example.test/el/products/one",
        "https://example.test/products/two",
    ]


def test_extract_isbn_accepts_hyphenated_isbn13_and_isbn10():
    assert extract_isbn("ISBN 978-1-2345-6789-0") == "9781234567890"
    assert extract_isbn("ISBN 0-123-45678-X") == "012345678X"
