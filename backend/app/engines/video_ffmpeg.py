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
    return hits[0] if hits else ""


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
    vf = f"{base},{zp}"
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
                       "-vf", f"{base},{zp}", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
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
    out = os.path.join(settings.media_dir, f"video_{uuid.uuid4().hex[:8]}.mp4")
    shutil.move(seg, out)
    return out


def get_music(ff: str) -> str:
    """เพลงประกอบ: ใช้ไฟล์ที่ผู้ใช้วางใน data/music ก่อน, ไม่มี -> สร้างเพลงคลอ ambient เริ่มต้น."""
    os.makedirs(settings.music_dir, exist_ok=True)
    for ext in ("*.mp3", "*.m4a", "*.wav", "*.aac", "*.ogg"):
        files = [f for f in glob.glob(os.path.join(settings.music_dir, ext))
                 if "_default_bed" not in os.path.basename(f)]
        if files:
            return sorted(files)[0]
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


def _build_ass(segs: list[tuple[str, float, float]]) -> str:
    out = os.path.join(settings.media_dir, f"_cap_{uuid.uuid4().hex[:8]}.ass")
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
        "Style: Pop,Tahoma,88,&H00FFFFFF,&H00141414,&H96000000,1,1,6,3,2,60,60,560\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    body = ""
    for text, start, end in segs:
        t = text.replace("\n", " ").replace("{", "(").replace("}", ")")
        eff = r"{\fad(70,50)\fscx72\fscy72\t(0,140,\fscx107\fscy107)\t(140,230,\fscx100\fscy100)}"
        body += f"Dialogue: 0,{_ass_t(start)},{_ass_t(end)},Pop,,0,0,0,,{eff}{t}\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(header + body)
    return out


def build_voice_captions(ff: str, script: str, voice: str | None):
    """แยกพากย์ทีละบรรทัด → วัดเวลาจริง → คืน (ไฟล์เสียงรวม, ไฟล์ซับ ASS ที่ซิงค์)."""
    from . import voice_tts
    lines = _caption_lines(script)
    if not lines:
        return None, None
    seg_files, segs, t = [], [], 0.0
    for ln in lines:
        mp3 = voice_tts.synth(ln, voice)
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


def add_audio(ff: str, video: str, narration_text: str, out: str, voice: str | None = None) -> str | None:
    """ใส่เสียงพากย์ (ทีละบรรทัด) + ซับเด้งตามเสียง + เพลงคลอ ลงในวีดีโอ."""
    narr, ass = (None, None)
    if narration_text:
        narr, ass = build_voice_captions(ff, narration_text, voice)
    music = get_music(ff) if settings.enable_music else ""
    v = settings.music_volume
    if not narr and not music:
        return None

    fc, vlabel = [], "0:v"
    if ass:
        # อ้างชื่อไฟล์ล้วน + รัน ffmpeg ใน cwd=media (เลี่ยง C: ใน filter path)
        fc.append(f"[0:v]ass={os.path.basename(ass)}[v]")
        vlabel = "[v]"
    inputs = ["-i", video]
    if narr:
        inputs += ["-i", narr]
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
    if narr and music:
        # duration=longest + เพลง loop → -shortest ตัดที่ความยาววีดีโอ (CTA ท้ายไม่หาย) เพลงคลอตลอด
        fc.append(f"[2:a]volume={v}[m];[1:a][m]amix=inputs=2:duration=longest:dropout_transition=0[a]")
        amap = "[a]"
    elif narr:
        amap = "1:a"
    else:
        fc.append(f"[1:a]volume={v}[a]")
        amap = "[a]"

    args = [*inputs]
    if fc:
        args += ["-filter_complex", ";".join(fc)]
    args += ["-map", vlabel, "-map", amap]
    args += (["-c:v", "libx264", "-pix_fmt", "yuv420p"] if ass else ["-c:v", "copy"])
    args += ["-c:a", "aac", "-movflags", "+faststart", "-shortest", out]
    ok = _run(ff, args, cwd=settings.media_dir)
    for tmp in (ass, narr):
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    return out if (ok and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def build_reel(scenes: list[tuple[str, str]], seconds_each: float | None = None,
               transition: float = 0.3, narration: str = "", voice: str | None = None,
               cta_lines: list[str] | None = None) -> str | None:
    """หลายภาพ -> คลิปตัดเร็วมีจังหวะ (zoom punch + hard cut) + ฉากปิด CTA + ซับเด้ง + เสียง + เพลง."""
    ff = find_ffmpeg()
    if not ff or not scenes:
        return None
    sec = seconds_each or settings.reel_scene_seconds
    imgs = [img for img, _ in scenes if img and os.path.exists(img)]
    if not imgs:
        return None
    # ตัดเร็ว: วนภาพให้ได้ ~5-8 ช็อต zoom punch
    n = min(8, max(5, len(imgs) + 2))
    clips = []
    for i in range(n):
        c = _scene_clip(ff, imgs[i % len(imgs)], "", sec, i, punch=True)
        if c:
            clips.append(c)
    # ฉากปิด CTA (ใช้ภาพแรก)
    if cta_lines:
        cta = _cta_clip(ff, imgs[0], cta_lines, settings.reel_cta_seconds)
        if cta:
            clips.append(cta)
    if not clips:
        return None

    silent = os.path.join(settings.media_dir, f"_silent_{uuid.uuid4().hex[:8]}.mp4")
    if len(clips) == 1:
        shutil.move(clips[0], silent)
    else:
        # ตัดตรง (hard cut) = จังหวะเร็ว
        lst = os.path.join(settings.media_dir, f"_list_{uuid.uuid4().hex[:6]}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for c in clips:
                f.write(f"file '{c.replace(os.sep, '/')}'\n")
        ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
        if not (ok and os.path.exists(silent) and os.path.getsize(silent) > 1000):
            ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst,
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", silent])  # fallback re-encode
        if os.path.exists(lst):
            os.remove(lst)
        for c in clips:
            if os.path.exists(c):
                os.remove(c)
        if not (ok and os.path.exists(silent) and os.path.getsize(silent) > 1000):
            return None

    # ใส่เสียงพากย์ + เพลง
    out = os.path.join(settings.media_dir, f"reel_{uuid.uuid4().hex[:8]}.mp4")
    final = add_audio(ff, silent, narration, out, voice)
    if final:
        if os.path.exists(silent):
            os.remove(silent)
        return final
    shutil.move(silent, out)   # ไม่มีเสียง -> ใช้คลิปเงียบ
    return out
