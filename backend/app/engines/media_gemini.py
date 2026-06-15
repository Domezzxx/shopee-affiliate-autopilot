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


def make_media(image_prompt: str, video_prompt: str) -> tuple[str, str]:
    """คืน (media_type, path) — วีดีโอถ้าเปิด ENABLE_VIDEO ไม่งั้นภาพ."""
    if settings.enable_video:
        return "video", generate_video(video_prompt)
    return "image", generate_image(image_prompt)
