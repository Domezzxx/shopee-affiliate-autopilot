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

_MIN_IMPRESSIONS = 200          # กลุ่มต้องมี impression รวมขั้นต่ำเท่านี้ถึงเชื่อผล
_MIN_GROUPS = 2                 # ต้องมีอย่างน้อย 2 ตัวเลือกถึงจะเทียบ "อันไหนดีกว่า"


def _insights_path() -> str:
    return os.path.join(settings.data_dir, "insights.json")


def _agg(rows: list[tuple[str, int, int]]) -> dict:
    """rows = [(key, impressions, clicks)] → {key: {imp, clk, ctr}} เรียงตาม ctr."""
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for key, imp, clk in rows:
        if not key:
            continue
        acc[key][0] += imp
        acc[key][1] += clk
    out = {}
    for k, (imp, clk) in acc.items():
        if imp >= _MIN_IMPRESSIONS:                  # นับเฉพาะกลุ่มที่ข้อมูลพอ
            out[k] = {"impressions": imp, "clicks": clk, "ctr": round(clk / imp, 4) if imp else 0.0}
    return dict(sorted(out.items(), key=lambda kv: kv[1]["ctr"], reverse=True))


def build_insights() -> dict:
    """รวมผลงานจริงทั้งหมด → บทเรียน (per ภาษา/label/platform + hook ที่ปัง). เซฟลง insights.json."""
    by_lang_rows, by_label_rows, by_plat_rows = [], [], []
    var_perf: dict[int, list] = {}   # variant_id → [imp, clk]
    total_imp = total_clk = 0
    with get_session() as s:
        metrics = s.exec(select(Metric)).all()
        if not metrics:
            return _save({"ready": False, "reason": "ยังไม่มี metric (รอเก็บผลโพสต์)"})
        vmap = {v.id: v for v in s.exec(select(Variant)).all()}
        for m in metrics:
            v = vmap.get(m.variant_id)
            if not v:
                continue
            total_imp += m.impressions; total_clk += m.clicks
            by_lang_rows.append((v.spoken_lang or "unknown", m.impressions, m.clicks))
            by_label_rows.append((v.label or "?", m.impressions, m.clicks))
            by_plat_rows.append((v.platform or "?", m.impressions, m.clicks))
            p = var_perf.setdefault(m.variant_id, [0, 0, v])
            p[0] += m.impressions; p[1] += m.clicks

    by_lang = _agg(by_lang_rows)
    by_label = _agg(by_label_rows)
    by_platform = _agg(by_plat_rows)

    # hook/บทพูดที่ปังจริง — variant ที่ ctr สูง + impression พอ
    top = []
    for vid, (imp, clk, v) in var_perf.items():
        if imp >= max(50, _MIN_IMPRESSIONS // 2) and clk:
            top.append({"ctr": round(clk / imp, 4), "impressions": imp,
                        "spoken_lang": v.spoken_lang, "platform": v.platform, "label": v.label,
                        "hook": (v.spoken_line or v.hook or "")[:80]})
    top.sort(key=lambda x: x["ctr"], reverse=True)

    baseline = round(total_clk / total_imp, 4) if total_imp else 0.0
    data = {
        "ready": total_imp >= _MIN_IMPRESSIONS,
        "baseline_ctr": baseline,
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


def insights_prompt() -> str:
    """แปลงบทเรียนเป็นคำแนะนำสั้นๆ ฉีดเข้า prompt ของ Claude — คืน '' ถ้าข้อมูลยังไม่พอ."""
    d = get_insights()
    if not d.get("ready"):
        return ""
    lines = []
    lang = d.get("by_spoken_lang", {})
    if len(lang) >= _MIN_GROUPS:
        best = next(iter(lang))
        rank = ", ".join(f"{k} {v['ctr']*100:.1f}%" for k, v in lang.items())
        lines.append(f"- ภาษาบทพูดที่ได้ผลจริง (เรียงดีสุด): {rank} → ดันภาษา '{best}' ให้มากขึ้น")
    label = d.get("by_label", {})
    if len(label) >= _MIN_GROUPS:
        best = next(iter(label))
        lines.append(f"- รูปแบบที่เวิร์กกว่า: {best} (CTR {label[best]['ctr']*100:.1f}%) → เขียนแนวนี้เป็นหลัก")
    plat = d.get("by_platform", {})
    if len(plat) >= _MIN_GROUPS:
        rank = ", ".join(f"{k} {v['ctr']*100:.1f}%" for k, v in plat.items())
        lines.append(f"- แพลตฟอร์มที่ตอบรับดี: {rank}")
    hooks = d.get("top_hooks", [])
    if hooks:
        ex = " / ".join(f"\"{h['hook']}\"" for h in hooks[:3] if h.get("hook"))
        if ex:
            lines.append(f"- hook ที่พิสูจน์แล้วว่าปัง (CTR สูง) ให้ใช้แนวนี้: {ex}")
    if not lines:
        return ""
    return ("\n\n📊 บทเรียนจากผลงานจริงที่ผ่านมา (data-driven — ทำตามนี้เพื่อให้ดีขึ้นเรื่อยๆ):\n"
            + "\n".join(lines)
            + f"\n(อ้างอิง CTR เฉลี่ยฐาน {d.get('baseline_ctr',0)*100:.2f}% จาก {d.get('total_impressions',0):,} impressions)")
