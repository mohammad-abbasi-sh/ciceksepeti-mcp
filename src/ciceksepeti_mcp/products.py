"""Stdlib parsing for ciceksepeti.com server-rendered pages.

Verified live 2026-11-06 against real pages:
- Search (/arama?query=…&qt=…): 30 product boxes per page, each an
  <a data-cs-product-box="true" data-product-id="…"> with img alt (title),
  data-cs-pb-name (title), data-cs-pb-review-count "(26946)", first price
  data-cs-pb-first-price-text ("1.149 TL"), final price
  data-cs-pb-price-text ("899,99 TL"), delivery text and a 5-star rating
  (filled stars carry data-cs-fill-icon="true", integer 0-5). Sort
  params orderby=3 (Ucuzdan Pahalıya, prices ascend) / orderby=2
  (Pahalıdan Ucuza, first price is max) verified live; paging page=N
  verified live (page 2 returns different product ids).
- Product page (/<slug>-at<id>): a schema.org Product JSON-LD block
  (name, brand, sku, description, image, offers with price / currency /
  availability / seller Organization, aggregateRating, review list with
  author + rating + date — no review bodies) plus a BreadcrumbList
  (category path).
- Homepage: 89 category links href="/d/<slug>" (flowers, plants, gifts).
"""
from __future__ import annotations

import html as _html
import json
import re
import statistics

BASE = "https://www.ciceksepeti.com"

SORTS = {
    "relevance": None,       # site default (Önerilen Sıralama)
    "price_asc": "3",        # Ucuzdan Pahalıya — verified live: prices ascend
    "price_desc": "2",       # Pahalıdan Ucuza — verified live: first price is max
}


def resolve_sort(sort: str) -> str | None:
    if sort not in SORTS:
        raise ValueError(
            f"unknown sort {sort!r} (expected one of: {', '.join(SORTS)})"
        )
    return SORTS[sort]


def parse_tr_number(text: str) -> float:
    """Turkish price text: '899,99 TL' -> 899.99, '1.149 TL' -> 1149.0,
    '13.498 TL' -> 13498.0."""
    s = text.strip().replace("\u00a0", "").replace(" ", "")
    s = s.replace("TL", "").replace("₺", "")
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def _ldjson_docs(html: str) -> list:
    docs = []
    for m in re.finditer(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        try:
            docs.append(json.loads(m.group(1)))
        except (json.JSONDecodeError, ValueError):
            continue
    return docs


def _walk(obj):
    """Yield every dict inside a parsed JSON document."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _find_typed(html: str, type_name: str) -> dict | None:
    for doc in _ldjson_docs(html):
        for node in _walk(doc):
            if node.get("@type") == type_name:
                return node
    return None


# ---------------------------------------------------------------- search

_BOX_START = re.compile(r'<a[^>]*data-cs-product-box="true"[^>]*>', re.S)
_NAME_RE = re.compile(r'data-cs-pb-name="true"[^>]*>([^<]+)<')
_REVIEW_RE = re.compile(r'data-cs-pb-review-count="true"[^>]*>\(?([\d.]+)\)?')
_FIRST_PRICE_RE = re.compile(r'data-cs-pb-first-price-text="true"[^>]*>([^<]+)<')
_PRICE_RE = re.compile(r'data-cs-pb-price-text="true"[^>]*>([^<]+)<')
_DELIVERY_RE = re.compile(r'data-cs-pb-delivery-info-text="true"[^>]*>([^<]+)<')
_IMG_RE = re.compile(r'data-cs-pb-image="true" alt="([^"]+)"')


def _box_segments(html: str) -> list[str]:
    """Split the search page into per-product box segments."""
    starts = [m.start() for m in _BOX_START.finditer(html)]
    if not starts:
        return []
    starts.append(len(html))
    return [html[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]


def parse_search_results(html: str, limit: int = 10) -> list[dict]:
    """Parse the search-page product boxes. Returns de-duplicated products."""
    out: list[dict] = []
    seen: set[str] = set()
    for seg in _box_segments(html):
        tag = _BOX_START.search(seg)
        if not tag:
            continue
        href_m = re.search(r'href="([^"]+)"', tag.group(0))
        id_m = re.search(r'data-product-id="(\d+)"', tag.group(0))
        if not href_m or not id_m:
            continue
        pid = id_m.group(1)
        if pid in seen:
            continue
        name_m = _NAME_RE.search(seg)
        price_m = _PRICE_RE.search(seg)
        if not name_m or not price_m:
            continue
        try:
            price_try = parse_tr_number(price_m.group(1))
        except ValueError:
            continue
        seen.add(pid)
        row: dict = {
            "title": _clean(name_m.group(1)),
            "url": BASE + href_m.group(1),
            "product_id": pid,
            "price_try": price_try,
            "price_currency": "TRY",
        }
        first_m = _FIRST_PRICE_RE.search(seg)
        if first_m:
            try:
                first = parse_tr_number(first_m.group(1))
                if first != price_try:
                    row["original_price_try"] = first
            except ValueError:
                pass
        rev_m = _REVIEW_RE.search(seg)
        if rev_m:
            try:
                row["review_count"] = int(rev_m.group(1).replace(".", ""))
            except ValueError:
                pass
        fills = seg.count('data-cs-fill-icon="true"')
        stars = seg.count('data-cs-star-icon="true"')
        if stars:
            row["rating"] = fills  # integer 0..5
        deliv_m = _DELIVERY_RE.search(seg)
        if deliv_m:
            row["delivery"] = _clean(deliv_m.group(1))
        img_m = _IMG_RE.search(seg)
        if img_m:
            src_m = re.search(r'data-cs-pb-image="true"[^>]*src="([^"]+)"', seg)
            if src_m:
                row["image"] = src_m.group(1)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def price_stats(products: list[dict]) -> dict:
    prices = sorted(p["price_try"] for p in products if p.get("price_try") is not None)
    if not prices:
        return {"count": 0}
    return {
        "count": len(prices),
        "min_try": prices[0],
        "median_try": round(statistics.median(prices), 2),
        "mean_try": round(sum(prices) / len(prices), 2),
        "max_try": prices[-1],
    }


# ---------------------------------------------------------------- detail

def parse_product_detail(html: str) -> dict:
    product = _find_typed(html, "Product")
    if not product:
        raise ValueError("no schema.org Product data found on this page")
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    rating = product.get("aggregateRating") or {}
    brand = product.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    price = offers.get("price")
    try:
        price_try = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_try = None
    availability = str(offers.get("availability") or "")
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
    seller = offers.get("seller") or {}
    if isinstance(seller, dict):
        seller_name = seller.get("name")
    else:
        seller_name = None
    detail: dict = {
        "name": product.get("name"),
        "sku": str(product.get("sku")) if product.get("sku") is not None else None,
        "brand": brand,
        "description": product.get("description"),
        "price_try": price_try,
        "price_currency": offers.get("priceCurrency") or "TRY",
        "in_stock": ("InStock" in availability) if availability else None,
        "rating": (
            float(rating.get("ratingValue"))
            if rating.get("ratingValue") is not None
            else None
        ),
        "review_count": (
            int(str(rating.get("reviewCount") or 0).replace(".", ""))
            if rating.get("reviewCount") is not None
            else None
        ),
        "seller": seller_name,
        "images": images[:5],
        "url": offers.get("url"),
    }
    # Category path from the BreadcrumbList (skip site root + product name).
    crumb = _find_typed(html, "BreadcrumbList")
    if crumb:
        names = [
            (el.get("item") or {}).get("name")
            for el in (crumb.get("itemListElement") or [])
            if isinstance(el.get("item"), dict)
        ]
        names = [n for n in names if n]
        if len(names) > 2:
            detail["category"] = " > ".join(names[1:-1])
    return {k: v for k, v in detail.items() if v is not None}


def parse_reviews(html: str, limit: int = 5) -> list[dict]:
    """Reviews from the Product JSON-LD (author + star rating + date;
    ciceksepeti does not server-render review bodies)."""
    product = _find_typed(html, "Product")
    if not product:
        return []
    out: list[dict] = []
    for node in product.get("review") or []:
        if not isinstance(node, dict):
            continue
        author = node.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        rr = node.get("reviewRating") or {}
        out.append(
            {
                "author": author,
                "rating": (
                    float(rr.get("ratingValue"))
                    if rr.get("ratingValue") is not None
                    else None
                ),
                "date": node.get("datePublished"),
            }
        )
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- categories

_CAT_RE = re.compile(r'<a[^>]*href="(/d/[^"]+)"[^>]*>([^<]{2,60})</a>')


def parse_categories(html: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for m in _CAT_RE.finditer(html):
        path, name = m.group(1), _clean(m.group(2))
        if not name or path in seen:
            continue
        seen.add(path)
        out.append(
            {
                "name": name,
                "url": BASE + path,
                "slug": path.strip("/").removeprefix("d/"),
            }
        )
    return out
