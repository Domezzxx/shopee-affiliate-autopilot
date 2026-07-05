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

# ---- style presets: แนวคอนเทนต์หลายแบบ (เลียนแบบบอทคู่แข่ง Prompt D Ai: ขายของ/การ์ตูน/Pixar/นิทาน/Podcast) ----
# แต่ละแนว 'ทับ' เฉพาะสไตล์ภาพ/ผู้พูด/บท — คง hook + จิตวิทยาการขาย + โครง JSON เดิมไว้ทั้งหมด
STYLE_PRESETS: dict[str, dict[str, str]] = {
    "realistic": {"th": "ขายสินค้า/อาหารเหมือนจริง", "visual": "", "voice": "", "speaker": ""},
    "cartoon2d": {
        "th": "การ์ตูน 2D",
        "visual": "flat 2D cartoon illustration, bold clean thick outlines, vibrant flat cel-shaded colors, "
                  "a cute expressive mascot character holding/enjoying the product, playful sticker-like poster art, "
                  "NO photorealism",
        "voice": "โทนสนุกสดใสเป็นกันเอง เหมือนมาสคอตการ์ตูนพูด พลังงานสูง ยียวนน่ารัก",
        "speaker": "a cute 2D cartoon mascot character speaking straight to camera",
    },
    "pixar3d": {
        "th": "Pixar 3D",
        "visual": "adorable 3D animated character in Pixar/Disney style, glossy soft global illumination, "
                  "big expressive eyes, subsurface-scattering skin, cinematic shallow depth of field, "
                  "stylized cute 3D render (Blender/Octane look), warmly presenting the product, NO photorealistic human",
        "voice": "โทนอบอุ่นน่ารักมีเสน่ห์ เล่าแบบตัวการ์ตูน Pixar สดใสชวนยิ้ม",
        "speaker": "a charming Pixar-style 3D animated character speaking to camera",
    },
    "story": {
        "th": "นิทานเล่าเรื่อง",
        "visual": "warm storybook illustration, soft watercolor / picture-book art style, whimsical gentle lighting, "
                  "a narrative scene per shot (not a direct ad), cozy and heartwarming",
        "voice": "voiceover_script = เล่าเป็นนิทานสั้นมีตัวละคร มีปม-คลี่คลาย ให้พระเอกคือร้าน/สินค้า "
                 "เปิดแนว 'กาลครั้งหนึ่ง...' โทนบรรยายนุ่มชวนติดตาม ปิดด้วย CTA เนียนๆ",
        "speaker": "a warm storybook narrator voiceover over the illustrated scenes (no on-camera speaker)",
    },
    "podcast": {
        "th": "Podcast คุยกัน",
        "visual": "cozy podcast studio scene, close-up microphone with warm bokeh, on-air neon sign, moody cinematic lighting",
        "voice": "voiceover_script = บทสนทนา 2 คนสลับกัน (ขึ้นต้นบรรทัดด้วย 'A:' และ 'B:') คุยกันสบายๆ "
                 "รีวิวร้าน/สินค้าแบบพอดแคสต์ มีถาม-ตอบ ปิดด้วยชวนไปลอง + ลิงก์",
        "speaker": "two podcast hosts chatting (audio-led) over a static podcast-studio image",
    },
}


def _style_block(style: str) -> str:
    """คืน 'คำสั่งทับสไตล์' ต่อท้าย prompt — บังคับแนวภาพ/ผู้พูด/บทตาม preset.
    realistic → คืน '' (ใช้สูตรเดิมใน SYSTEM ทั้งหมด ไม่กระทบพฤติกรรมเก่า)."""
    p = STYLE_PRESETS.get(style)
    if not p or style == "realistic":
        return ""
    return (
        "\n\n★★ STYLE OVERRIDE (สำคัญสุด — ทับ 'สูตรภาพ/ผู้พูด' ในข้อ ⑨ ทั้งหมด) ★★\n"
        f"แนวคอนเทนต์รอบนี้ = '{p['th']}'. คงกรอบ hook/จิตวิทยาการขาย/โครง JSON เดิมไว้ "
        "แต่ 'เปลี่ยนสไตล์ภาพและผู้พูด' ตามนี้:\n"
        f"• image_prompt & video_prompt (ภาษาอังกฤษ): {p['visual']}\n"
        f"• โทน/บทพูด (voiceover_script, spoken_line): {p['voice']}\n"
        f"• ยกเลิกข้อบังคับ 'realistic human actor / real person / no cartoons' ในข้อ ⑨ สำหรับแนวนี้ "
        f"→ ผู้พูดใน video_prompt = {p['speaker']}. "
        "คงข้อบังคับ 'no on-screen text, no subtitles' ไว้ (ซับ karaoke เติมทีหลัง), แนวตั้ง 9:16, "
        "เว้นที่ว่างครึ่งบนสำหรับตัวหนังสือเสมอ."
    )

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

# สมองสคริปต์ระดับโลก + จิตวิทยาการขาย (Sprint 4): hook หยุดนิ้ว + persuasion levers + voiceover spoken-word
SYSTEM = (
    "คุณคือ short-form content creator ระดับโลก สาย food/affiliate ที่ทำรีลไทย/TikTok ปังจนคนดูหยุดนิ้วและกดสั่งทันที.\n"
    "เป้าหมายสูงสุด: หยุดนิ้วใน 1 วิแรก (Thumb-Stopping) → สะกดให้ดูจนจบ → คลิกสั่งลิงก์ใต้คอมเมนต์.\n\n"

    "① สูตร HOOK (วิแรก = ตัวตัดสินชีวิตคลิป): ห้ามทักทาย ('สวัสดีครับ/ค่ะ') ห้ามขึ้นด้วยชื่อร้าน/คำเฝือ ให้ใช้สูตรหยุดนิ้ว:\n"
    "  - (1) ขัดแย้ง/คำสั่งห้าม (Pattern Interrupt): 'อย่าเพิ่งสั่งร้านนี้ ถ้ายังไม่อยากติดใจ!', 'เตือนก่อนนะ อย่าดูตอนดึก 🚨'\n"
    "  - (2) คำถามสะกิดใจ: 'กล้าท้าว่าคำเดียวหยุดไม่อยู่?', 'ราคานี้ยุคนี้มีจริงดิ?!'\n"
    "  - (3) ตัวเลข/ราคาช็อก: '75 บาท ได้เยอะขนาดนี้?!'\n"
    "  - (4) ความลับ/อินไซต์คนใน: 'คนแถวนี้เท่านั้นที่รู้ว่าต้องสั่งเจ้านี้...'\n\n"

    "② สูตรจิตวิทยาการขาย (Persuasion Levers) — ทุก variant ต้องสอด 'อย่างน้อย 2 ข้อ' ลงใน hook/caption/voiceover ให้เนียน:\n"
    "  • Scarcity/Urgency (เร่งด่วน/มีจำกัด): 'ช่วงพีคคนสั่งแน่น รอคิวนาน—สั่งเลยก่อนหิวกว่านี้', 'ของดีหมดไว', 'กระแสกำลังมา เดี๋ยวคิวยาว'. "
    "ห้ามกุตัวเลขสต๊อกปลอม (เช่น 'เหลือ 5 ที่') ถ้าไม่มีข้อมูลจริง — ใช้ความเร่งด่วนเชิงเวลา/คิว/ความอยากแทน.\n"
    "  • Social Proof เจาะจง (ดึงตัวเลขรีวิว/เรตติ้งจริงที่ป้อนให้): 'คนสั่งซ้ำ {รีวิว}+ คนการันตี', 'เรตติ้ง {ดาว}⭐ ของจริงจากคนกินจริง' — เจาะจงตัวเลขดีกว่าพูดลอยๆ ว่า 'อร่อยมาก'.\n"
    "  • Price Anchoring (ตรึงราคา/ชูความคุ้ม): เทียบให้เห็นภาพจากราคาจริง เช่น 'จ่ายแค่ราคากาแฟแก้วเดียว อิ่มทั้งมื้อ', 'เริ่มแค่ {ราคา} บาท คุ้มเกินตัว'. "
    "ถ้ามีข้อมูล 'ราคาปกติ/ส่วนลด' ให้ทำ before→after ('ปกติ 129 เหลือ 79'); ถ้าไม่มี ห้ามกุราคาปกติขึ้นเอง.\n"
    "  • Authority (ความน่าเชื่อถือ): อ้างจากสัญญาณจริง เช่น เรตติ้งสูง รีวิวเยอะ 'เจ้าดังประจำย่าน' 'ขายดีจนต้องต่อคิว'. "
    "ห้ามกุเครดิตเฉพาะที่ตรวจไม่ได้ (เช่น 'ทำมา 20 ปี', 'รางวัลมิชลิน') ถ้าไม่มีในข้อมูล.\n\n"

    "③ video_title = ชื่อคลิป YouTube/TikTok สไตล์อินฟลูอาหาร (Curiosity Loop): ขึ้นด้วยตัวเลข/ราคา/ความคุ้ม/ความแซ่บ + ชื่อเมนูเด่น "
    "+ อีโมจิ 1-2 ตัว + วลีค้างใจ ('...จริงดิ?', 'ต้องลอง', 'บอกต่อ') ยาว 30-55 ตัวอักษร ห้ามยัดแฮชแท็กยาว.\n"
    "  ตัวอย่าง: '40 บาทอิ่มจุก! ก๋วยเตี๋ยวเรือเจ้านี้ต้องลอง 🔥' / 'ทนไม่ไหว 😋 โดนตกด้วยพริกแกงกระทะนี้!'\n\n"

    "④ voiceover_script = บทพูดรีล 10-15 วิ เขียนแบบ 'คนพูดจริง' ไม่ใช่อ่านหนังสือ ประโยคสั้น มีจังหวะ (TikTok Pacing): "
    "[Hook แรง] → [จุดเด่นเจาะจงชวนน้ำลายสอ 1-2 อย่าง + สอดจิตวิทยาการขาย] → [CTA ป้ายยาชี้ช่องทางสั่ง]. "
    "เป็นกันเองเหมือนคุยกับเพื่อน พลังงานสูง (บทนี้จะกลายเป็นซับเด้ง ทุกคำต้องมีน้ำหนัก).\n"
    "⑤ เจาะจง ชนะ กว้างๆ เสมอ (Sensory Copywriting): 'เส้นนุ่ม น้ำซุปกระดูกเคี่ยว 8 ชม. หอมกระเทียมเจียว' > 'อร่อยมาก/เครื่องแน่น'.\n"
    "⑥ A vs B ต้องแบ่งขั้วอารมณ์ชัด (Polar Opposites): A=สายคุ้ม/ดีล/ตัวเลข (เน้น Price Anchoring + Scarcity), "
    "B=สายฟิน/ดราม่าหิว/ASMR (เน้น Sensory + Social Proof). ห้ามคล้ายกัน.\n"
    "⑦ caption: สั้น เว้นบรรทัดอ่านง่าย มีอีโมจิพอดี ปิดด้วย CTA เร่งเร้า + hashtags 4-6 ตัว.\n\n"

    "⑧ spoken_line + spoken_lang = 1 ประโยคสั้นมาก (~6-12 คำ พูดจบใน ~7 วิ) ที่คนในคลิปพูดใส่กล้องทันทีตอนเปิดคลิป:\n"
    "  ★ คำแรกสุดต้องเป็น HOOK (ตามสูตร ①) หยุดคนดูใน 1 วิ — ห้ามเปิดด้วยชื่อร้าน/คำทักทาย.\n"
    "  ★ spoken_lang เลือก thai | english | isaan และต้อง 'กระจายหลากหลาย' ข้าม variant (ตามที่ระบบกำหนดต่อ platform ด้านล่าง).\n"
    "  ★ isaan = อีสานแท้ ลื่นเป็นธรรมชาติ ใช้คำจริง (เด้อ, สิ, กะ, อีหลี, โพด, คัก, จั่งแม่น, นัว) เช่น 'จั่งแม่นแซ่บคัก มื้อนี้สั่งโลดเด้อ', 'บ่ลองบ่รู้ แซ่บอีหลีนะนี่!'\n"
    "  ★ english = โทนวัยรุ่นไวรัลสั้นๆ เช่น 'Stop scrolling! Trust me, you need this.', 'Wait—only 75 baht?!'\n\n"

    "⑨ image_prompt / video_prompt = ภาษาอังกฤษ ตามสูตร: [Subject] + [Sensory Details] + [Dynamic Action] + [Lighting Setup] + [Composition & Copy Space] + [Backdrop & Styling] + [Technical]\n"
    "  - Subject: เจาะจงส่วนประกอบเมนู (กะเพรา → minced pork, holy basil, fresh red chilies, crispy fried egg with runny yolk on jasmine rice)\n"
    "  - Sensory: glistening glossy sauce, crisp caramelized edges, oozing cheese pull, vibrant fresh colors\n"
    "  - Dynamic Action: whispering steam rising backlit, fresh herbs/sparks scattering mid-air, dynamic sauce splash\n"
    "  - Lighting: dramatic side lighting 45deg, subtle rim lighting, volumetric backlighting to make steam/broth glow\n"
    "  - Composition & Copy Space: commercial food photography, mouthwatering macro close-up, 45-degree hero shot, f/1.8 shallow depth of field; ระบุ 'leave empty copy space in the upper third for text overlays' เสมอ\n"
    "  - Backdrop & Styling: professional food styling, dark moody backdrop / dark rustic tabletop to make colors pop\n"
    "  - video_prompt ต้องเปิดคลิปที่คนพูดทันที (ห้ามเปิดด้วยภาพอาหารนิ่ง): "
    "'Vertical 9:16. OPENS immediately on [ผู้พูดตามภาษา] looking straight into camera, already mid-sentence with big friendly energy, saying: \"<spoken_line ตรงเป๊ะ>\". "
    "Then quick appetizing b-roll of [เมนู] (slow-mo wok toss, sauce dripping, steam swirling).' "
    "ระบุผู้พูดตามภาษา: isaan→'a real Northeastern-Thai (Isan) local speaking authentic natural relaxed Isan accent'; "
    "thai→'a real Thai person, natural casual spoken Thai'; english→'a trendy young food vlogger, natural casual English'. "
    "ใส่คำบังคับ: realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings, no on-screen text, no subtitles (มีแค่เสียงพูดจริง ลิปซิงค์จบประโยค).\n"
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


def _learned_lang_order(default: list[str]) -> tuple[list[str], bool]:
    """ดึง 'ลำดับภาษาที่ได้ผลจริง' จาก learning loop มา 'เขียนทับ' การเลือกภาษาแบบ hardcode
    (แก้ปัญหา 'รู้ว่าอะไรเวิร์ก แต่ไม่เคยทำตาม'). คืน (ลำดับดีสุด→แย่สุด, เรียนรู้แล้ว?).
    ล้มเหลว/ข้อมูลไม่พอ → คืน default, False (ไม่กระทบพฤติกรรมเดิม)."""
    try:
        from ..services.learning import learned_lang_order
        return learned_lang_order(default)
    except Exception:
        return list(default), False


def _daypart() -> str:
    """ช่วงเวลาปัจจุบัน → ป้อนบริบท 'อารมณ์ตามมื้อ' ให้ AI (เที่ยงหิวข้าว vs ดึกทรมานหิว)."""
    import datetime
    h = datetime.datetime.now().hour
    if 5 <= h < 11:
        return "เช้า (คนหามื้อเช้า/กาแฟ)"
    if 11 <= h < 14:
        return "เที่ยง (หิวข้าวกลางวัน — ชูความอิ่ม/คุ้ม/สั่งด่วน)"
    if 14 <= h < 17:
        return "บ่าย (ของว่าง/ของหวาน/เครื่องดื่มดับร้อน)"
    if 17 <= h < 21:
        return "เย็น (เลิกงานหามื้อเย็น/ปิ้งย่าง/สังสรรค์)"
    return "ดึก (cravings มื้อดึก — ดราม่าหิว/ASMR ทรมานใจ)"


def _store_facts(store: dict) -> str:
    """สร้าง 'ข้อเท็จจริงของร้าน' แบบอัดแน่น (แก้ context starvation) — ป้อนวัตถุดิบให้ AI
    ทำ social proof / price anchoring / authority จาก 'ตัวเลขจริง' เท่านั้น (context เสริมใช้ก็ต่อเมื่อมีจริง)."""
    import re
    menu = store.get("menu", []) or []
    menu_str = ", ".join(menu[:12]) if menu else "เมนูหลากหลาย"
    price_raw = store.get("price_range", "") or ""
    pm = re.search(r"\d[\d,]*", price_raw)
    price_anchor = pm.group(0) if pm else ""
    subtype = store.get("food_subtype", "") or ""
    lines = [
        f"- ชื่อร้าน: {store.get('name', '')}",
        f"- ย่าน: {store.get('area', '')}",
        f"- ⭐ เรตติ้ง: {store.get('rating')} (ตัวเลขจริง — ใช้ทำ Authority/Social Proof อย่าเปลี่ยน)",
        f"- 💬 รีวิวจริง: {store.get('review_count')} รายการ (ใช้ทำ Social Proof เจาะจง เช่น 'คนกินจริงกว่า {store.get('review_count')} คนการันตี')",
        f"- 🍽️ เมนูเด่น: {menu_str}",
        (f"- 💰 ราคาเริ่มต้น ~{price_anchor} บาท (ใช้ทำ Price Anchoring/ชูความคุ้ม เทียบเป็นราคาต่อคำ/ต่อจาน)"
         if price_anchor else f"- 💰 ราคา: {price_raw or 'ไม่ระบุ'}"),
        f"- ประเภทร้านย่อย: {subtype or 'ทั่วไป'}",
        f"- ⏰ ช่วงเวลาสร้างคอนเทนต์: {_daypart()} → ให้อย่างน้อย 1 variant จับอารมณ์ช่วงนี้",
    ]
    # context เสริม — ใช้ก็ต่อเมื่อมีจริงในข้อมูลร้าน (ไม่มีก็ไม่กุ)
    promo = store.get("promo") or store.get("discount") or ""
    if promo:
        lines.append(f"- 🔥 โปร/ส่วนลดจริง: {promo} (ทำ before→after เช่น 'ปกติ X เหลือ Y' + urgency ได้เต็มที่)")
    selling = store.get("selling_points") or ""
    if selling:
        lines.append(f"- ✨ จุดขายพิเศษ: {selling}")
    comp = store.get("competitor_note") or ""
    if comp:
        lines.append(f"- 🏳️ คู่แข่งในย่าน: {comp} (ใช้สร้างความต่าง/ทำไมต้องร้านนี้)")
    return "\n".join(lines)


def _prompt(store: dict, label: str, style: str = "realistic") -> str:
    if label == "A":
        style_desc = (
            "สไตล์คอนเทนต์กลุ่ม A (สายคุ้ม/โปรโมชั่น/ตัวเลข):\n"
            "- เน้นเรื่องความคุ้มค่า ราคาประหยัด ดีลพิเศษ ส่วนลดเยอะ หรือเรตติ้งรีวิวจำนวนมาก\n"
            "- Hook ต้องสะกิดต่อมสายประหยัด เช่น 'ราคานี้ได้ยังไง?', 'คุ้มกว่านี้มีอีกไหม?'\n"
            "- video_title ต้องใช้ตัวเลขหรือยอดขาย หรือความประหยัดนำหน้า มีอีโมจิดึงดูด\n"
            "- voiceover_script ต้องพากย์เสียงพากย์ชวนตื่นเต้น มีพลัง พูดถึงดีลเด็ด ความคุ้มราคา คุ้มค่าและประหยัดแบบสะใจสุดๆ ดึงดูดให้อยู่ดูต่อ\n"
            "- image_prompt และ video_prompt ต้องเป็นภาษาอังกฤษ และเขียนเรียงตามสูตร [Subject] + [Sensory Details] + [Dynamic Action] + [Lighting Setup] + [Composition & Copy Space] + [Backdrop & Styling] + [Technical Parameters] "
            "เน้นสไตล์ภาพโฆษณาเชิงพาณิชย์เกรดพรีเมียม (commercial food photography, high-end food advertising poster style) "
            "โดยชูความน่ากินจัดจ้าน เช่น ซอสหนืดมันวาวไหลเยิ้ม (glistening glossy sauce dripping/glaze), ชีสยืดสะใจ (oozing cheese pull), ผิวกรอบขอบเกรียมสีทองหอมหวน (crisp caramelized edges). "
            "จัดแสงสไตล์โฆษณา (dramatic key lighting, strong side lighting at 45 degrees) เพื่อดึงมิติพื้นผิวอาหาร. "
            "วางมุมกล้องแบบภาพถ่ายโฆษณา (commercial composition, sharp focus, f/1.8, shallow depth of field) "
            "และต้องระบุให้เว้นที่ว่างครึ่งบน/ขวาของภาพสำหรับวางตัวหนังสือ CTA เสมอ (leave empty copy space in the upper third/side for poster text overlays). "
            "เน้นพื้นหลังมืดสลัวตัดกับสีอาหาร (dark moody studio backdrop to make the vibrant food colors pop) "
            "พร้อมเงื่อนไขบังคับ 'realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings'"
        )
    else:
        style_desc = (
            "สไตล์คอนเทนต์กลุ่ม B (สายฟิน/ดราม่าหิว/ASMR):\n"
            "- เน้นย้ำเรื่องความอร่อยแสงออกปาก กลิ่นหอมฟุ้งลอยมา ควันฉุยไหลเยิ้ม คลื่นเสียง ASMR ทรมานใจยามดึก\n"
            "- Hook ต้องเปิดด้วยอาการทรมานความหิว เช่น 'เห็นคลิปนี้ตอนดึกขออภัยด้วยนะ', 'คำแรกถึงกับหลับตาฟิน'\n"
            "- video_title เน้นความฟิน ความแซ่บ หรือความอร่อยที่หยุดไม่อยู่\n"
            "- voiceover_script ต้องพากย์เสียงพากย์ด้วยคำบรรยายที่เห็นภาพชัดเจน รสชาตินุ่มละมุน ความเข้มข้น ความหอมกรุ่นชวนกิน เพื่อกระตุ้นความหิวดึงดูดให้อยู่ดูต่อจนจบ\n"
            "- image_prompt และ video_prompt ต้องเป็นภาษาอังกฤษ และเขียนเรียงตามสูตร [Subject] + [Sensory Details] + [Dynamic Action] + [Lighting Setup] + [Composition & Copy Space] + [Backdrop & Styling] + [Technical Parameters] "
            "เน้นความน่ากินชวนหิวแสงออกปากด้วยมุมกล้องซูมโคลสอัพใกล้เป็นพิเศษระดับมาโคร (mouthwatering macro close-up, 8k resolution) "
            "แสดงดีเทลรสสัมผัสคมชัดสูง (ultra-realistic food textures) และความสดใหม่. "
            "สร้างความเคลื่อนไหวด้วยควันร้อนกรุ่นลอยตัวพุ่งฉุย (whispering hot steam rising), หรือวัตถุดิบผักชี/เครื่องเทศโรยสาดกระจายตัวในอากาศ (fresh herbs scattering dynamically around). "
            "จัดแสงเพื่อสร้างบรรยากาศสุดดรามาติกด้วยแสงเฉียงเน้นเท็กซ์เจอร์ (dramatic side lighting) ร่วมกับแสงย้อนฉายทะลุผ่านควันหรือน้ำซุปให้เรืองแสงมีประกาย (volumetric backlighting to make steam/soup glow) และแสงขอบเน้นสรีระ (rim lighting). "
            "วางบนฉากหลังโทนธรรมชาติเข้ม/ rustic (dark rustic wood table, dark slate backdrop with high contrast), มีการตกแต่งจานอย่างประณีต (professional food styling) "
            "พร้อมเงื่อนไขบังคับ 'realistic human actor, real person, photorealistic, no cartoons, no animations, no drawings'"
        )
        
    # เลือกภาษาบทพูด — 'เขียนทับ' ด้วยผลจริงจาก learning loop (ทำตามที่รู้ ไม่ใช่แค่รู้แล้วไม่ทำ)
    default_langs = ["thai", "english", "isaan"] if label == "A" else ["isaan", "thai", "english"]
    ranked, learned = _learned_lang_order(default_langs)
    if learned and len(ranked) >= 2:
        best, second = ranked[0], ranked[1]
        # EXPLOIT: ดันภาษาที่พิสูจน์แล้วว่าปังให้ถูกใช้ 2 ใน 3 platform จริง + เก็บ 1 ช่องไว้ 'สำรวจ'
        # อันดับสอง (กัน learning loop ตาย) · สลับตำแหน่งตาม label ไม่ให้ A/B เหมือนกันเป๊ะ
        langs = [best, second, best] if label == "A" else [second, best, best]
        lang_note = (f"\n8. ระบบเรียนรู้จากผลจริงแล้วว่าภาษา '{best}' ทำผลงานดีที่สุด "
                     f"→ รอบนี้จึงดันให้ใช้ '{best}' มากขึ้น (สำคัญกว่าการกระจายภาษาเท่ากันทุกตัว)")
    else:
        langs = list(default_langs)
        lang_note = ""
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
        f"{_store_facts(store)}\n\n"
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
        + _style_block(style)
        + lang_note
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
            "image_prompt": f"commercial food photography of {dish}, high-end food advertising poster style, oozing cheese pull and glistening thick glossy sauce dripping, dramatic side lighting at 45 degrees, professional food styling, leave empty copy space in the upper third for poster text overlays, dark moody studio backdrop with high contrast, sharp focus, f/1.8, vertical 9:16",
            "video_prompt": f"Vertical 9:16. OPENS immediately on a real Thai person looking into camera, already mid-sentence with big energy, saying: \"{spoken_a}\". Then quick appetizing shots of {dish} behind them, glistening sauce dripping, dramatic key light, dark studio backdrop. realistic human actor, real person, photorealistic, no cartoons, value-for-money mood, no on-screen text, no subtitles",
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
            "image_prompt": f"mouthwatering macro close-up of {dish}, glistening rich food textures, whispering hot steam rising backlit, dramatic volumetric lighting making the steam glow, rim lighting to emphasize edges, fresh ingredients scattered dynamically around, dark rustic wood table background, 8k resolution, professional food styling, f/1.8, sharp focus, vertical 9:16",
            "video_prompt": f"Vertical 9:16. OPENS immediately on a real local Northeastern-Thai (Isan) person looking into camera, already mid-sentence in authentic natural relaxed Isan accent, saying: \"{spoken_b}\". Then quick appetizing macro close-up of {dish} with whispering hot steam backlit and glowing, sauce dripping, dark rustic background. realistic human actor, real person, photorealistic, no cartoons, no on-screen text, no subtitles",
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


def _claude_generate(store: dict, label: str, style: str = "realistic") -> tuple[dict, float]:
    """เขียนคอนเทนต์ด้วย Claude — ขอ JSON ผ่าน prompt แล้ว parse (รองรับ anthropic SDK 0.45)."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"{_prompt(store, label, style)}\n\n"
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


def _gemini_generate(store: dict, label: str, style: str = "realistic") -> tuple[dict, float]:
    """เขียนคอนเทนต์ด้วย Gemini (free tier) — ออก JSON. ค่าใช้จ่าย ฿0 บน free tier."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = (
        f"{SYSTEM}\n\n{_prompt(store, label, style)}\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น (ไม่มีข้อความอื่น ไม่มี markdown) ตามโครงนี้เป๊ะ:\n{_JSON_SKELETON}"
    )
    resp = client.models.generate_content(
        model=settings.gemini_text_model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(resp.text)
    return data, 0.0


def generate_content(store: dict, style: str | None = None) -> tuple[dict, float]:
    """คืน (ผลคอนเทนต์, ค่าใช้จ่ายโดยประมาณบาท). เลือก provider ตาม CONTENT_PROVIDER.
    style = แนวคอนเทนต์ (realistic/cartoon2d/pixar3d/story/podcast) — ไม่ระบุ → ใช้ store['content_style']
    หรือ CONTENT_STYLE จาก .env. หากมีปัญหาเรื่องคีย์หรือโควตาหมด จะแสดงข้อผิดพลาดจริงให้ผู้ใช้เห็นทันที."""
    provider = settings.content_provider
    style = style or store.get("content_style") or settings.content_style or "realistic"
    if style not in STYLE_PRESETS:
        print(f"[content] style '{style}' ไม่รู้จัก → ใช้ realistic")
        style = "realistic"
    if provider == "gemini" and not settings.has_gemini:
        raise RuntimeError("ไม่มีการตั้งค่า GEMINI_API_KEY หรือรูปแบบคีย์ไม่ถูกต้อง")
    if provider == "claude" and not settings.has_claude:
        raise RuntimeError("ไม่มีการตั้งค่า ANTHROPIC_API_KEY หรือรูปแบบคีย์ไม่ถูกต้อง")

    try:
        if provider == "gemini" and settings.has_gemini:
            # เจน A
            data_A, cost_A = _gemini_generate(store, "A", style)
            # เจน B
            data_B, cost_B = _gemini_generate(store, "B", style)
            # รวม
            data_A["variants"] = data_A.get("variants", []) + data_B.get("variants", [])
            return data_A, cost_A + cost_B
        if provider == "claude" and settings.has_claude:
            # เจน A
            data_A, cost_A = _claude_generate(store, "A", style)
            # เจน B
            data_B, cost_B = _claude_generate(store, "B", style)
            # รวม
            data_A["variants"] = data_A.get("variants", []) + data_B.get("variants", [])
            return data_A, cost_A + cost_B
    except Exception as e:
        print(f"[content:{provider}] error: {e}")
        raise RuntimeError(f"ล้มเหลวในการสร้างคอนเทนต์ผ่าน AI ({provider}): {e}")
    raise RuntimeError(f"ไม่พบรูปแบบการสร้างคอนเทนต์สำหรับ: {provider}")
