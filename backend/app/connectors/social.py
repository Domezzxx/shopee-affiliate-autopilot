"""Connector โพสต์ + คอมเมนต์แรก (affiliate link) — Hybrid: API ก่อน, ตกไป phone farm.

publish()         คืน {ok, method, account, external_id, error}
publish_comment() คืน {ok, comment_id, error}  (วาง affiliate link เป็นคอมเมนต์แรก)
ไม่มี credential → mock (คืน id ปลอม) เพื่อให้ flow ครบวง.
"""
from __future__ import annotations

import subprocess
import uuid

import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com/v21.0"


# ----------------------------------------------------------- Official API: POST
def _post_facebook(caption: str, media_path: str) -> dict:
    if not settings.has_meta:
        return {"ok": True, "method": "api", "account": "mock_fb_page",
                "external_id": f"fb_{uuid.uuid4().hex[:10]}", "error": ""}
    try:
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{GRAPH}/{settings.meta_page_id}/photos", data={
                "caption": caption,
                "url": media_path,
                "access_token": settings.meta_access_token,
            })
        r.raise_for_status()
        j = r.json()
        return {"ok": True, "method": "api", "account": settings.meta_page_id,
                "external_id": str(j.get("post_id", j.get("id", ""))), "error": ""}
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
    if not settings.youtube_refresh_token:
        return {"ok": True, "method": "api", "account": "mock_yt",
                "external_id": f"yt_{uuid.uuid4().hex[:10]}", "error": ""}
    # TODO: แลก access_token จาก refresh_token แล้ว resumable upload (videos.insert)
    return {"ok": False, "method": "api", "account": "yt",
            "external_id": "", "error": "youtube upload ยังไม่ implement (ต้องไฟล์วีดีโอ)"}


_API = {"facebook": _post_facebook, "instagram": _post_instagram, "youtube": _post_youtube}


# ----------------------------------------------------------- Official API: COMMENT
def _comment_meta(object_id: str, text_msg: str) -> dict:
    """วางคอมเมนต์บนโพสต์ FB/IG (Graph API /{object_id}/comments)."""
    try:
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{GRAPH}/{object_id}/comments", data={
                "message": text_msg, "access_token": settings.meta_access_token,
            })
        r.raise_for_status()
        return {"ok": True, "comment_id": str(r.json().get("id", "")), "error": ""}
    except Exception as e:
        return {"ok": False, "comment_id": "", "error": str(e)[:300]}


# ----------------------------------------------------------- Phone farm (ADB)
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


def _pick_device() -> str:
    devices = settings.phone_list
    return devices[uuid.uuid4().int % len(devices)] if devices else ""


def _post_phone(platform: str, caption: str, media_path: str) -> dict:
    device = _pick_device()
    if not device:
        return {"ok": True, "method": "phone", "account": "mock_phone",
                "external_id": f"ph_{uuid.uuid4().hex[:10]}", "error": ""}
    pkg = PACKAGES.get(platform)
    _adb(device, "push", media_path, "/sdcard/DCIM/autopilot.png")
    ok, _ = _adb(device, "shell", "monkey", "-p", pkg, "-c",
                 "android.intent.category.LAUNCHER", "1")
    # หมายเหตุ: ขั้นแตะ/พิมพ์แคปชั่นจริง ทำผ่าน uiautomator2 (Sprint 4)
    return {"ok": ok, "method": "phone", "account": device,
            "external_id": f"ph_{uuid.uuid4().hex[:10]}" if ok else "",
            "error": "" if ok else "adb launch failed"}


# ----------------------------------------------------------- entry points
def publish(platform: str, caption: str, media_path: str) -> dict:
    """โพสต์คอนเทนต์ — Hybrid routing ตาม POSTING_MODE."""
    mode = settings.posting_mode
    if mode == "phone":
        return _post_phone(platform, caption, media_path)
    res = _API[platform](caption, media_path)
    if not res["ok"] and mode == "hybrid":
        return _post_phone(platform, caption, media_path)   # API พลาด → phone farm
    return res


def publish_comment(platform: str, method: str, external_id: str, text_msg: str) -> dict:
    """วาง affiliate link เป็นคอมเมนต์แรกบนโพสต์ที่เพิ่งลง."""
    # mock / phone / youtube (ยังไม่มี comment API) → คืน id จำลอง
    if not settings.has_meta or method == "phone" or platform == "youtube" or not external_id:
        return {"ok": True, "comment_id": f"cmt_{uuid.uuid4().hex[:10]}", "error": ""}
    return _comment_meta(external_id, text_msg)
