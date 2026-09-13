from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .models import Book

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ISBN_RE = re.compile(r"(?<!\d)(?:97[89](?:[\s-]?\d){10}|\d(?:[\s-]?\d){8}[\s-]?[\dXx])(?!\d)")
PRICE_RE = re.compile(r"(?<!\d)(\d{1,5}(?:[.,]\d{2}))(?:\s*(?:€|�|EUR)|\s*$)")
PRODUCT_PATH_RE = re.compile(r"/(?:el/)?products?/", re.IGNORECASE)


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalize_url(value: str, base_url: str = "") -> str:
    absolute = urljoin(base_url, value.strip())
    parts = urlsplit(absolute)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def extract_isbn(*values: str) -> str:
    for value in values:
        match = ISBN_RE.search(value or "")
        if match:
            compact = re.sub(r"[\s-]", "", match.group(0)).upper()
            if len(compact) == 13:
                return compact
            if len(compact) == 10:
                return compact
    return ""


def _label_value(soup: BeautifulSoup, labels: Iterable[str]) -> str:
    label_patterns = [re.compile(rf"^\s*{label}\s*:?\s*$", re.I) for label in labels]
    for element in soup.find_all(string=True):
        text = clean_text(str(element))
        if not any(pattern.match(text) for pattern in label_patterns):
            continue
        parent = element.parent
        if parent is None:
            continue
        sibling = parent.find_next_sibling()
        if sibling:
            value = clean_text(sibling.get_text(" ", strip=True))
            if value:
                return value
        row = parent.find_parent("tr")
        if row:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                return clean_text(cells[-1].get_text(" ", strip=True))
        text_parent = clean_text(parent.parent.get_text(" ", strip=True) if parent.parent else "")
        remainder = re.sub(rf"^\s*{text}\s*:?\s*", "", text_parent, flags=re.I)
        if remainder:
            return clean_text(remainder)
    return ""


def _body_label_value(body_text: str, labels: Iterable[str]) -> str:
    joined = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{joined})\s*:\s*([^\n|]+)", body_text, re.I)
    return clean_text(match.group(1)) if match else ""


def _first_meta(soup: BeautifulSoup, *keys: str) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return clean_text(tag["content"])
    return ""


def _selector_text(soup: BeautifulSoup, selectors: str) -> str:
    element = soup.select_one(selectors)
    return clean_text(element.get_text(" ", strip=True) if element else "")


def _json_ld_book(soup: BeautifulSoup) -> dict[str, object]:
    """Return the site's Schema.org Book data when it is present."""
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if isinstance(candidate, dict) and (
                candidate.get("@type") == "Book"
                or "numberOfPages" in candidate
            ):
                return candidate
    return {}


def _preloaded_entity(soup: BeautifulSoup) -> dict[str, object]:
    """Read the product object embedded by the current Politeia frontend."""
    script = soup.find("script", id="bw-preloaded-data")
    if script is None:
        return {}
    raw = script.string or script.get_text()
    marker = "__BW_PRELOADED_DATA__"
    start = raw.find("{", raw.find(marker))
    if start < 0:
        return {}
    try:
        data, _ = json.JSONDecoder().raw_decode(raw[start:])
    except (TypeError, json.JSONDecodeError):
        return {}
    entity = data.get("entityToken") if isinstance(data, dict) else None
    return entity if isinstance(entity, dict) else {}


def _preloaded_attribute(entity: dict[str, object], names: Iterable[str]) -> str:
    attributes = entity.get("atrlst")
    if not isinstance(attributes, list):
        return ""
    wanted = {name.casefold() for name in names}
    for attribute in attributes:
        if not isinstance(attribute, dict):
            continue
        if clean_text(str(attribute.get("anm", ""))).casefold() not in wanted:
            continue
        for key in ("vtxt", "tval", "aitxt"):
            value = clean_text(str(attribute.get(key) or ""))
            if value:
                return value
    return ""


def _preloaded_topics(entity: dict[str, object]) -> str:
    categories = entity.get("cnm")
    if isinstance(categories, str) and categories.strip():
        return clean_text(categories)
    category_items = entity.get("prd_cat_items")
    if isinstance(category_items, list):
        names = [
            clean_text(str(item.get("Name", "")))
            for item in category_items
            if isinstance(item, dict) and item.get("Name")
        ]
        return ",".join(name for name in names if name)
    return ""


def _preloaded_dimensions(entity: dict[str, object]) -> str:
    size = entity.get("size")
    if isinstance(size, str) and size.strip():
        return clean_text(size)
    dimensions = entity.get("dimensions")
    if isinstance(dimensions, str):
        return clean_text(dimensions)
    if isinstance(dimensions, list):
        values = [clean_text(str(value)) for value in dimensions if value]
        return " x ".join(value for value in values if value)
    return ""


def _image_candidates(soup: BeautifulSoup, base_url: str) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for tag in soup.find_all(["meta", "a", "img", "source"]):
        values: list[str] = []
        if tag.name == "meta":
            if tag.get("content"):
                values.append(tag["content"])
        else:
            for attr in ("data-large-image", "data-original", "data-zoom-image", "data-src", "href", "src"):
                if tag.get(attr):
                    values.append(tag[attr])
            if tag.get("srcset"):
                values.extend(item.strip().split(" ")[0] for item in tag["srcset"].split(","))
        for value in values:
            url = normalize_url(value, base_url)
            path = urlsplit(url).path.lower()
            if not url.startswith(("http://", "https://")) or not re.search(r"\.(?:jpe?g|png|webp)(?:$|\?)", path):
                continue
            score = 0
            context = " ".join([str(tag.get("class", "")), str(tag.get("id", "")), value]).lower()
            if tag.name == "meta" and tag.get("property") == "og:image":
                score += 30
            if any(word in context for word in ("zoom", "large", "original", "cover", "product", "main")):
                score += 20
            if any(word in context for word in ("thumb", "small", "logo", "social")):
                score -= 20
            dimensions = re.findall(r"\d{3,4}", value)
            score += min(sum(map(int, dimensions)), 4000) // 100 if dimensions else 0
            candidates.append((score, url))
    return [url for _, url in sorted(set(candidates), reverse=True)]


def parse_book_html(content: str, book_url: str, visible_text: str = "") -> Book:
    """Extract a book without browser APIs, tolerating missing fields."""
    soup = BeautifulSoup(content, "html.parser")
    json_ld = _json_ld_book(soup)
    entity = _preloaded_entity(soup)
    body_text = soup.get_text("\n", strip=True)
    if visible_text and visible_text not in body_text:
        body_text = f"{body_text}\n{visible_text}"
    title_tag = soup.find("h1") or soup.select_one(".product-name, [itemprop='name']")
    title = clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")
    author_data = json_ld.get("author")
    author_from_data = author_data.get("name", "") if isinstance(author_data, dict) else author_data
    author = (
        _selector_text(soup, ".author, .product-author, [class*='author']")
        or _label_value(soup, ("Συγγραφέας", "Author"))
        or _body_label_value(body_text, ("Συγγραφέας", "Author"))
        or clean_text(str(author_from_data or ""))
    )
    if author and title.lower().endswith(f" - {author}".lower()):
        title = title[: -(len(author) + 3)].rstrip(" -")
    publisher_data = json_ld.get("publisher")
    publisher_from_data = publisher_data.get("name", "") if isinstance(publisher_data, dict) else publisher_data
    publisher = (
        _label_value(soup, ("Εκδότης", "Publisher"))
        or _body_label_value(body_text, ("Εκδότης", "Publisher"))
        or clean_text(str(publisher_from_data or ""))
    )
    pages = (
        _label_value(soup, ("Αριθμός σελίδων", "Σελίδες", "Pages"))
        or _body_label_value(body_text, ("Αριθμός σελίδων", "Σελίδες", "Pages"))
        or _preloaded_attribute(entity, ("Αριθμός Σελίδων", "Σελίδες", "Pages"))
        or clean_text(str(entity.get("pieces") or json_ld.get("numberOfPages") or ""))
    )
    dimensions = (
        _label_value(soup, ("Διαστάσεις", "Dimensions"))
        or _body_label_value(body_text, ("Διαστάσεις", "Dimensions"))
        or _preloaded_dimensions(entity)
    )
    release_date = (
        _label_value(soup, ("Ημερομηνία έκδοσης", "Publication date", "Release date"))
        or _body_label_value(body_text, ("Ημερομηνία έκδοσης", "Publication date", "Release date"))
        or clean_text(str(entity.get("release") or entity.get("publish_date") or ""))
    )
    topic = (
        _label_value(soup, ("Θέμα", "Topic", "Subject"))
        or _body_label_value(body_text, ("Θέμα", "Topic", "Subject"))
        or _preloaded_topics(entity)
    )
    def parse_price(source: str) -> str:
        match = PRICE_RE.search(source)
        return match.group(1).replace(",", ".") if match else ""

    edition_price = parse_price(_selector_text(soup, ".starting-price .formatted-price"))
    sale_price = parse_price(_selector_text(soup, ".final-price .formatted-price"))
    if not edition_price and not sale_price:
        price_source = _label_value(soup, ("Τιμή", "Price")) or body_text
        sale_price = parse_price(price_source)
    availability_text = _selector_text(soup, ".availability-container, .status") or body_text
    availability = "Εξαντλημένο" if any(value in availability_text for value in ("Εξαντλημένο", "Μη διαθέσιμο", "Out of stock")) else ""
    if not availability and "Άμεσα διαθέσιμο" in availability_text:
        availability = "Άμεσα διαθέσιμο"
    if not availability and "Διαθέσιμο" in availability_text:
        availability = "Διαθέσιμο"
    if not availability and "Available" in availability_text:
        availability = "Available"
    description_tag = soup.select_one("#product-description, .product-description, .description, [itemprop='description']")
    description = clean_text(
        description_tag.get_text(" ", strip=True)
        if description_tag
        else _first_meta(soup, "og:description", "description")
        or str(json_ld.get("description") or entity.get("dsm") or "")
    )
    candidates = _image_candidates(soup, book_url)
    image_data = json_ld.get("image") or entity.get("img1") or ""
    image_url = candidates[0] if candidates else normalize_url(str(image_data or _first_meta(soup, "og:image")), book_url)
    isbn = clean_text(str(json_ld.get("isbn") or entity.get("bc") or entity.get("barcodes") or ""))
    if not isbn:
        isbn = extract_isbn(book_url, body_text)
    series = (
        _body_label_value(body_text, ("Σειρά", "Series"))
        or _label_value(soup, ("Σειρά", "Series"))
        or _preloaded_attribute(entity, ("Σειρά", "Series"))
    )
    date_year = YEAR_RE.search(release_date)
    return Book(
        title=title,
        author=author,
        publisher=publisher,
        product_code=_body_label_value(body_text, ("Κωδ. Πολιτείας", "Κωδικός Πολιτείας", "Product code")),
        series=series,
        isbn=isbn,
        edition_price=edition_price,
        sale_price=sale_price,
        fixed_book_price=sale_price or edition_price,
        availability=availability,
        publication_year=date_year.group(0) if date_year else "",
        page_count=pages,
        dimensions=dimensions,
        release_date=release_date,
        topic=topic,
        cover_image=image_url,
        description=description,
        url=normalize_url(book_url),
    )


def extract_product_urls(content: str, base_url: str) -> list[str]:
    """Return unique product links in document order."""
    soup = BeautifulSoup(content, "html.parser")
    result: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        url = normalize_url(anchor["href"], base_url)
        if PRODUCT_PATH_RE.search(url) and url not in seen:
            seen.add(url)
            result.append(url)
    return result
