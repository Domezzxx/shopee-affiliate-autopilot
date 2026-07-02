# -*- coding: utf-8 -*-
"""สร้างภาพโปรโมทร้านอาหาร (ภาพนิ่ง) สำหรับโพสต์ FB/IG — ฟรี ไม่ใช้ AI image credit.

ใช้ภาพอาหาร (เฟรมจากคลิป Flow ที่มีอยู่ / รูป Shopee จริง) + overlay: ราคาใหญ่ + hook + ดาว + CTA.
คอนเซ็ปต์: เลื่อนผ่านเห็นแล้วเข้าใจทันที + อยากสั่ง.
"""
from __future__ import annotations

import math
import os
import random
import re
import uuid

from ..config import settings

W, H = 1080, 1350
ORANGE = (230, 98, 45)
YELLOW = (255, 209, 71)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF️]+")

# hook สำรองโทนป้ายยาอาหาร (ใช้เมื่อ variant ไม่มี hook)
_APPETITE = [
    "อร่อยจนลืมอิ่ม บอกเลยต้องลอง", "หิวแล้วใช่ไหม? ร้านนี้จัดให้",
    "เด็ดทุกเมนู ฟินทุกคำ", "สั่งทีไรไม่เคยพลาด", "ร้านนี้ของแทร่ ต้องลอง!",
]


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


def make_caption(store, hook: str = "", base_caption: str = "") -> str:
    """แคปชั่นโปรโมทร้านอาหารสไตล์ 'ป้ายยา' — 🛒 เกริ่น + ✅ บูลเล็ต + #แฮชแท็ก (อยากสั่งทันที)."""
    area = (getattr(store, "area", "") or "อุดรธานี").strip()
    area_tag = area.replace(" ", "")
    subtype = (getattr(store, "food_subtype", "") or "").strip()
    rating = getattr(store, "rating", 0) or 0
    name = _noemoji(getattr(store, "name", "") or "ร้านเด็ด")
    headline = _noemoji((hook or "").split("\n")[0]) or random.choice(_APPETITE)

    loc = f"📍 {name}"
    if subtype and subtype not in name:
        loc += f" · {subtype}"
    if area and area not in name:           # กันชื่อร้านที่มีชื่อย่านอยู่แล้ว (ไม่ซ้ำ)
        loc += f" · {area}"

    bullets = [f"✅ อร่อยระดับบอกต่อ เรตติ้ง {rating}⭐" if rating else "✅ อร่อยระดับบอกต่อ"]
    pm = re.search(r"\d[\d,]*", getattr(store, "price_range", "") or "")
    if pm:
        bullets.append(f"✅ เริ่มต้นเพียง {pm.group(0)} บาท คุ้มเกินราคา")
    bullets.append("✅ สั่งง่าย ส่งไว ผ่าน Shopee Food")
    bullets.append("✅ กดลิงก์สั่งได้เลย 👇 (อยู่คอมเมนต์แรกใต้โพสต์)")

    tags = ["#ShopeeFood", "#รีวิวร้านอร่อย", "#กินอะไรดี",
            f"#ของกิน{area_tag}", f"#ร้านอาหาร{area_tag}", "#อร่อยบอกต่อ"]

    parts = ["🛒 ร้านเด็ดบอกต่อ — สั่งง่ายผ่าน Shopee Food", "",
             f"😋 {headline}", loc, ""]
    parts += bullets
    parts += ["", " ".join(tags)]
    return "\n".join(parts)


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
    styles = ["premium_set", "viral_banner", "viral_editorial", "viral_neon", "viral_collage"]
    for idx, st in enumerate(stores):
        try:
            photo = get_promo_photo(st.id)
            style = styles[idx % len(styles)]
            if photo and make_promo(st, photo, hooks.get(st.id, ""), style=style):
                gen += 1
            else:
                skip += 1
        except Exception as e:  # pragma: no cover
            print(f"[promo] gen fail store {st.id}: {str(e)[:60]}")
            skip += 1
    return {"generated": gen, "skipped": skip, "total": len(stores)}


def make_promo(store, photo_path: str, hook: str = "", style: str = "viral_neon") -> str | None:
    """สร้างภาพโปรโมท 1080x1350 → คืน path (None ถ้าทำไม่ได้)."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
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

    def draw_slanted_badge(canvas, text, font, bg_color, fg_color, center_xy, angle=15):
        d = ImageDraw.Draw(canvas)
        tw = int(d.textlength(text, font=font))
        th = font.size
        pad_x, pad_y = 20, 10
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle([0, 0, bw, bh], radius=bh // 2, fill=bg_color)
        bd.text((pad_x, pad_y), text, font=font, fill=fg_color)
        rotated = badge.rotate(angle, resample=Image.BICUBIC, expand=True)
        px = center_xy[0] - rotated.width // 2
        py = center_xy[1] - rotated.height // 2
        canvas.paste(rotated, (px, py), rotated)

    # Clean text elements
    area_text = getattr(store, "area", "") or "อุดรธานี"
    if getattr(store, "category", "food") == "food":
        subtype = getattr(store, "food_subtype", "") or "ของกินเด็ด"
        bt = f"{subtype} · {area_text}"
    else:
        bt = f"ของดีบอกต่อ · {area_text}"
        
    hk = _noemoji((hook or "").split("\n")[0])[:42]
    nm = _noemoji(store.name)[:40]
    
    price_match = re.search(r"\d[\d,]*", store.price_range or "")
    price_val = f"{price_match.group(0)}.-" if price_match else ""

    if style == "viral_neon":
        # ------------------ VIRAL STYLE 1: NEON STREET STREET ------------------
        img = Image.new("RGB", (W, H), (15, 15, 17))
        d = ImageDraw.Draw(img, "RGBA")
        
        # Background Big Typography
        bg_txt = "SPICY"
        bg_f = F(280, True)
        d.text((W // 2 - 340, 200), bg_txt, font=bg_f, fill=(35, 35, 45, 120))
        
        # Circular Food Image Crop with Neon Border
        cx, cy, r = W // 2, H // 2 - 80, 360
        orig_img = Image.open(photo_path).convert("RGB")
        img_cropped = ImageOps.fit(orig_img, (r * 2, r * 2), centering=(0.5, 0.5))
        
        mask = Image.new("L", (r * 2, r * 2), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0, 0, r * 2, r * 2], fill=255)
        
        # Draw drop shadow behind circle
        d.ellipse([cx - r - 10, cy - r + 15, cx + r + 20, cy + r + 30], fill=(0, 0, 0, 180))
        # Draw neon outer rings
        d.ellipse([cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12], outline=ORANGE, width=6)
        d.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], outline=YELLOW, width=2)
        
        img.paste(img_cropped, (cx - r, cy - r), mask)
        
        # Add Slanted Sticker Banners
        draw_slanted_badge(img, "ห้ามพลาด!", F(32, True), (255, 50, 50), (255, 255, 255), (cx - 280, cy - 250), angle=-12)
        draw_slanted_badge(img, bt, F(28, True), YELLOW, (0, 0, 0), (cx + 280, cy + 220), angle=15)
        
        # Text Content at the bottom
        name_f = fit(d, nm, 960, 58)
        d.text((W // 2 - d.textlength(nm, font=name_f) // 2, H - 340), nm, font=name_f, fill=(255, 255, 255))
        
        # Rating star row
        rx = W // 2
        d.text((rx - 70, H - 280), f"{store.rating}", font=F(34, True), fill=(240, 240, 240))
        star(d, rx + 15, H - 263, 16, YELLOW)
        d.text((rx + 50, H - 277), "รีวิวห้าดาว", font=F(26, False), fill=(180, 180, 180))
        
        # Price Tag
        if price_val:
            price_txt = f"เริ่มต้นเพียง {price_val}"
            pw = d.textlength(price_txt, font=F(46, True))
            d.rounded_rectangle([W // 2 - pw // 2 - 20, H - 215, W // 2 + pw // 2 + 20, H - 150], radius=10, fill=(40, 42, 54))
            d.text((W // 2 - pw // 2, H - 208), price_txt, font=F(44, True), fill=YELLOW)
            
        # Giant CTA Button at bottom
        cy_btn = H - 120
        d.rounded_rectangle([60, cy_btn, W - 60, cy_btn + 80], radius=40, fill=ORANGE)
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"
        cw = d.textlength(cta, font=F(38, True))
        d.text(((W - cw) // 2, cy_btn + 18), cta, font=F(38, True), fill=(255, 255, 255))

    elif style == "viral_collage":
        # ------------------ VIRAL STYLE 2: RETRO MAGAZINE COLLAGE ------------------
        img = Image.new("RGB", (W, H), (245, 240, 230))
        d = ImageDraw.Draw(img, "RGBA")
        
        # Retro brown border at bottom
        d.rectangle([0, H - 140, W, H], fill=(40, 30, 20))
        
        # Food Image with sharp drop shadow
        ix, iy, iw, ih = 100, 180, 880, 700
        d.rectangle([ix + 20, iy + 20, ix + iw + 20, iy + ih + 20], fill=(40, 30, 20))
        d.rectangle([ix - 4, iy - 4, ix + iw + 4, iy + ih + 4], fill=(255, 255, 255))
        
        orig_img = Image.open(photo_path).convert("RGB")
        img_cropped = ImageOps.fit(orig_img, (iw, ih), centering=(0.5, 0.5))
        img.paste(img_cropped, (ix, iy))
        
        # Masking Tape sticker
        tape = Image.new("RGBA", (280, 80), (255, 240, 150, 180))
        td = ImageDraw.Draw(tape)
        td.text((40, 22), "แนะนำโดยแอดมิน", font=F(24, True), fill=(60, 40, 20))
        rotated_tape = tape.rotate(-15, resample=Image.BICUBIC, expand=True)
        img.paste(rotated_tape, (ix - 50, iy - 40), rotated_tape)
        
        # Slanted Yellow Tag
        draw_slanted_badge(img, "สูตรเด็ดดั้งเดิม!", F(30, True), YELLOW, (40, 30, 20), (ix + iw - 120, iy + ih - 40), angle=8)
        
        # Top Header labels
        d.rounded_rectangle([100, 70, 320, 120], radius=15, fill=ORANGE)
        d.text((120, 78), "เมนูเด็ดต้องลอง", font=F(24, True), fill=(255, 255, 255))
        
        star(d, W - 150, 95, 18, ORANGE)
        d.text((W - 250, 78), f"เรตติ้ง {store.rating}", font=F(28, True), fill=(40, 30, 20))
        
        # Text below photo
        y = H - 420
        nf = fit(d, nm, 880, 52)
        d.text((100, y), nm, font=nf, fill=(40, 30, 20))
        
        y += nf.size + 15
        if hk:
            hf = fit(d, hk, 880, 28, b=False)
            d.text((100, y), hk, font=hf, fill=(80, 70, 60))
            
        # Price & CTA (checkered brown area)
        if price_val:
            d.text((100, H - 98), f"เริ่มต้นเพียง {price_val}", font=F(38, True), fill=YELLOW)
            
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"
        cw = d.textlength(cta, font=F(32, True))
        d.rounded_rectangle([W - 100 - cw - 40, H - 105, W - 100, H - 45], radius=30, fill=ORANGE)
        d.text((W - 100 - cw - 20, H - 93), cta, font=F(32, True), fill=(255, 255, 255))

    elif style == "viral_editorial":
        # ------------------ VIRAL STYLE 3: EDITORIAL PREMIUM SPLASH ------------------
        img = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(img, "RGBA")
        
        # Dark slanted block
        d.polygon([(640, 0), (W, 0), (W, H), (480, H)], fill=(28, 30, 38))
        
        # Circular image crop on the right side
        cx, cy, r = W - 320, H // 2 - 120, 280
        orig_img = Image.open(photo_path).convert("RGB")
        img_cropped = ImageOps.fit(orig_img, (r * 2, r * 2), centering=(0.5, 0.5))
        
        mask = Image.new("L", (r * 2, r * 2), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0, 0, r * 2, r * 2], fill=255)
        
        # Glowing border rings
        d.ellipse([cx - r - 15, cy - r - 15, cx + r + 15, cy + r + 15], outline=ORANGE, width=12)
        d.ellipse([cx - r - 25, cy - r - 25, cx + r + 25, cy + r + 25], outline=YELLOW, width=3)
        
        img.paste(img_cropped, (cx - r, cy - r), mask)
        
        # Left Content layout (White side)
        mx = 80
        y = 150
        d.text((mx, y), "RECOMMENDED SPECIAL", font=F(24, True), fill=ORANGE)
        y += 40
        
        nf = fit(d, nm, 480, 64)
        d.text((mx, y), nm, font=nf, fill=(30, 30, 30))
        y += nf.size + 30
        
        # Rating Box
        d.rounded_rectangle([mx, y, mx + 200, y + 60], radius=15, fill=(240, 244, 248))
        star(d, mx + 30, y + 30, 15, ORANGE)
        d.text((mx + 65, y + 13), f"{store.rating} / 5", font=F(28, True), fill=(40, 50, 60))
        
        # Slanted sticker near food
        draw_slanted_badge(img, bt, F(26, True), YELLOW, (0, 0, 0), (cx - 150, cy + 240), angle=-8)
        
        # Hook details ticks (วาดเครื่องหมายถูกเอง กัน glyph กลายเป็นกล่อง)
        def check(dr, x, yy, sz, color):
            dr.line([(x, yy + sz * 0.55), (x + sz * 0.42, yy + sz)], fill=color, width=6)
            dr.line([(x + sz * 0.42, yy + sz), (x + sz, yy)], fill=color, width=6)
        y += 120
        details = ["คัดสรรวัตถุดิบชั้นดี", "ปรุงสดใหม่ร้อนๆ", "รสชาติอร่อยจัดจ้าน"]
        for item in details:
            check(d, mx + 2, y + 6, 26, (46, 170, 90))
            d.text((mx + 46, y), item, font=F(32, True), fill=(70, 70, 70))
            y += 54
            
        # Price tag
        y += 60
        if price_val:
            d.text((mx, y), "ราคาเริ่มต้นเพียง", font=F(26, False), fill=(120, 120, 120))
            y += 40
            d.text((mx, y), price_val, font=F(96, True), fill=ORANGE)
            
        # Bottom CTA banner
        cy_btn = H - 150
        d.rounded_rectangle([80, cy_btn, W - 80, cy_btn + 80], radius=20, fill=(30, 34, 42))
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"
        cw = d.textlength(cta, font=F(34, True))
        d.text(((W - cw) // 2, cy_btn + 20), cta, font=F(34, True), fill=(255, 255, 255))
        
        # Draw arrow box
        d.rounded_rectangle([W - 160, cy_btn + 15, W - 100, cy_btn + 65], radius=10, fill=ORANGE)
        d.text((W - 143, cy_btn + 22), ">", font=F(34, True), fill=(255, 255, 255))

    elif style == "viral_banner":
        # ------------------ VIRAL STYLE 4: HEADER/FOOTER BANNER LAYOUT ------------------
        img = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(img, "RGBA")
        
        DARK_BG = (28, 30, 38)
        LIGHT_BG = (245, 246, 248)
        
        # Draw Top Panel (Y=0 to 220) - Solid Dark Slate
        d.rectangle([0, 0, W, 220], fill=DARK_BG)
        # Draw Bottom Panel (Y=1020 to 1350) - Solid Light Warm Gray
        d.rectangle([0, 1020, W, H], fill=LIGHT_BG)
        d.line([0, 1020, W, 1020], fill=(220, 225, 235), width=2)
        
        # Paste Food Image in the Middle Window (Y=220 to 1020)
        img_w, img_h = W, 800
        orig_img = Image.open(photo_path).convert("RGB")
        img_cropped = ImageOps.fit(orig_img, (img_w, img_h), centering=(0.5, 0.5))
        img.paste(img_cropped, (0, 220))
        
        # Draw Content inside TOP PANEL (Y=0 to 220)
        d.text((60, 45), nm, font=F(52, True), fill=(255, 255, 255))
        
        # Subtitle Category Badge
        sf = F(22, True)
        tw = d.textlength(bt, font=sf)
        d.rounded_rectangle([60, 125, 60 + tw + 24, 170], radius=10, fill=ORANGE)
        d.text((72, 135), bt, font=sf, fill=(255, 255, 255))
        
        # Rating Stars (Top Right)
        rx = W - 260
        ry = 80
        d.text((rx, ry), f"{store.rating}", font=F(34, True), fill=(255, 255, 255))
        star(d, rx + 80, ry + 18, 16, YELLOW)
        d.text((rx + 115, ry + 7), "รีวิวห้าดาว", font=F(22, False), fill=(180, 185, 195))
        
        # Draw Content inside BOTTOM PANEL (Y=1020 to 1350)
        # Highlights row
        hl_txt = "หมูกรอบหนังฟูกรอบ  •  พริกแห้งเผ็ดร้อนหอมกระทะ  •  กะเพราป่าแท้ 100%"
        if hk:
            hl_txt = hk[:45]
        hf = F(24, True)
        tw_hl = d.textlength(hl_txt, font=hf)
        d.text(((W - tw_hl) // 2, 1055), hl_txt, font=hf, fill=(80, 90, 105))
        
        # Bottom row: Price and CTA Button
        d.text((60, 1140), "ราคาเริ่มต้น", font=F(22, False), fill=(120, 130, 145))
        d.text((60, 1170), price_val or "50.-", font=F(64, True), fill=ORANGE)
        
        # CTA Button on the right
        btn_x, btn_y, btn_w, btn_h = 480, 1150, 540, 80
        d.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=40, fill=ORANGE)
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"
        cw = d.textlength(cta, font=F(34, True))
        d.text((btn_x + (btn_w - cw) // 2, btn_y + 18), cta, font=F(34, True), fill=(255, 255, 255))

    elif style == "premium_set":
        # ---------- PREMIUM DARK+GOLD "เซตสุดคุ้ม" (แรงบันดาลใจ: โปสเตอร์เซตอีสาน/ราเมนในกลุ่ม GCT) ----------
        GOLD = (212, 175, 55)
        GOLD_LT = (244, 220, 130)
        DARKBG = (20, 17, 14)
        CREAM = (245, 238, 222)
        img = Image.new("RGB", (W, H), DARKBG)

        # วงแสงอุ่นหลังอาหาร (radial glow) ให้จานเด่นลอยขึ้นมา
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse([W // 2 - 470, 340, W // 2 + 470, 1200], fill=80)
        glow = glow.filter(ImageFilter.GaussianBlur(170))
        warm = Image.new("RGBA", (W, H), (150, 95, 35, 0)); warm.putalpha(glow)
        img = Image.alpha_composite(img.convert("RGBA"), warm).convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")

        # กรอบมุมทอง 4 มุม
        def corner(x, y, dx, dy, ln=70):
            d.line([(x, y), (x + dx * ln, y)], fill=GOLD, width=4)
            d.line([(x, y), (x, y + dy * ln)], fill=GOLD, width=4)
        corner(46, 46, 1, 1); corner(W - 46, 46, -1, 1)
        corner(46, H - 46, 1, -1); corner(W - 46, H - 46, -1, -1)

        # ป้ายหมวดบนสุด (เส้นขอบทอง)
        top_label = getattr(store, "food_subtype", "") or "เมนูแนะนำ"
        tf = F(28, True); tlw = d.textlength(top_label, font=tf)
        d.rounded_rectangle([W // 2 - tlw // 2 - 26, 88, W // 2 + tlw // 2 + 26, 148],
                            radius=30, outline=GOLD, width=2)
        d.text((W // 2 - tlw // 2, 99), top_label, font=tf, fill=GOLD_LT)

        # ชื่อร้าน (ทอง กลาง)
        nf = fit(d, nm, W - 170, 74)
        d.text((W // 2 - d.textlength(nm, font=nf) // 2, 168), nm, font=nf, fill=GOLD_LT)

        # เส้นคั่นทอง + เพชร
        dvy = 168 + nf.size + 20
        d.line([(W // 2 - 190, dvy), (W // 2 - 26, dvy)], fill=GOLD, width=2)
        d.line([(W // 2 + 26, dvy), (W // 2 + 190, dvy)], fill=GOLD, width=2)
        d.polygon([(W // 2, dvy - 9), (W // 2 - 13, dvy), (W // 2, dvy + 9), (W // 2 + 13, dvy)], fill=GOLD)

        # แผงรูปอาหาร (มุมมน กรอบทอง)
        px0, py0, px1, py1 = 95, 300, 985, 985
        pw, ph = px1 - px0, py1 - py0
        orig_img = Image.open(photo_path).convert("RGB")
        food = ImageOps.fit(orig_img, (pw, ph), centering=(0.5, 0.5))
        rmask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(rmask).rounded_rectangle([0, 0, pw, ph], radius=34, fill=255)
        img.paste(food, (px0, py0), rmask)
        d.rounded_rectangle([px0, py0, px1, py1], radius=34, outline=GOLD, width=5)

        # แท็ก "เมนูเด็ด" มุมซ้ายบนของแผง
        tag = "เมนูเด็ด"; tgf = F(27, True); tgw = d.textlength(tag, font=tgf)
        d.rounded_rectangle([px0 - 6, py0 - 8, px0 + tgw + 40, py0 + 50], radius=12, fill=GOLD)
        d.text((px0 + 18, py0 + 4), tag, font=tgf, fill=(38, 26, 4))

        # ป้ายราคาวงกลมทอง (มุมขวาล่างของแผง)
        if price_val:
            bx, by, br = px1 - 42, py1 - 44, 94
            d.ellipse([bx - br, by - br, bx + br, by + br], fill=GOLD)
            d.ellipse([bx - br + 7, by - br + 7, bx + br - 7, by + br - 7], outline=(150, 118, 34), width=2)
            sf2 = F(22, True)
            d.text((bx - d.textlength("เริ่มต้น", font=sf2) // 2, by - 48), "เริ่มต้น", font=sf2, fill=(70, 50, 12))
            pf = fit(d, price_val, br * 2 - 26, 54)
            d.text((bx - d.textlength(price_val, font=pf) // 2, by - 16), price_val, font=pf, fill=(36, 26, 6))

        # ===== ส่วนล่าง: ดาว + hook + CTA =====
        yb = 1030
        n_star = 5
        sx = W // 2 - (n_star * 46) // 2
        rr = round(getattr(store, "rating", 5) or 5)
        for i in range(n_star):
            star(d, sx + i * 46 + 18, yb + 16, 15, GOLD if i < rr else (95, 84, 56))
        rate_txt = f"{store.rating} · อร่อยระดับบอกต่อ"
        d.text((W // 2 - d.textlength(rate_txt, font=F(26, True)) // 2, yb + 42), rate_txt,
               font=F(26, True), fill=CREAM)
        if hk:
            hf2 = fit(d, hk, W - 170, 40, b=False)
            d.text((W // 2 - d.textlength(hk, font=hf2) // 2, yb + 92), hk, font=hf2, fill=(212, 202, 182))

        # ปุ่ม CTA แถบทอง
        cyb = H - 152
        d.rounded_rectangle([90, cyb, W - 90, cyb + 84], radius=42, fill=GOLD)
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"; cf = F(40, True)
        d.text((W // 2 - d.textlength(cta, font=cf) // 2, cyb + 19), cta, font=cf, fill=(30, 22, 6))

    else:
        # ------------------ STYLE: CLASSIC (Original Fallback) ------------------
        img = Image.open(photo_path).convert("RGB")
        sc = max(W / img.width, H / img.height)
        nw, nh = int(img.width * sc), int(img.height * sc)
        img = img.resize((nw, nh)).crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
        grad = Image.new("L", (1, H), 0)
        for y in range(H):
            a = int(110 * (1 - y / (H * 0.40))) if y < H * 0.40 else int(245 * ((y - H * 0.40) / (H * 0.60)))
            grad.putpixel((0, y), min(max(a, 0), 245))
        black = Image.new("RGBA", (W, H), (0, 0, 0, 0)); black.putalpha(grad.resize((W, H)))
        img = Image.alpha_composite(img.convert("RGBA"), black)
        d = ImageDraw.Draw(img, "RGBA")
        M = 60

        bf = F(34); bw = d.textlength(bt, font=bf)
        d.rounded_rectangle([M, 55, M + bw + 36, 55 + bf.size + 18], radius=26, fill=ORANGE)
        d.text((M + 18, 62), bt, font=bf, fill=(255, 255, 255))
        rf = F(40); rtxt = f"{store.rating}"; tw = d.textlength(rtxt, font=rf); sr = 22; pad = 18
        rw = pad + sr * 2 + 10 + tw + pad
        rx = W - M - rw; rh = rf.size + pad
        d.rounded_rectangle([rx, 55, rx + rw, 55 + rh], radius=rh // 2, fill=(255, 255, 255))
        star(d, rx + pad + sr, 55 + rh // 2, sr, YELLOW)
        d.text((rx + pad + sr * 2 + 10, 62), rtxt, font=rf, fill=ORANGE)

        y = H - 540
        if hk:
            fh = fit(d, hk, W - M * 2, 58)
            d.text((M, y), hk, font=fh, fill=(255, 255, 255)); y += fh.size + 22
        if price_val:
            d.text((M, y), "เริ่มต้นเพียง" if "-" in (store.price_range or "") else "เพียง",
                   font=F(38, False), fill=YELLOW); y += 46
            fb = fit(d, price_val, W - M * 2, 150)
            d.text((M - 4, y), price_val, font=fb, fill=YELLOW); y += fb.size + 14
        d.text((M, y), nm, font=fit(d, nm, W - M * 2, 42, b=False), fill=(240, 240, 240))
        cy = H - 130
        d.rounded_rectangle([M, cy, W - M, cy + 78], radius=39, fill=ORANGE)
        cta = "สั่งเลย — ลิงก์ใต้โพสต์ ↓"; fc = F(42); cw = d.textlength(cta, font=fc)
        d.text(((W - cw) // 2, cy + 16), cta, font=fc, fill=(255, 255, 255))

    os.makedirs(settings.media_dir, exist_ok=True)
    out = os.path.join(settings.media_dir, f"promo_{store.id}_{uuid.uuid4().hex[:6]}.png")
    img.convert("RGB").save(out, quality=92)
    return out
