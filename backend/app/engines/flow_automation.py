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


def _approve_credit(page) -> bool:
    """กดปุ่ม 'อนุมัติ' ยืนยันใช้เครดิตของ Flow.

    สำคัญ: ต้องเป็น element ที่ 'อยู่ในจอ + cursor:pointer' แล้วกดด้วย mouse จริง (trusted event ผ่าน CDP)
    — JS .click() ไม่ติด, และการเลือก label ขวาสุด/นอกจอ (การ์ดเก่าใน history) ก็กดไม่ติด.
    คืน True ถ้าเจอ+กด, False ถ้าไม่มีการ์ดให้อนุมัติ.
    """
    try:
        box = page.evaluate(r"""() => {
          const c=[...document.querySelectorAll('*')].filter(el=>{
            const t=(el.innerText||'').trim();
            if((t!=='อนุมัติ' && t!=='Approve') || el.children.length!==0) return false;
            const r=el.getBoundingClientRect();
            return r.top>=0 && r.top<window.innerHeight && getComputedStyle(el).cursor==='pointer';
          }).map(el=>{const r=el.getBoundingClientRect();
                     return {x:r.x+r.width/2, y:r.y+r.height/2, top:r.top};});
          if(!c.length) return null;
          c.sort((a,b)=>a.top-b.top);   // การ์ดบนสุดในจอ = อันที่รออนุมัติล่าสุด
          return c[0];
        }""")
        if box:
            page.mouse.move(box["x"], box["y"])
            time.sleep(0.15)
            page.mouse.click(box["x"], box["y"])
            print("[flow-auto] กด 'อนุมัติ' (trusted, cursor:pointer ในจอ)")
            return True
    except Exception as e:
        print(f"[flow-auto] approve error: {str(e)[:60]}")
    return False


def _click_text_trusted(page, text: str, exact: bool = True) -> bool:
    """คลิกข้อความบนหน้า Flow ด้วย mouse จริง (trusted) — เลือก element ในจอ, ขวา/ล่างสุด."""
    try:
        box = page.evaluate(
            r"""(args) => {
              const [txt, exact] = args;
              const c=[...document.querySelectorAll('button,[role=button],[role=menuitem],div,span,li')]
                .map(el=>({el, t:(el.innerText||'').trim(), r:el.getBoundingClientRect()}))
                .filter(o=>(exact? o.t===txt : o.t.includes(txt)) && o.r.width>5 && o.r.height>5
                           && o.r.top>=0 && o.r.top<window.innerHeight);
              if(!c.length) return null;
              c.sort((a,b)=> (b.r.x-a.r.x) || (b.r.y-a.r.y));
              const r=c[0].r; return {x:r.x+r.width/2, y:r.y+r.height/2};
            }""",
            [text, exact],
        )
        if box:
            page.mouse.move(box["x"], box["y"])
            time.sleep(0.1)
            page.mouse.click(box["x"], box["y"])
            return True
    except Exception:
        pass
    return False

def generate_video_flow(prompt: str) -> str:
    """
    Generate video short 9:16 using Google Flow web app via Playwright CDP.
    Returns the absolute path of the downloaded mp4 file.
    """
    print(f"[flow-auto] Starting Google Flow video generation for prompt: {prompt}")
    
    # Check if port 9222 is open, if not, attempt to launch Chrome automatically
    import socket
    import subprocess
    
    def is_port_open(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(("127.0.0.1", port))
                return True
        except Exception:
            return False
            
    if not is_port_open(9222):
        print("[flow-auto] Remote debugging port 9222 is closed. Attempting to auto-launch Chrome...")
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
        if chrome_exe:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            profile_dir = os.path.join(project_root, "data", "chrome_profile")
            os.makedirs(profile_dir, exist_ok=True)
            
            args = [
                chrome_exe,
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-sync",
                "--disable-client-side-phishing-detection",
                "--disable-default-apps",
                "--disable-component-update",
                "--disable-hang-monitor",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-logging",
                "--metrics-recording-only",
                "--disable-gpu-shader-disk-cache",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-features=Translate,BackForwardCache,CalculateNativeWinOcclusion,InterestFeedContentSuggestion",
                "https://labs.google/fx/tools/flow"
            ]
            flags = 0x00000008 if os.name == 'nt' else 0
            try:
                subprocess.Popen(args, creationflags=flags)
                print("[flow-auto] Launched Chrome process. Waiting for port 9222 to open...")
                for _ in range(8):
                    time.sleep(1)
                    if is_port_open(9222):
                        print("[flow-auto] Chrome remote debugging port 9222 successfully opened.")
                        break
            except Exception as launch_err:
                print(f"[flow-auto] Failed to auto-launch Chrome process: {launch_err}")

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
            page.goto("https://labs.google/fx/th/tools/flow", wait_until="domcontentloaded", timeout=60000)
        
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        
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
                time.sleep(1)  # Quick yield, wait_for below will handle dynamic loading
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
        
        # รอให้ช่องข้อความว่างลง (แสดงว่ากดส่งสำเร็จแล้ว) แทนที่จะ sleep 3 วินาทีตายตัว
        for _ in range(15):
            try:
                is_empty = page.evaluate(f"""() => {{
                    const el = document.querySelectorAll('[role="textbox"], textarea')[{vis_idx}];
                    return el ? (el.textContent.trim() === '' && el.value === '') : true;
                }}""")
                if is_empty:
                    print("[flow-auto] ช่องข้อความเคลียร์แล้ว (ส่งสำเร็จ)")
                    break
            except Exception:
                pass
            time.sleep(0.2)

        # 6) จัดการ Approve (dialog 'ใช้เครดิต N ไหม') — ลองกดหลายรอบ เผื่อ dialog โผล่ช้า
        for _ in range(6):
            if _approve_credit(page):
                break
            time.sleep(1.0)

        # 7) รอวีดีโอ "ใหม่" (src ไม่ซ้ำของเดิม) — กันบั๊กหยิบวีดีโอเก่าตัวแรกมา
        print("[flow-auto] Waiting for NEW video to generate (up to ~10 นาที, คิวอาจนาน)...")
        video_url = ""
        for i in range(300):   # ~10 นาที (Veo 2-5 นาที + คิว high-demand) — เกินนี้ fallback
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
            
            # กด Approve ทุกรอบ เผื่อ dialog โผล่มากลางทาง (idempotent — ไม่มีก็ข้าม)
            _approve_credit(page)

            # ตรวจจับ 'เครดิต/โควตาหมดจริง' เท่านั้น → พัก Flow + fallback
            # (ไม่ดักคำ transient ทั่วไปอย่าง 'ขออภัย/ข้อผิดพลาด' เพราะ false-positive — คิว 'high demand' = ปกติ ให้รอ)
            if i % 5 == 0:
                try:
                    body = page.evaluate("() => document.body.innerText")
                    quota_keywords = [
                        "เกินโควตา", "เครดิตไม่เพียงพอ", "เครดิต AI เพิ่มเติม", "หมดโควตา",
                        "insufficient credit", "out of credit", "quota exceeded",
                        "reached your limit", "สิทธิ์การใช้งานหมด",
                    ]
                    if any(k in body for k in quota_keywords):
                        try:
                            from ..services import system_state
                            system_state.set_flow_blocked()   # พัก Flow ไม่ยิงซ้ำ (โควตาหมดจริง)
                        except Exception:
                            pass
                        raise RuntimeError("โควตา/เครดิต Google Flow หมด — พัก Flow และใช้ระบบสำรอง")
                except RuntimeError:
                    raise
                except Exception:
                    pass
            if i % 15 == 0:    # log ทุก ~30 วิ ให้รู้ว่ายังรออยู่ (คิว high-demand อาจนาน)
                print(f"[flow-auto] ...รอวีดีโอใหม่ (มีในจอ {len(srcs)} ตัว) {i*2}s")
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


def _ensure_chrome_9222() -> None:
    """เปิด Chrome remote-debugging (9222) ถ้ายังไม่เปิด — ใช้ profile เดิม (ล็อกอิน Flow ค้างไว้)."""
    import socket
    import subprocess

    def is_open(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(("127.0.0.1", port))
                return True
        except Exception:
            return False

    if is_open(9222):
        return
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    exe = next((p for p in paths if os.path.exists(p)), None)
    if not exe:
        return
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    profile = os.path.join(root, "data", "chrome_profile")
    os.makedirs(profile, exist_ok=True)
    args = [exe, "--remote-debugging-port=9222", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check",
            "https://labs.google/fx/tools/flow"]
    try:
        subprocess.Popen(args, creationflags=0x00000008 if os.name == "nt" else 0)
        for _ in range(12):
            time.sleep(1)
            if is_open(9222):
                break
    except Exception as e:
        print(f"[flow-img] launch chrome failed: {e}")


def generate_video_from_image(image_path: str, prompt: str) -> str:
    """Image-to-video: เอารูป product จริง → Google Flow → วีดีโอ 9:16 ที่ 'ตรงเมนูจริง'.

    ขั้นตอน: อัปรูปเข้า Flow → '+' แนบรูปเข้า prompt ('เพิ่มไปยังพรอมต์') → พิมพ์ prompt →
    Enter → อนุมัติเครดิต (trusted) → รอวีดีโอใหม่ → โหลด .mp4. คืน path ของไฟล์.
    """
    if not image_path or not os.path.exists(image_path):
        raise RuntimeError(f"ไม่พบไฟล์รูป: {image_path}")
    print(f"[flow-img] image-to-video จากรูป: {image_path}")
    _ensure_chrome_9222()

    pw = sync_playwright().start()
    try:
        try:
            browser = pw.chromium.connect_over_cdp(settings.flow_cdp_url)
        except Exception as e:
            pw.stop()
            raise RuntimeError(f"เชื่อม Chrome 9222 ไม่ได้: {e}") from e

        context = browser.contexts[0]
        page = next((p for p in context.pages if "labs.google" in p.url or "flow" in p.url), None)
        if not page:
            page = context.new_page()
            page.goto("https://labs.google/fx/th/tools/flow", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        try:
            page.bring_to_front()
        except Exception:
            pass
        page.keyboard.press("Escape")
        time.sleep(0.5)

        # วีดีโอเดิม (เทียบหาตัวใหม่)
        existing = page.locator("video").evaluate_all("els => els.map(e => e.src).filter(Boolean)")
        existing_names = {_media_name(s) for s in existing if _media_name(s)}

        # 1) อัปโหลดรูป product เข้า Flow (input[type=file] รับ image — ซ่อนอยู่)
        page.locator("input[type='file']").first.set_input_files(image_path)
        fname = os.path.basename(image_path)
        print(f"[flow-img] อัปโหลด {fname}")
        time.sleep(3)

        # 2) เปิดเมนู '+' (add_2) ในแถบ composer
        if not _click_text_trusted(page, "add_2", exact=False):
            _click_text_trusted(page, "add", exact=False)
        time.sleep(1.5)

        # 3) เลือกรูปที่เพิ่งอัป + กด 'เพิ่มไปยังพรอมต์'
        _click_text_trusted(page, fname, exact=False)
        time.sleep(0.8)
        if not _click_text_trusted(page, "เพิ่มไปยังพรอมต์", exact=True):
            print("[flow-img] ⚠️ ไม่เจอ 'เพิ่มไปยังพรอมต์' — รูปอาจไม่แนบ (generate ต่อแบบ text)")
        time.sleep(1.0)

        # 4) พิมพ์ prompt ลงช่องที่มองเห็น
        vis_idx = page.evaluate("""() => {
          const t=[...document.querySelectorAll("[role='textbox'],textarea")];
          for(let i=0;i<t.length;i++){const r=t[i].getBoundingClientRect(); if(r.width>10&&r.height>10) return i;}
          return 0;
        }""")
        box = page.locator("[role='textbox'], textarea").nth(vis_idx)
        box.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        time.sleep(0.3)
        page.keyboard.insert_text(prompt)
        print(f"[flow-img] พิมพ์ prompt: {prompt[:50]}")
        time.sleep(0.8)

        # 5) ส่ง (Enter)
        page.keyboard.press("Enter")
        time.sleep(3)

        # 6) อนุมัติเครดิต (ลองหลายรอบ เผื่อ dialog โผล่ช้า)
        for _ in range(6):
            if _approve_credit(page):
                break
            time.sleep(1.0)

        # 7) รอวีดีโอใหม่ (~10 นาที, คิวอาจนาน) — กด approve ซ้ำทุกรอบเผื่อ dialog ค้าง
        print("[flow-img] รอวีดีโอใหม่ (สูงสุด ~10 นาที)...")
        video_url = ""
        for i in range(300):
            try:
                srcs = page.locator("video").evaluate_all("els => els.map(e => e.src).filter(Boolean)")
            except Exception:
                time.sleep(2)
                continue
            new = [s for s in srcs if "media.getMediaUrlRedirect" in s
                   and _media_name(s) and _media_name(s) not in existing_names]
            if new:
                video_url = new[-1]
                break
            _approve_credit(page)
            if i % 5 == 0:
                try:
                    body = page.evaluate("() => document.body.innerText")
                    if any(k in body for k in ["เกินโควตา", "เครดิตไม่เพียงพอ", "หมดโควตา",
                                               "out of credit", "quota exceeded", "สิทธิ์การใช้งานหมด"]):
                        try:
                            from ..services import system_state
                            system_state.set_flow_blocked()
                        except Exception:
                            pass
                        raise RuntimeError("โควตา/เครดิต Google Flow หมด — พัก Flow และใช้ระบบสำรอง")
                except RuntimeError:
                    raise
                except Exception:
                    pass
            if i % 15 == 0:
                print(f"[flow-img] ...รอวีดีโอใหม่ {i*2}s")
            time.sleep(2)

        if not video_url:
            raise RuntimeError("Timeout รอวีดีโอ image-to-video (อาจคิวนาน/ไม่เริ่ม)")

        # 8) โหลดวีดีโอผ่าน browser fetch → เซฟ .mp4
        print(f"[flow-img] ✓ ได้วีดีโอ: {video_url[:70]}")
        data_url = page.evaluate("""async (url) => {
            const resp = await fetch(url); const blob = await resp.blob();
            return await new Promise((res, rej) => {
                const fr = new FileReader(); fr.onloadend = () => res(fr.result); fr.onerror = rej;
                fr.readAsDataURL(blob);
            });
        }""", video_url)
        video_bytes = base64.b64decode(data_url.split(",", 1)[1])

        media_dir = settings.media_dir
        if media_dir == "/app/data/media":
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            media_dir = os.path.join(root, "data", "media")
        os.makedirs(media_dir, exist_ok=True)
        dest = os.path.join(media_dir, f"i2v_{uuid.uuid4().hex[:8]}.mp4")
        with open(dest, "wb") as f:
            f.write(video_bytes)
        print(f"[flow-img] ✅ บันทึก: {dest} ({len(video_bytes)} bytes)")
        return dest
    finally:
        try:
            pw.stop()
        except Exception:
            pass
