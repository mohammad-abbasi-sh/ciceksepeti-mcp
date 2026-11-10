# ciceksepeti-mcp 🇹🇷

> ⚠️ **Status: DEGRADED (2026-11-10)** — ciceksepeti.com currently blocks automated access: the connection is reset on chrome120 / chrome131 and refused (HTTP 403) on safari17_0 from this environment. All tools return a clear "blocked" error until the site allows access again. Check `ciceksepeti_health` for the live status.


mcp-name: io.github.mohammad-abbasi-sh/ciceksepeti-mcp

Unofficial **read-only** MCP server for ciceksepeti.com**, Türkiye's leading flower & gift delivery marketplace — search thousands of bouquets, plants and gifts, read product details (price, list price, stock, rating, seller, category), read customer reviews, browse 89 flower/plant/gift categories, and get price statistics (min / median / mean / max) for any query.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with ciceksepeti.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "ciceksepeti": {
      "command": "uvx",
      "args": ["ciceksepeti-mcp==0.1.1"]
    }
  }
}
```

Or run locally: `python -m ciceksepeti_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `ciceksepeti_search` | Search flowers & gifts by keyword — `query` ("kırmızı gül", "orkide", "doğum günü hediyesi"), `sort` ("relevance" / "price_asc" / "price_desc"), `limit` 1..24, `page` 1-based; returns title, price in TRY, list price, review count, star rating (0-5), delivery note, URL, image |
| `ciceksepeti_product_detail` | Detail of one product (`product` = full URL or path ending in "-at<id>"): name, brand, price in TRY, stock status, rating, review count, seller, category path, description, images |
| `ciceksepeti_list_categories` | 89 flower/plant/gift categories: Turkish name, URL, slug |
| `ciceksepeti_price_stats` | Price statistics for a query: count, min / median / mean / max price in TRY across the first page |
| `ciceksepeti_product_reviews` | Recent customer reviews of one product: reviewer, star rating and date (ciceksepeti does not server-render review bodies) |

Example output (`ciceksepeti_search` / "gül"):

```json
{"query": "gül", "sort": "relevance", "page": 1, "count": 10, "products": [
  {"title": "13'lü Kırmızı Gül Buketi",
   "url": "https://www.ciceksepeti.com/ask-sembolu-13-kirmizi-gul-buketi-at4033",
   "product_id": "4275287", "price_try": 899.99,
   "original_price_try": 1149.0, "price_currency": "TRY",
   "review_count": 26946, "rating": 4,
   "delivery": "Aynı Gün Ücretsiz Teslimat",
   "image": "https://cdn03.ciceksepeti.com/…"}, …]}
```

Example output (`ciceksepeti_product_detail` / 13'lü Kırmızı Gül Buketi):

```json
{"name": "13'lü Kırmızı Gül Buketi", "sku": "at4033",
 "brand": "Çiçeksepeti", "price_try": 899.99, "price_currency": "TRY",
 "in_stock": true, "rating": 4.0, "review_count": 26946,
 "seller": "Çiçeksepeti", "category": "Çiçek > Gül", …}
```

Example output (`ciceksepeti_price_stats` / "gül"):

```json
{"query": "gül", "sort": "relevance", "count": 10, "min_try": 479.99,
 "median_try": 884.99, "mean_try": 1097.59, "max_try": 2749.0}
```

## How it works

ciceksepeti.com answers plain HTTP clients, and the transport uses Chrome TLS
impersonation (`curl-cffi`, `chrome120`) so a stricter bot check does not
break the server. There is no public JSON API — data comes from the
site's server-rendered pages: search pages carry 30 product boxes
(title, price, review count, star rating, delivery note), product pages
carry a schema.org Product JSON-LD block plus a breadcrumb category
path, and the homepage carries 89 category links. Sorts are URL params
(`orderby=2` price desc, `orderby=3` price asc, verified live) and
paging is `page=N` (verified live). Requests are spaced ~0.8s apart;
everything is read-only, no login, no API key.

## Install

```bash
uvx ciceksepeti-mcp==0.1.1        # run directly (needs uv)
# or
pip install ciceksepeti-mcp==0.1.1
ciceksepeti-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-06);
live tests hit ciceksepeti.com.

## Roadmap

- Category-scoped search (search within one /d/ category slug)
- Occasion search (birthday, anniversary, Mother's Day collections)
- Price history (track a product over days)

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
