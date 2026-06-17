# -*- coding: utf-8 -*-
"""เดโม 'รีวิวในร้าน': พ่อครัวพูดเต็มจอชวนลูกค้า → แอคชั่นในครัว/คนกิน + พ่อครัว PiP + ASMR."""
import sys, os, uuid
sys.path.insert(0, "backend")
from app.engines import video_ffmpeg as vf, talking_head, stock_video, stock_sfx, media_gemini
from app.config import settings
from app.db import get_session, Store, jloads

ff = vf.find_ffmpeg()
M = settings.media_dir
def tmp(ext): return os.path.join(M, f"_chef_{uuid.uuid4().hex[:8]}.{ext}")
def rid(): return os.path.join(M, f"chef_reel_{uuid.uuid4().hex[:8]}.mp4")

STORE = int(sys.argv[1]) if len(sys.argv) > 1 else 2
VOICE = "th-TH-NiwatNeural"
chef = os.path.join(settings.data_dir, "persona", "chef.png")

with get_session() as s:
    st = s.get(Store, STORE)
    name = st.name
    menu = jloads(st.menu_json, [])
    urls = jloads(st.image_urls_json, [])

# สคริปต์พ่อครัว — ตื่นเต้น ชวนกิน
script = ("สวัสดีครับ! ร้านลุง ก๋วยเตี๋ยวเรือเลอรส เปิดมากว่าสี่สิบปี "
          "เส้นนุ่มๆ น้ำซุปสูตรเด็ด เคี่ยวเองทุกวัน เนื้อเปื่อยนุ่ม ลูกชิ้นเด้ง "
          "มาเด้อ มาชิมกันเยอะๆ นะครับ รับรองไม่ผิดหวัง สั่งเลย ลิงก์อยู่ในคอมเมนต์ครับ")

print("[1] เสียงพ่อครัว + ซับ...")
narr, ass = vf.build_voice_captions(ff, script, VOICE)
V = vf._duration(narr)
print("   voice:", round(V, 1), "วิ")

print("[2] พ่อครัวพูด (Wav2Lip)...")
chef_talk = talking_head.synthesize(narr, face=chef)
print("   chef_talk:", chef_talk, round(vf._duration(chef_talk or ''), 1))
if not chef_talk:
    sys.exit(2)

print("[3] พ่อครัวเต็มจอ (เบลอ-ฟิล 9:16)...")
chef_full = tmp("mp4")
vf._run(ff, ["-i", chef_talk, "-filter_complex",
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24[bg];"
    "[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[v]",
    "-map", "[v]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", chef_full])

T = round(min(4.5, V * 0.32), 2)   # ช่วงเปิดตัวพ่อครัวเต็มจอ
print(f"[4] ตัด intro พ่อครัว {T} วิ + PiP ส่วนที่เหลือ...")
chef_intro = tmp("mp4")
vf._run(ff, ["-i", chef_full, "-t", f"{T}", "-c:v", "libx264", "-pix_fmt", "yuv420p", chef_intro])
chef_pip_src = tmp("mp4")
vf._run(ff, ["-ss", f"{T}", "-i", chef_talk, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", chef_pip_src])

print("[5] footage ก๋วยเตี๋ยว (คิวรีตรงเมนู เลี่ยงของหลุดหัวข้อ)...")
queries = stock_video.build_queries(name + " ก๋วยเตี๋ยวเรือ", menu)
print("   queries:", queries)
stock = stock_video.search_food_clips(queries, n=6)
print("   ได้", len(stock), "คลิป")
if not stock:
    sys.exit(3)

need = V - T
beat = [0.9, 1.3, 1.0, 1.2]
clips, durs, i, acc = [], [], 0, 0.0
while acc < need and i < 14:
    src = stock[i % len(stock)]
    si = round(2.0 * beat[i % 4], 2)
    c = vf._video_clip(ff, src, max(1.4, si), i)
    if c:
        d = vf._duration(c) or si
        clips.append(c); durs.append(d)
        acc += d if len(clips) == 1 else (d - 0.22)
    i += 1
broll = tmp("mp4")
if len(clips) == 1:
    import shutil; shutil.copy(clips[0], broll)
else:
    vf._concat_xfade(ff, clips, durs, broll) or vf._concat_hardcut(ff, clips, broll)
for c in clips:
    if os.path.exists(c): os.remove(c)

print("[6] ซ้อนพ่อครัว PiP วงกลม บน footage...")
broll_pip = talking_head.overlay_pip(broll, chef_pip_src, width=300, corner="tr", keep_audio=False)

print("[7] ต่อ intro + แอคชั่น → ใส่เสียง+ASMR...")
visual = tmp("mp4")
lst = tmp("txt")
with open(lst, "w", encoding="utf-8") as f:
    f.write(f"file '{chef_intro.replace(os.sep,'/')}'\n")
    f.write(f"file '{broll_pip.replace(os.sep,'/')}'\n")
vf._run(ff, ["-f", "concat", "-safe", "0", "-i", lst,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", visual])

ambient = stock_sfx.build_sfx_bed() if stock_sfx.available() else None
out = rid()
final = vf._mux_audio(ff, visual, narr, ass, out, ambient)
print("RESULT:", final)
for t in (chef_full, chef_intro, chef_pip_src, broll, broll_pip, visual, lst, chef_talk):
    if t and os.path.exists(t): os.remove(t)
if final:
    open("data/persona/_last_chef.txt", "w", encoding="utf-8").write(final)
