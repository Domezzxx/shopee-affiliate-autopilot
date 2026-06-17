import os
import re
import time
import uuid
import base64
from playwright.sync_api import sync_playwright
from ..config import settings


def _media_name(src: str) -> str:
    """ดึง media name จาก url (...?name=XXXX#t=8.89) — เทียบตัวนี้ ไม่ใช่ทั้ง url ที่มี #fragment เปลี่ยน."""
    m = re.search(r"name=([^&#]+)", src or "")
    return m.group(1) if m else ""

def generate_video_flow(prompt: str) -> str:
    """
    Generate video short 9:16 using Google Flow web app via Playwright CDP.
    Returns the absolute path of the downloaded mp4 file.
    """
    print(f"[flow-auto] Starting Google Flow video generation for prompt: {prompt}")
    
    # 1) Connect to Chrome CDP
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(settings.flow_cdp_url)
    except Exception as e:
        pw.stop()
        print(f"[flow-auto] Connection failed: {e}")
        raise RuntimeError(
            f"Cannot connect to Chrome at {settings.flow_cdp_url}. "
            "Please ensure Chrome is running with remote debugging: "
            "chrome.exe --remote-debugging-port=9222"
        ) from e

    try:
        context = browser.contexts[0]
        page = None
        
        # 2) Find existing tab
        for p in context.pages:
            if "labs.google" in p.url or "flow" in p.url:
                page = p
                print(f"[flow-auto] Reusing existing Google Flow tab: {page.url}")
                break
                
        if not page:
            print("[flow-auto] Opening new tab for Google Flow...")
            page = context.new_page()
            page.goto("https://labs.google/fx/th/tools/flow", timeout=60000)
        
        page.wait_for_load_state("load", timeout=20000)
        
        # 3) Handle Dashboard (Click "+ New Project" / "โปรเจ็กต์ใหม่" if present)
        new_proj_selectors = [
            "button:has-text('โปรเจ็กต์ใหม่')",
            "button:has-text('โปรเจกต์ใหม่')",
            "button:has-text('New project')",
            "button:has-text('project')",
            "button:has-text('+')"
        ]
        
        for sel in new_proj_selectors:
            btn = page.locator(sel).first
            if btn.is_visible():
                print(f"[flow-auto] Dashboard detected. Clicking '{sel}'...")
                btn.click()
                time.sleep(5)  # Wait for project editor to load
                break
        
        # 4) Locate prompt input — ต้องเป็น textbox ที่ "มองเห็นจริง" (Flow มี textbox ซ่อน x=0
        #    ถ้าใช้ .first/.last จะโดนตัวซ่อน → พิมพ์ไม่ลง → ปุ่ม Generate ไม่ enable)
        vis_idx = page.evaluate("""() => {
          const tbs=[...document.querySelectorAll("[role='textbox'],textarea")];
          for(let i=0;i<tbs.length;i++){const r=tbs[i].getBoundingClientRect(); if(r.width>10&&r.height>10) return i;}
          return 0;
        }""")
        input_locator = page.locator("[role='textbox'], textarea").nth(vis_idx)
        input_locator.wait_for(state="visible", timeout=15000)

        # Focus + clear
        input_locator.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        time.sleep(0.4)

        # พิมพ์ด้วย insertText (ทำงานกับ Slate/contenteditable ได้ ต่างจาก keyboard.type ที่ไม่เข้า)
        print(f"[flow-auto] Typing prompt: {prompt[:60]}")
        page.keyboard.insert_text(prompt)
        time.sleep(0.8)

        # หมายเหตุ: inner_text ของ editor นี้อ่านไม่นิ่ง → ไม่เช็คเข้ม ใช้ "มีวีดีโอใหม่" เป็นตัวยืนยันแทน
        print(f"[flow-auto] พิมพ์ prompt แล้ว: {prompt[:50]}")

        # เก็บรายการวีดีโอ "เดิม" ก่อนกด Generate → จะได้รู้ว่าตัวไหนใหม่
        existing_srcs = page.locator("video").evaluate_all("els => els.map(e => e.src).filter(Boolean)")
        existing_names = {_media_name(s) for s in existing_srcs if _media_name(s)}
        print(f"[flow-auto] วีดีโอเดิมในโปรเจกต์: {len(existing_names)} ตัว")

        # 5) ส่งด้วย Enter (ทดสอบแล้วว่าช่องเคลียร์ = ส่งสำเร็จ — ปุ่มต่างๆ ไม่ trigger generate จริง)
        print("[flow-auto] ส่ง prompt (Enter)...")
        page.keyboard.press("Enter")
        time.sleep(3)

        # 6) จัดการ Approve ถ้ามี (โผล่บางครั้ง — เช็คเร็วๆ ไม่บล็อก)
        for _ in range(4):
            clicked = False
            for sel in ["div:has-text('อนุมัติ ไม่ต้องถามอีก')", "div:has-text('อนุมัติ')",
                        "button:has-text('อนุมัติ')", "button:has-text('Approve')"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        el.click(); clicked = True; print("[flow-auto] คลิก Approve"); break
                except Exception:
                    pass
            if clicked:
                break
            time.sleep(1.5)

        # 7) รอวีดีโอ "ใหม่" (src ไม่ซ้ำของเดิม) — กันบั๊กหยิบวีดีโอเก่าตัวแรกมา
        print("[flow-auto] Waiting for NEW video to generate (up to ~6 นาที)...")
        video_url = ""
        for i in range(150):   # ~5 นาที (Veo generate 2-5 นาที) — เกินนี้ fallback
            try:
                srcs = page.locator("video").evaluate_all("els => els.map(e => e.src).filter(Boolean)")
            except Exception as e:
                # page navigate/หลุด → หา Flow page ใหม่จาก context (กัน Target closed)
                print(f"[flow-auto] page หลุดชั่วคราว ({str(e)[:40]}) → re-acquire")
                try:
                    page = next((p for p in context.pages
                                 if "flow" in p.url or "labs.google" in p.url), page)
                except Exception:
                    pass
                time.sleep(2)
                continue
            # เทียบที่ media NAME (ไม่ใช่ทั้ง url ที่มี #fragment) → ได้วีดีโอใหม่จริง
            new = [s for s in srcs
                   if "media.getMediaUrlRedirect" in s and _media_name(s) and _media_name(s) not in existing_names]
            if new:
                video_url = new[-1]
                break
            # ตรวจจับข้อความล้มเหลว/เครดิตหมด ของ Flow assistant → fail เร็ว บอกสาเหตุชัด
            if i % 4 == 0:
                try:
                    body = page.evaluate("() => document.body.innerText")
                    if any(k in body for k in ["เกินโควตา", "เครดิตไม่เพียงพอ", "เครดิต AI เพิ่มเติม",
                                               "insufficient", "quota", "out of credit"]):
                        raise RuntimeError("เครดิต/โควตา Google Flow หมด — รอรีเซ็ต หรือเติมเครดิต (ดู labs.google/flow)")
                except RuntimeError:
                    raise
                except Exception:
                    pass
            if i % 15 == 0:    # log ทุก ~30 วิ ให้รู้ว่ายังรออยู่
                print(f"[flow-auto] ...รอวีดีโอใหม่ (มีในจอ {len(srcs)} ตัว, ยังไม่มีตัวใหม่) {i*2}s")
            time.sleep(2)

        if not video_url:
            raise RuntimeError("Timeout รอวีดีโอใหม่ — generate อาจไม่เริ่ม/ไม่เสร็จ (เช็ค prompt เข้าไหม)")

        print(f"[flow-auto] ✓ วีดีโอใหม่ generate เสร็จ: {video_url}")
        
        # 8) Download the video using browser context fetch
        print("[flow-auto] Downloading video via browser context fetch...")
        js_code = """
        async (url) => {
            const resp = await fetch(url);
            const blob = await resp.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }
        """
        base64_data_url = page.evaluate(js_code, video_url)
        
        # Decode base64 bytes
        header, encoded = base64_data_url.split(",", 1)
        video_bytes = base64.b64decode(encoded)
        
        # Save to the media folder
        media_dir = settings.media_dir
        if media_dir == "/app/data/media":
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            media_dir = os.path.join(project_root, "data", "media")
            
        os.makedirs(media_dir, exist_ok=True)
        filename = f"video_flow_{uuid.uuid4().hex[:8]}.mp4"
        dest_path = os.path.join(media_dir, filename)
        
        with open(dest_path, "wb") as f:
            f.write(video_bytes)
            
        print(f"[flow-auto] Video successfully generated and downloaded to: {dest_path} ({len(video_bytes)} bytes)")
        return dest_path
        
    except Exception as e:
        print(f"[flow-auto] Automation error: {e}")
        # Capture screenshot for debugging
        try:
            media_dir = settings.media_dir
            if media_dir == "/app/data/media":
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                media_dir = os.path.join(project_root, "data", "media")
            os.makedirs(media_dir, exist_ok=True)
            scr_path = os.path.join(media_dir, f"error_flow_{uuid.uuid4().hex[:8]}.png")
            page.screenshot(path=scr_path)
            print(f"[flow-auto] Screenshot saved for debugging: {scr_path}")
        except:
            pass
        raise e
    finally:
        # Disconnect CDP connection cleanly without closing the user's Chrome
        try:
            pw.stop()
        except:
            pass
