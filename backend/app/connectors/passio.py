# -*- coding: utf-8 -*-
"""Passio (Ecomobi) deeplink — สร้างลิงก์ affiliate ต่อร้าน แบบต่อสตริง (ไม่ต้องเรียก API).

รูปแบบ (จาก field tracking_link ใน datafeed จริง):
    https://goeco.mobi?token={PASSIO_TOKEN}&url={urlencode(landingUrl)}
พิสูจน์แล้ว: ยิงแล้ว redirect ไป shopee.co.th จริง + มี utm_medium=affiliates (คอมมิชชั่นเข้า).

ข้อดี: ต่อสตริงล้วน → สร้างครบทุกร้านทันที ไม่มี rate limit ไม่ต้องรออนุมัติ API.
ตั้งค่า: PASSIO_TOKEN ใน .env (จาก affiliate.passio.eco → Tools/API → Getting Started).
"""
from __future__ import annotations

import urllib.parse
import urllib.request

from ..config import settings


def configured() -> bool:
    return bool(settings.passio_token)


def build_deeplink(landing_url: str, sub_id: str = "") -> str | None:
    """คืน deeplink Passio จาก URL ร้าน/สินค้า Shopee (None ถ้าไม่มี token/url)."""
    if not (settings.passio_token and landing_url):
        return None
    params = {"token": settings.passio_token, "url": landing_url}
    if sub_id:
        params["aff_sub"] = str(sub_id)   # แท็ก sub เพื่อวัดผลรายร้าน (ถ้า Passio รองรับ)
    base = (settings.passio_base or "https://goeco.mobi").rstrip("/")
    return f"{base}?{urllib.parse.urlencode(params)}"


_FEED = "https://ga.passio.eco/api/v3/products"


def import_datafeed(keyword: str = "", limit: int = 30, page: int = 1, advertiser: str = "",
                    category: str = "สินค้า", save: bool = True) -> dict:
    """ดึงสินค้าจาก Passio datafeed → (save=True) สร้างเป็น Store พร้อม affiliate_link (tracking_link).
    ครอบคลุมทุก advertiser ที่ token เข้าถึงได้ (ตอนนี้ shopee.vn · เพิ่ม TH/Lazada เมื่อ Passio เปิดให้).
    save=False = พรีวิวเฉยๆ ไม่บันทึก."""
    import json as _json
    if not settings.passio_token:
        return {"error": "ยังไม่ได้ตั้งค่า PASSIO_TOKEN"}
    params = {"token": settings.passio_token, "limit": limit, "page": page}
    if keyword:
        params["keyword"] = keyword
    if advertiser:
        params["advertiser_id"] = advertiser
    url = _FEED + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        j = _json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
    except Exception as e:  # pragma: no cover
        return {"error": f"{type(e).__name__}: {str(e)[:150]}"}
    items = j.get("data") or []
    rows = []
    for it in items:
        link = it.get("product_link") or ""
        if not link:
            continue
        imgs = [it.get("product_picture")] + ([it.get("product_other_pictures")] if it.get("product_other_pictures") else [])
        rows.append({
            "name": (it.get("product_name") or "")[:200],
            "shopee_url": link,
            "affiliate_link": it.get("tracking_link") or build_deeplink(link),
            "image_urls_json": _json.dumps([u for u in imgs if u], ensure_ascii=False),
            "price_range": str(it.get("product_discounted") or it.get("product_price") or ""),
            "advertiser": it.get("advertiser_id", ""),
        })
    for r in rows:
        r["source"] = "passio"
    if not save:
        return {"preview": True, "total_available": j.get("meta", {}).get("total"),
                "got": len(rows), "rows": rows, "sample": rows[:5]}
    from ..db import Store, get_session
    from sqlmodel import select
    added = skip = 0
    with get_session() as s:
        seen = {st.shopee_url for st in s.exec(select(Store)).all()}
        for r in rows:
            if r["shopee_url"] in seen:
                skip += 1
                continue
            s.add(Store(name=r["name"], area="", rating=0.0, price_range=r["price_range"],
                        image_urls_json=r["image_urls_json"], shopee_url=r["shopee_url"],
                        affiliate_link=r["affiliate_link"], category=category, status="new"))
            seen.add(r["shopee_url"])
            added += 1
        s.commit()
    return {"added": added, "skipped": skip, "got": len(rows),
            "total_available": j.get("meta", {}).get("total"), "category": category}


def _bad_url(u: str) -> bool:
    u = (u or "").strip().rstrip("/")
    return (not u) or u in ("https://shopee.co.th", "http://shopee.co.th")


def build_all(limit: int | None = None, overwrite: bool = True, with_sub: bool = False) -> dict:
    """ตั้ง affiliate_link ให้ทุกร้านที่มี shopee_url (ต่อสตริง) — เร็ว ไม่มี network call."""
    from ..db import Store, get_session
    from sqlmodel import select
    if not configured():
        return {"error": "ยังไม่ได้ตั้งค่า PASSIO_TOKEN ใน .env"}
    done = skip = 0
    with get_session() as s:
        stores = s.exec(select(Store).order_by(Store.id)).all()
        if limit:
            stores = stores[:limit]
        for st in stores:
            url = (st.shopee_url or "").strip()
            if _bad_url(url):
                skip += 1
                continue
            if not overwrite and (st.affiliate_link or "").startswith("https://goeco"):
                skip += 1
                continue
            link = build_deeplink(url, sub_id=(f"s{st.id}" if with_sub else ""))
            if link:
                st.affiliate_link = link
                s.add(st)
                done += 1
            else:
                skip += 1
        s.commit()
    return {"done": done, "skipped": skip, "total": len(stores)}
