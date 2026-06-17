"""AI สมอง — Claude เขียนแคปชั่น/สคริปต์/A-B variant + คอมเมนต์แรก + วิเคราะห์ร้าน + ตารางโพสต์.

ออก JSON ตาม schema คงที่ (structured outputs) → ไม่ต้อง parse เดา.
ไม่มี API key → คืน mock ที่หน้าตาเหมือนจริง เพื่อให้ทั้งระบบเดินได้ทันที.
"""
from __future__ import annotations

import json
from typing import Any

from ..config import settings

# 3 platform × A/B = 6 variant ต่อร้าน
PLATFORMS = ["facebook", "instagram", "youtube"]

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
    "• image_prompt/video_prompt = อังกฤษ อาหารโคลสอัพน่ากินสุด มีไอ/ซอสยืด/แสงสวย 9:16 vertical.\n"
    "ภาษาไทยธรรมชาติเหมือนคนรีวิวจริง."
)


def _prompt(store: dict) -> str:
    return (
        "เขียนคอนเทนต์ affiliate ครบชุดสำหรับร้านนี้:\n"
        f"- ชื่อร้าน: {store['name']}\n"
        f"- ย่าน: {store.get('area','')}\n"
        f"- เรตติ้ง: {store.get('rating')} ({store.get('review_count')} รีวิว)\n"
        f"- เมนูเด่น: {', '.join(store.get('menu', [])[:6])}\n"
        f"- ช่วงราคา: {store.get('price_range','')}\n\n"
        "ออกผลลัพธ์ครบ A/B ทั้ง 3 platform (รวม 6 variants) + วิเคราะห์ร้าน + ตารางเวลาโพสต์ที่ดีที่สุด.\n"
        "first_comment ใส่ {LINK} ตรงที่จะวางลิงก์ affiliate."
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
            "voiceover_script": f"บอกเลยว่าคุ้ม! {dish}ร้าน {store['name']} {store.get('rating')} ดาว สั่งผ่าน Shopee Food ลิงก์อยู่คอมเมนต์",
            "image_prompt": f"appetizing close-up of {dish}, thai food, vibrant colors, price tag vibe, 9:16 vertical, food photography",
            "video_prompt": f"cinematic food reel of {dish} steaming hot, slow motion, value-for-money mood, 9:16 vertical, 8 seconds",
        })
        variants.append({
            "label": "B", "platform": p,
            "hook": f"เตือนแล้วนะ… {dish}ร้านนี้กินคำแรกแล้วหยุดไม่ได้ 😋",
            "video_title": f"กินคำแรกแล้วหยุดไม่ได้ 😋 {dish}เจ้าเด็ดย่าน{area}",
            "caption": f"สายกินห้ามพลาด 🚨\n{dish} {store['name']} ฟินทุกคำ\nนุ่ม หอม จัดเต็ม ส่งไวถึงบ้าน 🛵",
            "hashtags": [f"#ของกิน{area.replace(' ','')}", "#คาเฟ่อุดร", "#ShopeeFood", "#กินจุก", "#ฟินเวอร์"],
            "cta": "สั่งเลยก่อนหิวกว่านี้ ลิงก์คอมเมนต์แรก!",
            "first_comment": f"😋 ทนหิวไม่ไหวแล้วใช่ไหม กดสั่งเลย 👉 {{LINK}}",
            "voiceover_script": f"คำแรกก็ใจละลาย {dish}ร้าน {store['name']} ต้องลอง สั่งผ่าน Shopee Food ได้เลย",
            "image_prompt": f"top-down flatlay of {dish} with side dishes, warm cozy light, mouthwatering, 9:16 vertical",
            "video_prompt": f"fast-cut foodie ASMR reel, hands picking up {dish}, cheese/sauce pull close-up, 9:16 vertical",
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


def _claude_generate(store: dict) -> tuple[dict, float]:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.content_model,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": _prompt(store)}],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    u = resp.usage
    cost_usd = (u.input_tokens * 3 + u.output_tokens * 15) / 1_000_000   # sonnet 4.6
    return data, round(cost_usd * 36, 3)


# โครง JSON ที่บอก Gemini ให้ตอบเป๊ะ (version-robust — ไม่พึ่ง response_schema ของ SDK)
_JSON_SKELETON = (
    '{\n'
    '  "store_analysis": {"strengths": ["..."], "target_audience": "...", '
    '"best_platform": "facebook|instagram|youtube", "hook_angle": "..."},\n'
    '  "variants": [   // ต้องมี 6 ชิ้น = label A และ B ต่อทุก platform (facebook, instagram, youtube)\n'
    '    {"label": "A|B", "platform": "facebook|instagram|youtube", "hook": "...", '
    '"video_title": "ชื่อคลิปไวรัลสไตล์อินฟลูอาหาร 30-55 ตัวอักษร มีตัวเลข+เมนู+อีโมจิ", '
    '"caption": "...", "hashtags": ["#..."], "cta": "...", '
    '"first_comment": "... {LINK} ...", "voiceover_script": "...", '
    '"image_prompt": "english, 9:16 vertical", "video_prompt": "english, 9:16 vertical"}\n'
    '  ],\n'
    '  "posting_schedule": [{"platform": "...", "time_hint": "HH:MM", "reason": "..."}]\n'
    '}'
)


def _gemini_generate(store: dict) -> tuple[dict, float]:
    """เขียนคอนเทนต์ด้วย Gemini (free tier) — ออก JSON. ค่าใช้จ่าย ฿0 บน free tier."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = (
        f"{SYSTEM}\n\n{_prompt(store)}\n\n"
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
    error/ไม่มี key → fallback mock เพื่อให้ระบบไม่ล่ม."""
    provider = settings.content_provider
    try:
        if provider == "gemini" and settings.has_gemini:
            return _gemini_generate(store)
        if provider == "claude" and settings.has_claude:
            return _claude_generate(store)
    except Exception as e:  # pragma: no cover
        print(f"[content:{provider}] error → fallback mock: {e}")
    return _mock(store), 0.0
