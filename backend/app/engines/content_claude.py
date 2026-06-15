"""AI สมอง — Claude เขียนแคปชั่น/สคริปต์/A-B variant + วิเคราะห์ร้าน + วางตารางโพสต์.

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
                    "voiceover_script": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "video_prompt": {"type": "string"},
                },
                "required": ["label", "platform", "hook", "caption", "hashtags",
                             "cta", "voiceover_script", "image_prompt", "video_prompt"],
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

SYSTEM = (
    "คุณเป็นนักการตลาดสาย food affiliate มือทอง เชี่ยวชาญคอนเทนต์ไวรัลภาษาไทย "
    "สำหรับ Facebook Reels, Instagram Reels และ YouTube Shorts. "
    "ทุกแคปชั่นต้องดึงดูด หิว อยากกดลิงก์สั่งทันที. "
    "สร้าง 2 แนวทาง (A กับ B) ต่อ platform เพื่อทำ A/B test — ให้ A กับ B "
    "ใช้มุม/hook ที่ต่างกันชัดเจน (เช่น A=เน้นความคุ้ม, B=เน้นความอร่อย/ดราม่าหิว). "
    "ทุกข้อความเป็นภาษาไทยธรรมชาติ ไม่ใช้คำแข็ง. "
    "image_prompt/video_prompt เขียนเป็นภาษาอังกฤษสำหรับป้อน Gemini สัดส่วน 9:16."
)


def _prompt(store: dict) -> str:
    return (
        "สร้างคอนเทนต์ affiliate สำหรับร้านนี้:\n"
        f"- ชื่อร้าน: {store['name']}\n"
        f"- ย่าน: {store.get('area','')}\n"
        f"- เรตติ้ง: {store.get('rating')} ({store.get('review_count')} รีวิว)\n"
        f"- เมนูเด่น: {', '.join(store.get('menu', [])[:6])}\n"
        f"- ช่วงราคา: {store.get('price_range','')}\n"
        f"- ลิงก์ affiliate: {store.get('affiliate_link','(ใส่ในคอมเมนต์แรก)')}\n\n"
        "ออกผลลัพธ์ครบ A/B ทั้ง 3 platform (6 variants)."
    )


def _mock(store: dict) -> dict:
    menu = store.get("menu", ["เมนูเด็ด"])[:1] or ["เมนูเด็ด"]
    dish = menu[0]
    variants = []
    for p in PLATFORMS:
        variants.append({
            "label": "A", "platform": p,
            "hook": f"{dish}ร้านนี้ คุ้มจนต้องรีบสั่ง 🔥",
            "caption": f"{store['name']} {dish}เด็ด {store.get('rating')}⭐ จาก {store.get('review_count')} รีวิว! กดลิงก์สั่งเลย 👇",
            "hashtags": ["#กินอะไรดี", f"#{store.get('area','อุดร').replace(' ','')}", "#ShopeeFood", "#รีวิวร้านอร่อย"],
            "cta": "แตะลิงก์ในคอมเมนต์แรกสั่งเลย!",
            "voiceover_script": f"ใครหิว? {dish}ร้าน {store['name']} อร่อยจัดเต็ม สั่งง่ายผ่าน Shopee Food เลยจ้า",
            "image_prompt": f"appetizing close-up of {dish}, thai street food, vibrant, 9:16 vertical, food photography",
            "video_prompt": f"cinematic food reel of {dish} steaming hot, slow motion pour, 9:16 vertical, 8 seconds",
        })
        variants.append({
            "label": "B", "platform": p,
            "hook": f"เตือนแล้วนะ {dish}ร้านนี้กินแล้วติดใจ 😋",
            "caption": f"สายกินห้ามพลาด! {dish} {store['name']} ฟินทุกคำ จัดส่งไว 🛵 ลิงก์อยู่ในคอมเมนต์",
            "hashtags": ["#ของกินอุดร", "#คาเฟ่อุดร", "#ShopeeFood", "#กินจุก"],
            "cta": "สั่งเลยก่อนหิวกว่านี้!",
            "voiceover_script": f"คำแรกก็ใจละลาย {dish}ร้าน {store['name']} ต้องลอง สั่งผ่าน Shopee Food ได้เลย",
            "image_prompt": f"top-down flatlay of {dish} with side dishes, warm light, 9:16 vertical",
            "video_prompt": f"fast-cut foodie reel, hands picking up {dish}, cheese/sauce pull, 9:16 vertical",
        })
    return {
        "store_analysis": {
            "strengths": [f"เรตติ้งสูง {store.get('rating')}", "รีวิวเยอะ น่าเชื่อถือ", f"{dish}เป็นพระเอก"],
            "target_audience": "วัยรุ่น-วัยทำงานในย่าน ชอบสั่งเดลิเวอรี่",
            "best_platform": "facebook",
            "hook_angle": "ความคุ้ม + ดราม่าหิว",
        },
        "variants": variants,
        "posting_schedule": [
            {"platform": "facebook", "time_hint": "11:00", "reason": "ก่อนมื้อเที่ยง คนหาของกิน"},
            {"platform": "instagram", "time_hint": "17:30", "reason": "เลิกงาน เลื่อนฟีดหาของเย็น"},
            {"platform": "youtube", "time_hint": "20:00", "reason": "ไพรม์ไทม์ดู Shorts"},
        ],
    }


def generate_content(store: dict) -> tuple[dict, float]:
    """คืน (ผลคอนเทนต์, ค่าใช้จ่ายโดยประมาณบาท)."""
    if not settings.has_claude:
        return _mock(store), 0.0

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

    # ประมาณราคา (USD→บาท ~36) ด้วย sonnet 4.6: in $3 / out $15 ต่อ 1M
    u = resp.usage
    cost_usd = (u.input_tokens * 3 + u.output_tokens * 15) / 1_000_000
    return data, round(cost_usd * 36, 3)
