"""ทำวีดีโอ Reels/Shorts ฟรีจากภาพ AI ด้วย ffmpeg.

- image_to_reel : ภาพเดียว -> คลิป Ken Burns (ซูม/เลื่อน) + ข้อความ hook
- build_reel    : หลายภาพ -> คลิปเดียวต่อเนื่อง หลายฉาก + ครอสเฟด (montage)
ไม่มี ffmpeg หรือ error -> คืน None (ระบบ fallback ไปใช้ภาพนิ่ง).
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import uuid

from ..config import settings


def find_ffmpeg() -> str:
    if settings.ffmpeg_path and os.path.exists(settings.ffmpeg_path):
        return settings.ffmpeg_path
    p = shutil.which("ffmpeg")
    if p:
        return p
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    hits = glob.glob(os.path.join(base, "Gyan.FFmpeg*", "**", "ffmpeg.exe"), recursive=True)
    if hits:
        return hits[0]
    # fallback สุดท้าย: ffmpeg ที่มากับ imageio-ffmpeg (pip) — กันเครื่องที่ไม่มี ffmpeg ติดตั้ง (เช่น native Windows)
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return ""


def _font() -> str:
    for f in ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/leelawui.ttf",
              "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(f):
            return f
    return ""


def _wrap(text: str, width: int = 20, max_lines: int = 3) -> str:
    text = (text or "").strip()
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            lines.append(cur); cur = ""
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return "\n".join(lines)


def _esc(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:")


def _run(ff: str, args: list[str], cwd: str | None = None) -> bool:
    try:
        r = subprocess.run([ff, "-y", *args], capture_output=True, timeout=240, cwd=cwd)
        if r.returncode != 0:
            print(f"[ffmpeg] rc={r.returncode}: {r.stderr.decode('utf-8','ignore')[-300:]}")
        return r.returncode == 0
    except Exception as e:
        print(f"[ffmpeg] {e}")
        return False


def _scene_clip(ff: str, image_path: str, text: str, seconds: float, motion: int,
                punch: bool = False) -> str | None:
    """ภาพ 1 ใบ -> คลิป 1 ฉาก (ทิศทางกล้องต่างกันตาม motion). punch = ซูมแรง ใช้กับช็อตตัดเร็ว."""
    if not os.path.exists(image_path):
        return None
    frames = int(seconds * 30)
    out = os.path.join(settings.media_dir, f"_seg_{uuid.uuid4().hex[:8]}.mp4")
    base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    zi = 0.0048 if punch else 0.0013      # ความเร็วซูมเข้า
    pi = 0.0024 if punch else 0.0008      # ความเร็วซูมตอน pan
    zc = 1.45 if punch else 1.28          # เพดานซูม
    if motion % 3 == 0:        # ซูมเข้ากลางภาพ (punch)
        zp = (f"zoompan=z='min(zoom+{zi},{zc})':d={frames}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    elif motion % 3 == 1:      # เลื่อนซ้าย->ขวา + ซูม
        zp = (f"zoompan=z='min(zoom+{pi},1.3)':d={frames}:"
              f"x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    else:                      # เลื่อนบน->ล่าง + ซูม
        zp = (f"zoompan=z='min(zoom+{pi},1.3)':d={frames}:"
              f"x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{frames}':s=1080x1920:fps=30")
    # เกรดสีให้อาหารน่ากิน: อิ่มสี + คอนทราสต์ + อุ่นนิด + vignette ให้โฟกัสกลางจาน
    grade = "eq=contrast=1.08:saturation=1.34:brightness=0.015,unsharp=5:5:0.4,vignette=PI/5"
    vf = f"{base},{zp},{grade}"
    tmp = None
    font = _font()
    if font and text:
        tmp = os.path.join(settings.media_dir, f"_t_{uuid.uuid4().hex[:6]}.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(_wrap(text))
        vf += (f",drawtext=fontfile='{_esc(font)}':textfile='{_esc(tmp)}':fontcolor=white:"
               "fontsize=46:line_spacing=12:box=1:boxcolor=black@0.5:boxborderw=22:"
               "x=(w-text_w)/2:y=h-text_h-170")
    ok = _run(ff, ["-loop", "1", "-i", image_path, "-t", str(seconds), "-r", "30",
                   "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    if ok and os.path.exists(out) and os.path.getsize(out) > 1000:
        return out
    # ลองใหม่แบบไม่มีข้อความ (กัน drawtext พัง)
    if font and text:
        ok = _run(ff, ["-loop", "1", "-i", image_path, "-t", str(seconds), "-r", "30",
                       "-vf", f"{base},{zp},{grade}", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        if ok and os.path.exists(out) and os.path.getsize(out) > 1000:
            return out
    return None


def _cta_clip(ff: str, image_path: str, lines: list[str], seconds: float) -> str | None:
    """ฉากปิด — ภาพมืดลง + ข้อความ CTA ใหญ่กลางจอ (ชื่อร้าน + สั่งเลย + ลิงก์คอมเมนต์)."""
    if not os.path.exists(image_path) or not lines:
        return None
    frames = int(seconds * 30)
    out = os.path.join(settings.media_dir, f"_cta_{uuid.uuid4().hex[:8]}.mp4")
    base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    vf = (f"{base},eq=brightness=-0.30:saturation=0.85,"
          f"zoompan=z='min(zoom+0.0016,1.2)':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    font = _font()
    tmp = None
    if font:
        tmp = os.path.join(settings.media_dir, f"_t_{uuid.uuid4().hex[:6]}.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        vf += (f",drawtext=fontfile='{_esc(font)}':textfile='{_esc(tmp)}':fontcolor=white:"
               "fontsize=70:line_spacing=26:borderw=4:bordercolor=black:"
               "x=(w-text_w)/2:y=(h-text_h)/2")
    ok = _run(ff, ["-loop", "1", "-i", image_path, "-t", str(seconds), "-r", "30",
                   "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    return out if (ok and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def image_to_reel(image_path: str, text: str = "") -> str | None:
    """ภาพเดียว -> คลิป Ken Burns 1 ฉาก."""
    ff = find_ffmpeg()
    if not ff or not image_path:
        return None
    seg = _scene_clip(ff, image_path, text, max(3, settings.video_seconds), 0)
    if not seg:
        return None
    out = os.path.join(settings.media_dir, f"aireel_{uuid.uuid4().hex[:8]}.mp4")
    shutil.move(seg, out)
    return out


def get_music(ff: str) -> str:
    """เพลงประกอบ: ใช้ไฟล์ที่ผู้ใช้วางใน data/music ก่อน, ไม่มี -> สร้างเพลงคลอ ambient เริ่มต้น."""
    os.makedirs(settings.music_dir, exist_ok=True)
    for ext in ("*.mp3", "*.m4a", "*.wav", "*.aac", "*.ogg"):
        files = [f for f in glob.glob(os.path.join(settings.music_dir, ext))
                 if "_default_bed" not in os.path.basename(f)]
        if files:
            import random
            return random.choice(files)
    bed = os.path.join(settings.music_dir, "_default_bed.mp3")
    if os.path.exists(bed) and os.path.getsize(bed) > 1000:
        return bed
    # คอร์ด A เมเจอร์ (220 / 277.18 / 329.63 Hz) + tremolo ให้นุ่มๆ
    ok = _run(ff, ["-f", "lavfi", "-i", "sine=frequency=220:duration=30",
                   "-f", "lavfi", "-i", "sine=frequency=277.18:duration=30",
                   "-f", "lavfi", "-i", "sine=frequency=329.63:duration=30",
                   "-filter_complex",
                   "[0][1][2]amix=inputs=3,tremolo=f=4:d=0.5,aformat=channel_layouts=stereo[a]",
                   "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "6", bed])
    return bed if (ok and os.path.exists(bed) and os.path.getsize(bed) > 1000) else ""


def find_ffprobe() -> str:
    p = shutil.which("ffprobe")
    if p:
        return p
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    hits = glob.glob(os.path.join(base, "Gyan.FFmpeg*", "**", "ffprobe.exe"), recursive=True)
    return hits[0] if hits else ""


def _duration(path: str) -> float:
    fp = find_ffprobe()
    if not fp or not os.path.exists(path):
        return 0.0
    try:
        r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _caption_lines(script: str, max_lines: int = 7, target: int = 20) -> list[str]:
    """แตกสคริปต์เป็นบรรทัดซับสั้นๆ (TikTok-style ทีละวลี ~20 ตัวอักษร)."""
    import re
    text = re.sub(r"\s+", " ", (script or "").strip())
    if not text:
        return []
    lines, cur = [], ""
    for tok in text.split(" "):
        if cur and len(cur) + 1 + len(tok) > target:
            lines.append(cur); cur = tok
        else:
            cur = (cur + " " + tok).strip()
        while len(cur) > target + 10:          # token ไทยยาวไม่มีช่องว่าง → ตัดแข็ง
            lines.append(cur[:target]); cur = cur[target:]
    if cur:
        lines.append(cur)
    lines = [l.strip() for l in lines if l.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])]
    return lines[:max_lines]


def _ass_t(sec: float) -> str:
    cs = max(0, int(round(sec * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# สีไฮไลต์คำที่ 'พูดไปแล้ว' (TikTok karaoke sweep) — ASS ใช้ BGR: &H00BBGGRR
_HL_COLORS = [
    "&H0000FFFF",  # เหลืองสด
    "&H0014FF39",  # เขียวนีออน (#39FF14)
    "&H0000C8FF",  # ส้มทอง
    "&H00FFFF00",  # ฟ้าไซแอน
]
# สีฐาน (คำที่ 'ยังไม่พูด') — ขาว/นวล อ่านง่าย
_BASE_COLORS = ["&H00FFFFFF", "&H00F5FFFA", "&H00FFFFE0"]


def _kara_tokens(text: str, dur_cs: int) -> str:
    """แตกข้อความเป็น token แล้วใส่ \\kf (karaoke fill) ตามสัดส่วนความยาว → ไฮไลต์กวาดทีละคำตามจังหวะเสียง.
    - มีช่องว่าง (อังกฤษ/อีสาน) → แบ่งทีละคำจริง
    - ไม่มีช่องว่าง (ไทย) → แบ่งเป็นชิ้นตัวอักษร ~3 ตัว (กวาดเป็นจังหวะ ไม่ต้องตัดคำ)
    รวม cs ของทุก token = dur_cs พอดี (เศษยัดใส่ token สุดท้าย)."""
    t = (text or "").replace("\n", " ").replace("{", "(").replace("}", ")").strip()
    if not t:
        return ""
    if " " in t:
        toks = [w + " " for w in t.split(" ") if w != ""]
    else:
        toks = [t[i:i + 3] for i in range(0, len(t), 3)] or [t]
    weights = [max(1, len(x.strip()) or 1) for x in toks]
    total = sum(weights) or 1
    parts, acc = [], 0
    for i, (tok, w) in enumerate(zip(toks, weights)):
        cs = max(1, dur_cs - acc) if i == len(toks) - 1 else max(1, round(dur_cs * w / total))
        acc += cs
        parts.append(f"{{\\kf{cs}}}{tok}")
    return "".join(parts)


def _build_ass(segs: list[tuple[str, float, float]]) -> str:
    import random
    out = os.path.join(settings.media_dir, f"_cap_{uuid.uuid4().hex[:8]}.ass")
    # สุ่มขนาดฟอนต์ + สีไฮไลต์ (กันซ้ำแพตเทิร์น)
    # karaoke: \kf กวาดจาก PrimaryColour → SecondaryColour → ตั้ง Primary = ฐาน 'ยังไม่พูด' (ขาว),
    # Secondary = ไฮไลต์ 'พูดแล้ว' (สีสด) → คำเด้งเป็นสีสดตอนพูดแล้วค้างไว้ (สไตล์ TikTok)
    fsize = random.randint(82, 94)
    hl = random.choice(_HL_COLORS)
    base = random.choice(_BASE_COLORS)
    header = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        f"[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        f"OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        f"MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Pop,Tahoma,{fsize},{base},{hl},&H00141414,&H96000000,1,0,1,6,3,2,60,60,560,1\n\n"
        f"[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    body = ""
    for text, start, end in segs:
        dur_cs = max(1, int(round((end - start) * 100)))
        kara = _kara_tokens(text, dur_cs)
        if not kara:
            continue
        # ป็อปเข้า (scale bounce) + fade — แล้วให้ karaoke กวาดสีตลอดช่วงที่โชว์
        eff = r"{\fad(70,50)\fscx78\fscy78\t(0,150,\fscx106\fscy106)\t(150,240,\fscx100\fscy100)}"
        body += f"Dialogue: 0,{_ass_t(start)},{_ass_t(end)},Pop,,0,0,0,,{eff}{kara}\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(header + body)
    return out


def _split_speakers(script: str):
    """บทพอดแคสต์ 2 คน: ถ้า 'ทุกบรรทัด' ขึ้นต้นด้วย A:/B: (หรือ โฮสต์1/2, พิธีกร1/2) → คืน [(A|B, ข้อความ)],
    ไม่งั้นคืน None (ใช้ทางเสียงเดียวปกติ — ไม่กระทบแนวอื่น)."""
    import re as _re
    raw = [l.strip() for l in _re.split(r"[\r\n]+", script or "") if l.strip()]
    if len(raw) < 2:
        return None
    pat = _re.compile(r"^(?:host\s*)?([abAB])\s*[:：]\s*(.+)$|^(?:โฮสต์|พิธีกร)\s*([12])\s*[:：]\s*(.+)$")
    out = []
    for l in raw:
        m = pat.match(l)
        if not m:
            return None
        if m.group(1):
            out.append((m.group(1).upper(), m.group(2)))
        else:
            out.append(("A" if m.group(3) == "1" else "B", m.group(4)))
    return out or None


def build_voice_captions(ff: str, script: str, voice: str | None):
    """แยกพากย์ทีละบรรทัด → วัดเวลาจริง → คืน (ไฟล์เสียงรวม, ไฟล์ซับ ASS ที่ซิงค์).
    ถ้าเป็นบทพอดแคสต์ (A:/B:) → สลับ 2 เสียง (หญิง/ชาย) ต่อผู้พูดอัตโนมัติ."""
    from . import voice_tts
    import re as _re
    # ตัด emoji ออกจากบทพากย์/ซับ — กัน TTS อ่านเพี้ยน (เช่น 🍜) + ซับไม่มี emoji รก
    script = _re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿️]", "", script or "")
    # podcast 2 เสียง: บท A:/B: → สลับเสียงหญิง-ชายต่อผู้พูด (ตัดป้าย 'A:/B:' ออกจากซับ/เสียง)
    pairs = _split_speakers(script)
    if pairs:
        va = voice or "th-TH-PremwadeeNeural"
        vb = "th-TH-NiwatNeural" if va != "th-TH-NiwatNeural" else "th-TH-PremwadeeNeural"
        voiced = [(ln, va if spk == "A" else vb) for spk, text in pairs for ln in _caption_lines(text)]
    else:
        voiced = [(ln, voice) for ln in _caption_lines(script)]
    if not voiced:
        return None, None
    seg_files, segs, t = [], [], 0.0
    for ln, lnvoice in voiced:
        mp3 = voice_tts.synth(ln, lnvoice)
        if not mp3:
            continue
        d = _duration(mp3)
        if d <= 0.2:
            d = max(1.0, len(ln) * 0.09)
        seg_files.append(mp3)
        segs.append((ln, t, t + d))
        t += d
    if not seg_files:
        return None, None
    narration = os.path.join(settings.media_dir, f"narr_{uuid.uuid4().hex[:8]}.mp3")
    if len(seg_files) == 1:
        shutil.copyfile(seg_files[0], narration)
    else:
        lst = os.path.join(settings.media_dir, f"_al_{uuid.uuid4().hex[:6]}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for s in seg_files:
                f.write(f"file '{s.replace(os.sep, '/')}'\n")
        ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst, "-c:a", "libmp3lame", "-q:a", "4", narration])
        if os.path.exists(lst):
            os.remove(lst)
        if not (ok and os.path.exists(narration)):
            narration = seg_files[0]
    ass = _build_ass(segs)
    for s in seg_files:
        if s != narration and os.path.exists(s):
            os.remove(s)
    return narration, ass


def _build_ambient(ff: str, videos: list[str], n: int = 4) -> str | None:
    """ทำเสียง ASMR bed จากเสียงจริงใน footage (ซด/ผัด/ราดน้ำซุป) — คลิปไหนไม่มีเสียงข้าม."""
    auds = []
    for v in [x for x in videos if x and os.path.exists(x)][:n]:
        a = os.path.join(settings.media_dir, f"_amb_{uuid.uuid4().hex[:8]}.wav")
        if _run(ff, ["-i", v, "-vn", "-ac", "2", "-ar", "44100", "-t", "4", a]) \
                and os.path.exists(a) and os.path.getsize(a) > 8000:
            auds.append(a)
        elif os.path.exists(a):
            os.remove(a)
    if not auds:
        return None
    bed = os.path.join(settings.media_dir, f"asmr_{uuid.uuid4().hex[:8]}.wav")
    if len(auds) == 1:
        shutil.copyfile(auds[0], bed)
    else:
        lst = os.path.join(settings.media_dir, f"_aml_{uuid.uuid4().hex[:6]}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for a in auds:
                f.write(f"file '{a.replace(os.sep, '/')}'\n")
        ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst, bed])
        if os.path.exists(lst):
            os.remove(lst)
        if not (ok and os.path.exists(bed)):
            bed = auds[0]
    for a in auds:
        if a != bed and os.path.exists(a):
            os.remove(a)
    return bed if os.path.exists(bed) else None


def _mux_audio(ff: str, video: str, narr: str | None, ass: str | None, out: str,
               ambient: str | None = None) -> str | None:
    """รวมเสียง (พากย์ + ซับ + เพลง + บรรยากาศร้าน) ลงวีดีโอ.
    ถ้าใส่บรรยากาศแล้ว mux พัง (ไฟล์เสีย) → retry ไม่ใส่บรรยากาศ (คลิปไม่หาย)."""
    music = get_music(ff) if settings.enable_music else ""
    amb0 = ambient if (ambient and os.path.exists(ambient)) else ""

    def attempt(use_amb: bool) -> bool:
        amb = amb0 if use_amb else ""
        if not narr and not music and not amb:
            return False
        fc, vlabel = [], "0:v"
        if ass:
            fc.append(f"[0:v]ass={os.path.basename(ass)}[v]")   # cwd=media เลี่ยง C: ใน path
            vlabel = "[v]"
        inputs, idx, streams = ["-i", video], 1, []
        if narr:
            inputs += ["-i", narr]
            fc.append(f"[{idx}:a]volume=1.0[av]"); streams.append("[av]"); idx += 1
        if music:
            import random
            mdur = _duration(music)
            if mdur > 10.0:
                # สุ่มตำแหน่งเริ่มต้นของเพลงเพื่อแก้ปัญหา Audio Hash ซ้ำกัน
                offset = round(random.uniform(0.0, mdur - 5.0), 2)
                inputs += ["-stream_loop", "-1", "-ss", str(offset), "-i", music]
            else:
                inputs += ["-stream_loop", "-1", "-i", music]
            fc.append(f"[{idx}:a]volume={settings.music_volume}[am]"); streams.append("[am]"); idx += 1
        if amb:
            inputs += ["-stream_loop", "-1", "-i", amb]
            fc.append(f"[{idx}:a]volume={settings.asmr_volume}[aa]"); streams.append("[aa]"); idx += 1
        if len(streams) >= 2:
            # เพลง/บรรยากาศ loop → duration=longest อนันต์ → -shortest ตัดที่ความยาววีดีโอ
            fc.append(f"{''.join(streams)}amix=inputs={len(streams)}:duration=longest:dropout_transition=0[a]")
            amap = "[a]"
        else:
            amap = streams[0]
        args = [*inputs, "-filter_complex", ";".join(fc), "-map", vlabel, "-map", amap]
        args += (["-c:v", "libx264", "-pix_fmt", "yuv420p"] if ass else ["-c:v", "copy"])
        args += ["-c:a", "aac", "-movflags", "+faststart", "-shortest", out]
        return _run(ff, args, cwd=settings.media_dir) and os.path.exists(out) and os.path.getsize(out) > 1000

    ok = attempt(True)
    if not ok and amb0:
        print("[mux] ใส่บรรยากาศแล้วพัง → retry ไม่ใส่บรรยากาศ")
        ok = attempt(False)
    for tmp in (ass, narr, amb0):
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    return out if ok else None


def add_audio(ff: str, video: str, narration_text: str, out: str, voice: str | None = None,
              ambient: str | None = None) -> str | None:
    """ใส่เสียงพากย์ + ซับเด้ง + เพลง + (ออปชั่น) ASMR ลงในวีดีโอ (สร้างเสียงพากย์ให้)."""
    narr, ass = build_voice_captions(ff, narration_text, voice) if narration_text else (None, None)
    return _mux_audio(ff, video, narr, ass, out, ambient)


def _concat_hardcut(ff: str, clips: list[str], silent: str) -> bool:
    lst = os.path.join(settings.media_dir, f"_list_{uuid.uuid4().hex[:6]}.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.replace(os.sep, '/')}'\n")
    ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    if not (ok and os.path.exists(silent) and os.path.getsize(silent) > 1000):
        ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst,
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", silent])
    if os.path.exists(lst):
        os.remove(lst)
    return ok and os.path.exists(silent) and os.path.getsize(silent) > 1000


# transition แบบ whip/slide ให้คลิปลื่นมีพลัง (วนใช้หลายแบบ ฉากเข้า CTA = fade)
_TRANS = ["slideleft", "smoothleft", "wiperight", "slideup", "smoothright", "circleopen"]


def _concat_xfade(ff: str, clips: list[str], durs: list[float], silent: str,
                  trans: float = 0.22) -> bool:
    """ต่อคลิปด้วย xfade (whip/slide) แทน hard cut → ลื่นมีจังหวะ."""
    if len(clips) < 2:
        return False
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    fc, prev, acc = [], "[0:v]", durs[0]
    for i in range(1, len(clips)):
        import random
        t = "fade" if i == len(clips) - 1 else random.choice(_TRANS)
        off = max(0.05, acc - trans)
        lab = f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition={t}:duration={trans}:offset={off:.3f}{lab}")
        prev, acc = lab, acc + durs[i] - trans
    args = [*inputs, "-filter_complex", ";".join(fc), "-map", prev,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", silent]
    ok = _run(ff, args)
    return ok and os.path.exists(silent) and os.path.getsize(silent) > 1000


def build_reel(scenes: list[tuple[str, str]], seconds_each: float | None = None,
               transition: float = 0.3, narration: str = "", voice: str | None = None,
               cta_lines: list[str] | None = None, progress_cb=None) -> str | None:
    """หลายภาพ -> คลิปตัดเร็วมีจังหวะ (zoom punch + ความเร็วแปรผัน + xfade) + ฉากปิด CTA + ซับเด้ง + เสียง + เพลง.
    progress_cb(step:str, pct:int) = callback รายงานความคืบหน้า (optional)."""
    def _cb(step, pct):
        if progress_cb:
            try:
                progress_cb(step, pct)
            except Exception:
                pass
    ff = find_ffmpeg()
    if not ff or not scenes:
        return None
    sec = seconds_each or settings.reel_scene_seconds
    imgs = [img for img, _ in scenes if img and os.path.exists(img)]
    if not imgs:
        return None
    # ตัดเร็ว: วนภาพ ~5-8 ช็อต + ความเร็วแปรผันตามบีต (เร็ว-ช้าสลับ)
    import random
    n = min(8, max(5, len(imgs) + 2))
    # สุ่มความยาวฉากเพื่อให้ระยะเวลาการตัดต่อของแต่ละคลิปไม่เหมือนกัน
    beat = [round(random.uniform(0.65, 1.35), 2) for _ in range(n)]
    clips, durs = [], []
    for i in range(n):
        _cb(f"🎞️ เรนเดอร์ฉาก {i + 1}/{n}", 12 + int(i / n * 44))
        si = round(sec * beat[i], 2)
        # สุ่มมุมมองการเคลื่อนไหวกล้อง (motion direction)
        motion_idx = random.randint(0, 100)
        c = _scene_clip(ff, imgs[i % len(imgs)], "", si, motion_idx, punch=True)
        if c:
            clips.append(c)
            durs.append(_duration(c) or si)
    # ฉากปิด CTA (ใช้ภาพแรก)
    if cta_lines:
        cta = _cta_clip(ff, imgs[0], cta_lines, settings.reel_cta_seconds)
        if cta:
            clips.append(cta)
            durs.append(_duration(cta) or settings.reel_cta_seconds)
    if not clips:
        return None

    _cb("🎬 ต่อคลิป + ทรานซิชัน", 60)
    silent = os.path.join(settings.media_dir, f"_silent_{uuid.uuid4().hex[:8]}.mp4")
    if len(clips) == 1:
        shutil.move(clips[0], silent)
    else:
        ok = _concat_xfade(ff, clips, durs, silent)        # ลื่นด้วย xfade ก่อน
        if not ok:
            ok = _concat_hardcut(ff, clips, silent)        # fallback ตัดตรง
        for c in clips:
            if os.path.exists(c):
                os.remove(c)
        if not ok:
            return None

    # ใส่เสียงพากย์ + เพลง
    _cb("🎙️ ทำเสียงพากย์ + ซับ + เพลง", 75)
    out = os.path.join(settings.media_dir, f"reel_{uuid.uuid4().hex[:8]}.mp4")
    final = add_audio(ff, silent, narration, out, voice)
    if final:
        if os.path.exists(silent):
            os.remove(silent)
        return final
    shutil.move(silent, out)   # ไม่มีเสียง -> ใช้คลิปเงียบ
    return out


# ----------------------------------------------------------- รีวิวจริง (ผสม footage วีดีโอ)
def _is_video_file(p: str) -> bool:
    return p.lower().endswith((".mp4", ".mov", ".m4v", ".webm"))


def _frame_from(ff: str, video: str) -> str | None:
    """ดึง 1 เฟรมจากวีดีโอ -> ภาพนิ่ง (ใช้ทำฉาก CTA เมื่อไม่มีรูป)."""
    out = os.path.join(settings.media_dir, f"_fr_{uuid.uuid4().hex[:8]}.png")
    ok = _run(ff, ["-ss", "0.5", "-i", video, "-vframes", "1", out])
    return out if (ok and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def _video_clip(ff: str, video_path: str, seconds: float, motion: int = 0) -> str | None:
    """footage จริง -> ช็อต 1080x1920 + เกรดสีอาหาร (ตัดเสียงเดิมทิ้ง)."""
    if not os.path.exists(video_path):
        return None
    out = os.path.join(settings.media_dir, f"_vseg_{uuid.uuid4().hex[:8]}.mp4")
    base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
    grade = "eq=contrast=1.07:saturation=1.3:brightness=0.01,unsharp=5:5:0.3,vignette=PI/6"
    ss = "0.2" if motion % 2 == 0 else "0.8"   # เริ่มต่างจุด = ไม่ซ้ำ
    ok = _run(ff, ["-ss", ss, "-i", video_path, "-t", f"{seconds:.2f}", "-vf", f"{base},{grade}",
                   "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", out])
    return out if (ok and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def build_review_reel(media_items: list[str], narration: str = "", voice: str | None = None,
                      cta_lines: list[str] | None = None, cta_image: str | None = None) -> str | None:
    """คลิปรีวิวจริง: เสียงพากย์ก่อน → ตัดภาพ/footage ให้ยาว 'พอดีเสียง' (ไม่เหลือช่องว่าง) + xfade + CTA + ASMR.
    cta_image = รูปสำหรับฉากปิด CTA โดยเฉพาะ (เช่นรูปสินค้า Shopee) — แยกจากฉากหลักที่เป็นวีดีโอล้วน."""
    ff = find_ffmpeg()
    items = [p for p in (media_items or []) if p and os.path.exists(p)]
    if not ff or not items:
        return None
    sec = settings.reel_scene_seconds
    beat = [0.85, 1.25, 0.95, 1.15]
    trans, cta_sec = 0.22, settings.reel_cta_seconds

    # 1) เสียงพากย์ก่อน → วัดความยาว → ใช้กำหนดความยาวคลิป (เสียงคลุมทั้งคลิป = ไม่มีช่วงเงียบให้ปัดหนี)
    narr, ass = build_voice_captions(ff, narration, voice) if narration else (None, None)
    vdur = _duration(narr) if narr else 0.0
    # คุมความยาวรีล: Shorts ที่ดีสุด 12-22 วิ — เกินนี้ตัดเสียง + fade (ไม่ให้ยาวจนคนเบื่อ)
    max_sec = float(settings.reel_max_seconds)
    if narr and vdur > max_sec:
        trimmed = os.path.join(settings.media_dir, f"narr_{uuid.uuid4().hex[:8]}.mp3")
        if _run(ff, ["-i", narr, "-t", f"{max_sec:.2f}",
                     "-af", f"afade=t=out:st={max_sec-0.5:.2f}:d=0.5", trimmed]):
            if os.path.exists(narr):
                os.remove(narr)
            narr, vdur = trimmed, max_sec
    has_cta = bool(cta_lines)
    budget = max(3.5, vdur - (cta_sec if has_cta else 0.0)) if vdur else sec * 5

    import random
    # 2) เติมฉากจน "ยาวพอดีเสียง" (วนสื่อ) — นับความยาวจริงหลัง xfade
    clips, durs, i, acc = [], [], 0, 0.0
    while acc < budget and i < 16:
        src = items[i % len(items)]
        # สุ่มจังหวะเวลาตัดต่อของวีดีโอรีวิวแต่ละตัว
        si = round(sec * random.uniform(0.7, 1.35), 2)
        motion_idx = random.randint(0, 100)
        c = (_video_clip(ff, src, max(1.4, si), motion_idx) if _is_video_file(src)
             else _scene_clip(ff, src, "", si, motion_idx, punch=True))
        if c:
            d = _duration(c) or si
            clips.append(c); durs.append(d)
            acc += d if len(clips) == 1 else (d - trans)
        i += 1
    if not clips:
        for t in (narr, ass):
            if t and os.path.exists(t):
                os.remove(t)
        return None

    # 3) ฉากปิด CTA — ใช้ cta_image ที่ส่งมา (เช่นรูปสินค้า) ก่อน, ไม่มีก็ภาพในรายการ, สุดท้ายดึงเฟรม footage
    if has_cta:
        cta_img = (cta_image if (cta_image and os.path.exists(cta_image)) else None) \
            or next((p for p in items if not _is_video_file(p)), None) or _frame_from(ff, items[0])
        if cta_img:
            cta = _cta_clip(ff, cta_img, cta_lines, cta_sec)
            if cta:
                clips.append(cta); durs.append(_duration(cta) or cta_sec)

    silent = os.path.join(settings.media_dir, f"_silent_{uuid.uuid4().hex[:8]}.mp4")
    if len(clips) == 1:
        shutil.move(clips[0], silent)
    else:
        ok = _concat_xfade(ff, clips, durs, silent) or _concat_hardcut(ff, clips, silent)
        for c in clips:
            if os.path.exists(c):
                os.remove(c)
        if not ok:
            for t in (narr, ass):
                if t and os.path.exists(t):
                    os.remove(t)
            return None

    # 4) ASMR: footage เงียบ → ดึงจาก Freesound (ซด/ซิซเซิล/ราด) คลอใต้เสียงพากย์
    ambient = None
    try:
        from . import stock_sfx
        if stock_sfx.available():
            ambient = stock_sfx.build_sfx_bed()
    except Exception as e:  # pragma: no cover
        print(f"[asmr] {e}")

    out = os.path.join(settings.media_dir, f"reel_{uuid.uuid4().hex[:8]}.mp4")
    final = _mux_audio(ff, silent, narr, ass, out, ambient)
    if final:
        if os.path.exists(silent):
            os.remove(silent)
        return final
    shutil.move(silent, out)
    return out


def _has_audio(ff: str, path: str) -> bool:
    """เช็คว่าไฟล์วีดีโอมี stream เสียงไหม (ใช้ ffprobe)."""
    fp = find_ffprobe()
    if not fp:
        return True   # เดาว่ามี (ปล่อยให้ลอง)
    try:
        out = subprocess.run([fp, "-v", "error", "-select_streams", "a",
                              "-show_entries", "stream=index", "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=30)
        return bool((out.stdout or "").strip())
    except Exception:
        return False


def concat_av(clips: list[str], out: str | None = None) -> str | None:
    """ต่อวิดีโอหลายคลิปเป็น 'คลิปรวม' โดย **คงเสียงเดิมของแต่ละคลิป** (ไม่ทับ TTS) —
    ใช้รวมคลิป 'คนพูดหลายภาษา' (ไทย/อังกฤษ/อีสาน) ให้เป็นคลิปยาวขึ้น ลื่นไหล.
    สเกลทุกคลิปเป็น 720x1280 9:16 + เติมเสียงเงียบให้คลิปที่ไม่มีเสียง (กัน concat พัง)."""
    ff = find_ffmpeg()
    clips = [c for c in (clips or []) if c and os.path.exists(c) and _is_video_file(c)]
    if not ff or not clips:
        return None
    out = out or os.path.join(settings.media_dir, f"montage_{uuid.uuid4().hex[:8]}.mp4")
    if len(clips) == 1:
        try:
            shutil.copy(clips[0], out); return out
        except Exception:
            return clips[0]
    n = len(clips)
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", c]
    fc = []
    for i, c in enumerate(clips):
        fc.append(f"[{i}:v]scale=720:1280:force_original_aspect_ratio=decrease,"
                  f"pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];")
        if _has_audio(ff, c):
            fc.append(f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}];")
        else:
            # คลิปไม่มีเสียง → สร้างเสียงเงียบยาวเท่าคลิป (กัน stream ไม่ครบตอน concat)
            dur = _duration(c) or float(settings.video_seconds or 6)
            fc.append(f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=0:{dur:.2f}[a{i}];")
    pairs = "".join(f"[v{i}][a{i}]" for i in range(n))
    fc.append(f"{pairs}concat=n={n}:v=1:a=1[v][a]")
    args = inputs + ["-filter_complex", "".join(fc), "-map", "[v]", "-map", "[a]",
                     "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-movflags", "+faststart", "-y", out]
    if _run(ff, args) and os.path.exists(out):
        return out
    # fallback: ตัดตรงแบบ copy (คงเสียงถ้ามี) — เผื่อ filter พัง
    silent = os.path.join(settings.media_dir, f"montage_hc_{uuid.uuid4().hex[:8]}.mp4")
    if _concat_hardcut(ff, clips, silent) and os.path.exists(silent):
        return silent
    return None


def extract_frame(video_path: str) -> str | None:
    """ดึงเฟรมแรกของวีดีโอออกมาเป็นรูปภาพเพื่อใช้ทำคลิปรวม (montage) และ thumbnail."""
    if not video_path or not os.path.exists(video_path):
        return None
    # หากอินพุตเป็นรูปภาพอยู่แล้ว ให้คืนค่ารูปภาพนั้นกลับไปตรงๆ
    if video_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return video_path

    ff = find_ffmpeg()
    if not ff:
        return None
    out = video_path.rsplit(".", 1)[0] + "_thumb.png"
    # ดึงเฟรมแรกที่วินาทีที่ 0.5
    args = ["-ss", "0.5", "-i", video_path, "-vframes", "1", "-f", "image2", out]
    if _run(ff, args) and os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    # หากล้มเหลว (เช่น คลิปสั้นกว่า 0.5 วิ) ให้ลองดึงที่วินาทีที่ 0.0
    args = ["-ss", "0.0", "-i", video_path, "-vframes", "1", "-f", "image2", out]
    if _run(ff, args) and os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    return None

