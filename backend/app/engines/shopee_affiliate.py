# -*- coding: utf-8 -*-
"""Shopee Affiliate Open API — สร้างลิงก์ affiliate (คอมมิชชั่นเข้าพี่กอล์ฟ) + sub_id track.

ใช้สร้าง short link จาก URL สินค้า/ร้าน Shopee พร้อม sub_id (ติดตามว่าลิงก์มาจากคลิป/แพลตฟอร์มไหน).
ไม่มี APP_ID/SECRET → คืน None (ระบบ fallback ไปใช้ลิงก์ที่ใส่เองต่อร้าน).

วิธีได้ key: affiliate.shopee.co.th → Open API → App ID + Secret (ดู docs/คู่มือใช้งาน_API.md)
"""
from __future__ import annotations

import hashlib
import json
import time

from ..config import settings

# GraphQL endpoint (ไทย) — เปลี่ยนตามประเทศได้ถ้าจำเป็น
ENDPOINT = "https://open-api.affiliate.shopee.co.th/graphql"


def available() -> bool:
    return bool(settings.shopee_affiliate_app_id and settings.shopee_affiliate_secret)


def _signature(payload: str, ts: int) -> str:
    """ลายเซ็น SHA256(AppId + Timestamp + Payload + Secret) — ตามสเปก Shopee Affiliate Open API."""
    base = f"{settings.shopee_affiliate_app_id}{ts}{payload}{settings.shopee_affiliate_secret}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def generate_link(origin_url: str, sub_ids: list[str] | None = None) -> str | None:
    """สร้าง affiliate short link จาก URL สินค้า/ร้าน Shopee + sub_id (track). คืน None ถ้าทำไม่ได้."""
    if not available() or not origin_url:
        return None
    import httpx

    sub_ids = [s for s in (sub_ids or []) if s][:5]   # Shopee รับสูงสุด 5 sub_id
    # สร้าง GraphQL mutation (escape ค่าด้วย json.dumps ให้ปลอดภัย)
    query = (
        "mutation{generateShortLink(input:{originUrl:%s,subIds:%s}){shortLink}}"
        % (json.dumps(origin_url), json.dumps(sub_ids))
    )
    payload = json.dumps({"query": query}, separators=(",", ":"))
    ts = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "Authorization": (
            f"SHA256 Credential={settings.shopee_affiliate_app_id}, "
            f"Timestamp={ts}, Signature={_signature(payload, ts)}"
        ),
    }
    try:
        r = httpx.post(ENDPOINT, headers=headers, content=payload, timeout=20)
        data = r.json()
        if data.get("errors"):
            print(f"[shopee-aff] error: {str(data['errors'])[:200]}")
            return None
        link = (((data.get("data") or {}).get("generateShortLink") or {}).get("shortLink"))
        if link:
            return link
        print(f"[shopee-aff] no shortLink ใน response: {str(data)[:200]}")
    except Exception as e:  # pragma: no cover
        print(f"[shopee-aff] {str(e)[:120]}")
    return None
