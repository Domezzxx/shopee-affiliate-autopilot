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
                    "caption": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "cta": {"type": "string"},
                    "first_comment": {"type": "string"},
                    "voiceover_script": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "video_prompt": {"type": "string"},
                },
                "required": ["label", "platform", "hook", "caption", "hashtags",
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

# จูนใหม่ (Sprint 2): สั่งให้เขียนแบบ hook 3 วินาทีแรก + A/B ต่างมุมจริง + เขียนคอมเมนต์แรก
SYSTEM = (
    "คุณคือครีเอเตอร์สาย food affiliate อันดับ 1 ของไทย ทำคอนเทนต์ไวรัลให้ "
    "Facebook Reels / Instagram Reels / YouTube Shorts จนคนหยุดนิ้วแล้วสั่งทันที.\n"
    "กติกาการเขียน:\n"
    "1) HOOK 3 วิแรกต้องสะดุด — ใช้ความอยาก/ดราม่าหิว/ตัวเลขคุ้ม ไม่ใช่บรรยายเฉยๆ.\n"
    "2) caption สั้น กระชับ มี emoji พอดี เว้นบรรทัดอ่านง่าย ปิดด้วย CTA ชวนกดลิงก์คอมเมนต์แรก.\n"
    "3) A กับ B ต้องต่าง 'มุม' กันจริง เพื่อ A/B test: "
    "A = สายคุ้ม/โปร/ราคา, B = สายอร่อย/ฟิน/ดราม่าหิว. ห้ามเขียนคล้ายกัน.\n"
    "4) ปรับโทนตาม platform: FB=เล่าให้ญาติผู้ใหญ่แชร์ได้, IG=ฮิป มินิมอล เก๋, YouTube=ปากต่อปากเล่าเรื่อง.\n"
    "5) first_comment = ข้อความคอมเมนต์แรกที่จะวาง affiliate link "
    "(เขียนชวนกดสั้นๆ + ใส่ {LINK} เป็น placeholder ให้ระบบแทนลิงก์จริง).\n"
    "6) hashtags 4-6 อัน ผสมแท็กพื้นที่ + แท็กอาหาร + #ShopeeFood.\n"
    "7) image_prompt/video_prompt เขียนภาษาอังกฤษ สื่ออาหารน่ากิน สัดส่วน 9:16 vertical.\n"
    "ทุกข้อความภาษาไทยเป็นธรรมชาติ เหมือนคนรีวิวจริง ไม่แข็ง ไม่เป็นโฆษณาขายของจ๋า."
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
