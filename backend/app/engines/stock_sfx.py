# -*- coding: utf-8 -*-
"""เสียง ASMR อาหารจริง (ซด/ซิซเซิล/ราดน้ำซุป/เคี้ยว) จาก Freesound — ฟรี.

ใช้คลอใต้เสียงพากย์ ให้คลิป "ได้ยินความอร่อย" เหมือนรีวิวจริง.
(footage สต็อกเงียบ → ดึงเสียงจาก Freesound แทน). ไม่มี key → คืน None.
"""
from __future__ import annotations

import os
import uuid

from ..config import settings

SEARCH = "https://freesound.org/apiv2/search/text/"
# เสียง "บรรยากาศร้าน" ยาวต่อเนื่อง (ไม่ใช่ SFX สั้นวนลูป) — ฟังลื่น เหมือนนั่งในร้าน
# หมายเหตุ: ใช้คำง่ายๆ คำเดียว/สองคำ (Freesound หาเจอ) — คำยาวมักได้ none
AMBIENCE_QUERIES = ["restaurant ambience", "restaurant background", "food court",
                    "diner ambience", "cafe ambience", "kitchen ambience"]


def available() -> bool:
    return bool(settings.freesound_api_key)


def search_ambience(queries: list[str] | None = None) -> str | None:
    """หาเสียงบรรยากาศร้าน 'ยาว' (20-120 วิ) 1 ไฟล์ → คลอได้ทั้งคลิปไม่ต้องวนลูป."""
    if not settings.freesound_api_key:
        return None
    import httpx
    queries = queries or AMBIENCE_QUERIES
    headers = {"Authorization": f"Token {settings.freesound_api_key}"}
    os.makedirs(settings.media_dir, exist_ok=True)
    with httpx.Client(timeout=40, follow_redirects=True) as c:
        for q in queries:
            try:
                r = c.get(SEARCH, headers=headers,
                          params={"query": q, "fields": "previews,duration,name",
                                  "filter": "duration:[20 TO 120]", "page_size": 5, "sort": "score"})
                if r.status_code != 200:
                    continue
                for res in r.json().get("results", []):
                    prev = res.get("previews") or {}
                    url = prev.get("preview-hq-mp3") or prev.get("preview-lq-mp3")
                    if not url:
                        continue
                    dl = c.get(url)
                    if dl.status_code == 200 and len(dl.content) > 20000:
                        raw = os.path.join(settings.media_dir, f"_amraw_{uuid.uuid4().hex[:6]}.mp3")
                        with open(raw, "wb") as f:
                            f.write(dl.content)
                        # re-encode ให้สะอาด + ตัด 60 วิ + fade (กัน mp3 เสียตอน stream_loop)
                        from . import video_ffmpeg as vf
                        clean = os.path.join(settings.media_dir, f"amb_{uuid.uuid4().hex[:8]}.m4a")
                        ok = vf._run(vf.find_ffmpeg(), ["-i", raw, "-t", "60", "-ac", "2", "-ar", "44100",
                                                        "-af", "afade=t=in:d=0.5", "-c:a", "aac", clean])
                        if os.path.exists(raw):
                            os.remove(raw)
                        if ok and os.path.exists(clean):
                            print(f"[freesound] ใช้บรรยากาศ: {res.get('name','')[:40]} ({res.get('duration',0):.0f}s)")
                            return clean
            except Exception as e:  # pragma: no cover
                print(f"[freesound] {q}: {str(e)[:80]}")
    return None


def build_sfx_bed(queries: list[str] | None = None, n: int = 4) -> str | None:
    """คืนเสียงบรรยากาศร้านยาวๆ 1 ไฟล์ (คลอใต้เสียงพากย์ ฟังลื่น ไม่วนลูปน่ารำคาญ)."""
    return search_ambience(queries)
