# -*- coding: utf-8 -*-
"""เดโม "ปรับฟรีให้ปัง" ครบ 4: รูปจริง Shopee + AI หลายมุม / xfade / ความเร็วแปรผัน / persona วงกลม."""
import sys, os
sys.path.insert(0, "backend")

from sqlmodel import select
from app.db import get_session, Store, Variant, jloads
from app.engines import media_gemini, video_ffmpeg, talking_head

STORE_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 2
VOICE = "th-TH-NiwatNeural"

with get_session() as s:
    store = s.get(Store, STORE_ID)
    img_urls = jloads(store.image_urls_json, [])
    vs = s.exec(select(Variant).where(Variant.store_id == STORE_ID, Variant.label == "A")).all()
    narration = " ".join(v.voiceover_script or v.hook for v in vs) or \
        "ก๋วยเตี๋ยวเรือเจ้านี้ เส้นนุ่ม น้ำซุปเข้มข้น ราคาคุ้มมาก ต้องลองเลยครับ"
    name = store.name

dish = "Thai boat noodles (kuay teow reua), beef, herbs, dark rich broth"
print(f"store: {name[:34]}  shopee urls: {len(img_urls)}")

print("[1/4] โหลดรูปจริงจาก Shopee...")
real = media_gemini.download_images(img_urls, n=3)
print(f"   ได้รูปจริง {len(real)} รูป")

print("[2/4] สร้างภาพ AI หลายมุมเสริม...")
ai = media_gemini.generate_food_broll(dish, n=5)
ai = [p for p in ai if p and os.path.exists(p)]
print(f"   ได้ภาพ AI {len(ai)} รูป")

# สลับ จริง-AI ให้น่าเชื่อถือ + หลากหลาย
mixed, i, j = [], 0, 0
while i < len(real) or j < len(ai):
    if i < len(real):
        mixed.append(real[i]); i += 1
    if j < len(ai):
        mixed.append(ai[j]); j += 1
scenes = [(p, "") for p in mixed]
print(f"   รวม {len(scenes)} ช็อต (จริง+AI สลับ)")

cta = [name[:24], "สั่งเลยตอนนี้!", "ลิงก์ในคอมเมนต์แรก"]
print("[3/4] สร้าง reel (xfade + ความเร็วแปรผัน + เกรดสี + เสียงผู้ชาย)...")
food = video_ffmpeg.build_reel(scenes, narration=narration, voice=VOICE, cta_lines=cta)
print("   food:", food)
if not food:
    sys.exit(2)

print("[4/4] persona วงกลม TikTok พูดมุมจอ...")
final = talking_head.add_persona_pip(food, width=360, corner="tr")  # ใช้ shape=circle (default)
print("RESULT:", final)
if final:
    open("data/persona/_last_v2.txt", "w", encoding="utf-8").write(final)
