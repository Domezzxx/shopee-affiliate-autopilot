# -*- coding: utf-8 -*-
"""AccessTrade Deeplink (Custom Creative) API — สร้างลิงก์ affiliate ต่อร้าน แทน Shopee Open API.

สเปก (จาก support.accesstrade.global/api/creative-apis.html):
  POST {base}/v1/publishers/me/sites/{siteId}/campaigns/{campaignId}/creatives/custom
  headers: Authorization: {scheme} {api_key}   (ปกติ scheme = "Token")
  body: {"landingUrl": <url ร้าน Shopee>, "name": ..., "imageUrl": ...,
         "subIds": [{"label","value","name"}]}
  resp: {"content":[{"affiliateLink":"https://atth.me/go/...", ...}]}

ตั้งค่าใน .env: ACCESSTRADE_API_KEY, ACCESSTRADE_SITE_ID, ACCESSTRADE_SHOPEE_CAMPAIGN_ID
(เอาจากแดชบอร์ด publisher.accesstrade.in.th → Tools/โปรไฟล์ → API).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from ..config import settings


def configured() -> bool:
    return bool(settings.accesstrade_api_key and settings.accesstrade_site_id
               and settings.accesstrade_shopee_campaign_id)


def _headers() -> dict:
    scheme = (settings.accesstrade_auth_scheme or "Token").strip()
    return {"Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"{scheme} {settings.accesstrade_api_key}".strip()}


def _endpoint() -> str:
    base = settings.accesstrade_api_base.rstrip("/")
    return (f"{base}/v1/publishers/me/sites/{settings.accesstrade_site_id}"
            f"/campaigns/{settings.accesstrade_shopee_campaign_id}/creatives/custom")


def generate_deeplink(landing_url: str, sub_id: str = "", name: str = "",
                      image_url: str = "") -> tuple[str | None, str | None]:
    """สร้าง deeplink 1 ลิงก์ → (affiliate_link, error). error=None ถ้าสำเร็จ."""
    if not configured():
        return None, "ยังไม่ได้ตั้งค่า AccessTrade (API key / siteId / campaignId) ใน .env"
    if not landing_url:
        return None, "ไม่มี landing_url (shopee_url ของร้าน)"
    body: dict = {"landingUrl": landing_url}
    if name:
        body["name"] = name[:80]
    if image_url:
        body["imageUrl"] = image_url
    if sub_id:
        body["subIds"] = [{"label": "sub1", "name": "sub1", "value": str(sub_id)}]
    req = urllib.request.Request(_endpoint(), data=json.dumps(body).encode("utf-8"),
                                 headers=_headers(), method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        j = json.loads(r.read().decode("utf-8"))
        content = j.get("content") or j.get("data") or []
        if isinstance(content, dict):
            content = [content]
        link = (content[0].get("affiliateLink") if content else None) or j.get("affiliateLink")
        return (link, None) if link else (None, f"no affiliateLink in response: {str(j)[:200]}")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:250]}"
    except Exception as e:  # pragma: no cover
        return None, f"{type(e).__name__}: {str(e)[:200]}"


def test_connection() -> dict:
    """ทดสอบว่า key/endpoint ใช้ได้ — ลองสร้าง deeplink จาก URL Shopee ตัวอย่าง."""
    link, err = generate_deeplink("https://shopee.co.th/", sub_id="attest", name="connection test")
    return {"ok": bool(link), "link": link, "error": err, "endpoint": _endpoint()}


def build_all(limit: int | None = None, overwrite: bool = False, gap: float = 0.4) -> dict:
    """สร้าง deeplink ให้ทุกร้านที่มี shopee_url → เก็บลง store.affiliate_link."""
    from ..db import Store, get_session
    from sqlmodel import select
    if not configured():
        return {"error": "ยังไม่ได้ตั้งค่า AccessTrade ใน .env"}
    done = fail = skip = 0
    detail = []
    with get_session() as s:
        stores = s.exec(select(Store).order_by(Store.id)).all()
        if limit:
            stores = stores[:limit]
        for st in stores:
            if st.affiliate_link and st.affiliate_link.startswith("https://atth.me") and not overwrite:
                skip += 1
                continue
            url = (st.shopee_url or "").strip()
            if not url:
                skip += 1
                detail.append({"id": st.id, "skip": "no shopee_url"})
                continue
            link, err = generate_deeplink(url, sub_id=f"s{st.id}", name=st.name,
                                          image_url=_first_image(st))
            if link:
                st.affiliate_link = link
                s.add(st); s.commit()
                done += 1
                detail.append({"id": st.id, "name": st.name[:24], "link": link})
            else:
                fail += 1
                detail.append({"id": st.id, "name": st.name[:24], "error": err})
            time.sleep(gap)   # กัน rate limit
    return {"done": done, "failed": fail, "skipped": skip, "total": len(stores), "detail": detail[:25]}


def _first_image(store) -> str:
    try:
        from ..db import jloads
        urls = jloads(store.image_urls_json, [])
        return urls[0] if urls else ""
    except Exception:
        return ""


# ---------------------------------------------------------------- CSV (ทาง manual — ไม่ต้องมี API key)
def export_stores_csv(path: str | None = None) -> str:
    """ออกไฟล์ CSV: id,name,shopee_url,affiliate_link(ว่าง) ให้ผู้ใช้เอา shopee_url ไป
    generate ลิงก์ atth.me ใน Custom Creative แล้วเติมช่อง affiliate_link กลับมา."""
    import csv
    from ..db import Store, get_session
    from sqlmodel import select
    path = path or os.path.join(settings.data_dir, "stores_links.csv")
    with get_session() as s:
        stores = s.exec(select(Store).order_by(Store.id)).all()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "shopee_url", "affiliate_link"])
        for st in stores:
            w.writerow([st.id, st.name, st.shopee_url or "", ""])
    return path


def import_links_csv(path: str | None = None) -> dict:
    """อ่าน CSV (id[/name] + affiliate_link) → อัปเดต store.affiliate_link. คืนสรุป."""
    import csv
    from ..db import Store, get_session
    from sqlmodel import select
    path = path or os.path.join(settings.data_dir, "stores_links.csv")
    if not os.path.exists(path):
        return {"error": f"ไม่พบไฟล์ {path}"}
    updated = skipped = 0
    with get_session() as s:
        by_id = {st.id: st for st in s.exec(select(Store)).all()}
        by_name = {(st.name or "").strip(): st for st in by_id.values()}
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                link = (row.get("affiliate_link") or "").strip()
                if not link or not link.startswith("http"):
                    skipped += 1
                    continue
                st = None
                rid = (row.get("id") or "").strip()
                if rid.isdigit():
                    st = by_id.get(int(rid))
                if not st:
                    st = by_name.get((row.get("name") or "").strip())
                if st:
                    st.affiliate_link = link
                    s.add(st)
                    updated += 1
                else:
                    skipped += 1
        s.commit()
    return {"updated": updated, "skipped": skipped, "file": path}
