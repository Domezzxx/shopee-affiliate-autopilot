"""ดึงสถิติจริงจาก FB/IG/YouTube (impressions/engagement) → เก็บลง Metric → ป้อน learning loop.

YouTube: videos.list (viewCount, likeCount, commentCount)
Facebook: video object (views, likes, comments)
Instagram: media insights (reach/plays, likes, comments, saves, shares)

หมายเหตุ: FB/IG/YT ไม่รายงาน 'คลิกลิงก์ affiliate' (คลิกจริงอยู่ฝั่ง Shopee Affiliate) →
ที่นี่เก็บ impressions + engagement เป็นสัญญาณคุณภาพคอนเทนต์; learning จะจัดอันดับด้วย
engagement-rate เมื่อไม่มี clicks. upsert 1 Metric ต่อ 1 โพสต์ (กันนับซ้ำเวลาดึงหลายรอบ).
"""
from __future__ import annotations

import httpx
from sqlmodel import select

from ..config import settings
from ..db import Metric, Post, get_session
from ..connectors.social import GRAPH


def _num(x) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0


def _fetch_youtube(video_id: str, token: str) -> tuple[int, int, int]:
    """(impressions=views, clicks=0, engagement=likes+comments)."""
    r = httpx.get("https://www.googleapis.com/youtube/v3/videos",
                  params={"part": "statistics", "id": video_id},
                  headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return 0, 0, 0
    st = items[0].get("statistics", {})
    views = _num(st.get("viewCount"))
    eng = _num(st.get("likeCount")) + _num(st.get("commentCount"))
    return views, 0, eng


def _fetch_facebook(post_id: str) -> tuple[int, int, int]:
    """วิดีโอ/รีลเพจ: views + likes + comments (best-effort)."""
    tok = settings.meta_access_token
    imp = clk = eng = 0
    try:
        j = httpx.get(f"{GRAPH}/{post_id}",
                      params={"fields": "views,likes.summary(true),comments.summary(true)",
                              "access_token": tok}, timeout=30).json()
        imp = _num(j.get("views"))
        eng = _num((j.get("likes", {}).get("summary", {}) or {}).get("total_count")) \
            + _num((j.get("comments", {}).get("summary", {}) or {}).get("total_count"))
    except Exception:
        pass
    # ลองดึง impressions/clicks จาก insights (บางโพสต์รองรับ)
    try:
        ins = httpx.get(f"{GRAPH}/{post_id}/insights",
                        params={"metric": "post_impressions,post_clicks", "access_token": tok},
                        timeout=30).json()
        for d in ins.get("data", []):
            val = _num((d.get("values") or [{}])[0].get("value"))
            if d.get("name") == "post_impressions" and val:
                imp = val
            elif d.get("name") == "post_clicks":
                clk = val
    except Exception:
        pass
    return imp, clk, eng


def _fetch_instagram(media_id: str) -> tuple[int, int, int]:
    """IG reel/media insights: reach/plays + likes+comments+saves+shares."""
    tok = settings.meta_access_token
    try:
        ins = httpx.get(f"{GRAPH}/{media_id}/insights",
                        params={"metric": "reach,plays,likes,comments,saved,shares",
                                "access_token": tok}, timeout=30).json()
        vals = {d.get("name"): _num((d.get("values") or [{}])[0].get("value"))
                for d in ins.get("data", [])}
        imp = vals.get("plays") or vals.get("reach") or 0
        eng = sum(vals.get(k, 0) for k in ("likes", "comments", "saved", "shares"))
        return imp, 0, eng
    except Exception:
        return 0, 0, 0


def _skip(ext: str) -> bool:
    e = (ext or "").strip()
    return (not e) or e.startswith(("mock", "ph_", "yt_", "ig_", "fb_", "cmt_", "skip"))


def fetch_all() -> dict:
    """ดึงสถิติจริงทุกโพสต์ที่ posted (API จริง) → upsert Metric. คืนสรุป."""
    fetched = skipped = failed = 0
    yt_token = ""
    with get_session() as s:
        posts = s.exec(select(Post).where(Post.status == "posted")).all()
        for p in posts:
            if p.method == "phone" or _skip(p.external_id):
                skipped += 1
                continue
            try:
                if p.platform == "youtube":
                    if not yt_token:
                        from ..connectors.social import _yt_access_token
                        yt_token = _yt_access_token()
                    imp, clk, eng = _fetch_youtube(p.external_id, yt_token)
                elif p.platform == "facebook":
                    imp, clk, eng = _fetch_facebook(p.external_id)
                elif p.platform == "instagram":
                    imp, clk, eng = _fetch_instagram(p.external_id)
                else:
                    skipped += 1
                    continue
            except Exception as e:  # pragma: no cover
                print(f"[metrics] {p.platform} post {p.id} fail: {str(e)[:80]}")
                failed += 1
                continue

            if imp == 0 and eng == 0:
                skipped += 1
                continue
            ctr = round(clk / imp, 4) if imp else 0.0
            # upsert: 1 Metric ต่อโพสต์ (อัปเดต snapshot ล่าสุด ไม่ append ซ้ำ)
            m = s.exec(select(Metric).where(Metric.post_id == p.id)).first()
            if m:
                m.impressions, m.clicks, m.engagement, m.ctr = imp, clk, eng, ctr
            else:
                m = Metric(post_id=p.id, variant_id=p.variant_id, store_id=p.store_id,
                           impressions=imp, clicks=clk, engagement=eng, ctr=ctr)
            s.add(m)
            fetched += 1
        s.commit()
    return {"fetched": fetched, "skipped": skipped, "failed": failed}
