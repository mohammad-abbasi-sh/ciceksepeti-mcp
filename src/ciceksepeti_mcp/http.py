"""HTTP layer for ciceksepeti_mcp.

ciceksepeti.com answers HTTP 200 to plain HTTP clients with a browser UA
(verified live 2026-11-06: homepage, search, product pages). The
transport still uses curl-cffi chrome120 impersonation, the same proven
pattern as the other Turkey-factory servers, so a stricter bot check
does not break the server overnight. Requests are kept gentle (one at
a time, ~0.8s apart) and read-only.
"""
from __future__ import annotations

import time
from urllib.parse import quote_plus, urlparse

from curl_cffi import requests as _r

BASE = "https://www.ciceksepeti.com"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class CiceksepetiError(RuntimeError):
    pass


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport. Added 2026-11-10 (fleet audit fix).
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _r.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise CiceksepetiError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise CiceksepetiError(f"network error fetching {url}: {last_exc}") from last_exc


def _get(url: str) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _request(url, _HEADERS)
    except CiceksepetiError:
        raise
    except Exception as e:
        raise CiceksepetiError(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise CiceksepetiError(
            "ciceksepeti.com refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise CiceksepetiError(
            "ciceksepeti.com rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code == 404:
        raise CiceksepetiError(f"page not found (HTTP 404): {url}")
    if resp.status_code != 200:
        raise CiceksepetiError(f"unexpected HTTP {resp.status_code} fetching {url}")
    return resp.text


def fetch_search_html(query: str, sort_param: str | None = None, page: int = 1) -> str:
    """Search page HTML. sort_param: '2' (price desc) or '3' (price asc);
    default (None) is the site's recommended order."""
    url = f"{BASE}/arama?query={quote_plus(query)}&qt={quote_plus(query)}"
    if sort_param:
        url += f"&orderby={sort_param}"
    if page > 1:
        url += f"&page={page}"
    return _get(url)


def fetch_product_html(product: str) -> str:
    """Product page HTML. product: full URL or site path '/<slug>-at<id>'."""
    path = product.strip()
    if path.startswith("http"):
        parsed = urlparse(path)
        if "ciceksepeti.com" not in parsed.netloc:
            raise CiceksepetiError("product must be a ciceksepeti.com URL or path")
        path = parsed.path
    if not path.startswith("/"):
        path = "/" + path
    if "-at" not in path:
        raise CiceksepetiError(
            "product must be a product URL/path ending in '-at<id>' "
            "(find one with ciceksepeti_search first)"
        )
    return _get(f"{BASE}{path}")


def fetch_home_html() -> str:
    return _get(f"{BASE}/")


def health_check() -> dict:
    """One polite probe of the source site.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `ciceksepeti_health` tool
    and the daily smoke CI. Added 2026-11-10 (fleet audit fix).
    """
    url = "https://www.ciceksepeti.com/"
    try:
        fetch_home_html()
    except CiceksepetiError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
