"""ดึงร้าน Shopee Food แบบเสถียร — รองรับหลายโหมด + retry + parse ทนทาน + fallback graceful.

โหมด (SCRAPER_MODE):
  direct      — ยิงตรง (ใส่ proxy ได้ที่ SCRAPER_PROXY) — มักโดน Shopee บล็อก
  scraperapi  — ผ่าน api.scraperapi.com (มี free 1,000/เดือน) ใส่ SCRAPER_API_KEY
  scrapingbee — ผ่าน scrapingbee.com (มี free credits) ใส่ SCRAPER_API_KEY
  apify       — รัน Apify actor (ใส่ APIFY_TOKEN + APIFY_ACTOR)

scrape() ไม่เคย raise — คืน {"fetched", "stores", "error"} เสมอ (ระบบไม่ล่มถ้าโดนบล็อก).
"""
from __future__ import annotations

import time
import urllib.parse

import httpx

from ..config import settings

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _search_url(keyword: str, limit: int) -> str:
    kw = urllib.parse.quote(keyword)
    return (f"https://shopee.co.th/api/v4/search/search_items?by=relevancy&keyword={kw}"
            f"&limit={limit}&newest=0&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2")


def _get_json(url: str, proxy: str | None = None, retries: int = 3) -> dict:
    """GET + retry + ตรวจว่าเป็น JSON จริง (ไม่ใช่หน้า captcha/บล็อก)."""
    headers = {"User-Agent": UA, "Referer": "https://shopee.co.th/",
               "Accept": "application/json", "X-Requested-With": "XMLHttpRequest",
               "X-API-SOURCE": "pc"}
    last = "unknown"
    for i in range(retries):
        try:
            with httpx.Client(timeout=20, headers=headers, proxy=proxy,
                              follow_redirects=True) as c:
                r = c.get(url)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and ("json" in ct or r.text.lstrip().startswith("{")):
                return r.json()
            last = f"HTTP {r.status_code} ({ct[:30]})"
        except Exception as e:
            last = str(e)[:140]
        time.sleep(1.2 * (i + 1))
    return {"_error": last}


# ----------------------------------------------------------------- fetch modes
def _fetch_direct(url: str) -> dict:
    return _get_json(url, proxy=(settings.scraper_proxy or None))


def _fetch_scraperapi(url: str) -> dict:
    extra = "&ultra_premium=true" if settings.scraper_ultra_premium else ""
    api = ("http://api.scraperapi.com/?api_key=" + settings.scraper_api_key +
           "&country_code=th" + extra + "&url=" + urllib.parse.quote(url))
    return _get_json(api)


def _fetch_scrapingbee(url: str) -> dict:
    api = ("https://app.scrapingbee.com/api/v1/?api_key=" + settings.scraper_api_key +
           "&render_js=false&country_code=th&url=" + urllib.parse.quote(url))
    return _get_json(api)


def _fetch_apify(keyword: str, limit: int) -> dict:
    """รัน Apify actor แบบ sync แล้วดึง dataset items กลับมาเลย."""
    api = (f"https://api.apify.com/v2/acts/{settings.apify_actor}"
           f"/run-sync-get-dataset-items?token={settings.apify_token}")
    payload = {"keyword": keyword, "search": keyword, "maxItems": limit, "limit": limit}
    try:
        with httpx.Client(timeout=120) as c:
            r = c.post(api, json=payload)
        if r.status_code in (200, 201):
            return {"_apify_items": r.json()}
        return {"_error": f"apify HTTP {r.status_code}: {r.text[:120]}"}
    except Exception as e:
        return {"_error": f"apify {str(e)[:120]}"}


# ----------------------------------------------------------------- parse
def _num(x, d=0):
    try:
        return float(x)
    except Exception:
        return d


def _parse_shopee(data: dict, area: str) -> list[dict]:
    """parse ผล Shopee internal API → schema ของระบบ (ทนทานต่อ field หาย)."""
    items = data.get("items") or (data.get("data") or {}).get("items") or []
    out = []
    for it in items:
        b = it.get("item_basic") or it
        if not isinstance(b, dict):
            continue
        rating_obj = b.get("item_rating") or {}
        rating = round(_num(rating_obj.get("rating_star", b.get("rating", 0))), 1)
        rc_list = rating_obj.get("rating_count")
        review_count = int(rc_list[0]) if isinstance(rc_list, list) and rc_list else int(_num(b.get("review_count", 0)))
        name = b.get("name") or b.get("shop_name") or ""
        if not name:
            continue
        price = _num(b.get("price"))
        out.append({
            "name": name, "area": area, "rating": rating, "review_count": review_count,
            "price_range": (f"~{round(price/100000)} บาท" if price else ""),
            "menu": [w for w in name.split(" ")[:4] if w],
            "image_urls": ([f"https://cf.shopee.co.th/file/{b['image']}"] if b.get("image") else []),
            "shopee_url": (f"https://shopee.co.th/product/{b['shopid']}/{b['itemid']}"
                           if b.get("shopid") and b.get("itemid") else ""),
            "affiliate_link": "",
        })
    return out


def _parse_apify(items: list, area: str) -> list[dict]:
    """Apify actor คืน shape ต่างกันไป — map แบบ best-effort จาก field ที่พบบ่อย."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        name = it.get("name") or it.get("title") or it.get("shopName") or it.get("restaurantName") or ""
        if not name:
            continue
        out.append({
            "name": name, "area": it.get("area") or it.get("city") or area,
            "rating": round(_num(it.get("rating") or it.get("ratingStar") or it.get("avgRating")), 1),
            "review_count": int(_num(it.get("reviewCount") or it.get("totalReview") or it.get("ratingCount"))),
            "price_range": str(it.get("priceRange") or it.get("price") or ""),
            "menu": (it.get("menu") or it.get("categories") or [])[:4] if isinstance(it.get("menu") or it.get("categories"), list) else [],
            "image_urls": [it["image"]] if it.get("image") else (it.get("images") or [])[:1],
            "shopee_url": it.get("url") or it.get("link") or "",
            "affiliate_link": it.get("affiliate_link") or "",
        })
    return out


# ----------------------------------------------------------------- entry
def scrape(keyword: str | None = None, limit: int | None = None) -> dict:
    keyword = keyword or settings.shopee_keywords.split(";")[0].strip()
    limit = limit or settings.scraper_limit
    area = settings.shopee_keywords.split()[-1] if settings.shopee_keywords else "อุดรธานี"
    mode = settings.scraper_mode

    if mode == "apify":
        if not (settings.apify_token and settings.apify_actor):
            return {"fetched": 0, "stores": [], "error": "ยังไม่ตั้ง APIFY_TOKEN/APIFY_ACTOR"}
        res = _fetch_apify(keyword, limit)
        if "_error" in res:
            return {"fetched": 0, "stores": [], "error": res["_error"]}
        stores = _parse_apify(res.get("_apify_items", []), area)
        return {"fetched": len(stores), "stores": stores, "error": None, "mode": mode}

    url = _search_url(keyword, limit)
    fetch = {"direct": _fetch_direct, "scraperapi": _fetch_scraperapi,
             "scrapingbee": _fetch_scrapingbee}.get(mode, _fetch_direct)
    if mode in ("scraperapi", "scrapingbee") and not settings.scraper_api_key:
        return {"fetched": 0, "stores": [], "error": f"ยังไม่ตั้ง SCRAPER_API_KEY สำหรับโหมด {mode}"}
    data = fetch(url)
    if "_error" in data:
        return {"fetched": 0, "stores": [], "error": f"{mode}: {data['_error']}"}
    stores = _parse_shopee(data, area)
    return {"fetched": len(stores), "stores": stores, "error": None, "mode": mode}
