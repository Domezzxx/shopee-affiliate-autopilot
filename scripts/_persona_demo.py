# -*- coding: utf-8 -*-
"""เดโม: สร้าง reel อาหาร (เสียงผู้ชาย) + persona PiP พูดมุมจอ — ร้าน id ที่ส่งมา."""
import sys, os
sys.path.insert(0, "backend")

from sqlmodel import select
from app.db import get_session, Store, Variant
from app.engines import video_ffmpeg, talking_head

STORE_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 2
VOICE = "th-TH-NiwatNeural"   # เสียงผู้ชาย (persona หนุ่ม)

with get_session() as s:
    store = s.get(Store, STORE_ID)
    vs = s.exec(select(Variant).where(Variant.store_id == STORE_ID, Variant.label == "A")).all()
    scenes, narration, seen = [], [], set()
    for v in vs:
        img = v.image_path or (v.media_path if v.media_type == "image" else "")
        if img and os.path.exists(img) and img not in seen:
            seen.add(img)
            scenes.append((img, v.hook))
            narration.append(v.voiceover_script or v.hook)
    name = store.name

print(f"store: {name[:40]}  scenes: {len(scenes)}")
if not scenes:
    print("NO SCENES — รันร้านนี้ก่อน"); sys.exit(1)

cta = [name[:24], "สั่งเลยตอนนี้!", "ลิงก์ในคอมเมนต์แรก"]
print("[1/2] สร้าง reel อาหาร (เสียงผู้ชาย)...")
food = video_ffmpeg.build_reel(scenes, narration=" ".join(narration), voice=VOICE, cta_lines=cta)
print("   food reel:", food)
if not food:
    print("FAIL build_reel"); sys.exit(2)

print("[2/2] ใส่ persona พูดมุมจอ (Wav2Lip)...")
print("   persona available:", talking_head.available())
final = talking_head.add_persona_pip(food, width=380, corner="tr")
print("RESULT:", final)
if final:
    open("data/persona/_last_persona_reel.txt", "w", encoding="utf-8").write(final)
