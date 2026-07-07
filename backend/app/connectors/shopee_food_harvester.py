# -*- coding: utf-8 -*-
"""เก็บลิงก์ affiliate ต่อร้าน + รูป จาก ShopeeFood ผ่าน Phone Farm (ADB) — ไม่ต้องใช้ Open API.

กลไก (พิสูจน์แล้วว่าใช้ได้):
  แตะปุ่มแชร์ของร้าน → share sheet เด้ง (มีชื่อร้าน + รูป + QR + คัดลอกลิงก์)
  → แตะ "คัดลอกลิงก์" → อ่าน clipboard ด้วย uiautomator2 (set_input_ime) → ได้ลิงก์ s.shopee.co.th/...
  → ครอปรูปร้านจาก sheet → ปิด sheet → เลื่อนหา sharse ปุ่มถัดไป
ผลลัพธ์: data/food_affiliate_links.json  [{name, link, image}], รูปเก็บใน data/food_images/.

หมายเหตุ: ทำเป็นชุดช้าๆ + หน่วงเวลา (กันโดนจับว่าบอท / เคารพ ToS). แอปเป็น React Native
จึงแทบไม่มี resource-id → อาศัยข้อความ+พิกัดเป็นหลัก (อาจต้องปรับพิกัดตามรุ่นแอป/จอ).
"""
from __future__ import annotations

import json
import os
import re
import time

from ..config import settings

# ---- พิกัด/ค่าปรับได้ (จอ 720x1608 ของ Vivo V2419) ----
SHARE_X_MIN, SHARE_X_MAX = 630, 712      # ปุ่มแชร์ ↗ ของการ์ดร้าน อยู่ขวาสุด
SHARE_W_MIN, SHARE_W_MAX = 40, 80
LIST_TOP, LIST_BOTTOM = 440, 1450        # โซนรายการร้าน (กันแตะแถบบน/ล่าง)
SHEET_IMG_BOX = (148, 205, 576, 605)     # กรอบรูปใน share sheet (ครอปรูปร้าน)
GAP = 3.0                                # หน่วงระหว่างร้าน (วินาที) — โปรดักชันควร 5-15


def _dev():
    import adbutils
    devs = adbutils.AdbClient(host="127.0.0.1", port=5037).device_list()
    if not devs:
        raise RuntimeError("ไม่พบอุปกรณ์ ADB (Phone Farm)")
    ser = settings.phone_list[0] if getattr(settings, "phone_list", None) else devs[0].serial
    for d in devs:
        if d.serial == ser:
            return d
    return devs[0]


def _u2(serial):
    import uiautomator2 as u2
    dev = u2.connect(serial)
    try:
        dev.set_input_ime(True)   # จำเป็นสำหรับอ่าน clipboard
    except Exception:
        pass
    return dev


def _dump(d) -> str:
    d.shell("uiautomator dump /sdcard/u.xml")
    return d.shell("cat /sdcard/u.xml")


def _nodes(xml: str):
    out = []
    for n in re.findall(r"<node[^>]*/>", xml):
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        mc = re.search(r'class="([^"]*)"', n)
        mt = re.search(r'text="([^"]*)"', n)
        out.append({
            "cls": mc.group(1) if mc else "",
            "text": mt.group(1) if mt else "",
            "box": (x1, y1, x2, y2),
        })
    return out


def _find_share_buttons(xml: str):
    """คืน y-center ของปุ่มแชร์การ์ดร้าน (ViewGroup ทางขวา) เรียงจากบนลงล่าง."""
    ys = []
    for nd in _nodes(xml):
        x1, y1, x2, y2 = nd["box"]
        w = x2 - x1
        if SHARE_X_MIN <= x1 <= SHARE_X_MAX and SHARE_W_MIN <= w <= SHARE_W_MAX and LIST_TOP <= (y1 + y2) // 2 <= LIST_BOTTOM:
            ys.append(((x1 + x2) // 2, (y1 + y2) // 2))
    # dedupe ใกล้กัน
    ys.sort(key=lambda p: p[1])
    uniq = []
    for p in ys:
        if not uniq or abs(p[1] - uniq[-1][1]) > 40:
            uniq.append(p)
    return uniq


def _find_text(xml: str, needle: str):
    for nd in _nodes(xml):
        if needle in nd["text"]:
            x1, y1, x2, y2 = nd["box"]
            return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def _sheet_name(xml: str) -> str:
    """ชื่อร้านใน share sheet: ข้อความยาวสุดในโซนบน sheet ที่ไม่ใช่ป้าย/ปุ่ม."""
    skip = ("แชร์", "คัดลอก", "รับค่าคอมมิช", "Line", "Messenger", "WhatsApp",
            "Facebook", "Email", "SMS", "บันทึก", "Feed")
    cand = ""
    for nd in _nodes(xml):
        t = nd["text"].strip()
        x1, y1, x2, y2 = nd["box"]
        if t and 900 <= y1 <= 1300 and not any(s in t for s in skip) and len(t) > len(cand):
            cand = t
    return cand[:80]


def _img_dir():
    d = os.path.join(settings.data_dir, "food_images")
    os.makedirs(d, exist_ok=True)
    return d


def _crop_image(d, name: str) -> str | None:
    try:
        from PIL import Image
        import io
        raw = d.shell("screencap -p", encoding=None)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        crop = img.crop(SHEET_IMG_BOX)
        safe = re.sub(r"[^\w฀-๿]+", "_", name)[:40] or "shop"
        out = os.path.join(_img_dir(), f"{safe}_{int(time.time())}.jpg")
        crop.save(out, quality=88)
        return out
    except Exception as e:  # pragma: no cover
        print(f"[harvest] crop fail: {str(e)[:60]}")
        return None


def _state_path():
    return os.path.join(settings.data_dir, "food_affiliate_links.json")


def _load() -> list:
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(rows: list):
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def watch_clipboard(category: str = "EXTRACOMM", minutes: float = 10.0, poll: float = 1.5) -> dict:
    """โหมดกึ่งมือ (เชื่อถือได้ 100%): ผู้ใช้แตะ 'แชร์ → คัดลอกลิงก์' บนสินค้า EXTRACOMM ในแอปเอง
    บอทเฝ้า clipboard → เจอลิงก์ Shopee ใหม่ก็บันทึกเป็น Store (affiliate_link) อัตโนมัติ.

    วิธีใช้: เปิดแอป Shopee → โปรแกรม Affiliate → ข้อเสนอ → แท็บ 'ค่าคอมพิเศษ' → แตะแชร์+คัดลอกทีละชิ้น.
    """
    import time
    d = _dev()
    dev = _u2(d.serial)
    from ..db import Store, get_session
    from sqlmodel import select
    with get_session() as s:
        seen = {st.affiliate_link for st in s.exec(select(Store)).all() if st.affiliate_link}
    saved = []
    t_end = time.time() + minutes * 60
    last = ""
    while time.time() < t_end:
        try:
            cur = (dev.clipboard or "").strip()
        except Exception:
            cur = ""
        if cur and cur != last and cur.startswith("http") and ("shopee" in cur or "goeco" in cur) and cur not in seen:
            last = cur
            seen.add(cur)
            with get_session() as s:
                s.add(Store(name=f"[EXTRACOMM] {len(saved) + 1}", area="", rating=0.0,
                            price_range="", image_urls_json="[]", shopee_url="",
                            affiliate_link=cur, category=category, status="new"))
                s.commit()
            saved.append(cur)
            print(f"[watch] +{len(saved)}: {cur}")
        time.sleep(poll)
    return {"saved": len(saved), "links": saved[:50], "category": category}


def _find_share_ys(d, cols=(317, 662), y0=380, y1=1460):
    """ตรวจจับปุ่มแชร์ (วงกลมส้ม-แดง Shopee ~#ee4d2d) ตามคอลัมน์ → คืน (x,y) จริงของทุกปุ่มในจอ."""
    from PIL import Image
    import io
    raw = d.shell("screencap -p", encoding=None)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    W, H = img.size
    px = img.load()
    tr, tg, tb = 238, 77, 45   # Shopee orange-red

    def near(c):
        return abs(c[0] - tr) < 48 and abs(c[1] - tg) < 48 and abs(c[2] - tb) < 48
    out = []
    for x in cols:
        if x >= W:
            continue
        hits = [y for y in range(y0, min(H, y1)) if near(px[x, y])]
        if not hits:
            continue
        start = prev = hits[0]
        groups = []
        for y in hits[1:]:
            if y - prev > 10:
                groups.append((start, prev))
                start = y
            prev = y
        groups.append((start, prev))
        for a, b in groups:
            if b - a >= 14:   # ปุ่มสูงพอ (กันจุดแดงเล็กๆ)
                out.append((x, (a + b) // 2))
    out.sort(key=lambda p: p[1])
    return out


def harvest_products(category: str = "สินค้า", max_n: int = 20, max_scrolls: int = 8) -> dict:
    """เก็บลิงก์ affiliate สินค้า (ทุกหมวด) จากหน้า Shopee Affiliate 'ข้อเสนอ' (กริดสินค้า + ปุ่มแชร์).
    ต้องเปิดแอป Shopee → โปรแกรม Affiliate → ข้อเสนอ ค้างไว้ก่อน. บันทึกเป็น Store พร้อม affiliate_link.

    Shopee เป็น RN app ไม่เปิด selector → ใช้พิกัดคงที่ของกริด (จอ 720x1608) + dedup ด้วยลิงก์.
    ปุ่มแชร์: คอลซ้าย x=317 / ขวา x=662 · ปุ่ม 'คัดลอกลิงก์' ในชีต=(255,1338)."""
    import time
    d = _dev()
    dev = _u2(d.serial)
    COPY = (255, 1338)
    from ..db import Store, get_session
    from sqlmodel import select
    with get_session() as s:
        seen = {st.affiliate_link for st in s.exec(select(Store)).all() if st.affiliate_link}
    got = []
    stale = 0
    for _ in range(max_scrolls):
        progressed = False
        buttons = _find_share_ys(d)            # ตรวจจับปุ่มแชร์จริงในจอ (CV)
        print(f"[harvest-prod] detected {len(buttons)} share buttons")
        for (sx, sy) in buttons:
            if len(got) >= max_n:
                break
            d.shell(f"input tap {sx} {sy}"); time.sleep(2.2)
            d.shell(f"input tap {COPY[0]} {COPY[1]}"); time.sleep(1.3)
            try:
                link = (dev.clipboard or "").strip()
            except Exception:
                link = ""
            d.shell("input keyevent 4"); time.sleep(0.8)
            if link.startswith("http") and link not in seen:
                seen.add(link)
                with get_session() as s:
                    s.add(Store(name=f"[Shopee] สินค้า affiliate {len(got) + 1}", area="", rating=0.0,
                                price_range="", image_urls_json="[]", shopee_url="",
                                affiliate_link=link, category=category, status="new"))
                    s.commit()
                got.append(link)
                progressed = True
                print(f"[harvest-prod] +{len(got)}: {link}")
        if len(got) >= max_n:
            break
        d.shell("input swipe 360 1300 360 460 400"); time.sleep(1.6)
        stale = stale + 1 if not progressed else 0
        if stale >= 2:
            break
    return {"harvested": len(got), "links": got[:30], "category": category}


def harvest(max_n: int = 30, max_scrolls: int = 20) -> dict:
    """วนเก็บลิงก์+รูปจากหน้ารายการร้าน ShopeeFood (ต้องเปิดหน้านั้นค้างไว้ก่อน)."""
    d = _dev()
    dev = _u2(d.serial)
    rows = _load()
    seen = {r["link"] for r in rows if r.get("link")}
    new = 0
    scrolls = 0
    stale = 0
    while len(rows) - len(_load()) < max_n and new < max_n and scrolls < max_scrolls:
        xml = _dump(d)
        btns = _find_share_buttons(xml)
        if not btns:
            print("[harvest] ไม่พบปุ่มแชร์ในจอ — ตรวจว่าอยู่หน้ารายการร้าน ShopeeFood")
            break
        progressed = False
        for (sx, sy) in btns:
            d.shell(f"input tap {sx} {sy}"); time.sleep(2.2)     # เปิด share sheet
            sheet = _dump(d)
            copy = _find_text(sheet, "คัดลอกลิงก์")
            if not copy:
                d.shell("input keyevent 4"); time.sleep(1); continue   # ไม่ใช่ sheet
            name = _sheet_name(sheet)
            d.shell(f"input tap {copy[0]} {copy[1]}"); time.sleep(1.4)  # คัดลอกลิงก์
            link = ""
            try:
                link = (dev.clipboard or "").strip()
            except Exception:
                link = ""
            img = _crop_image(d, name) if link else None
            d.shell("input keyevent 4"); time.sleep(1)               # ปิด sheet
            if link and link not in seen:
                seen.add(link)
                rows.append({"name": name, "link": link, "image": img})
                _save(rows)
                new += 1; progressed = True
                print(f"[harvest] +{new}: {name[:30]} -> {link}")
                if new >= max_n:
                    break
            time.sleep(GAP)
        # เลื่อนหน้าเพื่อโหลดร้านเพิ่ม
        d.shell("input swipe 360 1200 360 500 500"); time.sleep(2.0)
        scrolls += 1
        stale = stale + 1 if not progressed else 0
        if stale >= 2:
            print("[harvest] ไม่มีร้านใหม่ 2 รอบ — น่าจะสุดรายการ")
            break
    return {"new": new, "total": len(rows), "file": _state_path()}
