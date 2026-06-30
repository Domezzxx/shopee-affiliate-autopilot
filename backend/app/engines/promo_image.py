# -*- coding: utf-8 -*-
"""สร้างภาพโปรโมทร้านอาหาร (ภาพนิ่ง) สำหรับโพสต์ FB/IG — ฟรี ไม่ใช้ AI image credit.

ใช้ภาพอาหาร (เฟรมจากคลิป Flow ที่มีอยู่ / รูป Shopee จริง) + overlay: ราคาใหญ่ + hook + ดาว + CTA.
คอนเซ็ปต์: เลื่อนผ่านเห็นแล้วเข้าใจทันที + อยากสั่ง.
"""
from __future__ import annotations

import math
import os
import re
import uuid

from ..config import settings

W, H = 1080, 1350
ORANGE = (230, 98, 45)
YELLOW = (255, 209, 71)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF️]+")


def _font_paths():
    """หาไฟล์ฟอนต์ไทย (Windows=Tahoma / Linux Docker=TLWG) → (bold, regular)."""
    cands = [("C:/Windows/Fonts/tahomabd.ttf", "C:/Windows/Fonts/tahoma.ttf"),
             ("/usr/share/fonts/truetype/tlwg/Garuda-Bold.ttf", "/usr/share/fonts/truetype/tlwg/Garuda.ttf"),
             ("/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf", "/usr/share/fonts/truetype/tlwg/Loma.ttf")]
    for b, r in cands:
        if os.path.exists(b) and os.path.exists(r):
            return b, r
    return None, None


def _noemoji(t: str) -> str:
    return _EMOJI.sub("", t or "").strip()


def get_promo_photo(store_id: int) -> str | None:
    """หาภาพอาหารของร้าน: เฟรมจากคลิปวิดีโอที่มีอยู่ → image_path → รูป Shopee จริง."""
    from ..db import Variant, get_session
    from ..engines import video_ffmpeg
    from sqlmodel import select
    with get_session() as s:
        vs = s.exec(select(Variant).where(Variant.store_id == store_id)).all()
    # 1) เฟรมจากคลิปวิดีโอ (สวยสุด)
    for v in vs:
        if v.media_type == "video" and v.media_path and os.path.exists(v.media_path):
            fr = video_ffmpeg.extract_frame(v.media_path)
            if fr and os.path.exists(fr):
                return fr
    # 2) image_path / รูปต้นฉบับ
    for v in vs:
        if v.image_path and os.path.exists(v.image_path):
            return v.image_path
    # 3) ดาวน์โหลดรูป Shopee จริงของร้าน (เผื่อร้านยังไม่มีคลิป — ครอบคลุมร้านที่ยังไม่ประมวลผล)
    try:
        from ..db import Store, get_session, jloads
        from . import media_gemini
        with get_session() as s:
            st = s.get(Store, store_id)
            urls = jloads(st.image_urls_json, []) if st else []
        if urls:
            imgs = media_gemini.download_images(urls, 1)
            if imgs:
                return imgs[0]
    except Exception as e:  # pragma: no cover
        print(f"[promo] photo dl fail store {store_id}: {str(e)[:60]}")
    return None


def make_promo_all(category: str | None = None, limit: int | None = None) -> dict:
    """สร้างภาพโปรโมทให้ทุกร้าน (ที่หารูปได้) → คืนสรุป. ใช้ hook จาก variant ถ้ามี."""
    from ..db import Store, Variant, get_session
    from sqlmodel import select
    with get_session() as s:
        q = select(Store).order_by(Store.id)
        if category:
            q = q.where(Store.category == category)
        stores = s.exec(q).all()
        hooks: dict[int, str] = {}
        for v in s.exec(select(Variant)).all():
            hooks.setdefault(v.store_id, v.hook)
    if limit:
        stores = stores[:limit]
    gen = skip = 0
    for st in stores:
        try:
            photo = get_promo_photo(st.id)
            if photo and make_promo(st, photo, hooks.get(st.id, "")):
                gen += 1
            else:
                skip += 1
        except Exception as e:  # pragma: no cover
            print(f"[promo] gen fail store {st.id}: {str(e)[:60]}")
            skip += 1
    return {"generated": gen, "skipped": skip, "total": len(stores)}


def make_promo(store, photo_path: str, hook: str = "") -> str | None:
    """สร้างภาพโปรโมท 1080x1350 → คืน path (None ถ้าทำไม่ได้)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    bold, reg = _font_paths()
    if not (bold and photo_path and os.path.exists(photo_path)):
        return None

    def F(sz, b=True):
        return ImageFont.truetype(bold if b else reg, sz)

    def fit(d, text, maxw, start, minsz=28, b=True):
        sz = start
        while sz > minsz and d.textlength(text, font=F(sz, b)) > maxw:
            sz -= 4
        return F(sz, b)

    def star(d, cx, cy, r, fill):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.42
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        d.polygon(pts, fill=fill)

    img = Image.open(photo_path).convert("RGB")
    sc = max(W / img.width, H / img.height)
    nw, nh = int(img.width * sc), int(img.height * sc)
    img = img.resize((nw, nh)).crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
    # gradient มืดด้านล่าง
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        a = int(110 * (1 - y / (H * 0.40))) if y < H * 0.40 else int(245 * ((y - H * 0.40) / (H * 0.60)))
        grad.putpixel((0, y), min(max(a, 0), 245))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 0)); black.putalpha(grad.resize((W, H)))
    img = Image.alpha_composite(img.convert("RGBA"), black)
    d = ImageDraw.Draw(img, "RGBA")
    M = 60

    # แบรนด์บนซ้าย
    area_text = getattr(store, "area", "") or "อุดรธานี"
    if getattr(store, "category", "food") == "food":
        subtype = getattr(store, "food_subtype", "") or "ของกินเด็ด"
        bt = f"{subtype} · {area_text}"
    else:
        bt = f"ของดีบอกต่อ · {area_text}"
    bf = F(34); bw = d.textlength(bt, font=bf)
    d.rounded_rectangle([M, 55, M + bw + 36, 55 + bf.size + 18], radius=26, fill=ORANGE)
    d.text((M + 18, 62), bt, font=bf, fill=(255, 255, 255))
    # เรตติ้ง + ดาว(วาดเอง) บนขวา
    rf = F(40); rtxt = f"{store.rating}"; tw = d.textlength(rtxt, font=rf); sr = 22; pad = 18
    rw = pad + sr * 2 + 10 + tw + pad
    rx = W - M - rw; rh = rf.size + pad
    d.rounded_rectangle([rx, 55, rx + rw, 55 + rh], radius=rh // 2, fill=(255, 255, 255))
    star(d, rx + pad + sr, 55 + rh // 2, sr, YELLOW)
    d.text((rx + pad + sr * 2 + 10, 62), rtxt, font=rf, fill=ORANGE)

    # ===== ล่าง =====
    y = H - 540
    hk = _noemoji((hook or "").split("\n")[0])[:42]
    if hk:
        fh = fit(d, hk, W - M * 2, 58)
        d.text((M, y), hk, font=fh, fill=(255, 255, 255)); y += fh.size + 22
    price = re.search(r"\d[\d,]*", store.price_range or "")
    if price:
        d.text((M, y), "เริ่มต้นเพียง" if "-" in (store.price_range or "") else "เพียง",
               font=F(38, False), fill=YELLOW); y += 46
        big = f"{price.group(0)}.-"
        fb = fit(d, big, W - M * 2, 150)
        d.text((M - 4, y), big, font=fb, fill=YELLOW); y += fb.size + 14
    nm = _noemoji(store.name)[:40]
    d.text((M, y), nm, font=fit(d, nm, W - M * 2, 42, b=False), fill=(240, 240, 240))
    # CTA
    cy = H - 130
    d.rounded_rectangle([M, cy, W - M, cy + 78], radius=39, fill=ORANGE)
    cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"; fc = F(42); cw = d.textlength(cta, font=fc)
    d.text(((W - cw) // 2, cy + 16), cta, font=fc, fill=(255, 255, 255))

    os.makedirs(settings.media_dir, exist_ok=True)
    out = os.path.join(settings.media_dir, f"promo_{store.id}_{uuid.uuid4().hex[:6]}.png")
    img.convert("RGB").save(out, quality=92)
    return out
