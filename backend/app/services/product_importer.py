# -*- coding: utf-8 -*-
"""รวมสินค้าจากหลายเครือข่าย affiliate (Passio + AccessTrade + Involve) → dedupe → บันทึกเป็น Store.

แต่ละเครือข่ายคืน rows normalize เหมือนกัน:
    {name, shopee_url, affiliate_link, image_urls_json, price_range, source, advertiser?}
Passio ใช้ได้จริงตอนนี้ · AccessTrade/Involve เสียบทันทีเมื่อได้ credentials (โครงพร้อมแล้ว).
"""
from __future__ import annotations

from ..config import settings


def _passio_fetch(keyword: str, limit: int):
    from ..connectors import passio
    if not passio.configured():
        return [], "ยังไม่ตั้งค่า PASSIO_TOKEN"
    r = passio.import_datafeed(keyword=keyword, limit=limit, save=False)
    if r.get("error"):
        return [], r["error"]
    return r.get("rows", []), None


def _accesstrade_fetch(keyword: str, limit: int):
    from ..connectors import accesstrade
    if not accesstrade.configured():
        return [], "AccessTrade ยังไม่ตั้งค่า (รอ API key จาก Support)"
    # TODO: เสียบ AccessTrade product datafeed API เมื่อได้ endpoint/สเปกจาก Support
    return [], "AccessTrade product feed ยังไม่เชื่อม (รอสเปก endpoint)"


def _involve_fetch(keyword: str, limit: int):
    if not getattr(settings, "involve_api_key", ""):
        return [], "Involve ยังไม่ตั้งค่า (property รอผ่าน + API key)"
    # TODO: เสียบ Involve Asia datafeed API เมื่อได้ credentials
    return [], "Involve datafeed ยังไม่เชื่อม"


_SOURCES = {
    "passio": _passio_fetch,
    "accesstrade": _accesstrade_fetch,
    "involve": _involve_fetch,
}


def import_all(keyword: str = "", limit: int = 30, category: str = "สินค้า",
               save: bool = True, sources: list[str] | None = None) -> dict:
    """ดึงสินค้าจากทุกเครือข่ายที่ตั้งค่าไว้ → dedupe (ตาม shopee_url) → (save) บันทึกเป็น Store."""
    names = sources or list(_SOURCES)
    per_source: dict = {}
    combined: list = []
    seen = set()
    for name in names:
        fn = _SOURCES.get(name)
        if not fn:
            continue
        try:
            rows, err = fn(keyword, limit)
        except Exception as e:  # pragma: no cover
            per_source[name] = {"got": 0, "note": f"error: {str(e)[:100]}"}
            continue
        if err:
            per_source[name] = {"got": 0, "note": err}
            continue
        uniq = 0
        for r in rows:
            u = r.get("shopee_url")
            if not u or u in seen:
                continue
            seen.add(u)
            combined.append(r)
            uniq += 1
        per_source[name] = {"got": len(rows), "unique": uniq}

    if not save:
        return {"preview": True, "sources": per_source,
                "total_unique": len(combined), "sample": combined[:6]}

    from ..db import Store, get_session
    from sqlmodel import select
    saved = skip = 0
    with get_session() as s:
        existing = {st.shopee_url for st in s.exec(select(Store)).all()}
        for r in combined:
            if r["shopee_url"] in existing:
                skip += 1
                continue
            s.add(Store(name=r["name"], area="", rating=0.0, price_range=r.get("price_range", ""),
                        image_urls_json=r.get("image_urls_json", "[]"), shopee_url=r["shopee_url"],
                        affiliate_link=r.get("affiliate_link", ""), category=category, status="new"))
            existing.add(r["shopee_url"])
            saved += 1
        s.commit()
    return {"sources": per_source, "saved": saved, "skipped": skip,
            "total_unique": len(combined), "category": category}
