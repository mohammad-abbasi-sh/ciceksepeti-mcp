"""MCP server: unofficial read-only access to ciceksepeti.com flowers & gifts."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import products as _P

mcp = FastMCP("ciceksepeti-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for ciceksepeti.com, Türkiye's leading
flower & gift delivery marketplace. Data comes from the site's public
server-rendered pages: search pages carry 30 product boxes each
(title, price in TRY, list price, review count, integer star rating
0-5, same-day delivery note, image), product pages carry a schema.org
Product JSON-LD block (price, rating, review count, reviews, images)
plus a breadcrumb category path, and the homepage carries 89 category
links (flowers, plants, gifts). Product URLs look like
"/ask-sembolu-13-kirmizi-gul-buketi-at4033" (the trailing "-at<id>"
is the product id; use ciceksepeti_search to find product URLs).
Prices are in Turkish Lira (TRY) unless noted. Search sorts:
relevance (default, recommended order), price_asc (cheapest first),
price_desc (most expensive first). Read-only, no login, no API key.
Transport uses Chrome TLS impersonation; the server spaces requests
~0.8s apart. Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey
MCP factory.\
"""


def _err(e: Exception) -> str:
    return json.dumps({"error": str(e)}, ensure_ascii=False)


def _validate_limit(limit: int) -> int:
    if not 1 <= limit <= 24:
        raise ValueError("limit must be between 1 and 24")
    return limit


@mcp.tool()
def ciceksepeti_search(query: str, limit: int = 10, sort: str = "relevance", page: int = 1) -> str:
    """Search ciceksepeti.com flowers & gifts by keyword. query: Turkish
    or ASCII, e.g. "kırmızı gül", "orkide", "doğum günü hediyesi".
    sort: "relevance" (default), "price_asc" (cheapest first),
    "price_desc" (most expensive first). limit 1..24; page 1-based.
    Returns title, price in TRY, list price, review count, star rating
    (0-5), delivery note, product URL and image per product."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit)
        if page < 1:
            raise ValueError("page must be >= 1")
        sort_param = _P.resolve_sort(sort)
        html = _http.fetch_search_html(query.strip(), sort_param=sort_param, page=page)
        rows = _P.parse_search_results(html, limit=limit)
    except (ValueError, _http.CiceksepetiError) as e:
        return _err(e)
    return json.dumps(
        {"query": query.strip(), "sort": sort, "page": page,
         "count": len(rows), "products": rows},
        ensure_ascii=False,
    )


@mcp.tool()
def ciceksepeti_product_detail(product: str) -> str:
    """Detail of one product: name, brand, price in TRY, stock status,
    rating and review count, seller, category path, description, images.
    product: a full product URL or site path ending in "-at<id>" (find
    one with ciceksepeti_search first), e.g.
    "/ask-sembolu-13-kirmizi-gul-buketi-at4033"."""
    try:
        html = _http.fetch_product_html(product)
        detail = _P.parse_product_detail(html)
    except (ValueError, _http.CiceksepetiError) as e:
        return _err(e)
    return json.dumps(detail, ensure_ascii=False)


@mcp.tool()
def ciceksepeti_list_categories() -> str:
    """Categories of ciceksepeti.com (89 flower/plant/gift categories):
    Turkish name, category URL and slug."""
    try:
        html = _http.fetch_home_html()
        cats = _P.parse_categories(html)
    except _http.CiceksepetiError as e:
        return _err(e)
    return json.dumps({"count": len(cats), "categories": cats}, ensure_ascii=False)


@mcp.tool()
def ciceksepeti_price_stats(query: str, limit: int = 24, sort: str = "relevance") -> str:
    """Price statistics for a search query: product count, min / median /
    mean / max price in TRY across the first page of results.
    query: e.g. "kırmızı gül"; limit 1..24 (default 24)."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit)
        sort_param = _P.resolve_sort(sort)
        html = _http.fetch_search_html(query.strip(), sort_param=sort_param)
        rows = _P.parse_search_results(html, limit=limit)
        stats = _P.price_stats(rows)
    except (ValueError, _http.CiceksepetiError) as e:
        return _err(e)
    return json.dumps(
        {"query": query.strip(), "sort": sort, **stats}, ensure_ascii=False
    )


@mcp.tool()
def ciceksepeti_product_reviews(product: str, limit: int = 5) -> str:
    """Recent customer reviews of one product: reviewer, star rating and
    date. (ciceksepeti does not server-render review bodies, so only
    author + rating + date are returned.) product: a full product URL
    or site path ending in "-at<id>" (find one with ciceksepeti_search
    first). limit 1..24."""
    try:
        _validate_limit(limit)
        html = _http.fetch_product_html(product)
        reviews = _P.parse_reviews(html, limit=limit)
    except (ValueError, _http.CiceksepetiError) as e:
        return _err(e)
    return json.dumps(
        {"product": product, "count": len(reviews), "reviews": reviews},
        ensure_ascii=False,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
