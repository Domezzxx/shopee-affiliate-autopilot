# -*- coding: utf-8 -*-
"""เดโม "รีวิวจริง": footage อาหารจริง (Pexels) + รูป Shopee + AI + persona วงกลม."""
import sys, os
sys.path.insert(0, "backend")

from sqlmodel import select
from app.db import get_session, Store, Variant, jloads
from app.engines import media_gemini, stock_video, video_ffmpeg, talking_head

STORE_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 2
VOICE = "th-TH-NiwatNeural"

with get_session() as s:
    store = s.get(Store, STORE_ID)
    img_urls = jloads(store.image_urls_json, [])
    vs = s.exec(select(Variant).where(Variant.store_id == STORE_ID, Variant.label == "A")).all()
    # สคริปต์เดียว กระชับ (ไม่เอา 3 อันต่อกัน → คลิปไม่ยาวเกิน)
    scripts = [v.voiceover_script for v in vs if v.voiceover_script]
    narration = (scripts[0] if scripts else
                 "เห็นแบบนี้ต้องลอง! ก๋วยเตี๋ยวเรือเจ้านี้ เส้นนุ่ม น้ำซุปเข้มข้น คุ้มมาก สั่งเลยครับ")
    name = store.name

with get_session() as s:
    menu = jloads(s.get(Store, STORE_ID).menu_json, [])
dish = "Thai boat noodles (kuay teow reua), beef, herbs, dark rich broth"
print(f"store: {name[:32]}")

print("[1/5] ดึง footage อาหารจริง (คิวรีตรงเมนูไทย)...")
print("   key available:", stock_video.available())
queries = stock_video.build_queries(name + " " + dish, menu)
print("   queries:", queries[:4])
stock = stock_video.search_food_clips(queries, n=6)
print(f"   ได้ footage จริง {len(stock)} คลิป")

print("[2/5] รูป Shopee/AI สำหรับฉาก CTA เท่านั้น (ฉากหลัก = วีดีโอล้วน)...")
real = media_gemini.download_images(img_urls, n=1)
cta_img = real[0] if real else (media_gemini.generate_food_broll(dish, n=1) or [None])[0]
print(f"   cta image: {os.path.basename(cta_img) if cta_img else 'none'}")

# ฉากหลัก = วีดีโอจริงล้วน (ไม่มีภาพนิ่งซูม = ไม่เหมือนสไลด์)
items = stock
print(f"[3/5] ฉากหลัก {len(items)} ช็อต = วีดีโอจริงล้วน")

cta = [name[:24], "สั่งเลยตอนนี้!", "ลิงก์ในคอมเมนต์แรก"]
print("[4/5] สร้างคลิปรีวิว (วีดีโอล้วน + xfade + เกรดสี + เสียงผู้ชาย + ASMR)...")
food = video_ffmpeg.build_review_reel(items, narration=narration, voice=VOICE,
                                      cta_lines=cta, cta_image=cta_img)
print("   food:", food)
if not food:
    sys.exit(2)

print("[5/5] persona วงกลมพูดมุมจอ...")
final = talking_head.add_persona_pip(food, width=340, corner="tr")
print("RESULT:", final)
if final:
    open("data/persona/_last_review.txt", "w", encoding="utf-8").write(final)
