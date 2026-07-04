"""โพสต์ซ้ำคลิปเดิม (ระหว่างรอ media credit กลับมา: Flow/Gemini รูป หมด).

เลือกคลิปวิดีโอเก่าที่ 'รีโพสต์นานสุด' → โพสต์ FB/IG หมุนเวียน + วางลิงก์ affiliate (คอมเมนต์ตะกร้า)
+ หน่วงเวลาระหว่างโพสต์ (กันแพลตฟอร์มแบนสแปม). ข้าม YouTube (quota + เข้มเรื่องคลิปซ้ำ).
จำว่าคลิปไหนรีโพสต์ไป platform ไหนล่าสุด (repost_state.json) → หมุนเวียนไม่ซ้ำเร็ว.
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime

from sqlmodel import select

from ..config import settings
from ..db import Post, Store, Variant, get_session
from ..connectors import social


def _state_path() -> str:
    return os.path.join(settings.data_dir, "repost_state.json")


def _load() -> dict:
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(st: dict) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception as e:  # pragma: no cover
        print(f"[repost] save state fail: {e}")


def promo_round(n: int | None = None, platforms=("facebook", "instagram")) -> dict:
    """สร้าง 'ภาพโปรโมทนิ่ง' (ฟรี ไม่ใช้ Flow credit) แล้วโพสต์ FB/IG + คอมเมนต์ตะกร้า + หน่วงกันสแปม.
    เลือกร้านที่โปรโมทนานสุดก่อน · ภาพดึงจากเฟรมคลิปที่มีอยู่."""
    from . import pipeline
    from ..engines import promo_image
    n = n or settings.repost_per_round
    state = _load()
    done = []
    with get_session() as s:
        stores = (s.exec(select(Store).where(Store.category == "food")).all()
                  or s.exec(select(Store)).all())
        stores.sort(key=lambda st: min(state.get(f"promo:{st.id}:{p}", 0) for p in platforms))
        picked = 0
        for st in stores:
            if picked >= n:
                break
            v = s.exec(select(Variant).where(Variant.store_id == st.id)).first()
            if not v:
                continue
            style = ["premium_set", "viral_banner", "viral_editorial", "viral_neon", "viral_collage"][picked % 5]
            photo = promo_image.get_promo_photo(st.id, style=style)   # style → รูปตั้งต้นแสง/โทนตรงกับ layout
            if not photo:
                continue
            img = promo_image.make_promo(st, photo, v.hook, style=style)
            if not img:
                continue
            plat = platforms[picked % len(platforms)]
            cap = promo_image.make_caption(st, v.hook, v.caption)   # แคปชั่นป้ายยาร้านอาหาร
            res = social.publish(plat, cap, img)         # โพสต์ภาพนิ่ง
            p = Post(variant_id=v.id, store_id=st.id, platform=plat,
                     method=res["method"], account=res["account"], external_id=res["external_id"],
                     status="posted" if res["ok"] else "failed", error=res["error"],
                     posted_at=datetime.utcnow() if res["ok"] else None)
            if res["ok"]:
                sub_id = f"s{st.id}_{plat}_{v.label}_promo"
                link = pipeline._affiliate_link_for(st, sub_id)
                text = pipeline._cart_comment(v.first_comment, link)
                c = social.publish_comment(plat, res["method"], res["external_id"], text)
                p.comment_id = c["comment_id"]
                p.comment_status = "posted" if c["ok"] else "failed"
                state[f"promo:{st.id}:{plat}"] = time.time()
            s.add(p); s.commit()
            done.append({"store": st.name[:24], "platform": plat, "ok": res["ok"]})
            print(f"[promo] {plat} {st.name[:20]} -> ok={res['ok']}")
            picked += 1
            if picked < n:
                time.sleep(random.uniform(settings.repost_gap_min, settings.repost_gap_max) * 60)
    _save(state)
    return {"promo_posted": sum(1 for d in done if d["ok"]), "detail": done}


def repost_round(n: int | None = None, platforms=("facebook", "instagram")) -> dict:
    """รีโพสต์ n คลิปเดิม (เก่าสุดก่อน) ไป platform หมุนเวียน + คอมเมนต์ลิงก์ + หน่วงกันสแปม."""
    from . import pipeline   # ใช้ _cart_comment + _affiliate_link_for (import ในฟังก์ชันกัน circular)
    n = n or settings.repost_per_round
    state = _load()
    done = []
    with get_session() as s:
        # คลิปวิดีโอที่ไฟล์ยังอยู่จริง
        cands = [v for v in s.exec(select(Variant).where(Variant.media_type == "video")).all()
                 if v.media_path and os.path.exists(v.media_path)]
        if not cands:
            return {"reposted": 0, "error": "ไม่มีคลิปเดิมให้รีโพสต์"}
        # เรียงตาม 'รีโพสต์นานสุด' (min last_ts ข้าม platform) — เก่าสุดได้คิวก่อน
        cands.sort(key=lambda v: min(state.get(f"{v.id}:{p}", 0) for p in platforms))
        picked = 0
        for i, v in enumerate(cands):
            if picked >= n:
                break
            plat = platforms[picked % len(platforms)]   # หมุนเวียน FB/IG
            store = s.get(Store, v.store_id)
            if not store:
                continue
            res = social.publish(plat, v.caption, v.media_path, title=v.video_title)
            p = Post(variant_id=v.id, store_id=v.store_id, platform=plat,
                     method=res["method"], account=res["account"], external_id=res["external_id"],
                     status="posted" if res["ok"] else "failed", error=res["error"],
                     posted_at=datetime.utcnow() if res["ok"] else None)
            if res["ok"]:
                sub_id = f"s{v.store_id}_{plat}_{v.label}_re"
                link = pipeline._affiliate_link_for(store, sub_id)
                text = pipeline._cart_comment(v.first_comment, link)
                c = social.publish_comment(plat, res["method"], res["external_id"], text)
                p.comment_id = c["comment_id"]
                p.comment_status = "posted" if c["ok"] else "failed"
                state[f"{v.id}:{plat}"] = time.time()
            s.add(p)
            s.commit()
            done.append({"variant": v.id, "store": store.name[:24], "platform": plat, "ok": res["ok"]})
            print(f"[repost] {plat} variant {v.id} ({store.name[:20]}) -> ok={res['ok']}")
            picked += 1
            # หน่วงระหว่างโพสต์ กันโดนแบนสแปม (ยกเว้นตัวสุดท้าย)
            if picked < n:
                time.sleep(random.uniform(settings.repost_gap_min, settings.repost_gap_max) * 60)
    _save(state)
    return {"reposted": sum(1 for d in done if d["ok"]), "rounds_n": n, "detail": done}
