# -*- coding: utf-8 -*-
"""ทดสอบ: (1) edge-tts สร้างเสียงไทยได้ไหม (2) ใส่พากย์ไทยลงวีดีโอ i2v ได้ไหม."""
import os, sys, glob
sys.path.insert(0, "backend")
os.environ.setdefault("DATA_DIR", os.path.abspath("data"))

from app.engines import voice_tts, video_ffmpeg

SCRIPT = ("บอกเลยว่าเด็ด! ก๋วยเตี๋ยวเรือร้านนี้ น้ำซุปเข้มข้น หอมเครื่อง เนื้อนุ่มเต็มชาม "
          "สั่งผ่าน Shopee Food คุ้มสุดๆ ลิงก์อยู่ในคอมเมนต์เลย!")

print("=== 1) edge-tts เสียงไทย ===")
mp3 = voice_tts.synth("ทดสอบเสียงพากย์ภาษาไทย อร่อยคุ้มราคา", "th-TH-PremwadeeNeural")
if mp3 and os.path.exists(mp3):
    print(f"  ✅ ได้เสียง: {mp3} ({os.path.getsize(mp3)} bytes, {video_ffmpeg._duration(mp3):.1f}s)")
else:
    print("  ❌ edge-tts/gTTS ไม่ได้เสียง (เช็คเน็ต)")
    sys.exit(1)

print("\n=== 2) ใส่พากย์ไทยลงวีดีโอ i2v ===")
vids = sorted(glob.glob("data/media/i2v_*.mp4"), key=os.path.getmtime)
if not vids:
    print("  ไม่มีวีดีโอ i2v ให้ทดสอบ"); sys.exit(0)
src = os.path.abspath(vids[-1])
print(f"  วีดีโอต้นฉบับ: {src}")
ff = video_ffmpeg.find_ffmpeg()
out = os.path.abspath("data/media/voiced_test.mp4")
final = video_ffmpeg.add_audio(ff, src, SCRIPT, out, "th-TH-PremwadeeNeural")
if final and os.path.exists(final):
    # เช็คว่ามี audio stream + ความยาว
    import subprocess
    r = subprocess.run([ff, "-i", final], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    has_audio = "Audio:" in r.stderr
    dur = [l for l in r.stderr.splitlines() if "Duration" in l]
    print(f"  ✅ ได้คลิปมีเสียง: {final} ({os.path.getsize(final)} bytes)")
    print(f"     มี audio stream: {has_audio}")
    print(f"     {dur[0].strip() if dur else ''}")
else:
    print("  ❌ ใส่เสียงไม่สำเร็จ")
