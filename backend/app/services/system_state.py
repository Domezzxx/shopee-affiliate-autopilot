# -*- coding: utf-8 -*-
"""สถานะระบบ เปิด/ปิด (จำได้ข้าม restart) + health check ว่าอะไรพร้อม/ไม่พร้อม.

แนวคิด: ผู้ใช้กดปิดระบบ → บอทหยุดทำงานอัตโนมัติ (ไม่รัน/ไม่โพสต์) แต่เซิร์ฟเวอร์ยังอยู่.
กดเปิดใหม่ → ทำงานต่อได้ทันที (สถานะเก็บใน data/system_state.json ไม่หายตอน restart).
"""
from __future__ import annotations

import json
import os

from ..config import settings

_DEFAULT = {"enabled": True}


def _state_file() -> str:
    return os.path.join(settings.data_dir, "system_state.json")


def get_state() -> dict:
    try:
        with open(_state_file(), encoding="utf-8") as f:
            return {**_DEFAULT, **json.load(f)}
    except Exception:
        return dict(_DEFAULT)


def set_enabled(enabled: bool) -> dict:
    st = get_state()
    st["enabled"] = bool(enabled)
    os.makedirs(settings.data_dir, exist_ok=True)
    with open(_state_file(), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    return st


def is_enabled() -> bool:
    return bool(get_state().get("enabled", True))


def _chrome_flow_ready() -> bool:
    """Chrome remote-debugging (9222) เปิดอยู่ไหม — จำเป็นสำหรับ Flow video."""
    try:
        import httpx
        url = settings.flow_cdp_url.rstrip("/") + "/json/version"
        return httpx.get(url, timeout=2).status_code == 200
    except Exception:
        return False


def health() -> dict:
    """เช็คว่าส่วนต่างๆ พร้อมไหม — dashboard จะได้โชว์ ไม่ต้องเดา/ไล่ debug."""
    return {
        "enabled": is_enabled(),
        "content_ai": settings.content_ready,          # Gemini/Claude เขียนได้
        "flow_chrome": _chrome_flow_ready(),           # Flow video (Chrome debug)
        "phone_devices": len(settings.phone_list),     # มือถือ phone farm
        "stock_video": bool(settings.pexels_api_key),
        "ambience_sfx": bool(settings.freesound_api_key),
        "meta": settings.has_meta,
        "youtube": bool(settings.youtube_refresh_token),
        "posting_mode": settings.posting_mode,
    }
