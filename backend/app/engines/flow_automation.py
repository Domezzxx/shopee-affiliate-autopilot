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
        
        # 4) Locate prompt input (Slate editor [role='textbox'])
        print(f"[flow-auto] Locating prompt input using selector: {settings.flow_selector_input}")
        input_locator = page.locator(settings.flow_selector_input).first
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

        # ตรวจว่าพิมพ์เข้าจริง — ถ้าช่องว่าง ลองวิธีสำรอง (fill / type) ก่อนยอมแพ้
        def _entered() -> str:
            try:
                return (input_locator.inner_text(timeout=2000) or "").strip()
            except Exception:
                return ""
        if not _entered():
            print("[flow-auto] insertText ไม่เข้า → ลอง fill/type สำรอง")
            try:
                input_locator.click()
                input_locator.fill(prompt)
            except Exception:
                page.keyboard.type(prompt, delay=15)
            time.sleep(0.8)
        if not _entered():
            raise RuntimeError("พิมพ์ prompt เข้า Google Flow ไม่ได้ (ช่องว่าง) — selector input อาจเปลี่ยน")
        print(f"[flow-auto] ✓ prompt ในช่องแล้ว: {_entered()[:50]}")

        # เก็บรายการวีดีโอ "เดิม" ในโปรเจกต์ ก่อนกด Generate → จะได้รู้ว่าตัวไหนคือตัวใหม่
        existing_srcs = page.locator("video").evaluate_all("els => els.map(e => e.src).filter(Boolean)")
        existing_names = {_media_name(s) for s in existing_srcs if _media_name(s)}
        print(f"[flow-auto] วีดีโอเดิมในโปรเจกต์: {len(existing_names)} ตัว")
        
        # 5) Locate and click Generate button
        print(f"[flow-auto] Locating generate button using selector: {settings.flow_selector_generate}")
        gen_btn = page.locator(settings.flow_selector_generate).first
        gen_btn.wait_for(state="visible", timeout=5000)
        
        # Wait until it is enabled (not aria-disabled="true")
        print("[flow-auto] Waiting for generate button to be enabled...")
        for _ in range(10):
            aria_disabled = gen_btn.evaluate("el => el.getAttribute('aria-disabled')")
            if aria_disabled != "true":
                break
            time.sleep(0.5)
            
        print("[flow-auto] Clicking Generate button...")
        try:
            gen_btn.click()
        except Exception as e:
            print(f"[flow-auto] คลิกปุ่ม Generate ไม่ได้ ({str(e)[:50]})")
        time.sleep(1.5)

        # ตรวจว่า submit สำเร็จ (ช่อง prompt ควรเคลียร์) — ถ้ายังค้าง = ยังไม่ส่ง → กด Enter ในช่อง
        if _entered():
            print("[flow-auto] prompt ยังค้างในช่อง → ลอง submit ด้วย Enter")
            try:
                input_locator.click()
                page.keyboard.press("Enter")
            except Exception:
                pass
            time.sleep(1.5)
        if _entered():
            # prompt ยังค้าง = submit ไม่ทำงาน (ปุ่ม Generate ของ Flow เปลี่ยน/หาไม่เจอ)
            # → fail เร็ว ไม่ค้าง 4 นาที + ไม่หยิบวีดีโอเก่ามาแทน (ให้ media_gemini fallback)
            raise RuntimeError("Google Flow ไม่ submit (prompt ค้างในช่อง) — ปุ่ม Generate หาไม่เจอ/UI เปลี่ยน")
        print("[flow-auto] ✓ submit สำเร็จ (ช่อง prompt ว่างแล้ว)")

        # 6) Wait for and click Approve button (อนุมัติ)
        # Google Flow presents the generated video in the sidebar and requires approval.
        print("[flow-auto] Waiting for Approve button...")
        approve_selectors = [
            "div:has-text('อนุมัติ ไม่ต้องถามอีก')",
            "div:has-text('อนุมัติ')",
            "div:has-text('Approve')",
            "button:has-text('อนุมัติ')",
            "button:has-text('Approve')"
        ]
        
        approved = False
        # Poll for approve button (up to 4 minutes)
        for _ in range(48):
            for sel in approve_selectors:
                el = page.locator(sel).first
                if el.is_visible():
                    print(f"[flow-auto] Found Approve button: '{sel}'. Clicking...")
                    el.click()
                    approved = True
                    break
            if approved:
                break
            time.sleep(5)
            
        # 7) รอวีดีโอ "ใหม่" (src ไม่ซ้ำของเดิม) — กันบั๊กหยิบวีดีโอเก่าตัวแรกมา
        print("[flow-auto] Waiting for NEW video to generate (up to ~6 นาที)...")
        video_url = ""
        for i in range(120):   # ~4 นาที
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
