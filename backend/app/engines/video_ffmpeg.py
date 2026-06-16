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


def _run(ff: str, args: list[str]) -> bool:
    try:
        r = subprocess.run([ff, "-y", *args], capture_output=True, timeout=240)
        if r.returncode != 0:
            print(f"[ffmpeg] rc={r.returncode}: {r.stderr.decode('utf-8','ignore')[-300:]}")
        return r.returncode == 0
    except Exception as e:
        print(f"[ffmpeg] {e}")
        return False


def _scene_clip(ff: str, image_path: str, text: str, seconds: int, motion: int) -> str | None:
    """ภาพ 1 ใบ -> คลิป 1 ฉาก (ทิศทางกล้องต่างกันตาม motion)."""
    if not os.path.exists(image_path):
        return None
    frames = seconds * 30
    out = os.path.join(settings.media_dir, f"_seg_{uuid.uuid4().hex[:8]}.mp4")
    base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    if motion % 3 == 0:        # ซูมเข้ากลางภาพ
        zp = (f"zoompan=z='min(zoom+0.0013,1.28)':d={frames}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    elif motion % 3 == 1:      # เลื่อนซ้าย->ขวา
        zp = (f"zoompan=z='min(zoom+0.0008,1.18)':d={frames}:"
              f"x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    else:                      # เลื่อนบน->ล่าง
        zp = (f"zoompan=z='min(zoom+0.0008,1.18)':d={frames}:"
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


def add_audio(ff: str, video: str, narration_text: str, out: str, voice: str | None = None) -> str | None:
    """ใส่เสียงพากย์ (TTS) + เพลงคลอ ลงในวีดีโอ. ไม่มีเสียงเลย -> None."""
    from . import voice_tts
    narr = voice_tts.synth(narration_text, voice) if narration_text else None
    music = get_music(ff) if settings.enable_music else ""
    v = settings.music_volume
    tail = ["-movflags", "+faststart", "-shortest", out]
    if narr and music:
        args = ["-i", video, "-i", narr, "-stream_loop", "-1", "-i", music,
                "-filter_complex",
                f"[2:a]volume={v}[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", *tail]
    elif narr:
        args = ["-i", video, "-i", narr, "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", *tail]
    elif music:
        args = ["-stream_loop", "-1", "-i", music, "-i", video,
                "-filter_complex", f"[0:a]volume={v}[a]",
                "-map", "1:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", *tail]
    else:
        return None
    return out if (_run(ff, args) and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def build_reel(scenes: list[tuple[str, str]], seconds_each: int = 4,
               transition: float = 0.6, narration: str = "", voice: str | None = None) -> str | None:
    """หลายภาพ (image_path, text) -> คลิปเดียวต่อเนื่อง หลายฉาก + ครอสเฟด + เสียงพากย์ + เพลง."""
    ff = find_ffmpeg()
    if not ff or not scenes:
        return None
    clips = []
    for i, (img, txt) in enumerate(scenes):
        c = _scene_clip(ff, img, txt, seconds_each, i)
        if c:
            clips.append(c)
    if not clips:
        return None

    silent = os.path.join(settings.media_dir, f"_silent_{uuid.uuid4().hex[:8]}.mp4")
    if len(clips) == 1:
        shutil.move(clips[0], silent)
    else:
        # ครอสเฟดต่อกัน: offset ของรอยต่อที่ k = k*(L - T)
        L, T = seconds_each, transition
        inputs: list[str] = []
        for c in clips:
            inputs += ["-i", c]
        chains, cur = [], "0:v"
        for k in range(1, len(clips)):
            off = round(k * (L - T), 3)
            lbl = "vout" if k == len(clips) - 1 else f"v{k}"
            chains.append(f"[{cur}][{k}:v]xfade=transition=fade:duration={T}:offset={off}[{lbl}]")
            cur = lbl
        ok = _run(ff, [*inputs, "-filter_complex", ";".join(chains), "-map", "[vout]",
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent])
        if not ok:
            lst = os.path.join(settings.media_dir, f"_list_{uuid.uuid4().hex[:6]}.txt")
            with open(lst, "w", encoding="utf-8") as f:
                for c in clips:
                    f.write(f"file '{c.replace(os.sep, '/')}'\n")
            ok = _run(ff, ["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
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
