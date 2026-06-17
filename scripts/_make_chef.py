# -*- coding: utf-8 -*-
"""สร้างหน้า 'พ่อครัว/แม่ครัว' persona สำหรับพูดชวนลูกค้า (front-facing เหมาะ lip-sync)."""
import sys, os, shutil
sys.path.insert(0, "backend")
from app.engines import media_gemini
from app.config import settings

pdir = os.path.join(settings.data_dir, "persona")
os.makedirs(pdir, exist_ok=True)

base = ("photorealistic portrait of a friendly Thai {who} in a noodle restaurant, "
        "wearing apron{extra}, standing behind the counter with steaming pots and bowls of noodles behind, "
        "warm inviting smile, looking straight at camera, front-facing, neutral closed mouth, "
        "upper body visible, warm restaurant lighting, welcoming vibe, sharp focus on face")
cands = [
    ("male cook in his 40s", " and white chef hat", "ลุงพ่อครัว"),
    ("woman cook in her 40s", " and bandana", "แม่ครัว"),
    ("young male street food vendor", "", "พ่อค้าหนุ่ม"),
]
for i, (who, extra, label) in enumerate(cands, 1):
    p = media_gemini.generate_image(base.format(who=who, extra=extra))
    dst = os.path.join(pdir, f"chef_{i}.png")
    shutil.copy(p, dst)
    print(f"#{i} {label}: {os.path.getsize(dst)} bytes")
print("DONE")
