# -*- coding: utf-8 -*-
"""สร้าง 'รูปตั้งต้น' ระดับโฆษณา ฟรี ด้วย Pollinations.ai (Flux) — ไม่ต้องมี key/สมัคร.

2 โหมด:
  - photo   : ภาพอาหารเสมือนจริง สว่าง น่ากิน (ใช้กับโปสเตอร์สไตล์ 'flyer' สว่างจัด)
  - cartoon : คาริคเจอร์/มาสคอตแม่ค้า สไตล์ Girlkik (ใช้กับโปสเตอร์สไตล์ 'cartoon')
AI สร้างเฉพาะ 'รูป' (สั่ง no text) ส่วนตัวอักษรไทยให้เอนจิน HTML เติมทับทีหลัง (AI เขียนไทยมั่ว).
"""
from __future__ import annotations

import hashlib
import os
import re
import time
import urllib.parse
import urllib.request

from ..config import settings

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF️]+")
_ENDPOINT = "https://image.pollinations.ai/prompt/"

# แมพประเภทร้าน → คำอธิบายอาหาร (อังกฤษ ให้ Flux เข้าใจ)
_DISH = {
    "ร้านตามสั่ง": "sizzling Thai stir-fried holy basil pork with fried egg over jasmine rice, wok hei",
    "ร้านก๋วยเตี๋ยว": "steaming bowl of Thai noodle soup with pork, herbs and chili",
    "ของหวาน": "colorful Thai dessert with coconut milk and shaved ice",
    "เครื่องดื่ม": "refreshing Thai iced milk tea and fruit soda with ice splash",
    "ของหวาน/เครื่องดื่ม": "Thai dessert and iced drinks, colorful and refreshing",
    "ปิ้งย่าง": "Thai grilled pork and seafood on charcoal barbecue, smoky",
    "อีสาน": "Thai Isaan feast, grilled chicken, papaya salad, sticky rice, laab",
}
_DEFAULT_DISH = "abundant delicious authentic Thai food spread, grilled meat, rice and fresh herbs"


def _clean(t: str) -> str:
    return _EMOJI.sub("", t or "").strip()


def _norm(t: str) -> str:
    """normalize สระที่พิมพ์แยก (เเ→แ) กัน keyword พลาด."""
    return (t or "").replace("เเ", "แ")


def _dish_hint(store) -> str:
    sub = _norm((getattr(store, "food_subtype", "") or "").strip())
    n = _norm(_clean(getattr(store, "name", "")))
    for key, desc in _DISH.items():
        if key and _norm(key) in sub:
            return desc
    # เดาจากชื่อร้าน
    if any(w in n for w in ("แดดเดียว", "แดดเดี")):
        return "Thai sun-dried fried pork (moo dad diew), crispy golden and glossy, with sticky rice and spicy chili dip"
    if any(w in n for w in ("ส้มตำ", "ตำ", "ลาบ", "ไก่ย่าง", "อีสาน", "แซ่บ", "ซั่ว")):
        return _DISH["อีสาน"]
    if any(w in n for w in ("ก๋วยเตี๋ยว", "เส้น", "บะหมี่", "ราเมน", "เกาเหลา")):
        return _DISH["ร้านก๋วยเตี๋ยว"]
    if any(w in n for w in ("หมูทอด", "ไก่ทอด", "ทอด", "กรอบ")):
        return "crispy golden Thai fried pork and chicken, deep fried, glistening and juicy"
    if any(w in n for w in ("ปิ้งย่าง", "ย่าง", "หมูกระทะ", "จิ้มจุ่ม")):
        return _DISH["ปิ้งย่าง"]
    if any(w in n for w in ("กาแฟ", "ชา", "คาเฟ่", "ดื่ม", "น้ำ", "ชานม")):
        return _DISH["เครื่องดื่ม"]
    if any(w in n for w in ("ขนม", "เค้ก", "ไอศ", "หวาน", "เบเกอ", "โรตี")):
        return _DISH["ของหวาน"]
    return _DEFAULT_DISH


def photo_prompt(store) -> str:
    dish = _dish_hint(store)
    return (f"professional commercial food photography of {dish}, "
            "bright natural daylight, vibrant saturated appetizing colors, fresh steam, "
            "shallow depth of field, top-down and 45 degree, on rustic Thai table, "
            "ultra detailed, mouth-watering, high resolution, food magazine quality, no text, no watermark")


def cartoon_prompt(store) -> str:
    dish = _dish_hint(store)
    return (f"Thai street food advertising poster illustration, exaggerated caricature cartoon style, "
            f"cheerful chubby Thai vendor character joyfully presenting {dish}, "
            "vivid saturated colors, warm market background with bokeh lanterns, dynamic energetic, "
            "comic pop-art, thick clean outlines, highly detailed mascot art, professional, no text, no watermark")


def _cache_dir() -> str:
    d = os.path.join(settings.data_dir, "ai_images")
    os.makedirs(d, exist_ok=True)
    return d


def gen_image(prompt: str, w: int = 1080, h: int = 1080, seed: int | None = None,
              model: str = "flux", force: bool = False) -> str | None:
    """เรียก Pollinations → คืน path (cache ตาม prompt+ขนาด+seed). retry กัน 500/502."""
    if seed is None:
        seed = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % 100000
    key = hashlib.md5(f"{prompt}|{w}x{h}|{seed}|{model}".encode()).hexdigest()[:16]
    out = os.path.join(_cache_dir(), f"{key}.jpg")
    if os.path.exists(out) and not force and os.path.getsize(out) > 5000:
        return out
    url = (_ENDPOINT + urllib.parse.quote(prompt) +
           f"?width={w}&height={h}&model={model}&nologo=true&seed={seed}")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=180).read()
            if len(data) < 5000:
                raise ValueError("image too small")
            with open(out, "wb") as f:
                f.write(data)
            return out
        except Exception as e:  # pragma: no cover
            print(f"[ai] pollinations retry {attempt}: {str(e)[:70]}")
            time.sleep(5)
    return None


def get_ai_image(store, mode: str = "photo", w: int = 1080, h: int = 1350) -> str | None:
    """สร้างรูปตั้งต้นตามโหมด (photo|cartoon) — seed=store.id ให้ผลคงที่ต่อร้าน."""
    prompt = cartoon_prompt(store) if mode == "cartoon" else photo_prompt(store)
    return gen_image(prompt, w, h, seed=int(getattr(store, "id", 0) or 0) + (7 if mode == "cartoon" else 0))
