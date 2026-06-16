"""Connector โพสต์ + คอมเมนต์แรก (affiliate link) — Hybrid: API ก่อน, ตกไป phone farm.

publish()         คืน {ok, method, account, external_id, error}
publish_comment() คืน {ok, comment_id, error}  (วาง affiliate link เป็นคอมเมนต์แรก)
ไม่มี credential → mock (คืน id ปลอม) เพื่อให้ flow ครบวง.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid

import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com/v21.0"


def _is_video(path: str) -> bool:
    return path.lower().endswith((".mp4", ".mov", ".m4v"))


# ----------------------------------------------------------- Official API: POST
def _post_facebook(caption: str, media_path: str) -> dict:
    """โพสต์ลง Facebook Page — อัปโหลดไฟล์ตรง (multipart) ไม่ต้องมี public URL."""
    if not settings.has_meta:
        return {"ok": True, "method": "api", "account": "mock_fb_page",
                "external_id": f"fb_{uuid.uuid4().hex[:10]}", "error": ""}
    try:
        is_vid = _is_video(media_path)
        endpoint = "videos" if is_vid else "photos"
        with open(media_path, "rb") as fh:
            files = {"source": (os.path.basename(media_path), fh)}
            data = {("description" if is_vid else "caption"): caption,
                    "access_token": settings.meta_access_token}
            with httpx.Client(timeout=300) as c:
                r = c.post(f"{GRAPH}/{settings.meta_page_id}/{endpoint}", data=data, files=files)
        r.raise_for_status()
        j = r.json()
        return {"ok": True, "method": "api", "account": settings.meta_page_id,
                "external_id": str(j.get("post_id", j.get("id", ""))), "error": ""}
    except Exception as e:
        return {"ok": False, "method": "api", "account": settings.meta_page_id,
                "external_id": "", "error": str(e)[:300]}


def _public_media_url(media_path: str) -> str:
    """IG ต้องการ public URL ของสื่อ — ใช้ PUBLIC_BASE_URL (เช่น ngrok/cloud)."""
    if not settings.public_base_url:
        return ""
    return settings.public_base_url.rstrip("/") + "/media/" + os.path.basename(media_path)


def _post_instagram(caption: str, media_path: str) -> dict:
    """โพสต์ลง IG (Reels ถ้าเป็นวีดีโอ) — IG รับเฉพาะ public URL ของสื่อ."""
    if not settings.has_meta or not settings.meta_ig_user_id:
        return {"ok": True, "method": "api", "account": "mock_ig",
                "external_id": f"ig_{uuid.uuid4().hex[:10]}", "error": ""}
    url = _public_media_url(media_path)
    if not url:
        return {"ok": False, "method": "api", "account": "ig", "external_id": "",
                "error": "IG ต้องตั้ง PUBLIC_BASE_URL (โฮสต์สื่อ public เช่น ngrok/cloud)"}
    try:
        tok = settings.meta_access_token
        is_vid = _is_video(media_path)
        data = {"caption": caption, "access_token": tok}
        if is_vid:
            data.update({"media_type": "REELS", "video_url": url})
        else:
            data["image_url"] = url
        with httpx.Client(timeout=180) as c:
            cid = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media", data=data).json()["id"]
            if is_vid:  # วีดีโอต้องรอประมวลผลก่อน publish
                for _ in range(20):
                    st = c.get(f"{GRAPH}/{cid}",
                               params={"fields": "status_code", "access_token": tok}).json()
                    if st.get("status_code") == "FINISHED":
                        break
                    time.sleep(3)
            pub = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media_publish",
                         data={"creation_id": cid, "access_token": tok}).json()
        return {"ok": True, "method": "api", "account": settings.meta_ig_user_id,
                "external_id": str(pub.get("id", "")), "error": ""}
    except Exception as e:
        return {"ok": False, "method": "api", "account": "ig",
                "external_id": "", "error": str(e)[:300]}


def _yt_access_token() -> str:
    r = httpx.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "refresh_token": settings.youtube_refresh_token,
        "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def _post_youtube(caption: str, media_path: str) -> dict:
    """อัปโหลด YouTube Shorts — OAuth refresh → resumable upload (videos.insert)."""
    if not settings.youtube_refresh_token:
        return {"ok": True, "method": "api", "account": "mock_yt",
                "external_id": f"yt_{uuid.uuid4().hex[:10]}", "error": ""}
    if not _is_video(media_path):
        return {"ok": False, "method": "api", "account": "yt", "external_id": "",
                "error": "YouTube ต้องไฟล์วีดีโอ (ตั้ง VIDEO_MODE=ffmpeg)"}
    try:
        token = _yt_access_token()
        title = ((caption.split("\n")[0] or "อร่อยบอกต่อ")[:90]) + " #Shorts"
        meta = {"snippet": {"title": title, "description": caption + "\n\n#Shorts"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        size = os.path.getsize(media_path)
        with httpx.Client(timeout=600) as c:
            init = c.post(
                "https://www.googleapis.com/upload/youtube/v3/videos"
                "?uploadType=resumable&part=snippet,status",
                headers={"Authorization": f"Bearer {token}",
                         "X-Upload-Content-Type": "video/*",
                         "X-Upload-Content-Length": str(size)}, json=meta)
            init.raise_for_status()
            with open(media_path, "rb") as fh:
                up = c.put(init.headers["Location"],
                           headers={"Authorization": f"Bearer {token}",
                                    "Content-Type": "video/*"}, content=fh.read())
            up.raise_for_status()
            return {"ok": True, "method": "api", "account": "youtube",
                    "external_id": str(up.json().get("id", "")), "error": ""}
    except Exception as e:
        return {"ok": False, "method": "api", "account": "yt",
                "external_id": "", "error": str(e)[:300]}


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
