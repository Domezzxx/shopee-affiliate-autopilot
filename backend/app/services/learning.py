"""Self-improvement loop — บอทเรียนรู้จากผลงานที่ผ่านมา (CTR จริง) แล้วป้อนกลับเข้าการเขียนคอนเทนต์.

แนวคิด: โพสต์ → เก็บ Metric (impressions/clicks/ctr) → build_insights() รวมว่า
'ภาษา/รูปแบบ/แพลตฟอร์ม/hook' ไหนได้ผลดีสุด → insights_prompt() แปลงเป็นคำแนะนำ
ฉีดเข้า prompt ของ Claude → คอนเทนต์รอบถัดไปเอนเข้าหาสิ่งที่เวิร์ก → วนซ้ำ ฉลาดขึ้นเรื่อยๆ.

degrade ได้: ถ้าข้อมูลยังน้อย → ไม่สรุป/ไม่แก้ prompt (ไม่มั่ว).
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

from sqlmodel import select

from ..config import settings
from ..db import Metric, Variant, get_session

_MIN_IMPRESSIONS = 200          # เกณฑ์ 'มั่นใจสูง' (high confidence)
_MIN_IMPRESSIONS_EARLY = 50     # เกณฑ์ 'สัญญาณเบื้องต้น' (real-time) — ร้านเล็ก/ยอดวิวช้าก็ได้ปรับ ไม่ต้องรอนาน
_MIN_GROUPS = 2                 # ต้องมีอย่างน้อย 2 ตัวเลือกถึงจะเทียบ "อันไหนดีกว่า"


def _insights_path() -> str:
    return os.path.join(settings.data_dir, "insights.json")


def _agg(rows: list[tuple[str, int, int, int]], rank_by: str = "ctr",
         min_imp: int = _MIN_IMPRESSIONS) -> dict:
    """rows = [(key, impressions, clicks, engagement)] → {key: {imp, clk, eng, ctr, eng_rate}}
    เรียงตาม rank_by ('ctr' หรือ 'eng_rate'). นับเฉพาะกลุ่มที่ impression ถึง min_imp (ปรับได้)."""
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for key, imp, clk, eng in rows:
        if not key:
            continue
        acc[key][0] += imp; acc[key][1] += clk; acc[key][2] += eng
    out = {}
    for k, (imp, clk, eng) in acc.items():
        if imp >= min_imp:                           # นับเฉพาะกลุ่มที่ข้อมูลพอ (ตามเกณฑ์ที่ส่งเข้ามา)
            out[k] = {"impressions": imp, "clicks": clk, "engagement": eng,
                      "ctr": round(clk / imp, 4) if imp else 0.0,
                      "eng_rate": round(eng / imp, 4) if imp else 0.0}
    return dict(sorted(out.items(), key=lambda kv: kv[1][rank_by], reverse=True))


def build_insights() -> dict:
    """รวมผลงานจริงทั้งหมด → บทเรียน (per ภาษา/label/platform + hook ที่ปัง). เซฟลง insights.json."""
    by_lang_rows, by_label_rows, by_plat_rows = [], [], []
    var_perf: dict[int, list] = {}   # variant_id → [imp, clk, eng, v]
    total_imp = total_clk = total_eng = 0
    with get_session() as s:
        metrics = s.exec(select(Metric)).all()
        if not metrics:
            return _save({"ready": False, "reason": "ยังไม่มี metric (รอเก็บผลโพสต์)"})
        vmap = {v.id: v for v in s.exec(select(Variant)).all()}
        for m in metrics:
            v = vmap.get(m.variant_id)
            if not v:
                continue
            total_imp += m.impressions; total_clk += m.clicks; total_eng += m.engagement
            by_lang_rows.append((v.spoken_lang or "unknown", m.impressions, m.clicks, m.engagement))
            by_label_rows.append((v.label or "?", m.impressions, m.clicks, m.engagement))
            by_plat_rows.append((v.platform or "?", m.impressions, m.clicks, m.engagement))
            p = var_perf.setdefault(m.variant_id, [0, 0, 0, v])
            p[0] += m.impressions; p[1] += m.clicks; p[2] += m.engagement

    # ถ้าคลิกแทบไม่มี (FB/IG/YT ไม่รายงานคลิก) → จัดอันดับด้วย engagement-rate แทน CTR
    use_eng = (total_imp > 0 and (total_clk / total_imp) < 0.0005)
    rank_by = "eng_rate" if use_eng else "ctr"

    # เกณฑ์ปรับตามปริมาณข้อมูล (real-time optimization): ข้อมูลเยอะ→ใช้เกณฑ์มั่นใจสูง,
    # ข้อมูลน้อย→ใช้เกณฑ์เบื้องต้น เพื่อให้ร้านเล็ก/ยอดวิวช้าได้รับการปรับด้วย (ไม่ต้องรอ 200 impressions)
    min_imp = _MIN_IMPRESSIONS if total_imp >= _MIN_IMPRESSIONS else _MIN_IMPRESSIONS_EARLY
    confidence = "high" if total_imp >= _MIN_IMPRESSIONS else "provisional"

    by_lang = _agg(by_lang_rows, rank_by, min_imp)
    by_label = _agg(by_label_rows, rank_by, min_imp)
    by_platform = _agg(by_plat_rows, rank_by, min_imp)

    # hook/บทพูดที่ปังจริง — variant ที่อัตรา (ctr/eng_rate) สูง + impression พอ
    top = []
    for vid, (imp, clk, eng, v) in var_perf.items():
        rate = (eng / imp if use_eng else clk / imp) if imp else 0.0
        if imp >= max(20, min_imp // 2) and rate > 0:
            top.append({"rate": round(rate, 4), "impressions": imp,
                        "spoken_lang": v.spoken_lang, "platform": v.platform, "label": v.label,
                        "hook": (v.spoken_line or v.hook or "")[:80]})
    top.sort(key=lambda x: x["rate"], reverse=True)

    data = {
        "ready": total_imp >= _MIN_IMPRESSIONS_EARLY,
        "confidence": confidence,          # high | provisional (บอกว่าเชื่อได้แค่ไหน)
        "min_impressions_used": min_imp,
        "metric_mode": rank_by,   # ctr | eng_rate
        "baseline_ctr": round(total_clk / total_imp, 4) if total_imp else 0.0,
        "baseline_eng_rate": round(total_eng / total_imp, 4) if total_imp else 0.0,
        "total_impressions": total_imp,
        "by_spoken_lang": by_lang,
        "by_label": by_label,
        "by_platform": by_platform,
        "top_hooks": top[:8],
    }
    return _save(data)


def _save(data: dict) -> dict:
    import datetime
    data["updated_at"] = datetime.datetime.utcnow().isoformat()
    try:
        os.makedirs(settings.data_dir, exist_ok=True)
        with open(_insights_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:  # pragma: no cover
        print(f"[learning] save fail: {e}")
    return data


def get_insights() -> dict:
    """อ่าน insights ล่าสุด (ไม่คำนวณใหม่) — สำหรับ dashboard/prompt."""
    try:
        with open(_insights_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ready": False}


def learned_lang_order(default: list[str]) -> tuple[list[str], bool]:
    """ลำดับภาษาบทพูดเรียงตาม 'ผลตอบรับจริง' (ดีสุดก่อน) เพื่อให้ตัวเขียนคอนเทนต์ 'ทำตามที่เรียนรู้' จริง —
    ไม่ใช่แค่รายงานแล้วจบ. เติมภาษาที่ยังไม่มีข้อมูลต่อท้ายตาม default (คงการสำรวจ). คืน (ลำดับ, ready?).
    ข้อมูลไม่พอ/ไม่ ready → คืน (default, False) เพื่อไม่กระทบพฤติกรรมเดิม."""
    d = get_insights()
    lang = d.get("by_spoken_lang", {})
    ranked = [k for k in lang.keys() if k and k != "unknown"]   # by_spoken_lang เรียงตาม performance อยู่แล้ว
    if not d.get("ready") or len(ranked) < _MIN_GROUPS:
        return list(default), False
    merged = ranked + [x for x in default if x not in ranked]
    return merged, True


def insights_prompt() -> str:
    """แปลงบทเรียนเป็นคำแนะนำสั้นๆ ฉีดเข้า prompt ของ Claude — คืน '' ถ้าข้อมูลยังไม่พอ."""
    d = get_insights()
    if not d.get("ready"):
        return ""
    conf_note = " (เบื้องต้น — ข้อมูลยังน้อย ใช้เป็นแนวโน้ม ปรับได้เร็วแบบ real-time)" if d.get("confidence") == "provisional" else ""
    mode = d.get("metric_mode", "ctr")
    rkey = "eng_rate" if mode == "eng_rate" else "ctr"
    mlabel = "engagement-rate" if mode == "eng_rate" else "CTR"

    def pct(v):
        return f"{v.get(rkey, 0) * 100:.1f}%"

    lines = []
    lang = d.get("by_spoken_lang", {})
    lang = {k: v for k, v in lang.items() if k != "unknown"}
    if len(lang) >= _MIN_GROUPS:
        best = next(iter(lang))
        rank = ", ".join(f"{k} {pct(v)}" for k, v in lang.items())
        lines.append(f"- ภาษาบทพูดที่ได้ผลจริง (เรียงดีสุด): {rank} → ดันภาษา '{best}' ให้มากขึ้น")
    label = d.get("by_label", {})
    if len(label) >= _MIN_GROUPS:
        best = next(iter(label))
        lines.append(f"- รูปแบบที่เวิร์กกว่า: {best} ({mlabel} {pct(label[best])}) → เขียนแนวนี้เป็นหลัก")
    plat = d.get("by_platform", {})
    if len(plat) >= _MIN_GROUPS:
        rank = ", ".join(f"{k} {pct(v)}" for k, v in plat.items())
        lines.append(f"- แพลตฟอร์มที่ตอบรับดี: {rank}")
    hooks = d.get("top_hooks", [])
    ex = " / ".join(f"\"{h['hook']}\"" for h in hooks[:3] if h.get("hook"))
    if ex:
        lines.append(f"- hook ที่พิสูจน์แล้วว่าปัง ({mlabel} สูง) ให้ใช้แนวนี้: {ex}")
    if not lines:
        return ""
    base = d.get("baseline_eng_rate", 0) if mode == "eng_rate" else d.get("baseline_ctr", 0)
    return (f"\n\n📊 บทเรียนจากผลงานจริงที่ผ่านมา{conf_note} (data-driven — ทำตามนี้เพื่อให้ดีขึ้นเรื่อยๆ):\n"
            + "\n".join(lines)
            + f"\n(วัดด้วย {mlabel}, ฐานเฉลี่ย {base*100:.2f}% จาก {d.get('total_impressions',0):,} impressions)")
