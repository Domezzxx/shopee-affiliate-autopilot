"""Gemini media — ภาพ "Nano Banana" + วีดีโอ Veo (ผ่าน Flow).

ไม่มี key → สร้าง placeholder 9:16 ด้วย PIL เพื่อให้ flow เดินได้.
"""
from __future__ import annotations

import os
import time
import uuid

from ..config import settings


def _placeholder(prompt: str, kind: str) -> str:
    """รูป 9:16 พร้อมข้อความ prompt — ใช้แทนตอนยังไม่ใส่ Gemini key."""
    from PIL import Image, ImageDraw
    os.makedirs(settings.media_dir, exist_ok=True)
    path = os.path.join(settings.media_dir, f"{kind}_{uuid.uuid4().hex[:8]}.png")
    img = Image.new("RGB", (720, 1280), (250, 245, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 720, 120], fill=(238, 108, 77))
    d.text((24, 45), f"[MOCK {kind.upper()}]", fill="white")
    # ตัด prompt ขึ้นจอเป็นบรรทัด
    words, line, y = prompt.split(), "", 200
    for w in words:
        if len(line) + len(w) > 42:
            d.text((24, y), line, fill=(60, 60, 60)); y += 34; line = ""
        line += w + " "
    d.text((24, y), line, fill=(60, 60, 60))
    img.save(path)
    return path


def _client():
    from google import genai
    return genai.Client(api_key=settings.gemini_api_key)


def generate_image(prompt: str) -> str:
    """สร้างภาพ 9:16 → คืน path ไฟล์."""
    if not settings.has_gemini:
        raise RuntimeError("ไม่มีการตั้งค่า GEMINI_API_KEY หรือรูปแบบคีย์ไม่ถูกต้อง")
    try:
        client = _client()
        resp = client.models.generate_content(
            model=settings.image_model,
            contents=[prompt + " — vertical 9:16 aspect ratio, high quality"],
        )
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                os.makedirs(settings.media_dir, exist_ok=True)
                path = os.path.join(settings.media_dir, f"image_{uuid.uuid4().hex[:8]}.png")
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
        raise RuntimeError("ไม่พบข้อมูลรูปภาพในผลลัพธ์ของ Gemini API (คีย์อาจไม่มีสิทธิ์รันโมเดลรูปภาพ)")
    except Exception as e:  # pragma: no cover
        print(f"[gemini] image error: {e}")
        raise RuntimeError(f"ล้มเหลวในการสร้างรูปภาพผ่าน Gemini API: {e}")


def generate_video(prompt: str, image_path: str = "") -> tuple[str, str]:
    """สร้างวีดีโอสั้น 9:16 ด้วย Google Flow Browser Automation (ฟรี) โดยมี fallback ไปที่ Veo API.

    image_path: ถ้ามีรูป product จริง → ทำ 'image-to-video' (วีดีโอตรงเมนูจริง) ก่อน,
    ทำไม่ได้ค่อย fallback ไป text-to-video แล้วค่อย Veo API.
    คืน (path, source) — source = 'flow' (Google Flow) หรือ 'veo' (Veo API).
    """
    if not settings.enable_video:
        raise RuntimeError("ระบบสร้างวิดีโอถูกปิดอยู่ (ENABLE_VIDEO=false)")

    # 0) ถ้า Flow ถูกพักอยู่ (เครดิตหมด) → ข้าม ไม่เสียเวลายิงซ้ำ
    try:
        from ..services import system_state
        if system_state.flow_blocked():
            raise RuntimeError("Google Flow โดนพักการใช้งานเนื่องจากตรวจพบว่าโควตาหมดในการรันก่อนหน้า")
    except RuntimeError:
        raise
    except Exception:
        pass

    # 1a) มีรูป product จริง → image-to-video ก่อน (วีดีโอตรงเมนูจริง = น่าเชื่อถือสุด)
    if image_path and os.path.exists(image_path):
        try:
            from .flow_automation import generate_video_from_image
            return generate_video_from_image(image_path, prompt), "flow"
        except Exception as e:
            print(f"[flow-img-fallback] image-to-video ล้มเหลว ({str(e)[:80]}) → ลอง text-to-video")

    # 1b) ไม่มีรูป/ทำไม่ได้ → text-to-video ด้วย Browser Automation (Flow)
    try:
        from .flow_automation import generate_video_flow
        return generate_video_flow(prompt), "flow"
    except Exception as e:
        print(f"[flow-auto-fallback] Failed browser automation: {e}")
        print("[flow-auto-fallback] Attempting to fall back to Veo API...")
        
        # 2) Fallback ไปที่ Veo API หากมีคีย์จริง (เริ่มด้วย AIzaSy)
        if settings.has_gemini and settings.gemini_api_key.startswith("AIzaSy"):
            try:
                client = _client()
                op = client.models.generate_videos(model=settings.video_model, prompt=prompt)
                for _ in range(30):                       # poll สูงสุด ~5 นาที
                    if op.done:
                        break
                    time.sleep(10)
                    op = client.operations.get(op)
                vid = op.response.generated_videos[0]
                os.makedirs(settings.media_dir, exist_ok=True)
                path = os.path.join(settings.media_dir, f"veo_{uuid.uuid4().hex[:8]}.mp4")
                client.files.download(file=vid.video)
                vid.video.save(path)
                return path, "veo"
            except Exception as api_err:
                print(f"[gemini] veo api error: {api_err}")
                raise RuntimeError(f"การรันด้วย Veo API ล้มเหลว: {api_err}")
        
        raise RuntimeError(f"การสร้างวิดีโอล้มเหลว: Google Flow ผิดพลาด ({e}) และคีย์ Veo API ไม่พร้อมใช้งาน")


# มุมกล้องสไตล์ food reel ปังๆ — ใช้สร้างภาพหลายช็อตคนละมุม (แก้ปัญหาคลิปซ้ำ/น่าเบื่อ)
_BROLL_ANGLES = [
    "extreme macro close-up, steam rising, shallow depth of field, droplets glistening",
    "top-down flat lay, ingredients and garnish arranged around the bowl, bright clean",
    "chopsticks lifting noodles mid-air, broth dripping, dynamic motion, side angle",
    "45-degree hero shot, garnish in sharp focus, creamy bokeh background, warm light",
    "pouring broth / spooning sauce action shot, splash, appetizing, dramatic light",
    "cozy hand holding the bowl, blurred restaurant background, lifestyle vibe",
]


def download_images(urls: list[str], n: int = 4) -> list[str]:
    """โหลดรูปจริง (เช่นจาก Shopee) มาผสมในคลิป → ของจริง + AI = น่าเชื่อถือ.
    Shopee อาจบล็อก hotlink (403) → ข้ามไฟล์ที่โหลดไม่ได้ คืนเท่าที่ได้."""
    import httpx
    out = []
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://shopee.co.th/"}
    for u in [x for x in (urls or []) if x][:n]:
        try:
            r = httpx.get(u, timeout=30, follow_redirects=True, headers=headers)
            if r.status_code == 200 and len(r.content) > 3000:
                os.makedirs(settings.media_dir, exist_ok=True)
                p = os.path.join(settings.media_dir, f"real_{uuid.uuid4().hex[:8]}.jpg")
                with open(p, "wb") as f:
                    f.write(r.content)
                out.append(p)
        except Exception as e:  # pragma: no cover
            print(f"[img dl] {str(e)[:80]}")
    return out


def generate_food_broll(dish: str, n: int = 6) -> list[str]:
    """สร้างภาพอาหารหลายมุมคนละช็อต (B-roll) จากเมนูเดียว → คลิปไม่ซ้ำ ดูมีชีวิต.
    ไม่มี key → placeholder. คืน list ของ path ภาพ."""
    dish = (dish or "delicious thai food").strip()
    out = []
    for ang in _BROLL_ANGLES[:max(1, n)]:
        prompt = (f"appetizing professional food photography of {dish}, {ang}, "
                  "vibrant mouthwatering colors, 9:16 vertical, ultra detailed, no text")
        out.append(generate_image(prompt))
    return out


def _voice_script(voiceover_script: str, hook: str) -> str:
    """บทพากย์ไทย 'รับประกันไม่ว่าง' — ถ้า AI ไม่ส่งบทมา ใช้ hook, ไม่มีก็ใช้ประโยคปิดการขายมาตรฐาน.
    → ทุกคลิปมีเสียงไทยเสมอ."""
    s = (voiceover_script or "").strip()
    if s:
        return s
    h = (hook or "").strip()
    if h:
        return h
    return "ร้านนี้เด็ดจริง อร่อยคุ้มราคา สั่งผ่าน Shopee Food ได้เลย ลิงก์อยู่ในคอมเมนต์!"


def _narrate_image(ff: str, img: str, script: str, voice: str) -> str | None:
    """ภาพ AI → วีดีโอ Ken Burns + เสียงพากย์ไทย (ยาวเท่าเสียง) + ซับเด้ง + เพลง. คืน path หรือ None."""
    from . import video_ffmpeg
    narr, ass = video_ffmpeg.build_voice_captions(ff, script, voice)
    if not narr:
        return None
    vdur = video_ffmpeg._duration(narr) or max(3, settings.video_seconds)
    seg = video_ffmpeg._scene_clip(ff, img, "", vdur, 0)
    if not seg:
        return None
    out_vid = os.path.join(settings.media_dir, f"aireel_{uuid.uuid4().hex[:8]}.mp4")
    final = video_ffmpeg._mux_audio(ff, seg, narr, ass, out_vid)   # cleans narr+ass
    if os.path.exists(seg):
        try:
            os.remove(seg)
        except Exception:
            pass
    return final


def make_media(image_prompt: str, video_prompt: str, hook: str = "", voiceover_script: str = "", label: str = "A", product_image: str = "") -> tuple[str, str, str, str]:
    """คืน (media_type, media_path, image_path, media_source) ตาม VIDEO_MODE — **ทุกคลิปมีเสียงพากย์ไทยเสมอ**.
    media_source = flow (Google Flow) | veo | ffmpeg | image — ใช้กรองใน Dashboard.
    image_path = ภาพต้นฉบับ เก็บไว้ใช้ทำคลิปรวม montage. product_image = รูป Shopee จริง → image-to-video."""
    from . import video_ffmpeg
    mode = settings.video_mode
    voice = "th-TH-PremwadeeNeural" if label == "A" else "th-TH-NiwatNeural"
    script = _voice_script(voiceover_script, hook)
    ff = video_ffmpeg.find_ffmpeg() if settings.enable_voiceover else ""

    # === โหมดวีดีโอจริง (Flow/Veo image-to-video) → พากย์ไทยทับ ===
    if mode == "veo" or (settings.enable_video and mode == "image"):
        vid, source = generate_video(video_prompt, image_path=product_image)   # source = flow | veo
        img = video_ffmpeg.extract_frame(vid) or ""
        if ff and script:
            out_vid = os.path.join(settings.media_dir, f"{source}_voiced_{uuid.uuid4().hex[:8]}.mp4")
            final = video_ffmpeg.add_audio(ff, vid, script, out_vid, voice)   # แทนเสียง Veo ด้วยพากย์ไทย
            if final:
                if os.path.exists(vid):
                    try:
                        os.remove(vid)
                    except Exception:
                        pass
                vid = final
            else:
                print("[voice] ⚠️ ใส่พากย์ไทยลงวีดีโอ Flow ไม่สำเร็จ (TTS อาจล่ม) — ใช้คลิปเดิม")
        return "video", vid, img, source

    # === โหมด ffmpeg / image → ภาพ AI กลายเป็นวีดีโอพากย์ไทย (image mode เดิมเงียบ → ตอนนี้มีเสียง) ===
    img = generate_image(image_prompt)
    if ff and script:
        narrated = _narrate_image(ff, img, script, voice)
        if narrated:
            return "video", narrated, img, "ffmpeg"
        print("[voice] ⚠️ ทำวีดีโอพากย์จากภาพไม่สำเร็จ (TTS อาจล่ม) — fallback")

    # fallback: ไม่มี ffmpeg/TTS → วีดีโอเงียบมี hook (โหมด ffmpeg) หรือภาพนิ่ง
    if mode == "ffmpeg":
        vid = video_ffmpeg.image_to_reel(img, hook)
        return ("video", vid, img, "ffmpeg") if vid else ("image", img, img, "image")
    return "image", img, img, "image"
