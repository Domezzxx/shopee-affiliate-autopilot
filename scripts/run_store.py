# -*- coding: utf-8 -*-
"""รัน pipeline เต็ม 1 ร้าน (generate_for_store) — สร้างคอนเทนต์ + 6 variant คลิป Flow + เสียงไทย.

รัน:  venv\\Scripts\\python.exe scripts\\run_store.py <store_id>
"""
import os, sys, time
sys.path.insert(0, "backend")
os.environ.setdefault("DATA_DIR", os.path.abspath("data"))

store_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

from app.services import pipeline
from app.db import get_session, Variant, Store
from sqlmodel import select
import app.engines.content_claude as cc

# เดโม: ถ้า Gemini เครดิตหมด → ใช้ mock content (Flow+เสียงไทยไม่ใช้ Gemini อยู่แล้ว)
_orig = cc.generate_content
def _safe_content(store):
    try:
        return _orig(store)
    except Exception as e:
        print(f"[run] Gemini ล่ม ({str(e)[:60]}) → ใช้ mock content", flush=True)
        return cc._mock(store), 0.0
cc.generate_content = _safe_content
pipeline.content_claude.generate_content = _safe_content

with get_session() as s:
    st = s.get(Store, store_id)
    print(f"[run] ร้าน #{store_id}: {st.name if st else '?'}", flush=True)

t0 = time.time()
res = pipeline.generate_for_store(store_id)
dt = round(time.time() - t0, 1)
print(f"\n[run] เสร็จใน {dt}s · result: {res}", flush=True)

# สรุป variant ที่ได้ + media_source
with get_session() as s:
    job_id = res.get("content_job_id")
    if job_id:
        vs = s.exec(select(Variant).where(Variant.content_job_id == job_id)).all()
        print(f"\n[run] === {len(vs)} variants ===", flush=True)
        for v in vs:
            fn = os.path.basename(v.media_path) if v.media_path else "(ไม่มี)"
            exists = os.path.exists(v.media_path) if v.media_path else False
            print(f"  {v.label} {v.platform:9} | source={v.media_source:6} | {v.media_type:5} | {fn} | exists={exists}", flush=True)
        flow_n = sum(1 for v in vs if (v.media_source or "") == "flow")
        print(f"\n[run] คลิป Flow: {flow_n}/{len(vs)} (จะโชว์ใน Dashboard)", flush=True)
