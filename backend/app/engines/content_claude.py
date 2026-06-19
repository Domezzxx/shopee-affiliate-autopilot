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
    "• image_prompt/video_prompt = อังกฤษ อาหารโคลสอัพน่ากินสุด มีไอ/ซอสยืด/แสงสวย 9:16 vertical, realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings.\n"
    "ภาษาไทยธรรมชาติเหมือนคนรีวิวจริง."
)


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
        
    return (
        f"เขียนคอนเทนต์ affiliate สำหรับร้านนี้ในกลุ่มตัวเลือก {label} (สำหรับ Facebook, Instagram, YouTube รวม 3 variants):\n"
        f"- ชื่อร้าน: {store['name']}\n"
        f"- ย่าน: {store.get('area','')}\n"
        f"- เรตติ้ง: {store.get('rating')} ({store.get('review_count')} รีวิว)\n"
        f"- เมนูเด่น: {', '.join(store.get('menu', [])[:6])}\n"
        f"- ช่วงราคา: {store.get('price_range','')}\n\n"
        f"{style_desc}\n\n"
        f"ข้อบังคับสำคัญ:\n"
        f"1. สร้างเฉพาะ variants ที่มีฟิลด์ label เป็น '{label}' เท่านั้น จำนวน 3 variants (platform ละ 1 ชิ้น)\n"
        f"2. ห้ามสร้าง label อื่นๆ ปะปนมาเด็ดขาด ทุก variant ใน list ต้องมี label: '{label}'\n"
        f"3. first_comment ใส่ {{LINK}} เสมอ\n"
        f"4. ตอบกลับตามโครงสร้าง JSON_SKELETON ที่ระบุ"
    )


def _mock(store: dict) -> dict:
    menu = store.get("menu", ["เมนูเด็ด"])[:1] or ["เมนูเด็ด"]
    dish = menu[0]
    area = store.get("area", "อุดร")
    variants = []
    for p in PLATFORMS:
        variants.append({
            "label": "A", "platform": p,
            "hook": f"{dish}ร้านนี้ {store.get('rating')}⭐ แต่ราคาเท่านี้เอง?! 🤯",
            "video_title": f"คุ้มเกินราคา! {dish}ย่าน{area} {store.get('rating')}⭐ ต้องลอง 🔥",
            "caption": f"{store['name']} {dish}เด็ดย่าน{area}\nจาก {store.get('review_count')} รีวิวตัวจริง\nคุ้มแบบนี้รีบสั่งเลย 👇",
            "hashtags": ["#กินอะไรดี", f"#{area.replace(' ','')}", "#ShopeeFood", "#ของกินคุ้ม", "#รีวิวร้านอร่อย"],
            "cta": "แตะลิงก์คอมเมนต์แรกสั่งเลย ก่อนโปรหมด!",
            "first_comment": f"🔗 สั่ง {dish} ร้าน {store['name']} ได้เลย 👉 {{LINK}}\nส่งไว ราคาคุ้ม 🛵",
            "voiceover_script": f"บอกเลยว่าคุ้มสุดๆ! {dish}ร้าน {store['name']} {store.get('rating')} ดาว สั่งผ่าน Shopee Food คุ้มราคา แบงค์แดงมีทอน ลิงก์อยู่คอมเมนต์เลย!",
            "image_prompt": f"appetizing close-up of {dish}, thai food, vibrant colors, price tag vibe, 9:16 vertical, food photography",
            "video_prompt": f"cinematic food reel of {dish} steaming hot, realistic human actor, real person, photorealistic, no cartoons, slow motion, value-for-money mood, 9:16 vertical, 8 seconds",
        })
        variants.append({
            "label": "B", "platform": p,
            "hook": f"เตือนแล้วนะ… {dish}ร้านนี้กินคำแรกแล้วหยุดไม่ได้ 😋",
            "video_title": f"กินคำแรกแล้วหยุดไม่ได้ 😋 {dish}เจ้าเด็ดย่าน{area}",
            "caption": f"สายกินห้ามพลาด 🚨\n{dish} {store['name']} ฟินทุกคำ\nนุ่ม หอม จัดเต็ม ส่งไวถึงบ้าน 🛵",
            "hashtags": [f"#ของกิน{area.replace(' ','')}", "#คาเฟ่อุดร", "#ShopeeFood", "#กินจุก", "#ฟินเวอร์"],
            "cta": "สั่งเลยก่อนหิวกว่านี้ ลิงก์คอมเมนต์แรก!",
            "first_comment": f"😋 ทนหิวไม่ไหวแล้วใช่ไหม กดสั่งเลย 👉 {{LINK}}",
            "voiceover_script": f"คำแรกก็ใจละลาย! {dish}ร้าน {store['name']} รสชาติกลมกล่อม หอมน้ำซุปเข้มข้นจนต้องร้องว้าว สั่งผ่าน Shopee Food ฟินด่วนๆ เลย!",
            "image_prompt": f"top-down flatlay of {dish} with side dishes, warm cozy light, mouthwatering, 9:16 vertical",
            "video_prompt": f"fast-cut foodie ASMR reel, hands picking up {dish}, realistic human actor, real person, photorealistic, no cartoons, cheese/sauce pull close-up, 9:16 vertical",
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


def _claude_generate(store: dict, label: str) -> tuple[dict, float]:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.content_model,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": _prompt(store, label)}],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
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
    '"image_prompt": "english, 9:16 vertical", "video_prompt": "english, 9:16 vertical"}\n'
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
