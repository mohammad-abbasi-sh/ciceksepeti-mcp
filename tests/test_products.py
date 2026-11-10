"""Offline tests for ciceksepeti_mcp.products — recorded real pages.

Fixtures are trimmed excerpts of real ciceksepeti.com pages fetched
2026-11-06 (search "gül", the 13'lü Kırmızı Gül Buketi product page,
homepage category links).
"""
import asyncio
import os
import unittest

from ciceksepeti_mcp import products as P

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class TestTrNumbers(unittest.TestCase):
    def test_price_formats(self):
        self.assertEqual(P.parse_tr_number("899,99 TL"), 899.99)
        self.assertEqual(P.parse_tr_number("1.149 TL"), 1149.0)
        self.assertEqual(P.parse_tr_number("13.498 TL"), 13498.0)
        self.assertEqual(P.parse_tr_number("479,99 TL"), 479.99)
        self.assertEqual(P.parse_tr_number("599"), 599.0)

    def test_bad_number(self):
        with self.assertRaises(ValueError):
            P.parse_tr_number("abc")


class TestSearchParse(unittest.TestCase):
    def setUp(self):
        self.html = _read("search-gul.html")

    def test_ten_products_limited(self):
        rows = P.parse_search_results(self.html, limit=10)
        self.assertEqual(len(rows), 10)

    def test_first_product(self):
        rows = P.parse_search_results(self.html, limit=10)
        first = rows[0]
        self.assertEqual(first["title"], "13'lü Kırmızı Gül Buketi")
        self.assertEqual(first["product_id"], "4275287")
        self.assertEqual(
            first["url"],
            "https://www.ciceksepeti.com/ask-sembolu-13-kirmizi-gul-buketi-at4033",
        )
        self.assertEqual(first["price_try"], 899.99)
        self.assertEqual(first["original_price_try"], 1149.0)
        self.assertEqual(first["price_currency"], "TRY")
        self.assertEqual(first["review_count"], 26946)
        self.assertEqual(first["rating"], 4)
        self.assertEqual(first["delivery"], "Aynı Gün Ücretsiz Teslimat")
        self.assertTrue(first["image"].startswith("https://cdn03.ciceksepeti.com/"))

    def test_second_product(self):
        rows = P.parse_search_results(self.html, limit=10)
        self.assertEqual(rows[1]["price_try"], 1249.0)

    def test_limit(self):
        self.assertEqual(len(P.parse_search_results(self.html, limit=2)), 2)

    def test_empty_html(self):
        self.assertEqual(P.parse_search_results("<html></html>"), [])

    def test_price_stats(self):
        rows = P.parse_search_results(self.html, limit=10)
        stats = P.price_stats(rows)
        self.assertEqual(stats["count"], 10)
        self.assertEqual(stats["min_try"], 479.99)
        self.assertEqual(stats["median_try"], 884.99)
        self.assertEqual(stats["mean_try"], 1097.59)
        self.assertEqual(stats["max_try"], 2749.0)

    def test_price_stats_empty(self):
        self.assertEqual(P.price_stats([]), {"count": 0})


class TestDetailParse(unittest.TestCase):
    def setUp(self):
        self.html = _read("product-gul.html")

    def test_core_fields(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(d["name"], "13'lü Kırmızı Gül Buketi")
        self.assertEqual(d["sku"], "at4033")
        self.assertEqual(d["brand"], "Çiçeksepeti")
        self.assertEqual(d["price_try"], 899.99)
        self.assertEqual(d["price_currency"], "TRY")
        self.assertTrue(d["in_stock"])
        self.assertEqual(d["rating"], 4.0)
        self.assertEqual(d["review_count"], 26946)
        self.assertEqual(d["seller"], "Çiçeksepeti")

    def test_category(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(d["category"], "Çiçek > Gül")

    def test_images(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(len(d["images"]), 5)
        self.assertTrue(d["images"][0].startswith("https://cdn03.ciceksepeti.com/"))

    def test_description(self):
        d = P.parse_product_detail(self.html)
        self.assertTrue(d["description"].startswith("Ürün Yüksekliği: 30-40 cm"))

    def test_no_product_raises(self):
        with self.assertRaises(ValueError):
            P.parse_product_detail("<html><body>no json-ld here</body></html>")


class TestReviewsParse(unittest.TestCase):
    def test_reviews(self):
        reviews = P.parse_reviews(_read("product-gul.html"), limit=5)
        self.assertEqual(len(reviews), 5)
        self.assertEqual(reviews[0]["author"], "M*** S***")
        self.assertEqual(reviews[0]["rating"], 5.0)
        self.assertEqual(reviews[0]["date"], "2026-11-06")
        self.assertEqual(reviews[3]["rating"], 1.0)

    def test_limit(self):
        html = _read("product-gul.html")
        self.assertEqual(len(P.parse_reviews(html, limit=1)), 1)

    def test_no_reviews(self):
        self.assertEqual(P.parse_reviews("<html></html>"), [])


class TestCategoriesParse(unittest.TestCase):
    def test_twenty_categories(self):
        cats = P.parse_categories(_read("home-categories.html"))
        self.assertEqual(len(cats), 20)
        self.assertEqual(cats[0]["name"], "Öğretmenler Günü")
        self.assertEqual(
            cats[0]["url"],
            "https://www.ciceksepeti.com/d/ogretmenler-gunu-cicekleri",
        )
        self.assertEqual(cats[0]["slug"], "ogretmenler-gunu-cicekleri")
        self.assertEqual(cats[1]["name"], "Kasımpatı")
        self.assertEqual(cats[-1]["name"], "Atatürk Çiçeği - Ponsetya")

    def test_empty(self):
        self.assertEqual(P.parse_categories("<html></html>"), [])


class TestSorts(unittest.TestCase):
    def test_resolve(self):
        self.assertIsNone(P.resolve_sort("relevance"))
        self.assertEqual(P.resolve_sort("price_asc"), "3")
        self.assertEqual(P.resolve_sort("price_desc"), "2")

    def test_unknown_sort(self):
        with self.assertRaises(ValueError):
            P.resolve_sort("bogus")


class TestServerToolsRegistered(unittest.TestCase):
    def test_tools_registered(self):
        from ciceksepeti_mcp.server import mcp

        tools = asyncio.run(mcp.list_tools())
        names = sorted(t.name for t in tools)
        self.assertEqual(
            names,
            [
                "ciceksepeti_health",
                "ciceksepeti_list_categories",
                "ciceksepeti_price_stats",
                "ciceksepeti_product_detail",
                "ciceksepeti_product_reviews",
                "ciceksepeti_search",
            ],
        )


if __name__ == "__main__":
    unittest.main()
