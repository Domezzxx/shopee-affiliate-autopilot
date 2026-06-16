"""เสียงพากย์ไทยฟรี — edge-tts (เสียงนิวรัล Microsoft) → gTTS เป็น fallback.

synth(text) -> path ไฟล์ mp3 หรือ None.
ไม่มีเน็ต/ลิบ -> None (วีดีโอจะไม่มีเสียงพากย์ แต่ไม่ล่ม).
"""
from __future__ import annotations

import asyncio
import os
import uuid

from ..config import settings


def synth(text: str, voice: str | None = None) -> str | None:
    text = (text or "").strip()
    if not text or not settings.enable_voiceover:
        return None
    v = voice or settings.tts_voice
    os.makedirs(settings.media_dir, exist_ok=True)
    out = os.path.join(settings.media_dir, f"voice_{uuid.uuid4().hex[:8]}.mp3")

    # 1) edge-tts (คุณภาพดีสุด ฟรี) — เก็บเสียงผ่าน stream() + retry (endpoint ฟรีตอบบ้างไม่ตอบบ้าง)
    try:
        import time

        import edge_tts

        async def _go() -> bytes:
            data = b""
            async for chunk in edge_tts.Communicate(text, v).stream():
                if chunk["type"] == "audio":
                    data += chunk["data"]
            return data

        for attempt in range(4):
            try:
                audio = asyncio.run(_go())
                if audio:
                    with open(out, "wb") as f:
                        f.write(audio)
                    if os.path.getsize(out) > 500:
                        return out
            except Exception as e:
                print(f"[tts] edge-tts attempt {attempt + 1}/4: {e}")
            time.sleep(0.6)
    except Exception as e:  # pragma: no cover
        print(f"[tts] edge-tts unavailable: {e}")

    # 2) gTTS fallback
    try:
        from gtts import gTTS
        gTTS(text=text, lang="th").save(out)
        if os.path.exists(out) and os.path.getsize(out) > 500:
            return out
    except Exception as e:  # pragma: no cover
        print(f"[tts] gTTS error: {e}")
    return None
