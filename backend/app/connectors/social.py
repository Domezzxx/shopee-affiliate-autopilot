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


def _err(j: dict) -> str:
    """ดึงข้อความ error จาก Graph API response ให้อ่านรู้เรื่อง."""
    e = (j or {}).get("error", {})
    if isinstance(e, dict):
        msg = e.get("message") or e.get("error_user_msg") or ""
        code = e.get("code", "")
        return f"[{code}] {msg}".strip() if (msg or code) else str(j)[:200]
    return str(j)[:200]


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
                "error": "IG ต้องตั้ง PUBLIC_BASE_URL (โฮสต์สื่อ public เช่น ngrok/cloudflared)"}
    try:
        tok = settings.meta_access_token
        is_vid = _is_video(media_path)
        data = {"caption": caption, "access_token": tok}
        if is_vid:
            data.update({"media_type": "REELS", "video_url": url})
        else:
            data["image_url"] = url
        with httpx.Client(timeout=180) as c:
            cj = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media", data=data).json()
            if "id" not in cj:  # API ตอบ error → บอกสาเหตุชัดๆ ไม่ใช่ KeyError
                return {"ok": False, "method": "api", "account": "ig", "external_id": "",
                        "error": "สร้าง IG container ไม่ได้: " + _err(cj)}
            cid = cj["id"]
            if is_vid:  # วีดีโอต้องรอประมวลผลก่อน publish
                ready = False
                for _ in range(30):
                    st = c.get(f"{GRAPH}/{cid}",
                               params={"fields": "status_code", "access_token": tok}).json()
                    code = st.get("status_code")
                    if code == "FINISHED":
                        ready = True
                        break
                    if code == "ERROR":
                        return {"ok": False, "method": "api", "account": "ig",
                                "external_id": "", "error": "IG ประมวลผลวีดีโอล้มเหลว (ERROR)"}
                    time.sleep(3)
                if not ready:
                    return {"ok": False, "method": "api", "account": "ig", "external_id": "",
                            "error": "IG ประมวลผลวีดีโอนานเกิน (timeout)"}
            pub = c.post(f"{GRAPH}/{settings.meta_ig_user_id}/media_publish",
                         data={"creation_id": cid, "access_token": tok}).json()
        if "id" not in pub:
            return {"ok": False, "method": "api", "account": "ig", "external_id": "",
                    "error": "publish IG ไม่ได้: " + _err(pub)}
        return {"ok": True, "method": "api", "account": settings.meta_ig_user_id,
                "external_id": str(pub["id"]), "error": ""}
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


def _viral_title(title: str, caption: str) -> str:
    """ชื่อคลิปไวรัล: ใช้ video_title จาก AI ก่อน, ไม่มีก็ดึงบรรทัดแรกของแคปชั่น + เติม #Shorts."""
    base = (title or "").strip()
    if not base:
        # fallback: บรรทัดแรกที่มีเนื้อหาของแคปชั่น (= hook)
        base = next((ln.strip() for ln in (caption or "").splitlines() if ln.strip()), "อร่อยบอกต่อ")
    base = base[:88]
    if "#shorts" not in base.lower():
        base = f"{base} #Shorts"
    return base[:100]   # YouTube จำกัดชื่อ 100 ตัวอักษร


def _post_youtube(caption: str, media_path: str, title: str = "") -> dict:
    """อัปโหลด YouTube Shorts — OAuth refresh → resumable upload (videos.insert).
    title = ชื่อคลิปไวรัล (จาก AI video_title); ว่าง → fallback จากแคปชั่น."""
    if not settings.youtube_refresh_token:
        return {"ok": True, "method": "api", "account": "mock_yt",
                "external_id": f"yt_{uuid.uuid4().hex[:10]}", "error": ""}
    if not _is_video(media_path):
        return {"ok": False, "method": "api", "account": "yt", "external_id": "",
                "error": "YouTube ต้องไฟล์วีดีโอ (ตั้ง VIDEO_MODE=ffmpeg)"}
    try:
        token = _yt_access_token()
        vtitle = _viral_title(title, caption)
        meta = {"snippet": {"title": vtitle, "description": caption + "\n\n#Shorts"},
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


# ----------------------------------------------------------- preflight (เช็คความพร้อมก่อนโพสต์จริง)
def _verify_facebook() -> dict:
    """ยิง Graph API จริงเพื่อยืนยันว่า Page token ใช้ได้ + อ่านชื่อเพจได้."""
    if not settings.has_meta:
        return {"ready": False, "live": False, "detail": "ยังไม่ตั้ง META_PAGE_ID + META_ACCESS_TOKEN (โหมด mock)"}
    try:
        with httpx.Client(timeout=30) as c:
            j = c.get(f"{GRAPH}/{settings.meta_page_id}",
                      params={"fields": "name,id", "access_token": settings.meta_access_token}).json()
        if "name" in j:
            return {"ready": True, "live": True, "detail": f"พร้อมโพสต์เพจ: {j['name']}"}
        return {"ready": False, "live": False, "detail": "token/เพจใช้ไม่ได้: " + _err(j)}
    except Exception as e:
        return {"ready": False, "live": False, "detail": f"เชื่อม Graph API ไม่ได้: {str(e)[:160]}"}


def _verify_instagram() -> dict:
    if not settings.has_meta or not settings.meta_ig_user_id:
        return {"ready": False, "live": False, "detail": "ยังไม่ตั้ง META_IG_USER_ID + META_ACCESS_TOKEN (โหมด mock)"}
    detail = []
    ok = True
    try:
        with httpx.Client(timeout=30) as c:
            j = c.get(f"{GRAPH}/{settings.meta_ig_user_id}",
                      params={"fields": "username", "access_token": settings.meta_access_token}).json()
        if "username" in j:
            detail.append(f"บัญชี IG: @{j['username']}")
        else:
            ok = False
            detail.append("IG user/token ใช้ไม่ได้: " + _err(j))
    except Exception as e:
        ok = False
        detail.append(f"เชื่อม Graph API ไม่ได้: {str(e)[:120]}")
    if not settings.public_base_url:
        ok = False
        detail.append("ขาด PUBLIC_BASE_URL (IG รับเฉพาะ public URL ของสื่อ)")
    else:
        detail.append(f"public URL: {settings.public_base_url}")
    return {"ready": ok, "live": ok, "detail": " · ".join(detail)}


def _verify_youtube() -> dict:
    if not (settings.youtube_refresh_token and settings.youtube_client_id):
        return {"ready": False, "live": False, "detail": "ยังไม่ตั้ง YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN (โหมด mock)"}
    try:
        _yt_access_token()
        return {"ready": True, "live": True, "detail": "OAuth refresh token ใช้ได้ พร้อมอัปโหลด Shorts"}
    except Exception as e:
        return {"ready": False, "live": False, "detail": f"refresh token ใช้ไม่ได้: {str(e)[:160]}"}


def preflight() -> dict:
    """ตรวจความพร้อมโพสต์จริงต่อ platform — ยิง API จริงเพื่อยืนยัน token/สิทธิ์."""
    fb = _verify_facebook()
    ig = _verify_instagram()
    yt = _verify_youtube()
    any_live = any(x["live"] for x in (fb, ig, yt))
    return {
        "facebook": fb, "instagram": ig, "youtube": yt,
        "posting_mode": settings.posting_mode,
        "post_delay": settings.enable_post_delay,
        "any_live": any_live,
        "summary": ("พร้อมโพสต์จริงบางช่องทางแล้ว" if any_live
                    else "ยังเป็นโหมด mock ทั้งหมด — ใส่ credential ใน .env เพื่อโพสต์จริง"),
    }


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
    
    from . import phone_automator
    
    print(f"[phone-farm] Routing post to device {device} for platform {platform}")
    try:
        if platform == "facebook":
            res = phone_automator.post_facebook_reel(device, media_path, caption)
        elif platform == "instagram":
            res = phone_automator.post_instagram_reel(device, media_path, caption)
        elif platform == "youtube":
            res = phone_automator.post_youtube_shorts(device, media_path, caption)
        elif platform == "shopee_video":
            res = phone_automator.post_shopee_video(device, media_path, caption)
        else:
            return {"ok": False, "method": "phone", "account": device, "external_id": "",
                    "error": f"Platform {platform} is not supported on phone farm."}
                    
        if res["ok"]:
            return {"ok": True, "method": "phone", "account": device,
                    "external_id": f"ph_{uuid.uuid4().hex[:10]}", "error": ""}
        else:
            return {"ok": False, "method": "phone", "account": device, "external_id": "",
                    "error": res["error"]}
    except Exception as e:
        return {"ok": False, "method": "phone", "account": device, "external_id": "",
                "error": f"Phone automation exception: {e}"}


# ----------------------------------------------------------- entry points
def publish(platform: str, caption: str, media_path: str, title: str = "") -> dict:
    """โพสต์คอนเทนต์ — Hybrid routing ตาม POSTING_MODE. title = ชื่อคลิปไวรัล (ใช้กับ YouTube)."""
    mode = settings.posting_mode
    if mode == "phone" or platform == "shopee_video":
        return _post_phone(platform, caption, media_path)
    if platform == "youtube":
        res = _post_youtube(caption, media_path, title)
    else:
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
