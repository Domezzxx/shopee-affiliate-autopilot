# -*- coding: utf-8 -*-
"""โปสเตอร์อาหารระดับ 'Graphic Design' — เรนเดอร์ HTML/CSS ผ่าน Chrome headless → PNG.

เหนือกว่า PIL: เงานุ่มหลายชั้น, ไล่เฉด, กระจกฝ้า (glassmorphism), ทองเมทัลลิก,
ฟิล์มเกรน, vignette, ฟอนต์ดิสเพลย์ Google (Kanit/Prompt/Anton). ฟรี ไม่ใช้ AI image credit.
"""
from __future__ import annotations

import base64
import mimetypes
import os
import re
import uuid

from ..config import settings

W, H = 1080, 1350
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF️]+")


def _noemoji(t: str) -> str:
    return _EMOJI.sub("", t or "").strip()


def _short_name(name: str, limit: int = 24) -> str:
    """ตัดชื่อร้านยาวๆ ให้เหลือหัวเรื่องสั้นกระชับ (ตัดที่วงเล็บ/คำพูด + จำกัดจำนวนคำ)."""
    n = re.split(r'[("“–\-]', _noemoji(name))[0].strip()
    if len(n) <= limit:
        return n or _noemoji(name)[:limit]
    out = ""
    for w in n.split():
        if out and len(out) + 1 + len(w) > limit:
            break
        out = (out + " " + w).strip()
    return out or n[:limit]


def _data_uri(path: str) -> str | None:
    """แปลงรูปเป็น data URI (ฝังใน HTML — ไม่ต้อง serve ไฟล์)."""
    try:
        mime = mimetypes.guess_type(path)[0] or "image/jpeg"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


# ฟิล์มเกรน (SVG feTurbulence) ฝังเป็น data URI — ทำให้ภาพดู 'ถ่ายจริง' ไม่แบน
_GRAIN = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140">'
    b'<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>'
    b'<feColorMatrix type="saturate" values="0"/></filter>'
    b'<rect width="100%" height="100%" filter="url(#n)"/></svg>'
).decode())

_FONTS = ("https://fonts.googleapis.com/css2?"
          "family=Kanit:wght@500;600;700;800;900&family=Prompt:wght@400;500;600;700&"
          "family=Mitr:wght@500;600;700&family=Chonburi&family=Bai+Jamjuree:wght@700&"
          "family=Sriracha&family=Charmonman:wght@700&"
          "family=Anton&family=Bebas+Neue&display=swap")


def _burst_svg(fill: str = "#e11d2a", points: int = 22) -> str:
    """ป้ายระเบิด (spiky starburst) เป็น data URI — ใช้เป็นพื้นหลังป้ายราคา."""
    import math
    cx = cy = 100
    pts = []
    for i in range(points * 2):
        r = 98 if i % 2 == 0 else 74
        a = math.pi * i / points - math.pi / 2
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    poly = " ".join(pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
           f'<polygon points="{poly}" fill="{fill}" stroke="#fff" stroke-width="5"/></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _price(store) -> str:
    m = re.search(r"\d[\d,]*", getattr(store, "price_range", "") or "")
    return m.group(0) if m else ""


def build_poster_html(store, photo_uri: str, hook: str = "", style: str = "cinematic",
                      campaign: str | None = None) -> str:
    """คืน HTML โปสเตอร์ 1080x1350 (ใช้ร่วมกับ render_to_png). campaign=ป้ายแคมเปญ (None=อ่านจาก settings)."""
    if campaign is None:
        campaign = getattr(settings, "promo_campaign", "") or ""
    camp_on = bool(campaign.strip())
    name = _short_name(getattr(store, "name", "") or "ร้านเด็ด")
    area = (getattr(store, "area", "") or "อุดรธานี").strip()
    subtype = (getattr(store, "food_subtype", "") or "ของกินเด็ด").strip()
    rating = getattr(store, "rating", 0) or 0
    price = _price(store)
    hk = _noemoji((hook or "").split("\n")[0])[:60]
    kicker = f"{subtype} · {area}"

    common = f"""
    *{{margin:0;padding:0;box-sizing:border-box}}
    @import url('{_FONTS}');
    html,body{{width:{W}px;height:{H}px;overflow:hidden}}
    body{{font-family:'Kanit',sans-serif;position:relative;background:#0d0b09}}
    .photo{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
    .grain{{position:absolute;inset:0;background-image:url('{_GRAIN}');
      background-size:340px;mix-blend-mode:overlay;opacity:.10;pointer-events:none}}
    .vignette{{position:absolute;inset:0;box-shadow:inset 0 0 340px 40px rgba(0,0,0,.85);pointer-events:none}}
    .gold{{background:linear-gradient(180deg,#fff6cf 0%,#f4d879 42%,#e7bd52 62%,#b7842c 100%);
      -webkit-background-clip:text;background-clip:text;color:transparent}}
    .chip{{backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
      background:rgba(20,17,13,.42);border:1px solid rgba(244,216,120,.55)}}
    .name{{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
      overflow:hidden;overflow-wrap:break-word}}
    .campaign{{position:absolute;border-radius:20px;border:4px solid #1a2a6c;
      background:linear-gradient(180deg,#eaf6ff,#c8e6fb);
      display:flex;align-items:center;gap:22px;padding:14px 30px;
      box-shadow:0 12px 28px rgba(0,0,0,.3);z-index:4}}
    /* โลโก้ ไทยช่วยไทย พลัส 60/40 (จำลองจากของจริง) */
    .logo{{position:relative;display:flex;flex-direction:column;line-height:.82;flex:0 0 auto;padding-top:14px}}
    .logo .flagacc{{position:absolute;top:-6px;left:-6px;width:78px;height:52px;transform:rotate(-8deg);
      filter:drop-shadow(1px 2px 2px rgba(0,0,0,.3));z-index:0}}
    .logo .row{{display:flex;align-items:flex-start;position:relative;z-index:1}}
    .logo .thai{{font-family:'Sriracha';font-size:64px;color:#16276e;transform:skewX(-6deg);
      -webkit-text-stroke:1px #fff;text-shadow:2px 3px 4px rgba(0,0,0,.22);padding-left:34px}}
    .logo .chuay{{font-family:'Sriracha';font-size:64px;color:#16276e;transform:skewX(-6deg);
      text-shadow:2px 3px 3px rgba(0,0,0,.22)}}
    .logo .plus{{font-family:'Sriracha';font-size:36px;color:#39a935;margin-left:6px;margin-top:-4px}}
    .logo .btm{{display:flex;align-items:center;gap:14px;margin-top:-4px}}
    .logo .num{{font-family:'Sriracha';font-size:48px;color:#39a935;letter-spacing:1px;padding-left:40px}}
    .paotang{{display:flex;align-items:center;gap:8px;background:#0b53c6;border-radius:10px;padding:5px 12px 5px 8px}}
    .paotang .qr{{width:26px;height:26px;background:#fff;border-radius:4px;
      background-image:radial-gradient(#0b53c6 42%,transparent 44%);background-size:9px 9px;background-position:2px 2px}}
    .paotang span{{color:#fff;font-family:'Kanit';font-weight:600;font-size:24px}}
    .campaign .tag{{font-family:'Kanit';font-weight:700;font-size:30px;color:#16276e;line-height:1.15;
      border-left:3px solid #9fb8d8;padding-left:20px}}
    .campaign .tag b{{color:#c1121f}}
    """

    if style == "flyer":
        return _tpl_flyer(photo_uri, name, subtype, area, hk, rating, price, common, camp_on)
    if style == "cartoon":
        return _tpl_cartoon(photo_uri, name, subtype, area, hk, rating, price, common, camp_on)
    if style == "editorial":
        return _tpl_editorial(photo_uri, name, kicker, hk, rating, price, common)
    if style == "magazine":
        return _tpl_magazine(photo_uri, name, kicker, hk, rating, price, common)
    return _tpl_cinematic(photo_uri, name, kicker, hk, rating, price, common)


def _flag_svg() -> str:
    """ธงชาติไทยแบบสะบัด (5 แถบ) เป็น data URI — ใช้เป็นแอคเซนต์บนโลโก้."""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 70">'
           '<defs><clipPath id="w"><path d="M0,7 Q25,-3 50,5 T100,5 V63 Q75,73 50,65 T0,65 Z"/></clipPath></defs>'
           '<g clip-path="url(#w)">'
           '<rect width="100" height="70" fill="#ed1c24"/>'
           '<rect width="100" height="12" y="12" fill="#fff"/>'
           '<rect width="100" height="22" y="24" fill="#16276e"/>'
           '<rect width="100" height="12" y="46" fill="#fff"/>'
           '</g></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _campaign_html(pos: str) -> str:
    """ป้ายแคมเปญ 'ไทยช่วยไทย พลัส 60/40' (จำลองโลโก้จริง + ธงสะบัด + เป๋าตัง). pos = css ตำแหน่ง."""
    return (f'<div class="campaign" style="{pos}">'
            '<div class="logo">'
            f'<img class="flagacc" src="{_flag_svg()}">'
            '<div class="row"><span class="thai">ไทย</span><span class="chuay">ช่วยไทย</span>'
            '<span class="plus">พลัส</span></div>'
            '<div class="btm"><span class="num">60/40</span>'
            '<span class="paotang"><span class="qr"></span><span>เป๋าตัง</span></span></div>'
            '</div>'
            '<div class="tag">ร้านนี้<br>ร่วมโครงการ</div>'
            '</div>')


def _stars(rating) -> str:
    full = int(round(float(rating or 0)))
    return "".join(f'<span style="color:{"#f4d879" if i<full else "rgba(255,255,255,.25)"}">★</span>'
                   for i in range(5))


def _tpl_flyer(uri, name, subtype, area, hk, rating, price, common, campaign=False) -> str:
    """สไตล์ A — แฟลชสว่างจัด รูปอาหารจริง ตัวอักษรหนามีขอบ ป้ายราคาระเบิด (แบบกระดังงา)."""
    burst = _burst_svg("#e11d2a")
    price_html = (f'<div class="burst"><span class="bk">เริ่มต้น</span>'
                  f'<span class="bv">{price}.-</span></div>') if price else ""
    sub = subtype if subtype and subtype != "ของกินเด็ด" else "อร่อยแซ่บถึงใจ"
    camp = _campaign_html("left:64px;right:64px;bottom:172px") if campaign else ""
    fc_h = 500 if campaign else 560   # ย่อการ์ดรูปนิดเมื่อมีป้ายแคมเปญ กันชน
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{common}
    body{{background:
      radial-gradient(120% 90% at 50% 30%,rgba(255,255,255,.55),transparent 45%),
      repeating-conic-gradient(from 0deg at 50% 38%,#ffd53a 0deg 9deg,#ffc915 9deg 18deg)}}
    .kbanner{{position:absolute;top:56px;left:50%;transform:translateX(-50%) rotate(-2deg);
      background:#161616;color:#ffd53a;font-weight:700;font-size:34px;padding:8px 34px;border-radius:8px;
      box-shadow:0 8px 0 rgba(0,0,0,.18)}}
    .ftitle{{position:absolute;top:108px;left:0;right:0;text-align:center;
      font-family:'Kanit';font-weight:900;font-size:138px;line-height:.9;color:#e11d2a;
      -webkit-text-stroke:4px #fff;paint-order:stroke fill;transform:rotate(-2deg);
      filter:drop-shadow(5px 6px 0 rgba(0,0,0,.82)) drop-shadow(0 12px 14px rgba(0,0,0,.3));
      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;padding:0 30px}}
    .sbanner{{position:absolute;top:328px;left:50%;transform:translateX(-50%) rotate(-1deg);
      background:#161616;color:#fff;font-weight:600;font-size:38px;padding:10px 40px;border-radius:10px;white-space:nowrap}}
    .foodcard{{position:absolute;top:410px;left:120px;width:840px;height:{fc_h}px;transform:rotate(-3deg);
      border:16px solid #fff;box-shadow:0 26px 50px rgba(0,0,0,.45);overflow:hidden;background:#fff}}
    .foodcard img{{width:100%;height:100%;object-fit:cover}}
    .burst{{position:absolute;top:372px;right:44px;width:300px;height:300px;transform:rotate(9deg);
      background:url('{burst}') center/contain no-repeat;display:flex;flex-direction:column;
      align-items:center;justify-content:center;color:#fff;filter:drop-shadow(0 12px 16px rgba(0,0,0,.4));z-index:3}}
    .burst .bk{{font-weight:600;font-size:30px;margin-bottom:-6px}}
    .burst .bv{{font-family:'Kanit';font-weight:900;font-size:76px;line-height:1;letter-spacing:-1px}}
    .rbadge{{position:absolute;left:70px;top:900px;width:150px;height:150px;border-radius:50%;
      background:#0a7d34;border:5px solid #fff;color:#fff;display:flex;flex-direction:column;
      align-items:center;justify-content:center;transform:rotate(-6deg);box-shadow:0 10px 18px rgba(0,0,0,.3);z-index:3}}
    .rbadge b{{font-size:52px;line-height:1}} .rbadge span{{font-size:24px}}
    .cta{{position:absolute;left:0;right:0;bottom:0;height:150px;
      background:linear-gradient(90deg,#c1121f,#e11d2a);border-top:8px solid #ffd53a;
      display:flex;align-items:center;justify-content:center;gap:16px;
      color:#fff;font-family:'Kanit';font-weight:800;font-size:48px}}
    </style></head><body>
      <div class="kbanner">ร้านอาหาร · {area}</div>
      <div class="ftitle">{name}</div>
      <div class="sbanner">{sub}</div>
      <div class="foodcard"><img src="{uri}"></div>
      {price_html}
      <div class="rbadge"><b>{rating}</b><span>เรตติ้ง</span></div>
      {camp}
      <div class="cta">สั่งเลย · ลิงก์ใต้โพสต์ ↓</div>
    </body></html>"""


def _tpl_cartoon(uri, name, subtype, area, hk, rating, price, common, campaign=False) -> str:
    """สไตล์ B — ครอบภาพการ์ตูน/คาริคเจอร์ + ไตเติลระเบิด + ป้ายราคาแดง (แบบ Girlkik)."""
    burst = _burst_svg("#e11d2a")
    price_html = (f'<div class="burst"><span class="bk">เริ่มต้น</span>'
                  f'<span class="bv">{price}.-</span></div>') if price else ""
    sub = subtype if subtype and subtype != "ของกินเด็ด" else "อร่อยทุกคำ"
    camp = _campaign_html("left:40px;right:40px;bottom:150px") if campaign else ""
    burst_b, rate_b = (296, 306) if campaign else (210, 172)   # ยกป้ายราคา/เรตติ้งขึ้นเมื่อมีแคมเปญ
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{common}
    .scrim{{position:absolute;inset:0;background:
      linear-gradient(180deg,rgba(0,0,0,.55) 0%,transparent 24%,transparent 68%,rgba(0,0,0,.72) 100%)}}
    .ctitle{{position:absolute;top:64px;left:0;right:0;text-align:center;
      font-family:'Kanit';font-weight:900;font-size:120px;line-height:.9;color:#ffd53a;
      -webkit-text-stroke:8px #7a0010;paint-order:stroke fill;transform:rotate(-2deg);
      filter:drop-shadow(4px 6px 0 #000) drop-shadow(0 12px 14px rgba(0,0,0,.55));
      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;padding:0 40px}}
    .ribbon{{position:absolute;top:340px;left:50%;transform:translateX(-50%) rotate(-1deg);
      background:#e11d2a;color:#fff;font-weight:700;font-size:40px;padding:10px 46px;border-radius:12px;
      border:3px solid #fff;box-shadow:0 8px 20px rgba(0,0,0,.4);white-space:nowrap}}
    .burst{{position:absolute;bottom:{burst_b}px;right:44px;width:300px;height:300px;transform:rotate(9deg);
      background:url('{burst}') center/contain no-repeat;display:flex;flex-direction:column;
      align-items:center;justify-content:center;color:#fff;filter:drop-shadow(0 12px 16px rgba(0,0,0,.45))}}
    .burst .bk{{font-weight:600;font-size:30px;margin-bottom:-6px}}
    .burst .bv{{font-family:'Kanit';font-weight:900;font-size:76px;line-height:1;letter-spacing:-1px}}
    .rate{{position:absolute;bottom:{rate_b}px;left:40px;padding:12px 22px;border-radius:100px;font-weight:700;
      font-size:32px;color:#fff;display:flex;gap:10px;align-items:center}}
    .cta{{position:absolute;left:0;right:0;bottom:0;height:140px;
      background:linear-gradient(90deg,#c1121f,#e11d2a);border-top:8px solid #ffd53a;
      display:flex;align-items:center;justify-content:center;
      color:#fff;font-family:'Kanit';font-weight:800;font-size:46px}}
    </style></head><body>
      <img class="photo" src="{uri}">
      <div class="scrim"></div><div class="grain"></div>
      <div class="ctitle">{name}</div>
      <div class="ribbon">{sub} · {area}</div>
      <div class="rate chip"><span class="gold" style="font-size:26px;letter-spacing:2px">{_stars(rating)}</span>{rating}</div>
      {price_html}
      {camp}
      <div class="cta">สั่งเลย · ลิงก์ใต้โพสต์ ↓</div>
    </body></html>"""


def _tpl_cinematic(uri, name, kicker, hk, rating, price, common) -> str:
    price_block = (f'<div class="price"><span class="pk">เริ่มต้น</span>'
                   f'<span class="pv gold">{price}<span class="pb">.-</span></span></div>') if price else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{common}
    .scrim{{position:absolute;inset:0;background:
      linear-gradient(180deg,rgba(8,6,4,.72) 0%,rgba(8,6,4,0) 26%,rgba(8,6,4,0) 40%,rgba(8,6,4,.62) 66%,rgba(8,6,4,.96) 100%),
      radial-gradient(120% 80% at 50% 120%,rgba(120,70,20,.35),transparent 60%)}}
    .top{{position:absolute;top:46px;left:46px;right:46px;display:flex;justify-content:space-between;align-items:flex-start}}
    .tag{{padding:12px 22px;border-radius:100px;font-weight:700;font-size:26px;letter-spacing:.5px;color:#1a140a;
      background:linear-gradient(180deg,#fbe89b,#e7bd52);box-shadow:0 8px 24px rgba(0,0,0,.4)}}
    .rate{{padding:12px 20px;border-radius:100px;font-weight:700;font-size:30px;color:#fff;display:flex;gap:10px;align-items:center}}
    .rate .st{{font-size:26px;letter-spacing:2px}}
    .wrap{{position:absolute;left:56px;right:56px;bottom:60px}}
    .kick{{font-weight:600;font-size:28px;letter-spacing:6px;text-transform:uppercase;
      color:#f4d879;margin-bottom:14px;text-shadow:0 2px 10px rgba(0,0,0,.6)}}
    .name{{font-weight:900;font-size:96px;line-height:.98;color:#fff;letter-spacing:-1px;
      text-shadow:0 6px 30px rgba(0,0,0,.7);margin-bottom:8px}}
    .hook{{font-family:'Prompt';font-weight:500;font-size:34px;color:#ece3d4;
      margin-top:16px;text-shadow:0 2px 12px rgba(0,0,0,.8);max-width:820px}}
    .bar{{margin-top:34px;display:flex;align-items:center;gap:26px}}
    .price{{display:flex;flex-direction:column;line-height:1}}
    .pk{{font-weight:500;font-size:26px;color:#d8cbb2;letter-spacing:1px}}
    .pv{{font-weight:900;font-size:104px;letter-spacing:-2px;filter:drop-shadow(0 4px 14px rgba(0,0,0,.5))}}
    .pb{{font-size:46px}}
    .cta{{flex:1;text-align:center;padding:26px;border-radius:100px;font-weight:800;font-size:38px;color:#1a140a;
      background:linear-gradient(180deg,#ffe89a,#eec25a 55%,#d59f36);
      box-shadow:0 14px 40px rgba(214,175,55,.45),inset 0 2px 3px rgba(255,255,255,.6)}}
    </style></head><body>
      <img class="photo" src="{uri}">
      <div class="scrim"></div><div class="grain"></div><div class="vignette"></div>
      <div class="top">
        <div class="tag">{kicker}</div>
        <div class="rate chip"><span class="st gold">{_stars(rating)}</span>{rating}</div>
      </div>
      <div class="wrap">
        <div class="kick">ร้านนี้ต้องลอง</div>
        <div class="name">{name}</div>
        {f'<div class="hook">{hk}</div>' if hk else ''}
        <div class="bar">
          {price_block}
          <div class="cta">สั่งเลย · ลิงก์ใต้โพสต์ ↓</div>
        </div>
      </div>
    </body></html>"""


def _tpl_editorial(uri, name, kicker, hk, rating, price, common) -> str:
    """ครึ่งบนรูป · ครึ่งล่างการ์ดครีม สไตล์นิตยสาร."""
    price_block = (f'<div class="pk">ราคาเริ่มต้น</div><div class="pv gold">{price}<span>.-</span></div>') if price else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{common}
    body{{background:#14110d}}
    .ph{{position:absolute;top:0;left:0;right:0;height:790px;overflow:hidden}}
    .ph img{{width:100%;height:100%;object-fit:cover}}
    .ph .fade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,8,6,.5),transparent 30%,transparent 62%,rgba(20,17,13,1) 100%)}}
    .tag{{position:absolute;top:46px;left:46px;padding:12px 22px;border-radius:100px;font-weight:700;font-size:26px;
      color:#1a140a;background:linear-gradient(180deg,#fbe89b,#e7bd52);box-shadow:0 8px 24px rgba(0,0,0,.45)}}
    .rate{{position:absolute;top:44px;right:46px;padding:12px 20px;border-radius:100px;font-weight:700;font-size:30px;
      color:#fff;display:flex;gap:10px;align-items:center}}
    .card{{position:absolute;left:0;right:0;bottom:0;height:560px;padding:56px 60px 60px;
      background:linear-gradient(180deg,#14110d,#1c1712)}}
    .kick{{font-weight:600;font-size:26px;letter-spacing:6px;text-transform:uppercase;color:#f4d879;margin-bottom:16px}}
    .name{{font-weight:900;font-size:82px;line-height:.98;color:#fff;letter-spacing:-1px}}
    .rule{{height:3px;width:120px;margin:26px 0;background:linear-gradient(90deg,#f4d879,transparent)}}
    .hook{{font-family:'Prompt';font-weight:500;font-size:32px;color:#cfc4b2;max-width:760px}}
    .foot{{position:absolute;left:60px;right:60px;bottom:56px;display:flex;align-items:flex-end;justify-content:space-between}}
    .pk{{font-weight:500;font-size:24px;color:#b7ab95}}
    .pv{{font-weight:900;font-size:96px;line-height:.9;letter-spacing:-2px}} .pv span{{font-size:42px}}
    .cta{{padding:24px 40px;border-radius:100px;font-weight:800;font-size:34px;color:#1a140a;
      background:linear-gradient(180deg,#ffe89a,#eec25a 55%,#d59f36);box-shadow:0 14px 36px rgba(214,175,55,.4)}}
    </style></head><body>
      <div class="ph"><img src="{uri}"><div class="fade"></div></div>
      <div class="tag">{kicker}</div>
      <div class="rate"><span class="gold" style="font-size:26px;letter-spacing:2px">{_stars(rating)}</span>{rating}</div>
      <div class="card">
        <div class="kick">เมนูแนะนำ</div>
        <div class="name">{name}</div>
        <div class="rule"></div>
        {f'<div class="hook">{hk}</div>' if hk else ''}
        <div class="foot">
          <div>{price_block}</div>
          <div class="cta">สั่งเลย ↓</div>
        </div>
      </div>
    </body></html>"""


def _tpl_magazine(uri, name, kicker, hk, rating, price, common) -> str:
    """แถบทองพาดเฉียง + ตัวเลขราคายักษ์ (โปสเตอร์โปรแรงๆ)."""
    price_block = (f'<div class="big gold">{price}<span>.-</span></div>') if price else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{common}
    .scrim{{position:absolute;inset:0;background:
      linear-gradient(90deg,rgba(8,6,4,.9) 0%,rgba(8,6,4,.35) 45%,transparent 70%),
      linear-gradient(0deg,rgba(8,6,4,.9),transparent 40%)}}
    .ribbon{{position:absolute;top:120px;left:-60px;transform:rotate(-6deg);padding:14px 90px;
      background:linear-gradient(180deg,#fbe89b,#dca843);color:#1a140a;font-weight:800;font-size:32px;
      letter-spacing:2px;box-shadow:0 12px 30px rgba(0,0,0,.5)}}
    .wrap{{position:absolute;left:60px;right:60px;bottom:70px}}
    .kick{{font-weight:600;font-size:26px;letter-spacing:6px;text-transform:uppercase;color:#f4d879;margin-bottom:12px}}
    .name{{font-weight:900;font-size:88px;line-height:.96;color:#fff;letter-spacing:-1px;text-shadow:0 6px 26px rgba(0,0,0,.7)}}
    .hook{{font-family:'Prompt';font-weight:500;font-size:32px;color:#e6dccb;margin-top:18px;max-width:720px;text-shadow:0 2px 10px rgba(0,0,0,.8)}}
    .big{{font-weight:900;font-size:150px;line-height:.85;letter-spacing:-4px;margin-top:20px;filter:drop-shadow(0 6px 18px rgba(0,0,0,.55))}}
    .big span{{font-size:60px}}
    .cta{{display:inline-block;margin-top:16px;padding:24px 50px;border-radius:100px;font-weight:800;font-size:36px;color:#1a140a;
      background:linear-gradient(180deg,#ffe89a,#eec25a 55%,#d59f36);box-shadow:0 14px 40px rgba(214,175,55,.45)}}
    .rate{{position:absolute;top:44px;right:46px;padding:12px 20px;border-radius:100px;font-weight:700;font-size:30px;color:#fff;display:flex;gap:10px;align-items:center}}
    </style></head><body>
      <img class="photo" src="{uri}">
      <div class="scrim"></div><div class="grain"></div><div class="vignette"></div>
      <div class="ribbon">เมนูเด็ด · ห้ามพลาด</div>
      <div class="rate chip"><span class="gold" style="font-size:26px;letter-spacing:2px">{_stars(rating)}</span>{rating}</div>
      <div class="wrap">
        <div class="kick">{kicker}</div>
        <div class="name">{name}</div>
        {f'<div class="hook">{hk}</div>' if hk else ''}
        {f'<div style="font-weight:500;font-size:26px;color:#d8cbb2;margin-top:22px">เริ่มต้นเพียง</div>{price_block}' if price else ''}
        <div class="cta">สั่งเลย · ลิงก์ใต้โพสต์ ↓</div>
      </div>
    </body></html>"""


# ---------------------------------------------------------------- render engine
def render_to_png(html: str, out_path: str, scale: int = 2) -> str | None:
    """เรนเดอร์ HTML → PNG ขนาด 1080x1350 (คมที่ scale=2 → ไฟล์ 2160x2700)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--force-color-profile=srgb"], **kw)
                break
            except Exception:
                continue
        if not browser:
            return None
        try:
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
            page.set_content(html, wait_until="networkidle")
            try:
                page.evaluate("document.fonts.ready")
            except Exception:
                pass
            page.wait_for_timeout(900)   # ให้ฟอนต์/เอฟเฟกต์ settle
            page.screenshot(path=out_path)
            return out_path
        finally:
            browser.close()


def make_promo_pro(store, photo_path: str, hook: str = "", style: str = "cinematic") -> str | None:
    """สร้างโปสเตอร์ระดับดีไซน์ → คืน path (None ถ้าทำไม่ได้)."""
    if not (photo_path and os.path.exists(photo_path)):
        return None
    uri = _data_uri(photo_path)
    if not uri:
        return None
    html = build_poster_html(store, uri, hook, style)
    os.makedirs(settings.media_dir, exist_ok=True)
    out = os.path.join(settings.media_dir, f"promo_{store.id}_{uuid.uuid4().hex[:6]}.png")
    try:
        return render_to_png(html, out, scale=2)
    except Exception as e:  # pragma: no cover
        print(f"[promo_html] render fail store {getattr(store,'id','?')}: {str(e)[:80]}")
        return None
