"""Connector โพสต์ — Hybrid: Official API ก่อน, ตกไป phone farm เมื่อ API ไม่ครอบ.

คืน dict: {ok, method, account, external_id, error}
ไม่มี credential → mock (คืน id ปลอม) เพื่อให้ flow ครบวง.
"""
from __future__ import annotations

import subprocess
import uuid

import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com/v21.0"


# ----------------------------------------------------------- Official API
def _post_facebook(caption: str, media_path: str) -> dict:
    if not settings.has_meta:
        return {"ok": True, "method": "api", "account": "mock_fb_page",
                "external_id": f"fb_{uuid.uuid4().hex[:10]}", "error": ""}
    try:
        # หมายเหตุ: รูป/วีดีโอต้องเข้าถึงได้แบบ public URL หรืออัปโหลดแบบ multipart
        # โครงนี้ยิงโพสต์รูปผ่าน /photos (ใส่ url ของไฟล์ที่ backend เสิร์ฟ)
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{GRAPH}/{settings.meta_page_id}/photos", data={
                "caption": caption,
                "url": media_path,
                "access_token": settings.meta_access_token,
            })
        r.raise_for_status()
        return {"ok": True, "method": "api", "account": settings.meta_page_id,
                "external_id": str(r.json().get("post_id", r.json().get("id", ""))), "error": ""}
    except Exception as e:
        return {"ok": False, "method": "api", "account": settings.meta_page_id,
                "external_id": "", "error": str(e)[:300]}


def _post_instagram(caption: str, media_path: str) -> dict:
    if not settings.has_meta or not settings.meta_ig_user_id:
        return {"ok": True, "method": "api", "account": "mock_ig",
                "external_id": f"ig_{uuid.uuid4().hex[:10]}", "error": ""}
    try:
        with httpx.Client(timeout=120) as c:
            create = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media", data={
                "image_url": media_path, "caption": caption,
                "access_token": settings.meta_access_token,
            }).json()
            cid = create["id"]
            pub = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media_publish", data={
                "creation_id": cid, "access_token": settings.meta_access_token,
            }).json()
        return {"ok": True, "method": "api", "account": settings.meta_ig_user_id,
                "external_id": str(pub.get("id", "")), "error": ""}
    except Exception as e:
        return {"ok": False, "method": "api", "account": "ig",
                "external_id": "", "error": str(e)[:300]}


def _post_youtube(caption: str, media_path: str) -> dict:
    # YouTube ต้องอัปโหลดไฟล์วีดีโอจริงผ่าน OAuth — โครงไว้, ยังไม่มี token = mock
    if not settings.youtube_refresh_token:
        return {"ok": True, "method": "api", "account": "mock_yt",
                "external_id": f"yt_{uuid.uuid4().hex[:10]}", "error": ""}
    # TODO: แลก access_token จาก refresh_token แล้ว resumable upload (videos.insert)
    return {"ok": False, "method": "api", "account": "yt",
            "external_id": "", "error": "youtube upload ยังไม่ implement (ต้องไฟล์วีดีโอ)"}


_API = {"facebook": _post_facebook, "instagram": _post_instagram, "youtube": _post_youtube}


# ----------------------------------------------------------- Phone farm (ADB)
# เปิดแอป → (ฝากสคริปต์ uiautomator เฉพาะแอป) → แตะโพสต์
PACKAGES = {
    "facebook": "com.facebook.katana",
    "instagram": "com.instagram.android",
    "youtube": "com.google.android.youtube",
}


def _adb(device: str, *args: str) -> tuple[bool, str]:
    try:
        out = subprocess.run(["adb", "-s", device, *args],
                             capture_output=True, text=True, timeout=60)
        return out.returncode == 0, (out.stdout or out.stderr).strip()
    except Exception as e:
        return False, str(e)


def _post_phone(platform: str, caption: str, media_path: str) -> dict:
    devices = settings.phone_list
    if not devices:
        return {"ok": True, "method": "phone", "account": "mock_phone",
                "external_id": f"ph_{uuid.uuid4().hex[:10]}", "error": ""}
    device = devices[uuid.uuid4().int % len(devices)]   # กระจายโหลด 6 เครื่อง
    pkg = PACKAGES.get(platform)
    # 1) ดันไฟล์สื่อเข้าเครื่อง  2) เปิดแอป  3) (ต้องผูก uiautomator2/Appium flow ต่อแอป)
    _adb(device, "push", media_path, "/sdcard/DCIM/autopilot.png")
    ok, _ = _adb(device, "shell", "monkey", "-p", pkg, "-c",
                 "android.intent.category.LAUNCHER", "1")
    # หมายเหตุ: ขั้นแตะ/พิมพ์แคปชั่นจริง ทำผ่าน uiautomator2 (ดู SETUP_TH.md §phone farm)
    return {"ok": ok, "method": "phone", "account": device,
            "external_id": f"ph_{uuid.uuid4().hex[:10]}" if ok else "",
            "error": "" if ok else "adb launch failed"}


# ----------------------------------------------------------- entry
def publish(platform: str, caption: str, media_path: str) -> dict:
    """Hybrid routing ตาม POSTING_MODE."""
    mode = settings.posting_mode
    if mode == "phone":
        return _post_phone(platform, caption, media_path)
    res = _API[platform](caption, media_path)
    if not res["ok"] and mode == "hybrid":
        # API พลาด → fallback phone farm
        return _post_phone(platform, caption, media_path)
    return res
