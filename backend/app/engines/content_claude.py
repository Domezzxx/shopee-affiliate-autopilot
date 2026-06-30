"""AI สมอง — Claude เขียนแคปชั่น/สคริปต์/A-B variant + คอมเมนต์แรก + วิเคราะห์ร้าน + ตารางโพสต์.

ออก JSON ตาม schema คงที่ (structured outputs) → ไม่ต้อง parse เดา.
ไม่มี API key → คืน mock ที่หน้าตาเหมือนจริง เพื่อให้ทั้งระบบเดินได้ทันที.
"""
from __future__ import annotations

import json
from typing import Any

from ..config import settings

# 4 platform × A/B = 8 variant ต่อร้าน
PLATFORMS = ["facebook", "instagram", "youtube", "shopee_video"]

CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "store_analysis": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "strengths": {"type": "array", "items": {"type": "string"}},
                "target_audience": {"type": "string"},
                "best_platform": {"type": "string", "enum": PLATFORMS},
                "hook_angle": {"type": "string"},
            },
            "required": ["strengths", "target_audience", "best_platform", "hook_angle"],
        },
        "variants": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string", "enum": ["A", "B"]},
                    "platform": {"type": "string", "enum": PLATFORMS},
                    "hook": {"type": "string"},
                    "video_title": {"type": "string"},
                    "caption": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "cta": {"type": "string"},
                    "first_comment": {"type": "string"},
                    "voiceover_script": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "video_prompt": {"type": "string"},
                },
                "required": ["label", "platform", "hook", "video_title", "caption", "hashtags",
                             "cta", "first_comment", "voiceover_script",
                             "image_prompt", "video_prompt"],
            },
        },
        "posting_schedule": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "platform": {"type": "string", "enum": PLATFORMS},
                    "time_hint": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["platform", "time_hint", "reason"],
            },
        },
    },
    "required": ["store_analysis", "variants", "posting_schedule"],
}

# สมองสคริปต์ระดับโลก (Sprint 3): hook ดึง + voiceover แบบ spoken-word (กลายเป็นซับเด้งตามเสียง)
SYSTEM = (
    "คุณคือ short-form content creator ระดับโลก สาย food/affiliate ที่ทำรีลไทยปังจนคนดูจบแล้วกดสั่ง.\n"
    "เป้าหมาย: คนหยุดนิ้วใน 1 วิแรก → ดูจนจบ → กดลิงก์.\n\n"
    "หลักการที่ต้องใช้ทุกครั้ง:\n"
    "• HOOK (วิแรก) = ตัวตัดสิน ใช้สูตร: คำถามสะกิด / ตัวเลขช็อก / ความขัดแย้ง ('ราคานี้ได้ไง?') / "
    "คำสั่งห้าม ('อย่าเพิ่งเลื่อนผ่าน'). ห้ามเปิดด้วยชื่อร้านหรือคำเฝือ.\n"
    "• video_title = ชื่อคลิป YouTube/TikTok สไตล์อินฟลูเอนเซอร์อาหารไทยให้ปังจนคนกดดู: "
    "ขึ้นด้วยตัวเลข/ราคา/อารมณ์ความคุ้ม + ชื่อเมนูเด่นชัดเจน + อีโมจิ 1-2 ตัว, "
    "ยาว 30-55 ตัวอักษร, สร้าง curiosity ('...จริงดิ?', 'ต้องลอง', 'บอกต่อ', 'เจ้าเด็ด'), "
    "ห้ามยัด hashtag ยาว (ระบบเติม #Shorts ให้เอง). "
    "ตัวอย่างโทน: '40 บาทอิ่มจุก! ก๋วยเตี๋ยวเรือเจ้านี้ต้องลอง 🔥' / "
    "'บอกเลยว่าคุ้ม 😋 12 หม้อ 75 บาท ที่ต้องสั่ง'.\n"
    "• voiceover_script = บทพูดรีล 10-15 วิ เขียนแบบ 'พูด' ไม่ใช่ 'อ่าน' — ประโยคสั้นๆ เป็นจังหวะต่อเนื่อง: "
    "[hook แรง] → [จุดขาย 1-2 อย่างที่เจาะจง เห็นภาพ ได้กลิ่น/รส] → [CTA ชวนกด]. "
    "เหมือนคุยกับเพื่อน มีพลัง ไม่ขายของจ๋า. **บทนี้จะกลายเป็นซับไตเติลเด้งตามเสียง ทุกวลีต้องโดน**.\n"
    "• เจาะจง ชนะ กว้างๆ เสมอ: 'เส้นนุ่ม น้ำซุปเคี่ยว 8 ชม.' > 'อร่อยมาก'.\n"
    "• A vs B ต้องคนละมุมจริง: A = สายคุ้ม/ดีล/ตัวเลข, B = สายฟิน/ดราม่าหิว/ASMR. ห้ามคล้ายกัน.\n"
    "• โทนต่อ platform: FB=อบอุ่นแชร์ได้, IG=ฮิปมินิมอล, YouTube=เล่าเรื่องปากต่อปาก.\n"
    "• caption สั้น มี emoji พอดี เว้นบรรทัด ปิดด้วย CTA · first_comment ใส่ {LINK} · hashtags 4-6 อัน.\n"
    "• spoken_line + spoken_lang = 'บทพูดให้คนในคลิปพูดใส่กล้อง' — **1 ประโยคสั้นมาก ~6-12 คำ พูดจบสบายๆ ใน ~7 วินาที** "
    "(คลิปยาวแค่ ~8 วิ → ห้ามยาวจนพูดไม่ทัน/ถูกตัดกลางประโยค). พูดจริงไม่ใช่บรรยาย.\n"
    "  ★ กฎเหล็ก: **คำ 'แรกสุด' ของ spoken_line ต้องเป็น HOOK ที่สะกดให้หยุดนิ้วใน 1 วิ** (อย่าเปิดด้วยชื่อร้าน/คำทักทาย/คำเฝือ). "
    "และคลิปต้อง 'เปิดมาที่คนพูดเลย' (บทพูดคือสิ่งแรกที่ได้ยิน).\n"
    "  ★ หมุนเวียน 'สูตร hook' ให้ทุก variant คนละแบบ (ห้ามซ้ำสูตร/ห้ามขึ้นต้นเหมือนกัน): "
    "(1) คำถามสะกิด (2) ตัวเลข/ราคาช็อก (3) คำสั่งห้าม (4) ขัดแย้ง/เกินคาด (5) ดราม่าหิว (6) ความลับ/อินไซต์.\n"
    "  ★ spoken_lang เลือก thai | english | isaan ต้อง 'กระจายหลากหลาย' ข้าม variant (ห้ามภาษาเดียวทั้งหมด).\n"
    "  ★ **isaan = ภาษาอีสานแท้ พูดลื่นเป็นธรรมชาติเหมือนคนอีสานคุยกันจริง ไม่แข็ง ไม่ฝืน ไม่ใช่คนภาคกลางพยายามพูดอีสาน** — "
    "ใช้คำลงท้าย/คำเชื่อมอีสานจริง (เด้อ, สิ, กะ, อีหลี, โพด, คัก, จั่งแม่น, นัว) เช่น 'แซ่บคักอีหลี กินแล้วอยู่บ่ได้เด้อ', "
    "'จั่งแม่นแซ่บ มื้อนี้สั่งโลด', 'ลองเบิ่งเด้อ นัวโพดเลย'. "
    "english=โทนวัยรุ่นไวรัลสั้นๆ เช่น 'Wait—only 75 baht?!', 'Stop scrolling, trust me'.\n"
    "• image_prompt/video_prompt = อังกฤษ อาหารโคลสอัพน่ากินสุด มีไอ/ซอสยืด/แสงสวย 9:16 vertical, realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings.\n"
    "  **video_prompt ต้องสั่งให้คลิปเปิดมาที่คนพูดทันที** (ห้ามเปิดด้วยภาพอาหารนิ่งๆ ก่อน — น่าเบื่อ). โครงสร้าง: "
    "'Vertical 9:16. OPENS immediately on [ระบุผู้พูด] looking straight into camera, already mid-sentence with big friendly energy, saying: \"<บทพูดตรงกับ spoken_line>\". "
    "Then quick appetizing shots of [เมนู] behind/around them.' "
    "ระบุผู้พูดให้สมจริงตามภาษา: isaan→'a real local Northeastern-Thai (Isan) person speaking in authentic, natural, relaxed Isan/Lao-Isan accent (not stiff, not robotic, like a real local chatting)'; "
    "thai→'a real Thai person, natural casual spoken Thai'; english→'a trendy young food vlogger, natural casual English'. "
    "เพื่อให้ Veo สร้างคนพูด+เสียงจริง ลิปซิงค์ พูดให้จบประโยค — และ 'no on-screen text, no subtitles' (ห้ามตัวหนังสือบนจอ มีแค่เสียงพูด).\n"
    "ภาษาไทยธรรมชาติเหมือนคนรีวิวจริง."
)


def _learned_guidance() -> str:
    """ดึง 'บทเรียนจากผลงานจริง' (self-improvement loop) มาฉีดเข้า prompt — ทำให้บอทฉลาดขึ้นเรื่อยๆ.
    ถ้าข้อมูลยังไม่พอจะคืน '' (ไม่กระทบ prompt)."""
    try:
        from ..services.learning import insights_prompt
        return insights_prompt()
    except Exception:
        return ""


def _prompt(store: dict, label: str) -> str:
    if label == "A":
        style_desc = (
            "สไตล์คอนเทนต์กลุ่ม A (สายคุ้ม/โปรโมชั่น/ตัวเลข):\n"
            "- เน้นเรื่องความคุ้มค่า ราคาประหยัด ดีลพิเศษ ส่วนลดเยอะ หรือเรตติ้งรีวิวจำนวนมาก\n"
            "- Hook ต้องสะกิดต่อมสายประหยัด เช่น 'ราคานี้ได้ยังไง?', 'คุ้มกว่านี้มีอีกไหม?'\n"
            "- video_title ต้องใช้ตัวเลขหรือยอดขาย หรือความประหยัดนำหน้า มีอีโมจิดึงดูด\n"
            "- voiceover_script ต้องพากย์เสียงพากย์ชวนตื่นเต้น มีพลัง พูดถึงดีลเด็ด ความคุ้มราคา คุ้มค่าและประหยัดแบบสะใจสุดๆ ดึงดูดให้อยู่ดูต่อ\n"
            "- image_prompt และ video_prompt ต้องเป็นภาษาอังกฤษ เน้นจานใหญ่ แสงสว่างสดใส (bright lighting) "
            "และมีองค์ประกอบของความคุ้มค่า (value-for-money atmosphere) พร้อมเงื่อนไขบังคับ "
            "'realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings'"
        )
    else:
        style_desc = (
            "สไตล์คอนเทนต์กลุ่ม B (สายฟิน/ดราม่าหิว/ASMR):\n"
            "- เน้นย้ำเรื่องความอร่อยแสงออกปาก กลิ่นหอมฟุ้งลอยมา ควันฉุยไหลเยิ้ม คลื่นเสียง ASMR ทรมานใจยามดึก\n"
            "- Hook ต้องเปิดด้วยอาการทรมานความหิว เช่น 'เห็นคลิปนี้ตอนดึกขออภัยด้วยนะ', 'คำแรกถึงกับหลับตาฟิน'\n"
            "- video_title เน้นความฟิน ความแซ่บ หรือความอร่อยที่หยุดไม่อยู่\n"
            "- voiceover_script ต้องพากย์เสียงพากย์ด้วยคำบรรยายที่เห็นภาพชัดเจน รสชาตินุ่มละมุน ความเข้มข้น ความหอมกรุ่นชวนกิน เพื่อกระตุ้นความหิวดึงดูดให้อยู่ดูต่อจนจบ\n"
            "- image_prompt และ video_prompt ต้องเป็นภาษาอังกฤษ เน้นความรู้สึกอยากกินแบบสุดขีด (mouthwatering close-up) "
            "มีควันลอยฉุย (steam rising) หรือน้ำซุป/ซอสไหลเยิ้ม (sauce pouring / cheese pull) "
            "พร้อมเงื่อนไขบังคับ 'realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings'"
        )
        
    # กระจายภาษาบทพูดให้หลากหลาย: A=ไทย/อังกฤษ/อีสาน, B=อีสาน/ไทย/อังกฤษ → ครบ 2 ภาษาต่อ 1 ภาษาใน 6 variant
    langs = (["thai", "english", "isaan"] if label == "A" else ["isaan", "thai", "english"])
    # สูตร HOOK ต่อ platform (คนละแบบทุกตัว กันซ้ำ) — คำแรกของ spoken_line ต้องมาจากสูตรนี้
    hooks = (["ตัวเลข/ราคาช็อก (เช่น '10 โลแค่ 172?!')",
              "ขัดแย้ง/เกินคาด (เช่น 'ถูกขนาดนี้มีจริงดิ')",
              "คำสั่งห้าม (เช่น 'อย่าเพิ่งปัดผ่าน!')"] if label == "A" else
             ["ดราม่าหิว/เตือนก่อนดู (เช่น 'เตือนแล้วนะ ดูตอนดึกทรมาน')",
              "คำถามสะกิด (เช่น 'กล้ากินคำเดียวแล้วหยุดไหม?')",
              "ความลับ/อินไซต์ (เช่น 'คนในรู้ว่าต้องสั่งเจ้านี้')"])
    subtype = store.get("food_subtype", "")
    category = store.get("category", "food")
    subtype_guidance = ""
    if category == "food" and subtype:
        subtype_guidance = (
            f"คำแนะนำเพิ่มเติมสำหรับประเภทร้านย่อย '{subtype}':\n"
            f"- หากเป็น 'ร้านก๋วยเตี๋ยว': ปรับโทนคอนเทนต์ แคปชั่น และสคริปต์สั้น ให้เน้นบรรยากาศควันฉุย ซดน้ำซุปร้อนๆ รสชาติกลมกล่อม ความเหนียวนุ่มของเส้น ลูกชิ้นทำเองรสเด็ด หรือเนื้อเปื่อยชิ้นโต\n"
            f"- หากเป็น 'ร้านตามสั่ง': เน้นสไตล์ผัดกระทะไฟลุก (wok hei) ความรวดเร็วทันใจ เมนูหลากหลายที่มีให้เลือกชิม รสชาติจัดจ้านถึงเครื่อง กลิ่นหอมฟุ้งติดจมูก\n"
            f"- หากเป็น 'ของหวาน/เครื่องดื่ม': เน้นความละมุน หวานสดชื่น ดับร้อน หน้าตาสวยงามดูดี ถ่ายรูปสวย ชวนให้ไปถ่ายรูปเช็คอิน\n"
            f"- หากเป็นประเภทอื่น ๆ: ให้เน้นบรรยายความอร่อยเฉพาะตัวของเมนูนั้นๆ เป็นหลัก\n\n"
        )

    return (
        f"เขียนคอนเทนต์ affiliate สำหรับร้านนี้ในกลุ่มตัวเลือก {label} (สำหรับ Facebook, Instagram, YouTube รวม 3 variants):\n"
        f"- ชื่อร้าน: {store['name']}\n"
        f"- ย่าน: {store.get('area','')}\n"
        f"- เรตติ้ง: {store.get('rating')} ({store.get('review_count')} รีวิว)\n"
        f"- เมนูเด่น: {', '.join(store.get('menu', [])[:6])}\n"
        f"- ช่วงราคา: {store.get('price_range','')}\n"
        f"- ประเภทร้านย่อย: {subtype or 'ทั่วไป'}\n\n"
        f"{subtype_guidance}"
        f"{style_desc}\n\n"
        f"ข้อบังคับสำคัญ:\n"
        f"1. สร้างเฉพาะ variants ที่มีฟิลด์ label เป็น '{label}' เท่านั้น จำนวน 3 variants (platform ละ 1 ชิ้น)\n"
        f"2. ห้ามสร้าง label อื่นๆ ปะปนมาเด็ดขาด ทุก variant ใน list ต้องมี label: '{label}'\n"
        f"3. first_comment ใส่ {{LINK}} เสมอ\n"
        f"4. ทุก variant ต้องมี spoken_line (บทพูดคนในคลิป) + spoken_lang และ 'ฝัง spoken_line ลงใน video_prompt' "
        f"ในรูป a real person looks at camera and says: \"...\" (ตัวบทตรงกับ spoken_line เป๊ะ)\n"
        f"5. กำหนด spoken_lang ต่อ platform ในกลุ่มนี้: facebook='{langs[0]}', instagram='{langs[1]}', youtube='{langs[2]}' "
        f"(บทพูดต้องเป็นภาษานั้นจริง — isaan ใช้คำอีสานแท้)\n"
        f"6. spoken_line แต่ละ platform ต้องเปิดด้วย 'สูตร hook' คนละแบบดังนี้ (คำแรกสุดต้องโดนใน 1 วิ ห้ามขึ้นต้นซ้ำกัน): "
        f"facebook={hooks[0]} · instagram={hooks[1]} · youtube={hooks[2]}\n"
        f"7. ตอบกลับตามโครงสร้าง JSON_SKELETON ที่ระบุ"
        + _learned_guidance()
    )


def _mock(store: dict) -> dict:
    menu = store.get("menu", ["เมนูเด็ด"])[:1] or ["เมนูเด็ด"]
    dish = menu[0]
    area = store.get("area", "อุดร")
    variants = []
    subtype = store.get("food_subtype", "")
    if subtype == "ร้านก๋วยเตี๋ยว":
        hook_a = f"ซดน้ำซุปร้อนๆ ฟินๆ! {dish}ร้านนี้ {store.get('rating')}⭐ ราคาดีงามมาก! 🍜"
        title_a = f"ก๋วยเตี๋ยวซดน้ำซุปฟิน! {dish}ย่าน{area} ⭐ ต้องลอง 🔥"
        caption_a = f"🍜 ใครสายเส้นห้ามพลาด! {store['name']} เจ้าเด็ดย่าน{area}\nน้ำซุปเข้มข้น เส้นเหนียวนุ่มสุดๆ\nรีบกดสั่งมาซดร้อนๆ ที่บ้านเลย 👇"
        voice_a = f"ก๋วยเตี๋ยวฟินๆ ต้องร้านนี้เลย! {dish}ร้าน {store['name']} น้ำซุปหอมกลมกล่อม เส้นเหนียวนุ่ม แบงค์แดงมีทอน กดสั่ง Shopee Food ด่วน!"
        spoken_a = "ซดซุปร้อนๆ เส้นนุ่มฟินมาก!"

        hook_b = f"เตือนแล้วนะ… {dish}ร้านนี้ระวังซดหมดถ้วยไม่รู้ตัว! 😋"
        title_b = f"ซดเกลี้ยงชาม! {dish}เจ้าเด็ดย่าน{area} 😋"
        caption_b = f"สายก๋วยเตี๋ยวต้องซูด! 🚨\n{dish} {store['name']} น้ำซุปกลมกล่อม เส้นนุ่มเครื่องแน่น\nสั่ง Shopee Food ส่งไวทันใจ 🛵"
        voice_b = f"คำแรกก็วางชามไม่ลง! {dish}ร้าน {store['name']} น้ำซุปเข้มข้นเคี่ยวนาน ลูกชิ้นเด้งดึ๋ง สั่งมาฟินที่บ้านได้เลยผ่าน Shopee Food!"
        spoken_b = "แซ่บคักอีหลี ซดหมดชามเลยเด้อ!"
    elif subtype == "ร้านตามสั่ง":
        hook_a = f"ผัดไฟลุก กระทะหอมๆ! {dish}ร้านนี้ {store.get('rating')}⭐ อิ่มจุกราคาประหยัด! 🍳"
        title_a = f"ตามสั่งจานยักษ์! {dish}ย่าน{area} ⭐ คุ้มมาก 🔥"
        caption_a = f"🍳 อิ่มอร่อยตามใจสั่ง! {store['name']} ผัดร้อนๆ กลิ่นหอมกระทะย่าน{area}\nเมนูหลากหลาย ปริมาณจัดเต็ม\nกดสั่งในคอมเมนต์แรกเลย 👇"
        voice_a = f"ตามสั่งจานยักษ์อิ่มจุก! ร้าน {store['name']} กับเมนู {dish} ผัดไฟลุกหอมกระทะสุดๆ ราคาดีงาม แบงค์แดงมีทอน สั่งเลย!"
        spoken_a = "กระทะร้อนหอมฟุ้ง อิ่มคุ้มจัด!"

        hook_b = f"เตือนแล้วนะ… {dish}ตามสั่งร้านนี้ระวังจานเดียวไม่พอ! 😋"
        title_b = f"หอมกระทะไฟลุก! {dish}ตามสั่งเจ้าเด็ดย่าน{area} 😋"
        caption_b = f"สายกินตามสั่งห้ามพลาด! 🚨\n{dish} {store['name']} รสชาติเข้มข้นถึงใจ หอมกลิ่นไหม้กระทะอ่อนๆ\nกดสั่ง Shopee Food เลย 🛵"
        voice_b = f"กลิ่นหอมกระทะยั่วๆ มาแล้ว! {dish}ร้าน {store['name']} รสชาติเข้มข้นจัดจ้าน เครื่องแน่นเต็มคำ สั่งผ่าน Shopee Food ฟินแน่นอน!"
        spoken_b = "แซ่บคักอีหลี หอมกลิ่นกระทะคักๆ เด้อนี่!"
    elif subtype == "ของหวาน/เครื่องดื่ม":
        hook_a = f"หวานเย็นสดชื่น ดับร้อนฟินๆ! {dish}ร้านนี้ {store.get('rating')}⭐ ราคาดีงาม! 🍧"
        title_a = f"ของหวานดับร้อนสุดฟิน! {dish}ย่าน{area} ⭐ ราคาดีงาม 🔥"
        caption_a = f"🍧 สายหวานต้องเช็คอิน! {store['name']} ของอร่อยย่าน{area}\nหวานเย็นสดชื่น ถ่ายรูปสวยรสชาติละมุน\nกดสั่งดับร้อนด่วนเลย 👇"
        voice_a = f"เติมความหวานดับร้อนกันหน่อย! {dish}ร้าน {store['name']} ของหวานฟินๆ ละมุนลิ้น แบงค์แดงมีทอน สั่งผ่าน Shopee Food ได้เลย!"
        spoken_a = "หวานเย็นชื่นใจ ดับร้อนฟินสุดๆ!"

        hook_b = f"เตือนแล้วนะ… ของหวานร้านนี้ระวังคำเดียวหยุดไม่ได้! 😋"
        title_b = f"หวานละมุนฟินเวอร์! {dish}เจ้าเด็ดย่าน{area} 😋"
        caption_b = f"สายของหวานห้ามพลาด! 🚨\n{dish} {store['name']} หอมหวานมันเข้มข้น ฟินทุกคำที่กิน\nสั่งผ่าน Shopee Food ส่งตรงถึงบ้าน 🛵"
        voice_b = f"ความอร่อยแสงออกปากมาเสิร์ฟแล้ว! {dish}ร้าน {store['name']} รสชาติละมุนลิ้น หวานพอดีๆ กินแล้วฟินสุดๆ สั่งผ่าน Shopee Food ด่วน!"
        spoken_b = "หวานมันแซ่บคัก กินแล้วหยุดบ่ได้เลยเด้อ!"
    else:
        hook_a = f"{dish}ร้านนี้ {store.get('rating')}⭐ แต่ราคาเท่านี้เอง?! 🤯"
        title_a = f"คุ้มเกินราคา! {dish}ย่าน{area} {store.get('rating')}⭐ ต้องลอง 🔥"
        caption_a = f"{store['name']} {dish}เด็ดย่าน{area}\nจาก {store.get('review_count')} รีวิวตัวจริง\nคุ้มแบบนี้รีบสั่งเลย 👇"
        voice_a = f"บอกเลยว่าคุ้มสุดๆ! {dish}ร้าน {store['name']} {store.get('rating')} ดาว สั่งผ่าน Shopee Food คุ้มราคา แบงค์แดงมีทอน ลิงก์อยู่คอมเมนต์เลย!"
        spoken_a = "ราคานี้ได้ไงเนี่ย คุ้มเกินไปแล้ว!"

        hook_b = f"เตือนแล้วนะ… {dish}ร้านนี้กินคำแรกแล้วหยุดไม่ได้ 😋"
        title_b = f"กินคำแรกแล้วหยุดไม่ได้ 😋 {dish}เจ้าเด็ดย่าน{area}"
        caption_b = f"สายกินห้ามพลาด 🚨\n{dish} {store['name']} ฟินทุกคำ\nนุ่ม หอม จัดเต็ม ส่งไวถึงบ้าน 🛵"
        voice_b = f"คำแรกก็ใจละลาย! {dish}ร้าน {store['name']} รสชาติกลมกล่อม หอมน้ำซุปเข้มข้นจนต้องร้องว้าว สั่งผ่าน Shopee Food ฟินด่วนๆ เลย!"
        spoken_b = "แซ่บคักอีหลี กินแล้วอยู่บ่ได้เด้อ!"

    for p in PLATFORMS:
        variants.append({
            "label": "A", "platform": p,
            "hook": hook_a,
            "video_title": title_a,
            "caption": caption_a,
            "hashtags": ["#กินอะไรดี", f"#{area.replace(' ','')}", "#ShopeeFood", "#ของกินคุ้ม", "#รีวิวร้านอร่อย"],
            "cta": "แตะลิงก์คอมเมนต์แรกสั่งเลย ก่อนโปรหมด!",
            "first_comment": f"🔗 สั่ง {dish} ร้าน {store['name']} ได้เลย 👉 {{LINK}}\nส่งไว ราคาคุ้ม 🛵",
            "voiceover_script": voice_a,
            "spoken_lang": "thai",
            "spoken_line": spoken_a,
            "image_prompt": f"appetizing close-up of {dish}, thai food, vibrant colors, price tag vibe, 9:16 vertical, food photography",
            "video_prompt": f"Vertical 9:16. OPENS immediately on a real Thai person looking into camera, already mid-sentence with big energy, saying: \"{spoken_a}\". Then quick appetizing shots of {dish} steaming hot behind them. realistic human actor, real person, photorealistic, no cartoons, value-for-money mood, no on-screen text, no subtitles",
        })
        variants.append({
            "label": "B", "platform": p,
            "hook": hook_b,
            "video_title": title_b,
            "caption": caption_b,
            "hashtags": [f"#ของกิน{area.replace(' ','')}", "#คาเฟ่อุดร", "#ShopeeFood", "#กินจุก", "#ฟินเวอร์"],
            "cta": "สั่งเลยก่อนหิวกว่านี้ ลิงก์คอมเมนต์แรก!",
            "first_comment": f"😋 ทนหิวไม่ไหวแล้วใช่ไหม กดสั่งเลย 👉 {{LINK}}",
            "voiceover_script": voice_b,
            "spoken_lang": "isaan",
            "spoken_line": spoken_b,
            "image_prompt": f"top-down flatlay of {dish} with side dishes, warm cozy light, mouthwatering, 9:16 vertical",
            "video_prompt": f"Vertical 9:16. OPENS immediately on a real local Northeastern-Thai (Isan) person looking into camera, already mid-sentence in authentic natural relaxed Isan accent (not stiff), saying: \"{spoken_b}\". Then quick appetizing close-up of {dish} behind them. realistic human actor, real person, photorealistic, no cartoons, no on-screen text, no subtitles",
        })
    return {
        "store_analysis": {
            "strengths": [f"เรตติ้งสูง {store.get('rating')}", f"รีวิวเยอะ {store.get('review_count')} น่าเชื่อถือ", f"{dish}เป็นพระเอก"],
            "target_audience": f"วัยรุ่น-วัยทำงานย่าน{area} ชอบสั่งเดลิเวอรี่",
            "best_platform": "facebook",
            "hook_angle": "ความคุ้ม (A) ปะทะ ดราม่าหิว (B)",
        },
        "variants": variants,
        "posting_schedule": [
            {"platform": "facebook", "time_hint": "11:00", "reason": "ก่อนมื้อเที่ยง คนหาของกิน"},
            {"platform": "instagram", "time_hint": "17:30", "reason": "เลิกงาน เลื่อนฟีดหาของเย็น"},
            {"platform": "youtube", "time_hint": "20:00", "reason": "ไพรม์ไทม์ดู Shorts"},
        ],
    }


def _strip_json(text: str) -> str:
    """ดึง JSON ออกจากข้อความ — เผื่อ Claude ห่อด้วย ```json ... ``` หรือมีคำเกริ่นนำ."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    s, e = t.find("{"), t.rfind("}")
    return t[s:e + 1] if s != -1 and e != -1 else t


def _claude_generate(store: dict, label: str) -> tuple[dict, float]:
    """เขียนคอนเทนต์ด้วย Claude — ขอ JSON ผ่าน prompt แล้ว parse (รองรับ anthropic SDK 0.45)."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"{_prompt(store, label)}\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น (ไม่มีข้อความอื่น ไม่มี markdown code fence) ตามโครงนี้เป๊ะ:\n{_JSON_SKELETON}"
    )
    resp = client.messages.create(
        model=settings.content_model,
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(_strip_json(text))
    u = resp.usage
    cost_usd = (u.input_tokens * 3 + u.output_tokens * 15) / 1_000_000   # sonnet 4.6
    return data, round(cost_usd * 36, 3)


_JSON_SKELETON = (
    '{\n'
    '  "store_analysis": {"strengths": ["..."], "target_audience": "...", '
    '"best_platform": "facebook|instagram|youtube|shopee_video", "hook_angle": "..."},\n'
    '  "variants": [   // ต้องมี 4 ชิ้นสำหรับ label ที่กำหนดต่อทุก platform (facebook, instagram, youtube, shopee_video)\n'
    '    {"label": "A|B", "platform": "facebook|instagram|youtube|shopee_video", "hook": "...", '
    '"video_title": "ชื่อคลิปไวรัลสไตล์อินฟลูอาหาร 30-55 ตัวอักษร มีตัวเลข+เมนู+อีโมจิ", '
    '"caption": "...", "hashtags": ["#..."], "cta": "...", '
    '"first_comment": "... {LINK} ...", "voiceover_script": "...", '
    '"spoken_lang": "thai|english|isaan", '
    '"spoken_line": "บทพูดสั้นที่คนในคลิปพูดใส่กล้อง ตรงกับ spoken_lang", '
    '"image_prompt": "english, 9:16 vertical", '
    '"video_prompt": "Vertical 9:16. OPENS immediately on [ผู้พูดตามภาษา] looking into camera, already mid-sentence with energy, saying: \\"<spoken_line ตรงเป๊ะ>\\". Then quick appetizing shots of the dish behind them. photorealistic, real person, no on-screen text, no subtitles"}\n'
    '  ],\n'
    '  "posting_schedule": [{"platform": "...", "time_hint": "HH:MM", "reason": "..."}]\n'
    '}'
)


def _gemini_generate(store: dict, label: str) -> tuple[dict, float]:
    """เขียนคอนเทนต์ด้วย Gemini (free tier) — ออก JSON. ค่าใช้จ่าย ฿0 บน free tier."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = (
        f"{SYSTEM}\n\n{_prompt(store, label)}\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น (ไม่มีข้อความอื่น ไม่มี markdown) ตามโครงนี้เป๊ะ:\n{_JSON_SKELETON}"
    )
    resp = client.models.generate_content(
        model=settings.gemini_text_model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(resp.text)
    return data, 0.0


def generate_content(store: dict) -> tuple[dict, float]:
    """คืน (ผลคอนเทนต์, ค่าใช้จ่ายโดยประมาณบาท). เลือก provider ตาม CONTENT_PROVIDER.
    หากมีปัญหาเรื่องคีย์หรือโควตาหมด จะแสดงข้อผิดพลาดจริงให้ผู้ใช้เห็นทันที."""
    provider = settings.content_provider
    if provider == "gemini" and not settings.has_gemini:
        raise RuntimeError("ไม่มีการตั้งค่า GEMINI_API_KEY หรือรูปแบบคีย์ไม่ถูกต้อง")
    if provider == "claude" and not settings.has_claude:
        raise RuntimeError("ไม่มีการตั้งค่า ANTHROPIC_API_KEY หรือรูปแบบคีย์ไม่ถูกต้อง")
        
    try:
        if provider == "gemini" and settings.has_gemini:
            # เจน A
            data_A, cost_A = _gemini_generate(store, "A")
            # เจน B
            data_B, cost_B = _gemini_generate(store, "B")
            # รวม
            data_A["variants"] = data_A.get("variants", []) + data_B.get("variants", [])
            return data_A, cost_A + cost_B
        if provider == "claude" and settings.has_claude:
            # เจน A
            data_A, cost_A = _claude_generate(store, "A")
            # เจน B
            data_B, cost_B = _claude_generate(store, "B")
            # รวม
            data_A["variants"] = data_A.get("variants", []) + data_B.get("variants", [])
            return data_A, cost_A + cost_B
    except Exception as e:
        print(f"[content:{provider}] error: {e}")
        raise RuntimeError(f"ล้มเหลวในการสร้างคอนเทนต์ผ่าน AI ({provider}): {e}")
    raise RuntimeError(f"ไม่พบรูปแบบการสร้างคอนเทนต์สำหรับ: {provider}")
