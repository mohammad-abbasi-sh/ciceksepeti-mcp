"""Live tests for ciceksepeti_mcp — real requests to ciceksepeti.com.

Requires network + Chrome TLS impersonation (curl-cffi). The server is
polite by design (~0.8s between requests), so this file takes ~10s.
Run: python -m unittest discover -s tests -v
"""
import json
import unittest

from ciceksepeti_mcp import http as H
from ciceksepeti_mcp import products as P

KNOWN_PRODUCT = "/ask-sembolu-13-kirmizi-gul-buketi-at4033"


class TestLiveSearch(unittest.TestCase):
    def test_search_gul(self):
        html = H.fetch_search_html("gül")
        rows = P.parse_search_results(html, limit=3)
        self.assertGreaterEqual(len(rows), 1)
        first = rows[0]
        self.assertTrue(first["title"])
        self.assertTrue(first["price_try"] > 0)
        self.assertTrue(first["product_id"])
        self.assertTrue(
            first["url"].startswith("https://www.ciceksepeti.com/")
        )
        self.assertIn("-at", first["url"])

    def test_search_price_asc_order(self):
        html = H.fetch_search_html("gül", sort_param="3")
        rows = P.parse_search_results(html, limit=10)
        self.assertGreaterEqual(len(rows), 2)
        prices = [r["price_try"] for r in rows]
        self.assertEqual(prices, sorted(prices))

    def test_search_price_desc_first_is_max(self):
        html = H.fetch_search_html("gül", sort_param="2")
        rows = P.parse_search_results(html, limit=10)
        self.assertGreaterEqual(len(rows), 2)
        prices = [r["price_try"] for r in rows]
        self.assertEqual(prices[0], max(prices))

    def test_search_page_two_differs(self):
        page1 = P.parse_search_results(H.fetch_search_html("gül"), limit=10)
        page2 = P.parse_search_results(H.fetch_search_html("gül", page=2), limit=10)
        ids1 = {r["product_id"] for r in page1}
        ids2 = {r["product_id"] for r in page2}
        self.assertTrue(ids1)
        self.assertTrue(ids2)
        self.assertFalse(ids1 & ids2)

    def test_search_no_results_shape(self):
        # A nonsense query returns a page; parser must not crash.
        html = H.fetch_search_html("zzzxqqqwwwnonexistent")
        rows = P.parse_search_results(html, limit=5)
        self.assertIsInstance(rows, list)


class TestLiveDetail(unittest.TestCase):
    def test_known_product(self):
        html = H.fetch_product_html(KNOWN_PRODUCT)
        d = P.parse_product_detail(html)
        self.assertIn("Kırmızı Gül Buketi", d["name"])
        self.assertEqual(d["sku"], "at4033")
        self.assertTrue(d["price_try"] > 0)
        self.assertEqual(d["price_currency"], "TRY")
        self.assertIn("Gül", d.get("category", ""))

    def test_known_product_reviews(self):
        html = H.fetch_product_html(KNOWN_PRODUCT)
        reviews = P.parse_reviews(html, limit=3)
        self.assertGreaterEqual(len(reviews), 1)
        self.assertIsNotNone(reviews[0]["rating"])

    def test_bad_product_path(self):
        with self.assertRaises(H.CiceksepetiError):
            H.fetch_product_html("not-a-product-path")


class TestLiveCategoriesAndStats(unittest.TestCase):
    def test_categories(self):
        cats = P.parse_categories(H.fetch_home_html())
        self.assertGreaterEqual(len(cats), 20)
        names = [c["name"] for c in cats]
        self.assertIn("Gül Buketleri", names)

    def test_price_stats(self):
        html = H.fetch_search_html("gül")
        rows = P.parse_search_results(html, limit=10)
        stats = P.price_stats(rows)
        self.assertGreaterEqual(stats["count"], 1)
        self.assertLessEqual(stats["min_try"], stats["median_try"])
        self.assertLessEqual(stats["median_try"], stats["max_try"])


class TestLiveToolsEndToEnd(unittest.TestCase):
    """Exercise the MCP tool functions themselves (they hit the network)."""

    def test_search_tool_json(self):
        from ciceksepeti_mcp.server import ciceksepeti_search

        out = json.loads(ciceksepeti_search("gül", limit=2))
        self.assertEqual(out["query"], "gül")
        self.assertEqual(out["count"], 2)
        self.assertTrue(out["products"][0]["price_try"] > 0)

    def test_stats_tool_json(self):
        from ciceksepeti_mcp.server import ciceksepeti_price_stats

        out = json.loads(ciceksepeti_price_stats("gül", limit=5))
        self.assertGreaterEqual(out["count"], 1)
        self.assertLessEqual(out["min_try"], out["max_try"])

    def test_bad_sort_tool_error_json(self):
        from ciceksepeti_mcp.server import ciceksepeti_search

        out = json.loads(ciceksepeti_search("gül", sort="nope"))
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
