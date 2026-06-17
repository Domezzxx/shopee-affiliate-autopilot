# -*- coding: utf-8 -*-
"""AI persona พูดได้ (Wav2Lip lip-sync) + ซ้อนมุมจอ (PiP) บนคลิปอาหาร.

flow: เสียงพากย์ -> Wav2Lip ทำให้ persona ขยับปากตามเสียง -> overlay มุมจอบน reel อาหาร.
persona = หน้าคงที่ data/persona/influencer.png (สร้างจาก Gemini ครั้งเดียว).
รันบน CPU (torch) — static image เรนเดอร์เร็ว.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid

from ..config import settings
from . import video_ffmpeg as vf

# tools/Wav2Lip อยู่ที่ราก repo (ขึ้นจาก backend/app/engines 4 ชั้น)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WAV2LIP_DIR = os.path.join(_ROOT, "tools", "Wav2Lip")
CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")


def persona_path() -> str:
    return os.path.join(settings.data_dir, "persona", "influencer.png")


def available() -> bool:
    """พร้อมใช้ไหม — มีโมเดล + หน้า persona + โค้ด inference."""
    return all(os.path.exists(p) for p in
               (CHECKPOINT, persona_path(), os.path.join(WAV2LIP_DIR, "inference.py")))


def _env_with_ffmpeg() -> dict:
    """Wav2Lip inference.py เรียก ffmpeg จาก PATH — เติม dir ของ ffmpeg ให้."""
    env = os.environ.copy()
    ff = vf.find_ffmpeg()
    if ff:
        env["PATH"] = os.path.dirname(ff) + os.pathsep + env.get("PATH", "")
    return env


def synthesize(audio_path: str, face: str | None = None, out: str | None = None) -> str | None:
    """เสียง -> วีดีโอ persona พูด (ปากซิงค์เสียง). คืน path mp4 หรือ None."""
    face = face or persona_path()
    if not (os.path.exists(face) and os.path.exists(audio_path) and os.path.exists(CHECKPOINT)):
        return None
    out = out or os.path.join(settings.media_dir, f"talk_{uuid.uuid4().hex[:8]}.mp4")
    cmd = [sys.executable, "inference.py",
           "--checkpoint_path", CHECKPOINT, "--face", face, "--audio", audio_path,
           "--outfile", out, "--static", "True", "--pads", "0", "20", "0", "0", "--nosmooth"]
    try:
        r = subprocess.run(cmd, cwd=WAV2LIP_DIR, env=_env_with_ffmpeg(),
                           capture_output=True, timeout=900)
        if r.returncode != 0:
            print(f"[wav2lip] rc={r.returncode}: {r.stderr.decode('utf-8','ignore')[-300:]}")
            return None
    except Exception as e:  # pragma: no cover
        print(f"[wav2lip] {e}")
        return None
    return out if (os.path.exists(out) and os.path.getsize(out) > 1000) else None


_CORNER = {
    "tr": "W-w-{m}:{m2}",          # บนขวา (เลี่ยงซับล่าง)
    "tl": "{m}:{m2}",
    "br": "W-w-{m}:H-h-{m2}",
    "bl": "{m}:H-h-{m2}",
}


def _mux_args(out: str, keep_audio: bool = True):
    a = ["-map", "[v]"]
    if keep_audio:
        a += ["-map", "0:a", "-c:a", "aac"]
    else:
        a += ["-an"]
    a += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if keep_audio:
        a += ["-shortest"]
    return a + [out]


def _circle_fc(width: int, pos_p: str, pos_r: str) -> str:
    """filter_complex: persona วงกลม + วงแหวนขาว (TikTok style)."""
    r = width // 2
    ring = width + 12
    rr = ring // 2
    keep = "lum='lum(X\\,Y)':cb='cb(X\\,Y)':cr='cr(X\\,Y)'"
    circ_a = f"a='if(gt(hypot(X-{r}\\,Y-{r})\\,{r})\\,0\\,255)'"
    return (
        f"[2:v]format=yuva420p,geq=lum=235:cb=128:cr=128:"
        f"a='if(gt(hypot(X-{rr}\\,Y-{rr})\\,{rr})\\,0\\,255)'[ring];"
        f"[1:v]scale={width}:{width}:force_original_aspect_ratio=increase,crop={width}:{width},"
        f"format=yuva420p,geq={keep}:{circ_a}[p];"
        f"[0:v][ring]overlay={pos_r}:eof_action=pass[t];"
        f"[t][p]overlay={pos_p}:eof_action=pass[v]"
    )


def overlay_pip(food_reel: str, persona_video: str, out: str | None = None,
                width: int = 380, corner: str = "tr", shape: str = "circle",
                keep_audio: bool = True) -> str | None:
    """ซ้อน persona มุมจอบนคลิป (วงกลม TikTok หรือสี่เหลี่ยม). keep_audio=False ใช้กับคลิปเงียบ."""
    ff = vf.find_ffmpeg()
    if not ff or not (os.path.exists(food_reel) and os.path.exists(persona_video)):
        return None
    out = out or os.path.join(settings.media_dir, f"persona_{uuid.uuid4().hex[:8]}.mp4")
    pos = _CORNER.get(corner, _CORNER["tr"]).format(m=40, m2=150)

    if shape == "circle":
        # วงแหวน (ใหญ่กว่า persona 6px รอบด้าน) วางเยื้อง -6 ให้ล้อมพอดี
        pos_r = _CORNER.get(corner, _CORNER["tr"]).format(m=34, m2=144)
        fc = _circle_fc(width, pos, pos_r)
        args = ["-i", food_reel, "-i", persona_video,
                "-f", "lavfi", "-i", f"color=c=white:s={width+12}x{width+12}",
                "-filter_complex", fc, *_mux_args(out, keep_audio)]
        if vf._run(ff, args) and os.path.exists(out) and os.path.getsize(out) > 1000:
            return out
        print("[pip] circle ล้มเหลว → fallback สี่เหลี่ยม")

    # สี่เหลี่ยมกรอบขาว (fallback / shape=rect)
    fc = (f"[1:v]scale={width}:-2,setsar=1,pad=iw+12:ih+12:6:6:white@0.92[p];"
          f"[0:v][p]overlay={pos}:eof_action=pass[v]")
    args = ["-i", food_reel, "-i", persona_video, "-filter_complex", fc, *_mux_args(out, keep_audio)]
    ok = vf._run(ff, args)
    return out if (ok and os.path.exists(out) and os.path.getsize(out) > 1000) else None


def _extract_audio(video: str) -> str | None:
    """ดึงเสียงจากคลิป -> wav 16kHz mono (อาหาร Wav2Lip)."""
    ff = vf.find_ffmpeg()
    if not ff or not os.path.exists(video):
        return None
    wav = os.path.join(settings.media_dir, f"_pa_{uuid.uuid4().hex[:8]}.wav")
    ok = vf._run(ff, ["-i", video, "-ar", "16000", "-ac", "1", wav])
    return wav if (ok and os.path.exists(wav)) else None


def add_persona_pip(food_reel: str, face: str | None = None,
                    width: int = 380, corner: str = "tr") -> str | None:
    """รับคลิปอาหารที่มีเสียงพากย์แล้ว -> ใส่ persona พูดมุมจอ (ลิปซิงค์เสียงเดียวกัน)."""
    if not (food_reel and os.path.exists(food_reel)):
        return None
    audio = _extract_audio(food_reel)          # เสียงเดียวกับในคลิป => ลิปซิงค์ตรง
    if not audio:
        return None
    talk = synthesize(audio, face=face)
    if os.path.exists(audio):
        os.remove(audio)
    if not talk:
        return None
    final = overlay_pip(food_reel, talk, width=width, corner=corner)
    if os.path.exists(talk):
        os.remove(talk)
    return final
