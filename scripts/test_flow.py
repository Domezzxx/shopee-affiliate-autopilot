# -*- coding: utf-8 -*-
"""ทดสอบว่า Google Flow automation รันได้จริง.

ขั้น 1: เปิด Chrome debug (9222) + เช็คว่าล็อกอิน Flow อยู่ไหม
ขั้น 2: ถ้า --run จะยิง generate วีดีโอจริง 1 คลิป (กินเครดิต) แล้วยืนยันว่าได้ไฟล์ mp4

รัน:  venv\\Scripts\\python.exe scripts\\test_flow.py            # เช็ค login อย่างเดียว
     venv\\Scripts\\python.exe scripts\\test_flow.py --run      # ยิง generate จริง
"""
import os
import sys
import socket
import subprocess
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

from playwright.sync_api import sync_playwright


def is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(("127.0.0.1", port))
            return True
    except Exception:
        return False


def launch_chrome():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    exe = next((p for p in paths if os.path.exists(p)), None)
    if not exe:
        print("[test] ไม่เจอ chrome.exe"); return False
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profile = os.path.join(root, "data", "chrome_profile")
    args = [exe, "--remote-debugging-port=9222", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check",
            "https://labs.google/fx/tools/flow"]
    print("[test] เปิด Chrome debug (profile เดิม)...")
    subprocess.Popen(args, creationflags=0x00000008 if os.name == "nt" else 0)
    for _ in range(15):
        time.sleep(1)
        if is_port_open(9222):
            print("[test] port 9222 เปิดแล้ว")
            return True
    print("[test] port 9222 ไม่เปิด")
    return False


def check_login():
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = None
        for p in ctx.pages:
            if "labs.google" in p.url or "flow" in p.url:
                page = p; break
        if not page:
            page = ctx.new_page()
            page.goto("https://labs.google/fx/tools/flow", wait_until="domcontentloaded", timeout=60000)
        # ให้เวลาโหลด UI
        for _ in range(15):
            time.sleep(1)
            try:
                body = page.evaluate("() => document.body.innerText")
            except Exception:
                body = ""
            # มีช่องพิมพ์ prompt มองเห็น = ล็อกอิน + เข้า editor ได้
            tb = page.evaluate("""() => {
              const t=[...document.querySelectorAll("[role='textbox'],textarea")];
              return t.some(e=>{const r=e.getBoundingClientRect(); return r.width>10&&r.height>10;});
            }""")
            signed_out = any(k in body for k in ["ลงชื่อเข้าใช้", "Sign in", "เข้าสู่ระบบ", "Sign in to"])
            if tb:
                print(f"[test] ✅ ล็อกอินอยู่ + เจอช่องพิมพ์ prompt (url={page.url})")
                return "ready"
            if signed_out:
                print(f"[test] ⚠️ ยังไม่ได้ล็อกอิน (เจอปุ่ม Sign in) — ล็อกอินใน Chrome ที่เพิ่งเปิด แล้วรันใหม่")
                return "login"
        print(f"[test] ❓ ไม่แน่ใจสถานะ (url={page.url}) — เปิด Chrome ดูด้วยตา")
        return "unknown"
    finally:
        try: pw.stop()
        except Exception: pass


def main():
    do_run = "--run" in sys.argv
    if not is_port_open(9222):
        if not launch_chrome():
            print("[test] เปิด Chrome ไม่สำเร็จ"); return 2
    else:
        print("[test] port 9222 เปิดอยู่แล้ว")

    state = check_login()
    if state != "ready":
        print("[test] หยุดก่อน — ต้องล็อกอิน Flow ให้เรียบร้อยก่อนทดสอบยิงจริง")
        return 1

    if not do_run:
        print("[test] login OK. ใส่ --run เพื่อยิง generate วีดีโอจริง")
        return 0

    print("[test] === ยิง generate วีดีโอจริง ===")
    from app.engines.flow_automation import generate_video_flow
    t0 = time.time()
    prompt = ("Cinematic vertical 9:16 food review b-roll: steaming Thai boat noodles "
              "in a bowl, close steam rising, warm light, handheld, appetizing")
    path = generate_video_flow(prompt)
    dt = round(time.time() - t0, 1)
    ok = path and os.path.exists(path) and os.path.getsize(path) > 10000
    print(f"[test] {'✅ สำเร็จ' if ok else '⚠️ ล้มเหลว'} ใช้เวลา {dt}s · ไฟล์: {path}"
          + (f" ({os.path.getsize(path)} bytes)" if ok else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
