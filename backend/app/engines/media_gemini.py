"""Gemini media — ภาพ "Nano Banana" + วีดีโอ Veo (ผ่าน Flow).

ไม่มี key → สร้าง placeholder 9:16 ด้วย PIL เพื่อให้ flow เดินได้.
"""
from __future__ import annotations

import os
import time
import uuid

from ..config import settings


def _placeholder(prompt: str, kind: str) -> str:
    """รูป 9:16 พร้อมข้อความ prompt — ใช้แทนตอนยังไม่ใส่ Gemini key."""
    from PIL import Image, ImageDraw
    os.makedirs(settings.media_dir, exist_ok=True)
    path = os.path.join(settings.media_dir, f"{kind}_{uuid.uuid4().hex[:8]}.png")
    img = Image.new("RGB", (720, 1280), (250, 245, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 720, 120], fill=(238, 108, 77))
    d.text((24, 45), f"[MOCK {kind.upper()}]", fill="white")
    # ตัด prompt ขึ้นจอเป็นบรรทัด
    words, line, y = prompt.split(), "", 200
    for w in words:
        if len(line) + len(w) > 42:
            d.text((24, y), line, fill=(60, 60, 60)); y += 34; line = ""
        line += w + " "
    d.text((24, y), line, fill=(60, 60, 60))
    img.save(path)
    return path


def _client():
    from google import genai
    return genai.Client(api_key=settings.gemini_api_key)


def generate_image(prompt: str) -> str:
    """สร้างภาพ 9:16 → คืน path ไฟล์."""
    if not settings.has_gemini:
        return _placeholder(prompt, "image")
    try:
        client = _client()
        resp = client.models.generate_content(
            model=settings.image_model,
            contents=[prompt + " — vertical 9:16 aspect ratio, high quality"],
        )
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                os.makedirs(settings.media_dir, exist_ok=True)
                path = os.path.join(settings.media_dir, f"image_{uuid.uuid4().hex[:8]}.png")
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
        return _placeholder(prompt, "image")
    except Exception as e:  # pragma: no cover
        print(f"[gemini] image error: {e}")
        return _placeholder(prompt, "image")


def generate_video(prompt: str) -> str:
    """สร้างวีดีโอสั้น 9:16 ด้วย Veo → คืน path ไฟล์ mp4."""
    if not settings.has_gemini or not settings.enable_video:
        return _placeholder(prompt, "video")
    try:
        client = _client()
        op = client.models.generate_videos(model=settings.video_model, prompt=prompt)
        for _ in range(30):                       # poll สูงสุด ~5 นาที
            if op.done:
                break
            time.sleep(10)
            op = client.operations.get(op)
        vid = op.response.generated_videos[0]
        os.makedirs(settings.media_dir, exist_ok=True)
        path = os.path.join(settings.media_dir, f"video_{uuid.uuid4().hex[:8]}.mp4")
        client.files.download(file=vid.video)
        vid.video.save(path)
        return path
    except Exception as e:  # pragma: no cover
        print(f"[gemini] video error: {e}")
        return _placeholder(prompt, "video")


# มุมกล้องสไตล์ food reel ปังๆ — ใช้สร้างภาพหลายช็อตคนละมุม (แก้ปัญหาคลิปซ้ำ/น่าเบื่อ)
_BROLL_ANGLES = [
    "extreme macro close-up, steam rising, shallow depth of field, droplets glistening",
    "top-down flat lay, ingredients and garnish arranged around the bowl, bright clean",
    "chopsticks lifting noodles mid-air, broth dripping, dynamic motion, side angle",
    "45-degree hero shot, garnish in sharp focus, creamy bokeh background, warm light",
    "pouring broth / spooning sauce action shot, splash, appetizing, dramatic light",
    "cozy hand holding the bowl, blurred restaurant background, lifestyle vibe",
]


def download_images(urls: list[str], n: int = 4) -> list[str]:
    """โหลดรูปจริง (เช่นจาก Shopee) มาผสมในคลิป → ของจริง + AI = น่าเชื่อถือ.
    Shopee อาจบล็อก hotlink (403) → ข้ามไฟล์ที่โหลดไม่ได้ คืนเท่าที่ได้."""
    import httpx
    out = []
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://shopee.co.th/"}
    for u in [x for x in (urls or []) if x][:n]:
        try:
            r = httpx.get(u, timeout=30, follow_redirects=True, headers=headers)
            if r.status_code == 200 and len(r.content) > 3000:
                os.makedirs(settings.media_dir, exist_ok=True)
                p = os.path.join(settings.media_dir, f"real_{uuid.uuid4().hex[:8]}.jpg")
                with open(p, "wb") as f:
                    f.write(r.content)
                out.append(p)
        except Exception as e:  # pragma: no cover
            print(f"[img dl] {str(e)[:80]}")
    return out


def generate_food_broll(dish: str, n: int = 6) -> list[str]:
    """สร้างภาพอาหารหลายมุมคนละช็อต (B-roll) จากเมนูเดียว → คลิปไม่ซ้ำ ดูมีชีวิต.
    ไม่มี key → placeholder. คืน list ของ path ภาพ."""
    dish = (dish or "delicious thai food").strip()
    out = []
    for ang in _BROLL_ANGLES[:max(1, n)]:
        prompt = (f"appetizing professional food photography of {dish}, {ang}, "
                  "vibrant mouthwatering colors, 9:16 vertical, ultra detailed, no text")
        out.append(generate_image(prompt))
    return out


def make_media(image_prompt: str, video_prompt: str, hook: str = "") -> tuple[str, str, str]:
    """คืน (media_type, media_path, image_path) ตาม VIDEO_MODE.
    image_path = ภาพต้นฉบับ เก็บไว้ใช้ทำคลิปรวม (montage) ภายหลัง.
    image  = ภาพนิ่ง 9:16 (ฟรี) · ffmpeg = ภาพ AI → วีดีโอ Reels ฟรี · veo = Veo (เสียเงิน)."""
    mode = settings.video_mode
    if mode == "veo" or (settings.enable_video and mode == "image"):
        return "video", generate_video(video_prompt), ""
    if mode == "ffmpeg":
        img = generate_image(image_prompt)              # ภาพฟรีจาก Gemini ก่อน
        from . import video_ffmpeg
        vid = video_ffmpeg.image_to_reel(img, hook)     # แปลงเป็นวีดีโอ
        return ("video", vid, img) if vid else ("image", img, img)
    img = generate_image(image_prompt)
    return "image", img, img
