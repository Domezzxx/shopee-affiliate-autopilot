"""วงจรหลัก: ร้าน → Claude เขียน → Gemini ทำสื่อ → คิวโพสต์ A/B → ยิง → เก็บผล → auto-optimize."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlmodel import select

from ..config import settings
from ..db import ContentJob, Metric, Post, Store, Variant, get_session, jloads
from ..engines import content_claude, media_gemini
from ..connectors import social


def generate_for_store(store_id: int) -> dict:
    """ขั้น 2+3: Claude เขียน + Gemini ทำสื่อ → สร้าง ContentJob + 6 Variant พร้อมสื่อ."""
    with get_session() as s:
        store = s.get(Store, store_id)
        if not store:
            return {"error": "store not found"}
        store_dict = {
            "name": store.name, "area": store.area, "rating": store.rating,
            "review_count": store.review_count, "price_range": store.price_range,
            "menu": jloads(store.menu_json, []), "affiliate_link": store.affiliate_link,
        }
        data, cost = content_claude.generate_content(store_dict)

        job = ContentJob(
            store_id=store.id, status="media_ready",
            analysis_json=json.dumps(data["store_analysis"], ensure_ascii=False),
            schedule_json=json.dumps(data["posting_schedule"], ensure_ascii=False),
            model_used=settings.content_model if settings.has_claude else "mock",
            cost_baht=cost,
        )
        s.add(job); s.commit(); s.refresh(job)

        for v in data["variants"]:
            mtype, mpath = media_gemini.make_media(v["image_prompt"], v["video_prompt"])
            s.add(Variant(
                content_job_id=job.id, store_id=store.id, label=v["label"],
                platform=v["platform"], hook=v["hook"], caption=v["caption"],
                hashtags_json=json.dumps(v["hashtags"], ensure_ascii=False),
                cta=v["cta"], voiceover_script=v["voiceover_script"],
                image_prompt=v["image_prompt"], video_prompt=v["video_prompt"],
                media_type=mtype, media_path=mpath,
            ))
        store.status = "active"
        s.add(store); s.commit()
        return {"content_job_id": job.id, "variants": 6, "cost_baht": cost}


def publish_job(content_job_id: int) -> dict:
    """ขั้น 4: ยิงทุก variant ของ job ออก platform (Hybrid) + คิว affiliate link คอมเมนต์แรก."""
    posted = []
    with get_session() as s:
        variants = s.exec(select(Variant).where(Variant.content_job_id == content_job_id)).all()
        for v in variants:
            caption = v.caption + "\n\n👇 ลิงก์สั่งในคอมเมนต์แรก"
            res = social.publish(v.platform, caption, v.media_path)
            p = Post(
                variant_id=v.id, store_id=v.store_id, platform=v.platform,
                method=res["method"], account=res["account"],
                external_id=res["external_id"],
                status="posted" if res["ok"] else "failed",
                error=res["error"], posted_at=datetime.utcnow() if res["ok"] else None,
            )
            s.add(p); posted.append({"platform": v.platform, "label": v.label, **res})
        job = s.get(ContentJob, content_job_id)
        if job:
            job.status = "posted"; s.add(job)
        s.commit()
    return {"posted": posted}


def run_full(store_id: int) -> dict:
    """ครบวง 1 ร้าน: generate → publish."""
    g = generate_for_store(store_id)
    if "error" in g:
        return g
    p = publish_job(g["content_job_id"])
    return {**g, **p}


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
