"""REST API ทั้งหมด — stores / content / posts / abtest / dashboard / metrics / keys."""
from __future__ import annotations

import csv
import io
import json
import random
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import select

from .config import settings
from .db import ContentJob, Metric, Post, Store, Variant, get_session, jloads
from .services import pipeline

router = APIRouter(prefix="/api")


# ----------------------------------------------------------------- schemas
class StoreIn(BaseModel):
    name: str
    area: str = ""
    rating: float = 0.0
    review_count: int = 0
    price_range: str = ""
    menu: list[str] = []
    image_urls: list[str] = []
    affiliate_link: str = ""
    shopee_url: str = ""


class IngestIn(BaseModel):
    """n8n scraper ส่งร้านดิบเข้ามาเป็น batch — backend กรองตามเกณฑ์เอง."""
    stores: list[StoreIn]


def _save_store(s, st: StoreIn) -> Store:
    obj = Store(
        name=st.name, area=st.area, rating=st.rating, review_count=st.review_count,
        price_range=st.price_range, menu_json=json.dumps(st.menu, ensure_ascii=False),
        image_urls_json=json.dumps(st.image_urls, ensure_ascii=False),
        affiliate_link=st.affiliate_link, shopee_url=st.shopee_url,
    )
    s.add(obj)
    return obj


# ----------------------------------------------------------------- stores: ingest (batch, filtered)
@router.post("/ingest")
def ingest(payload: IngestIn):
    """ขั้น 1: รับร้านจาก n8n → กรอง rating/รีวิว → กันซ้ำด้วยชื่อ+ย่าน."""
    added, skipped = 0, 0
    with get_session() as s:
        for st in payload.stores:
            if st.rating < settings.shopee_min_rating or st.review_count < settings.shopee_min_reviews:
                skipped += 1
                continue
            if s.exec(select(Store).where(Store.name == st.name, Store.area == st.area)).first():
                skipped += 1
                continue
            _save_store(s, st)
            added += 1
        s.commit()
    return {"added": added, "skipped": skipped}


# ----------------------------------------------------------------- stores: manual add (no filter)
@router.post("/stores/add")
def add_store(st: StoreIn):
    """เพิ่มร้านเองจาก Dashboard — ไม่ติดเกณฑ์กรอง (ผู้ใช้เลือกเอง) แต่ยังกันซ้ำ."""
    with get_session() as s:
        if s.exec(select(Store).where(Store.name == st.name, Store.area == st.area)).first():
            raise HTTPException(409, "ร้านนี้มีอยู่แล้ว")
        obj = _save_store(s, st)
        s.commit(); s.refresh(obj)
        return {"id": obj.id, "name": obj.name}


# ----------------------------------------------------------------- stores: CSV upload
@router.post("/ingest/csv")
async def ingest_csv(file: UploadFile = File(...)):
    """อัปโหลด CSV (header: name,area,rating,review_count,price_range,menu,affiliate_link,shopee_url).
    menu คั่นหลายเมนูด้วย | — กรองตามเกณฑ์ rating/รีวิวเหมือน /ingest."""
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    stores = []
    for row in reader:
        try:
            stores.append(StoreIn(
                name=(row.get("name") or "").strip(),
                area=(row.get("area") or "").strip(),
                rating=float(row.get("rating") or 0),
                review_count=int(float(row.get("review_count") or 0)),
                price_range=(row.get("price_range") or "").strip(),
                menu=[m.strip() for m in (row.get("menu") or "").split("|") if m.strip()],
                affiliate_link=(row.get("affiliate_link") or "").strip(),
                shopee_url=(row.get("shopee_url") or "").strip(),
            ))
        except Exception:
            continue
    return ingest(IngestIn(stores=[s for s in stores if s.name]))


@router.post("/scrape")
def scrape_now(keyword: str | None = None, limit: int | None = None):
    """ดึงร้าน Shopee Food (ตาม SCRAPER_MODE: direct/proxy/apify) → กรอง → ingest.
    n8n เรียก endpoint เดียวนี้แทน HTTP+Code node ที่เปราะ. ไม่เคย 500 ถ้าโดนบล็อก."""
    from .services import shopee_scraper
    res = shopee_scraper.scrape(keyword, limit)
    if res.get("error"):
        return {"fetched": res.get("fetched", 0), "added": 0, "skipped": 0,
                "mode": settings.scraper_mode, "error": res["error"]}
    ing = ingest(IngestIn(stores=[StoreIn(**s) for s in res["stores"]]))
    return {"fetched": res["fetched"], "mode": res.get("mode"), "error": None, **ing}


@router.get("/scrape/status")
def scrape_status():
    return {"mode": settings.scraper_mode,
            "has_proxy": bool(settings.scraper_proxy),
            "has_scraper_key": bool(settings.scraper_api_key),
            "has_apify": bool(settings.apify_token and settings.apify_actor),
            "keywords": settings.shopee_keywords}


@router.get("/stores")
def list_stores(status: str | None = None):
    with get_session() as s:
        q = select(Store).order_by(Store.created_at.desc())
        if status:
            q = q.where(Store.status == status)
        rows = s.exec(q).all()
        return [{
            "id": r.id, "name": r.name, "area": r.area, "rating": r.rating,
            "review_count": r.review_count, "menu": jloads(r.menu_json, []),
            "status": r.status, "low_ctr_days": r.low_ctr_days,
            "affiliate_link": r.affiliate_link,
        } for r in rows]


# ----------------------------------------------------------------- pipeline
@router.post("/stores/{store_id}/run")
def run_store(store_id: int, background: BackgroundTasks):
    """ครบวง 1 ร้าน (ทำเบื้องหลัง เพราะ Gemini ช้า)."""
    if not get_session().get(Store, store_id):
        raise HTTPException(404, "store not found")
    background.add_task(pipeline.run_full, store_id)
    return {"status": "started", "store_id": store_id}


def _run_all_seq(ids: list[int]):
    """รันทีละร้าน (sequential) — กัน SQLite lock จากการเขียนพร้อมกัน."""
    for sid in ids:
        try:
            pipeline.run_full(sid)
        except Exception as e:  # pragma: no cover
            print(f"[run-all] store {sid}: {e}")


@router.post("/run-all")
def run_all(background: BackgroundTasks, limit: int = 20):
    """ยิงครบวงทุกร้านสถานะ new (รันเรียงทีละร้านใน task เดียว กัน lock + rate limit)."""
    with get_session() as s:
        ids = [r.id for r in s.exec(
            select(Store).where(Store.status == "new").limit(limit)).all()]
    background.add_task(_run_all_seq, ids)
    return {"status": "started", "count": len(ids)}


@router.get("/content/{store_id}")
def get_content(store_id: int):
    with get_session() as s:
        store = s.get(Store, store_id)
        link = (store.affiliate_link or store.shopee_url or "(ลิงก์)") if store else "(ลิงก์)"
        jobs = s.exec(select(ContentJob).where(ContentJob.store_id == store_id)).all()
        variants = s.exec(select(Variant).where(Variant.store_id == store_id)).all()
        return {
            "reel_url": store.reel_url if store else "",
            "jobs": [{"id": j.id, "status": j.status, "analysis": jloads(j.analysis_json, {}),
                      "schedule": jloads(j.schedule_json, []), "cost_baht": j.cost_baht,
                      "model": j.model_used} for j in jobs],
            "variants": [{"id": v.id, "label": v.label, "platform": v.platform,
                          "hook": v.hook, "caption": v.caption, "cta": v.cta,
                          "first_comment": (v.first_comment or "").replace("{LINK}", link),
                          "hashtags": jloads(v.hashtags_json, []),
                          "media_type": v.media_type,
                          "media_url": ("/media/" + v.media_path.replace("\\", "/").split("/")[-1]) if v.media_path else ""}
                         for v in variants],
        }


# ----------------------------------------------------------------- รวมคลิป (montage reel)
VOICE_MAP = {"female": "th-TH-PremwadeeNeural", "male": "th-TH-NiwatNeural"}


@router.post("/stores/{store_id}/reel")
def make_reel(store_id: int, label: str = "A", voice: str = "female"):
    """รวมภาพ A (หรือ B) หลายช็อตของร้าน → คลิปต่อเนื่อง + เสียงพากย์ (female/male) + เพลง."""
    import os
    from .engines import video_ffmpeg

    voice_name = VOICE_MAP.get(voice, settings.tts_voice)
    with get_session() as s:
        store = s.get(Store, store_id)
        if not store:
            raise HTTPException(404, "store not found")
        vs = s.exec(select(Variant).where(Variant.store_id == store_id, Variant.label == label)).all()
        scenes, narration, seen = [], [], set()
        for v in vs:
            img = v.image_path or (v.media_path if v.media_type == "image" else "")
            if img and os.path.exists(img) and img not in seen:
                seen.add(img)
                scenes.append((img, v.hook))
                narration.append(v.voiceover_script or v.hook)
        if not scenes:
            raise HTTPException(400, "ไม่มีภาพต้นฉบับ — รันร้านนี้ใหม่ก่อน (โหมด ffmpeg จะเก็บภาพไว้)")
        reel = video_ffmpeg.build_reel(scenes, narration=" ".join(narration), voice=voice_name)
        if not reel:
            raise HTTPException(500, "สร้างคลิปไม่สำเร็จ")
        store.reel_url = "/media/" + os.path.basename(reel)
        s.add(store); s.commit()
        return {"reel_url": store.reel_url, "scenes": len(scenes)}


# ----------------------------------------------------------------- posts
@router.get("/posts")
def list_posts():
    with get_session() as s:
        rows = s.exec(select(Post).order_by(Post.created_at.desc()).limit(200)).all()
        return [{"id": p.id, "store_id": p.store_id, "platform": p.platform,
                 "method": p.method, "account": p.account, "status": p.status,
                 "external_id": p.external_id, "error": p.error,
                 "comment_status": p.comment_status,
                 "posted_at": p.posted_at.isoformat() if p.posted_at else None}
                for p in rows]


# ----------------------------------------------------------------- metrics (A/B feed)
class MetricIn(BaseModel):
    post_id: int
    impressions: int = 0
    clicks: int = 0
    engagement: int = 0


@router.post("/metrics")
def push_metric(m: MetricIn):
    """n8n/connector ดึงผลจาก platform แล้วส่งเข้ามา → ใช้ตัดสิน A/B."""
    with get_session() as s:
        post = s.get(Post, m.post_id)
        if not post:
            raise HTTPException(404, "post not found")
        ctr = round(m.clicks / m.impressions, 4) if m.impressions else 0.0
        s.add(Metric(post_id=post.id, variant_id=post.variant_id, store_id=post.store_id,
                     impressions=m.impressions, clicks=m.clicks,
                     engagement=m.engagement, ctr=ctr))
        s.commit()
    return {"ok": True, "ctr": ctr}


@router.post("/metrics/simulate")
def simulate_metrics():
    """โหมดเดโม: สุ่มผลให้โพสต์ทั้งหมด เพื่อเห็น A/B + auto-optimize ทำงานทันที."""
    n = 0
    with get_session() as s:
        for post in s.exec(select(Post).where(Post.status == "posted")).all():
            imp = random.randint(300, 3000)
            clk = int(imp * random.uniform(0.002, 0.03))
            s.add(Metric(post_id=post.id, variant_id=post.variant_id, store_id=post.store_id,
                         impressions=imp, clicks=clk, engagement=int(clk * 1.5),
                         ctr=round(clk / imp, 4)))
            n += 1
        s.commit()
    return {"simulated": n}


@router.get("/abtest/{store_id}")
def abtest(store_id: int):
    return pipeline.abtest_result(store_id)


@router.post("/auto-optimize")
def run_optimize():
    return pipeline.auto_optimize()


# ----------------------------------------------------------------- keys / status
@router.get("/keys/status")
def keys_status():
    """บอกว่าเชื่อม key อะไรจริงแล้วบ้าง → Dashboard โชว์ real vs mock."""
    return {
        "claude": settings.has_claude,
        "gemini": settings.has_gemini,
        "meta": settings.has_meta,
        "youtube": bool(settings.youtube_refresh_token),
        "phones": len(settings.phone_list),
        "video": settings.enable_video,
        "posting_mode": settings.posting_mode,
        "content_provider": settings.content_provider,
        "content_ready": settings.content_ready,
        "real_mode": settings.content_ready,
    }


# ----------------------------------------------------------------- dashboard summary
@router.get("/dashboard")
def dashboard():
    with get_session() as s:
        stores = s.exec(select(Store)).all()
        posts = s.exec(select(Post)).all()
        metrics = s.exec(select(Metric)).all()
        jobs = s.exec(select(ContentJob)).all()
        imp = sum(m.impressions for m in metrics)
        clk = sum(m.clicks for m in metrics)
        per_plat: dict[str, dict] = {}
        pmap = {p.id: p for p in posts}
        for m in metrics:
            plat = pmap.get(m.post_id).platform if pmap.get(m.post_id) else "?"
            d = per_plat.setdefault(plat, {"impressions": 0, "clicks": 0})
            d["impressions"] += m.impressions; d["clicks"] += m.clicks
        for d in per_plat.values():
            d["ctr"] = round(d["clicks"] / d["impressions"], 4) if d["impressions"] else 0.0
        return {
            "stores_total": len(stores),
            "stores_active": sum(1 for x in stores if x.status == "active"),
            "stores_paused": sum(1 for x in stores if x.status == "paused"),
            "posts_total": len(posts),
            "posts_failed": sum(1 for p in posts if p.status == "failed"),
            "comments_posted": sum(1 for p in posts if p.comment_status == "posted"),
            "impressions": imp, "clicks": clk,
            "ctr": round(clk / imp, 4) if imp else 0.0,
            "content_cost_baht": round(sum(j.cost_baht for j in jobs), 2),
            "by_platform": per_plat,
            "config": {
                "posting_mode": settings.posting_mode,
                "has_claude": settings.has_claude, "has_gemini": settings.has_gemini,
                "has_meta": settings.has_meta, "video": settings.enable_video,
                "phones": len(settings.phone_list),
                "content_provider": settings.content_provider,
                "real_mode": settings.content_ready,
            },
        }
