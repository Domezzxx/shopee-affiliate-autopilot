"""วงจรหลัก: ร้าน → Claude เขียน → Gemini ทำสื่อ → คิวโพสต์ A/B → ยิง → วาง affiliate link คอมเมนต์แรก → เก็บผล → auto-optimize."""
from __future__ import annotations

import json
import random
import time
from datetime import datetime

from sqlmodel import select

from ..config import settings
from ..db import ContentJob, Metric, Post, Store, Variant, get_session, jloads
from ..engines import content_claude, media_gemini
from ..connectors import social


# ----------------------------------------------------------- progress tracking (สำหรับ progress bar บน dashboard)
_PROGRESS: dict = {}


def _prog(key, name: str, step: str, pct: float,
          status: str = "running", detail: str = "") -> None:
    """อัปเดตความคืบหน้า. key = id งาน (store_id สำหรับรันคลิป / 'reel-{id}-{label}' สำหรับรวมคลิป)."""
    _PROGRESS[key] = {
        "key": str(key), "name": name, "step": step,
        "pct": max(0, min(100, int(pct))), "status": status, "detail": detail,
        "ts": time.time(),
    }


def progress_list() -> list[dict]:
    """รายการความคืบหน้าที่กำลังทำ — ตัด done/error ที่ค้างเกิน 12 วิ ออก (ให้หน้าเว็บเห็น 'เสร็จ' แวบนึง)."""
    now = time.time()
    out = []
    for k, v in list(_PROGRESS.items()):
        if v["status"] in ("done", "error") and now - v["ts"] > 12:
            _PROGRESS.pop(k, None)
            continue
        out.append(v)
    return sorted(out, key=lambda x: x["ts"])


def generate_for_store(store_id: int) -> dict:
    """ขั้น 2+3: Claude เขียน + Gemini ทำสื่อ → สร้าง ContentJob + 6 Variant พร้อมสื่อ + คอมเมนต์แรก."""
    with get_session() as s:
        store = s.get(Store, store_id)
        if not store:
            return {"error": "store not found"}
        name = store.name
        _prog(store_id, name, "✍️ AI กำลังเขียนคอนเทนต์", 8)
        store_dict = {
            "name": store.name, "area": store.area, "rating": store.rating,
            "review_count": store.review_count, "price_range": store.price_range,
            "menu": jloads(store.menu_json, []), "affiliate_link": store.affiliate_link,
        }
        data, cost = content_claude.generate_content(store_dict)

        _prog(store_id, name, "🎨 เริ่มสร้างภาพ/วีดีโอ", 18)
        job = ContentJob(
            store_id=store.id, status="media_ready",
            analysis_json=json.dumps(data["store_analysis"], ensure_ascii=False),
            schedule_json=json.dumps(data["posting_schedule"], ensure_ascii=False),
            model_used=(settings.gemini_text_model if settings.content_provider == "gemini" and settings.has_gemini
                        else settings.content_model if settings.content_provider == "claude" and settings.has_claude
                        else "mock"),
            cost_baht=cost,
        )
        s.add(job); s.commit(); s.refresh(job)

        # โหลดรูป product จริงจาก Shopee 1 รูป → ใช้ทำ image-to-video (วีดีโอตรงเมนูจริง)
        product_img = ""
        try:
            imgs = media_gemini.download_images(jloads(store.image_urls_json, []), 1)
            product_img = imgs[0] if imgs else ""
            if product_img:
                _prog(store_id, name, "🖼️ ได้รูป product จริง → image-to-video", 16)
        except Exception as e:
            print(f"[product-img] {e}")

        variants = data["variants"]
        total = len(variants) or 1
        for i, v in enumerate(variants):
            _prog(store_id, name, f"🎬 สร้างสื่อ {i + 1}/{total}", 18 + int(i / total * 64),
                  detail=f"{v['platform']} · {v['label']}")
            mtype, mpath, ipath = media_gemini.make_media(v["image_prompt"], v["video_prompt"], v["hook"], v["voiceover_script"], v["label"], product_image=product_img)
            s.add(Variant(
                content_job_id=job.id, store_id=store.id, label=v["label"],
                platform=v["platform"], hook=v["hook"],
                video_title=v.get("video_title", ""), caption=v["caption"],
                hashtags_json=json.dumps(v["hashtags"], ensure_ascii=False),
                cta=v["cta"], first_comment=v.get("first_comment", ""),
                voiceover_script=v["voiceover_script"],
                image_prompt=v["image_prompt"], video_prompt=v["video_prompt"],
                media_type=mtype, media_path=mpath, image_path=ipath,
            ))
        store.status = "active"
        s.add(store); s.commit()
        _prog(store_id, name, "💾 บันทึกสื่อเสร็จ", 88)
        return {"content_job_id": job.id, "variants": 6, "cost_baht": cost}


def _affiliate_link(store: Store) -> str:
    return store.affiliate_link or store.shopee_url or "(ยังไม่ได้ใส่ลิงก์ affiliate)"


def _affiliate_link_for(store: Store, sub_id: str = "") -> str:
    """ลิงก์ affiliate สำหรับโพสต์ — ลองสร้างผ่าน Shopee Affiliate API (track ด้วย sub_id) ก่อน,
    ทำไม่ได้ค่อยใช้ลิงก์ที่ใส่เองต่อร้าน."""
    try:
        from ..engines import shopee_affiliate
        origin = store.shopee_url or store.affiliate_link
        if shopee_affiliate.available() and origin and "shopee" in origin.lower():
            link = shopee_affiliate.generate_link(origin, [sub_id] if sub_id else [])
            if link:
                return link
    except Exception as e:  # pragma: no cover
        print(f"[affiliate] {e}")
    return _affiliate_link(store)


def _is_video_file(p: str) -> bool:
    return bool(p) and p.lower().endswith((".mp4", ".mov", ".m4v", ".webm"))


def publish_job(content_job_id: int) -> dict:
    """ขั้น 4: ยิงทุก variant ออก platform (Hybrid) → วาง affiliate link คอมเมนต์แรก. อัปเดต progress ต่อ platform."""
    import os
    posted = []
    with get_session() as s:
        variants = s.exec(select(Variant).where(Variant.content_job_id == content_job_id)).all()
        if not variants:
            return {"posted": []}
        sid = variants[0].store_id
        store0 = s.get(Store, sid)
        name = store0.name if store0 else str(sid)
        # YouTube ต้องไฟล์วีดีโอ — ถ้า variant เป็นภาพ ใช้ reel (คลิปรวม) ของร้านแทน
        reel_local = ""
        if store0 and store0.reel_url:
            cand = os.path.join(settings.media_dir, os.path.basename(store0.reel_url))
            if os.path.exists(cand):
                reel_local = cand
        n = len(variants)
        posted_media: set = set()   # กันอัปสื่อ "ตัวเดียวกัน" ซ้ำใน platform เดียว (YouTube ลบคลิปซ้ำ)
        for idx, v in enumerate(variants):
            _prog(sid, name, f"📤 โพสต์ {v.platform} {v.label}", 90 + int(idx / n * 9), detail=f"{idx + 1}/{n}")
            store = s.get(Store, v.store_id)
            media = v.media_path
            if v.platform == "youtube" and reel_local and not _is_video_file(media):
                media = reel_local        # YouTube ต้องวีดีโอ → ใช้ reel แทนภาพ
            # ข้ามถ้าสื่อ+platform ซ้ำกับที่โพสต์ไปแล้วในรอบนี้ (กัน duplicate → โดน platform ลบ)
            mkey = (v.platform, os.path.basename(media) if media else "")
            if mkey in posted_media:
                _prog(sid, name, f"⏭️ ข้าม {v.platform} {v.label} (สื่อซ้ำ)", 90 + int((idx + 1) / n * 9))
                posted.append({"platform": v.platform, "label": v.label, "ok": False,
                               "method": "skip", "account": "", "external_id": "",
                               "error": "ข้ามสื่อซ้ำ (กัน duplicate)", "comment": ""})
                continue
            posted_media.add(mkey)
            # โพสต์จริง: สุ่มหน่วงเวลาระหว่างโพสต์ กัน spam detection
            if idx and settings.enable_post_delay:
                time.sleep(random.uniform(settings.post_delay_min, settings.post_delay_max) * 60)
            res = social.publish(v.platform, v.caption, media, title=v.video_title)
            _prog(sid, name, f"{'✅' if res['ok'] else '⚠️'} {v.platform} {v.label}",
                  90 + int((idx + 1) / n * 9), detail=("สำเร็จ" if res["ok"] else "ไม่สำเร็จ"))
            p = Post(
                variant_id=v.id, store_id=v.store_id, platform=v.platform,
                method=res["method"], account=res["account"],
                external_id=res["external_id"],
                status="posted" if res["ok"] else "failed",
                error=res["error"], posted_at=datetime.utcnow() if res["ok"] else None,
            )
            # โพสต์สำเร็จ → วาง affiliate link เป็นคอมเมนต์แรก (แทน {LINK} ด้วยลิงก์จริง)
            if res["ok"]:
                # sub_id track ต่อโพสต์ = ร้าน_แพลตฟอร์ม_variant → รู้ว่าคอมมิชชั่นมาจากคลิปไหน
                sub_id = f"s{v.store_id}_{v.platform}_{v.label}"
                link = _affiliate_link_for(store, sub_id)
                text = (v.first_comment or "สั่งเลย 👉 {LINK}").replace("{LINK}", link)
                c = social.publish_comment(v.platform, res["method"], res["external_id"], text)
                p.comment_id = c["comment_id"]
                p.comment_status = "posted" if c["ok"] else "failed"
            s.add(p)
            posted.append({"platform": v.platform, "label": v.label,
                           "comment": p.comment_status, **res})
        job = s.get(ContentJob, content_job_id)
        if job:
            job.status = "posted"; s.add(job)
        s.commit()
    return {"posted": posted}


def _store_name(store_id: int) -> str:
    with get_session() as s:
        st = s.get(Store, store_id)
        return st.name if st else str(store_id)


def run_full(store_id: int) -> dict:
    """ครบวง 1 ร้าน: generate → publish. อัปเดต progress ตลอด (gen→post→done/error)."""
    try:
        g = generate_for_store(store_id)
        if "error" in g:
            _prog(store_id, _store_name(store_id), "❌ " + g["error"], 100, status="error")
            return g
        name = _store_name(store_id)
        
        # ตรวจสอบว่าร้านค้าต้องการอนุมัติก่อนโพสต์หรือไม่
        with get_session() as s:
            store = s.get(Store, store_id)
            requires_approval = store.requires_approval if store else False
            
        if requires_approval:
            # เปลี่ยนสถานะงาน ContentJob เป็น pending_approval
            with get_session() as s:
                job = s.get(ContentJob, g["content_job_id"])
                if job:
                    job.status = "pending_approval"
                    s.add(job)
                    s.commit()
            _prog(store_id, name, "⏳ รออนุมัติก่อนโพสต์", 100, status="done")
            return {**g, "status": "pending_approval", "detail": "Waiting for human approval"}
            
        _prog(store_id, name, "📤 กำลังโพสต์/วางลิงก์", 90)
        p = publish_job(g["content_job_id"])
        # สรุปผลโพสต์ต่อ platform (YT/FB/IG ✓/✗)
        abbr = {"youtube": "YT", "facebook": "FB", "instagram": "IG", "shopee_video": "Shopee"}
        by: dict = {}
        for x in p.get("posted", []):
            a = abbr.get(x.get("platform"), x.get("platform", "?"))
            d = by.setdefault(a, [0, 0])
            d[0 if x.get("ok") else 1] += 1
        summary = " · ".join(f"{a} {ok}✓" + (f" {bad}✗" if bad else "") for a, (ok, bad) in by.items())
        _prog(store_id, name, "✅ เสร็จ! " + summary, 100, status="done", detail="โพสต์แล้ว")
        return {**g, **p}
    except Exception as e:  # pragma: no cover
        _prog(store_id, _store_name(store_id), f"❌ ผิดพลาด: {str(e)[:80]}", 100, status="error")
        raise


def build_montage(store_id: int, label: str = "A", voice_name: str | None = None) -> dict:
    """รวมคลิป (montage) ของร้าน label A/B + อัปเดต progress bar ตลอด."""
    import os
    from ..engines import video_ffmpeg
    key = f"reel-{store_id}-{label}"
    name = _store_name(store_id)
    det = f"คลิป {label}"
    try:
        with get_session() as s:
            store = s.get(Store, store_id)
            if not store:
                return {"error": "store not found"}
            name = store.name
            vs = s.exec(select(Variant).where(Variant.store_id == store_id, Variant.label == label)).all()
            scenes, narration, seen = [], [], set()
            for v in vs:
                img = v.image_path or (v.media_path if v.media_type == "image" else "")
                if (not img or not os.path.exists(img)) and v.media_type == "video" and v.media_path and os.path.exists(v.media_path):
                    thumb = video_ffmpeg.extract_frame(v.media_path)
                    if thumb:
                        v.image_path = thumb
                        s.add(v)
                        img = thumb
                if img and os.path.exists(img) and img not in seen:
                    seen.add(img); scenes.append((img, v.hook)); narration.append(v.voiceover_script or v.hook)
            s.commit()
            cta = [name[:24], "สั่งเลยตอนนี้!", "ลิงก์ในคอมเมนต์แรก"]
        if not scenes:
            _prog(key, name, "❌ ไม่มีภาพต้นฉบับ — รันร้านนี้ใหม่ก่อน", 100, status="error", detail=det)
            return {"error": "no source images"}

        _prog(key, name, "🎬 เริ่มรวมคลิป", 8, detail=det)
        reel = video_ffmpeg.build_reel(
            scenes, narration=" ".join(narration), voice=voice_name, cta_lines=cta,
            progress_cb=lambda step, pct: _prog(key, name, step, pct, detail=det))
        if not reel:
            _prog(key, name, "❌ สร้างคลิปไม่สำเร็จ", 100, status="error", detail=det)
            return {"error": "build failed"}

        with get_session() as s:
            store = s.get(Store, store_id)
            store.reel_url = "/media/" + os.path.basename(reel)
            s.add(store); s.commit()
            url = store.reel_url
        _prog(key, name, "✅ รวมคลิปเสร็จ!", 100, status="done", detail=det)
        return {"reel_url": url, "scenes": len(scenes)}
    except Exception as e:  # pragma: no cover
        _prog(key, name, f"❌ ผิดพลาด: {str(e)[:80]}", 100, status="error", detail=det)
        raise


def build_restaurant(store_id: int, voice_name: str | None = None) -> dict:
    """รีวิวในร้าน: พ่อครัวพูดชวน + แอคชั่น (Flow video ถ้ามี ไม่งั้น stock) + พ่อครัว PiP + ASMR."""
    import os
    from ..engines import talking_head, stock_video
    key = f"rest-{store_id}"
    name = _store_name(store_id)
    try:
        with get_session() as s:
            store = s.get(Store, store_id)
            if not store:
                return {"error": "store not found"}
            name = store.name
            menu = jloads(store.menu_json, [])
            vs = s.exec(select(Variant).where(Variant.store_id == store_id)).all()
            scripts = [v.voiceover_script for v in vs if v.voiceover_script]
            narration = scripts[0] if scripts else (
                f"สวัสดีครับ ร้าน {name[:20]} อร่อยเด็ด เส้นนุ่ม น้ำซุปสูตรเด็ด "
                "มาชิมกันเยอะๆ นะครับ รับรองไม่ผิดหวัง สั่งเลย ลิงก์อยู่ในคอมเมนต์ครับ")
            flow_vids = [v.media_path for v in vs
                         if v.media_path and os.path.basename(v.media_path).startswith("video_flow_")
                         and os.path.exists(v.media_path)]
            imgs = [v.image_path for v in vs if v.image_path and os.path.exists(v.image_path)]

        _prog(key, name, "🍜 เตรียมสื่อ + footage", 6)
        media = list(dict.fromkeys(flow_vids))            # Flow video จริงก่อน (เมนูเป๊ะ)
        if len(media) < 3:                                # ไม่พอ → เติม stock ก๋วยเตี๋ยว
            try:
                media += stock_video.search_food_clips(stock_video.build_queries(name, menu), n=6)
            except Exception as e:  # pragma: no cover
                print(f"[restaurant] stock: {e}")
        media += imgs[:2]
        media = [m for m in dict.fromkeys(media) if m and os.path.exists(m)]
        if not media:
            _prog(key, name, "❌ ไม่มีสื่อ — รันร้านนี้ก่อน", 100, status="error")
            return {"error": "no media"}

        reel = talking_head.build_restaurant_reel(
            media, narration, voice=voice_name,
            progress_cb=lambda step, pct: _prog(key, name, step, pct))
        if not reel:
            _prog(key, name, "❌ สร้างรีวิวไม่สำเร็จ (ต้องมี persona พ่อครัว + เสียง)", 100, status="error")
            return {"error": "build failed"}

        with get_session() as s:
            store = s.get(Store, store_id)
            store.reel_url = "/media/" + os.path.basename(reel)
            s.add(store); s.commit()
            url = store.reel_url
        _prog(key, name, "✅ รีวิวในร้านเสร็จ!", 100, status="done")
        return {"reel_url": url}
    except Exception as e:  # pragma: no cover
        _prog(key, name, f"❌ {str(e)[:80]}", 100, status="error")
        raise


# ----------------------------------------------------------- A/B + auto-optimize
def abtest_result(store_id: int) -> dict:
    """รวม metric ต่อ variant แล้วเทียบ A vs B (per platform) — ประกาศผู้ชนะเมื่อ impression ครบ."""
    with get_session() as s:
        variants = s.exec(select(Variant).where(Variant.store_id == store_id)).all()
        out = {}
        for v in variants:
            metrics = s.exec(select(Metric).where(Metric.variant_id == v.id)).all()
            imp = sum(m.impressions for m in metrics)
            clk = sum(m.clicks for m in metrics)
            out.setdefault(v.platform, {})[v.label] = {
                "variant_id": v.id, "impressions": imp, "clicks": clk,
                "ctr": round(clk / imp, 4) if imp else 0.0,
                "hook": v.hook,
            }
        verdict = {}
        for platform, ab in out.items():
            a, b = ab.get("A"), ab.get("B")
            if not (a and b):
                continue
            ready = (a["impressions"] + b["impressions"]) >= settings.abtest_min_impressions
            winner = "A" if a["ctr"] >= b["ctr"] else "B"
            verdict[platform] = {
                "winner": winner if ready else None,
                "ready": ready,
                "lift": round(abs(a["ctr"] - b["ctr"]), 4),
            }
        return {"store_id": store_id, "by_platform": out, "verdict": verdict}


def auto_optimize() -> dict:
    """ขั้น 5: ร้าน CTR ต่ำ 3 วันติด → pause (ประหยัด cost). คืนสรุปการกระทำ."""
    actions = []
    with get_session() as s:
        for store in s.exec(select(Store).where(Store.status == "active")).all():
            metrics = s.exec(select(Metric).where(Metric.store_id == store.id)).all()
            imp = sum(m.impressions for m in metrics)
            clk = sum(m.clicks for m in metrics)
            ctr = (clk / imp) if imp else 0.0
            if imp >= settings.abtest_min_impressions and ctr < settings.abtest_pause_ctr:
                store.low_ctr_days += 1
                if store.low_ctr_days >= 3:
                    store.status = "paused"
                    actions.append({"store": store.name, "action": "paused", "ctr": round(ctr, 4)})
            else:
                store.low_ctr_days = 0
            s.add(store)
        s.commit()
    return {"ran_at": datetime.utcnow().isoformat(), "actions": actions}
