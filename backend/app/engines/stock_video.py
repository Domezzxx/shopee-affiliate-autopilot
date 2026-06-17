# -*- coding: utf-8 -*-
"""ดึง footage อาหารจริง (เคลื่อนไหว) จาก Pexels — ฟรี ให้คลิปดูเป็นรีวิวจริง.

ใช้ร่วมกับภาพ AI/รูปจริง: เส้นยืด ไอลอย ราดน้ำซุป คนกิน = motion จริง แก้ "สไลด์โชว์".
ไม่มี PEXELS_API_KEY → คืน [] (ระบบ fallback ไปใช้ภาพ).
"""
from __future__ import annotations

import os
import uuid

from ..config import settings

PEXELS_VIDEO = "https://api.pexels.com/videos/search"

# คิวรีหลากหลายให้ได้ footage หลายแบบ (เคลื่อนไหวต่างกัน)
DEFAULT_QUERIES = [
    "noodle soup close up", "eating noodles chopsticks", "pouring hot broth",
    "asian street food cooking", "ramen steam", "thai food",
]


def available() -> bool:
    return bool(settings.pexels_api_key)


# คีย์เวิร์ดเมนู (ไทย/อังกฤษ) -> คิวรีค้น footage ที่ "ตรงเมนูนั้นเป๊ะ" (ไม่เอา generic ที่ดึงของมั่ว)
_DISH_MAP = [
    # ก๋วยเตี๋ยวเรือ/เส้น: เลี่ยงคิวรีที่ดึงราเมง — ใช้ตัวที่ออกมาไทย/น้ำซุปดำ (ทดสอบแล้ว)
    (("ก๋วยเตี๋ยว", "เตี๋ยว", "เส้น", "noodle", "boat noodle", "เกี๊ยว", "บะหมี่", "ราดหน้า"),
     ["thai pork noodle", "thai street food noodle", "beef noodle soup", "pho beef noodle"]),
    (("ข้าวผัด", "fried rice", "ผัด", "กะเพรา", "stir fry"),
     ["thai fried rice", "wok stir fry close up", "fried rice plate"]),
    (("ข้าว", "rice", "ข้าวมันไก่", "ข้าวหมู"),
     ["rice plate close up", "thai rice dish", "khao man gai"]),
    (("ส้มตำ", "ตำ", "papaya", "som tum", "ยำ"),
     ["thai papaya salad", "som tum", "thai spicy salad"]),
    (("หมูกระทะ", "ปิ้ง", "ย่าง", "bbq", "grill"),
     ["grilled meat sizzling", "bbq grill close up", "korean bbq"]),
    (("ไก่ทอด", "ทอด", "fried chicken", "fried"),
     ["fried chicken close up", "crispy fried chicken", "deep fried food"]),
    (("ชาบู", "สุกี้", "hotpot", "shabu", "ต้มยำ", "ต้ม"),
     ["hotpot boiling", "thai tom yum soup", "shabu shabu"]),
    (("ขนม", "เค้ก", "หวาน", "dessert", "cake", "ไอศ", "ice cream"),
     ["dessert close up", "cake slice macro", "ice cream macro"]),
    (("ชา", "กาแฟ", "coffee", "drink", "น้ำ", "เครื่องดื่ม"),
     ["pouring iced drink", "coffee pour close up", "bubble tea"]),
]


def build_queries(dish: str = "", menu: list[str] | None = None) -> list[str]:
    """คิวรีค้น footage 'เฉพาะเมนูนั้น' เท่านั้น — ไม่เติม generic ที่ทำให้หลุดหัวข้อ."""
    text = (dish + " " + " ".join(menu or [])).lower()
    for keys, queries in _DISH_MAP:
        if any(k in text for k in keys):
            return queries          # ล็อกเฉพาะเมนูที่ตรง
    return ["asian food close up", "eating food chopsticks", "delicious food macro"]


def _pick_file(video: dict) -> str:
    """เลือกไฟล์วีดีโอแนวตั้ง/ความละเอียดพอดี (~720-1080) จาก video_files."""
    files = video.get("video_files", []) or []
    portrait = [f for f in files if (f.get("height") or 0) >= (f.get("width") or 0)]
    pool = portrait or files
    # เรียงตามความสูง เลือกตัวที่ >=720 ตัวเล็กสุด (โหลดเร็ว) ไม่งั้นตัวใหญ่สุด
    pool = sorted(pool, key=lambda f: (f.get("height") or 0))
    for f in pool:
        if f.get("link") and (f.get("height") or 0) >= 720:
            return f["link"]
    return pool[-1]["link"] if pool and pool[-1].get("link") else ""


def search_food_clips(queries: list[str] | None = None, n: int = 4) -> list[str]:
    """ค้น + โหลด footage อาหารจริงหลายแบบ → คืน list ของ path mp4 (เท่าที่โหลดได้)."""
    if not settings.pexels_api_key:
        return []
    import httpx
    queries = queries or DEFAULT_QUERIES
    headers = {"Authorization": settings.pexels_api_key}
    out: list[str] = []
    os.makedirs(settings.media_dir, exist_ok=True)
    with httpx.Client(timeout=40, follow_redirects=True) as c:
        for q in queries:
            if len(out) >= n:
                break
            try:
                r = c.get(PEXELS_VIDEO, headers=headers,
                          params={"query": q, "orientation": "portrait",
                                  "per_page": 5, "size": "medium"})
                if r.status_code != 200:
                    print(f"[pexels] {q}: HTTP {r.status_code}")
                    continue
                for v in r.json().get("videos", []):
                    link = _pick_file(v)
                    if not link:
                        continue
                    dl = c.get(link)
                    if dl.status_code == 200 and len(dl.content) > 20000:
                        p = os.path.join(settings.media_dir, f"stock_{uuid.uuid4().hex[:8]}.mp4")
                        with open(p, "wb") as f:
                            f.write(dl.content)
                        out.append(p)
                        break   # 1 คลิปต่อคิวรี (ความหลากหลาย)
            except Exception as e:  # pragma: no cover
                print(f"[pexels] {q}: {str(e)[:80]}")
    return out
