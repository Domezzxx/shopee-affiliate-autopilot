# -*- coding: utf-8 -*-
"""End-to-end image-to-video ใน Google Flow: อัปรูป product จริง → แนบเข้า prompt → generate → โหลด mp4.

รัน:  venv\\Scripts\\python.exe scripts\\flow_img2video.py <image.jpg> "<prompt>"
"""
import os, re, sys, time, base64
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "products", "test_boatnoodle.jpg")
PROMPT = sys.argv[2] if len(sys.argv) > 2 else (
    "Animate this real bowl of Thai boat noodles into a cinematic vertical 9:16 food clip: "
    "steam rising, broth gently simmering, chopsticks lifting noodles, warm appetizing light, subtle handheld motion")


def media_name(s):
    m = re.search(r"name=([^&#]+)", s or ""); return m.group(1) if m else ""


def click_text(page, text, exact=True, right_most=True):
    """กดข้อความด้วย mouse จริง (trusted) — exact หรือ contains, เลือกตัวขวาสุด/ในจอ."""
    box = page.evaluate(r"""(args) => {
      const [txt, exact] = args;
      const c=[...document.querySelectorAll('button,[role=button],[role=menuitem],div,span,li')]
        .map(el=>({el,t:(el.innerText||'').trim(),r:el.getBoundingClientRect()}))
        .filter(o=>(exact? o.t===txt : o.t.includes(txt)) && o.r.width>5 && o.r.height>5
                   && o.r.top>=0 && o.r.top<window.innerHeight);
      if(!c.length) return null;
      c.sort((a,b)=> (b.r.x-a.r.x) || (b.r.y-a.r.y));
      const r=c[0].r; return {x:r.x+r.width/2, y:r.y+r.height/2};
    }""", [text, exact])
    if not box:
        return False
    page.mouse.move(box["x"], box["y"]); time.sleep(0.1)
    page.mouse.click(box["x"], box["y"])
    return True


def main():
    print(f"[i2v] รูป: {IMG}\n[i2v] prompt: {PROMPT[:70]}...")
    pw = sync_playwright().start()
    b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    page = next((p for p in ctx.pages if "flow" in p.url or "labs.google" in p.url), None)
    page.bring_to_front()
    page.keyboard.press("Escape"); time.sleep(0.5)

    # วีดีโอเดิม (ไว้เทียบหาตัวใหม่)
    before = page.locator("video").evaluate_all("els=>els.map(e=>e.src).filter(Boolean)")
    before_names = {media_name(s) for s in before if media_name(s)}
    print(f"[i2v] วีดีโอเดิม: {len(before_names)}")

    # 1) อัปโหลดรูป product
    page.locator("input[type='file']").first.set_input_files(IMG)
    fname = os.path.basename(IMG)
    print(f"[i2v] อัปโหลด {fname} ...")
    time.sleep(3)

    # 2) เปิดเมนู '+' (add_2) ในแถบ composer
    if not click_text(page, "add_2", exact=False):
        # fallback: หาไอคอน add ตัวล่างสุด
        click_text(page, "add", exact=False)
    time.sleep(1.5)

    # 3) เลือกรูปที่เพิ่งอัป (คลิกชื่อไฟล์ถ้ามี) แล้วกด 'เพิ่มไปยังพรอมต์'
    click_text(page, fname, exact=False); time.sleep(0.8)
    if click_text(page, "เพิ่มไปยังพรอมต์", exact=True):
        print("[i2v] ✅ แนบรูปเข้า prompt แล้ว")
    else:
        page.screenshot(path=os.path.join(ROOT, "data", "i2v_attach_fail.png"))
        print("[i2v] ❌ แนบรูปไม่ติด — ยกเลิก ไม่ submit (กันเสียเครดิต) ดู data/i2v_attach_fail.png")
        pw.stop(); return 2
    time.sleep(1.0)

    # ยืนยันว่ามี 'ชิปรูป' ติดอยู่ในแถบ prompt ก่อน submit
    has_chip = page.evaluate("() => [...document.querySelectorAll('img')].some(i=>{const r=i.getBoundingClientRect(); return r.top>550 && r.width>20 && r.width<160;})")
    print(f"[i2v] มีชิปรูปในแถบ prompt: {has_chip}")

    # 4) พิมพ์ prompt ลงช่องที่มองเห็น
    vis_idx = page.evaluate(r"""() => {
      const t=[...document.querySelectorAll("[role='textbox'],textarea")];
      for(let i=0;i<t.length;i++){const r=t[i].getBoundingClientRect(); if(r.width>10&&r.height>10) return i;}
      return 0;
    }""")
    box = page.locator("[role='textbox'], textarea").nth(vis_idx)
    box.click()
    page.keyboard.press("Control+A"); page.keyboard.press("Delete"); time.sleep(0.3)
    page.keyboard.insert_text(PROMPT)
    print("[i2v] พิมพ์ prompt แล้ว")
    time.sleep(0.8)

    # 5) submit (Enter)
    page.keyboard.press("Enter")
    print("[i2v] กด Enter ส่ง")
    time.sleep(3)

    # 6) อนุมัติเครดิต (trusted click 'อนุมัติ' หลายรอบ เผื่อ dialog โผล่ช้า)
    approved = False
    for _ in range(8):
        if click_text(page, "อนุมัติ", exact=True):
            approved = True; print("[i2v] กด 'อนุมัติ' (trusted)")
            time.sleep(1.5)
        # เช็คว่าเริ่มสร้าง/เข้าคิว
        scheduled = page.evaluate("() => /scheduled|queue|กำลังสร้าง|high demand|กำลังประมวล/i.test(document.body.innerText)")
        if scheduled:
            print("[i2v] ✅ เริ่ม generate / เข้าคิวแล้ว"); break
        time.sleep(1.5)

    # 7) รอวีดีโอใหม่ (นานสุด ~10 นาที เพราะอาจเข้าคิว)
    print("[i2v] รอวีดีโอใหม่ (สูงสุด ~10 นาที)...")
    url = ""
    for i in range(300):
        try:
            srcs = page.locator("video").evaluate_all("els=>els.map(e=>e.src).filter(Boolean)")
        except Exception:
            time.sleep(2); continue
        new = [s for s in srcs if "media.getMediaUrlRedirect" in s
               and media_name(s) and media_name(s) not in before_names]
        if new:
            url = new[-1]; break
        if i % 15 == 0:
            print(f"[i2v] ...รออยู่ {i*2}s (วีดีโอในจอ {len(srcs)})")
        time.sleep(2)

    if not url:
        page.screenshot(path=os.path.join(ROOT, "data", "i2v_timeout.png"))
        print("[i2v] ⚠️ ยังไม่ได้วีดีโอใน 10 นาที (ดู data/i2v_timeout.png)"); pw.stop(); return 1

    # 8) โหลดวีดีโอ
    print(f"[i2v] ✓ ได้วีดีโอใหม่: {url[:80]}")
    data_url = page.evaluate("""async (u) => {
        const r = await fetch(u); const blob = await r.blob();
        return await new Promise((res,rej)=>{const fr=new FileReader();fr.onloadend=()=>res(fr.result);fr.onerror=rej;fr.readAsDataURL(blob);});
    }""", url)
    enc = data_url.split(",", 1)[1]
    vid = base64.b64decode(enc)
    out = os.path.join(ROOT, "data", "media", f"i2v_{int(time.time())}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(vid)
    ok = len(vid) > 10000
    print(f"[i2v] {'✅ สำเร็จ' if ok else '⚠️'} โหลดแล้ว: {out} ({len(vid)} bytes)")
    pw.stop()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
