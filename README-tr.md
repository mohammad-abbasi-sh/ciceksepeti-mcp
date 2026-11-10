# ciceksepeti-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/ciceksepeti-mcp

Türkiye'nin önde gelen çiçek & hediye teslimat pazaryeri
**ciceksepeti.com** için resmi olmayan, **salt okunur** MCP sunucusu —
binlerce buket, bitki ve hediyede arama yapın, ürün detaylarını okuyun
(fiyat, liste fiyatı, stok, puan, satıcı, kategori), müşteri
yorumlarını okuyun, 89 çiçek/bitki/hediye kategorisine göz atın ve
herhangi bir sorgu için fiyat istatistikleri (min / medyan / ortalama /
maks) alın.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı süreç)
> kapsamında geliştirildi. ciceksepeti.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

```json
{
  "mcpServers": {
    "ciceksepeti": {
      "command": "uvx",
      "args": ["ciceksepeti-mcp==0.1.0"]
    }
  }
}
```

veya yerel çalıştırın: `python -m ciceksepeti_mcp.server`
(`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|----------|
| `ciceksepeti_search` | Anahtar kelimeyle çiçek & hediye arama — `query` ("kırmızı gül", "orkide", "doğum günü hediyesi"), `sort` ("relevance" / "price_asc" / "price_desc"), `limit` 1..24, `page` 1'den başlar; başlık, TL fiyat, liste fiyatı, yorum sayısı, yıldız puanı (0-5), teslimat notu, URL, görsel döndürür |
| `ciceksepeti_product_detail` | Bir ürünün detayı (`product` = "-at<id>" ile biten URL veya yol): ad, marka, TL fiyat, stok durumu, puan, yorum sayısı, satıcı, kategori yolu, açıklama, görseller |
| `ciceksepeti_list_categories` | 89 çiçek/bitki/hediye kategorisi: Türkçe ad, URL, slug |
| `ciceksepeti_price_stats` | Bir sorgunun fiyat istatistikleri: adet, min / medyan / ortalama / maks fiyat (TL) |
| `ciceksepeti_product_reviews` | Bir ürünün son müşteri yorumları: yorumcu, yıldız puanı ve tarih (ciceksepeti yorum metinlerini sunucu taraflı işlemez) |

Örnek çıktı (`ciceksepeti_search` / "gül"):

```json
{"query": "gül", "count": 10, "products": [
  {"title": "13'lü Kırmızı Gül Buketi",
   "url": "https://www.ciceksepeti.com/ask-sembolu-13-kirmizi-gul-buketi-at4033",
   "product_id": "4275287", "price_try": 899.99,
   "original_price_try": 1149.0, "review_count": 26946, "rating": 4,
   "delivery": "Aynı Gün Ücretsiz Teslimat"}, …]}
```

## Nasıl çalışır?

ciceksepeti.com düz HTTP istemcilerine yanıt verir; aktarım yine de
Chrome TLS taklidi (`curl-cffi`, `chrome120`) kullanır, böylece daha
katı bir bot kontrolü sunucuyu bozmaz. Herkese açık bir JSON API yoktur
— veriler sitenin sunucu taraflı işlenmiş HTML sayfalarından gelir:
arama sayfaları sayfa başına 30 ürün kutusu (başlık, fiyat, yorum
sayısı, yıldız puanı, teslimat notu), ürün sayfaları schema.org Product
JSON-LD + breadcrumb kategori yolu, ana sayfa ise 89 kategori bağlantısı
taşır. Sıralama URL parametresidir (`orderby=2` pahalıdan ucuza,
`orderby=3` ucuzdan pahalıya — canlı doğrulandı), sayfalama `page=N`
(canlı doğrulandı). İstekler ~0.8 sn arayla yapılır; her şey salt
okunurdur, giriş gerekmez, API anahtarı gerekmez.

## Kurulum

```bash
uvx ciceksepeti-mcp==0.1.0        # doğrudan çalıştır (uv gerekir)
# veya
pip install ciceksepeti-mcp==0.1.0
ciceksepeti-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kayıtlı örnek sayfalarla çalışır (gerçek sayfalar,
2026-11-06); canlı testler ciceksepeti.com'a bağlanır.

## Lisans

MIT — bkz. [LICENSE](LICENSE).
