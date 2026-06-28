import os
import time
import uuid
import logging
import threading
import subprocess
import uiautomator2 as u2
from adbutils import adb
from ..config import settings

logger = logging.getLogger("phone_automator")

# เธรดล็อกแยกตามเครื่อง เพื่อความปลอดภัยในการเข้าถึงอุปกรณ์พร้อมกัน
DEVICE_LOCKS: dict[str, threading.Lock] = {}
LOCKS_MUTEX = threading.Lock()

def get_device_lock(device_ip: str) -> threading.Lock:
    """ดึงหรือสร้าง Lock สำหรับอุปกรณ์นั้น ๆ"""
    with LOCKS_MUTEX:
        if device_ip not in DEVICE_LOCKS:
            DEVICE_LOCKS[device_ip] = threading.Lock()
        return DEVICE_LOCKS[device_ip]


def run_adb(device_ip: str, *args: str) -> tuple[bool, str]:
    """เรียกใช้คำสั่ง ADB command สำหรับอุปกรณ์เฉพาะเจาะจง"""
    try:
        cmd = ["adb", "-s", device_ip, *args]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return res.returncode == 0, (res.stdout or res.stderr).strip()
    except Exception as e:
        return False, str(e)


def connect_device(device_ip: str) -> u2.Device:
    """เชื่อมต่อ ADB และเริ่มต้น uiautomator2 agent"""
    logger.info(f"[phone-farm] Connecting to device {device_ip}...")
    
    # 1) ต่อสาย/เน็ตผ่าน ADB
    run_adb(device_ip, "connect", device_ip)
    time.sleep(1)
    
    try:
        # 2) เริ่มเชื่อม u2
        d = u2.connect(device_ip)
        # ทดสอบการตอบสนองพื้นฐาน (เช่น ดึงขนาดหน้าจอ)
        info = d.info
        logger.info(f"[phone-farm] Successfully connected to {device_ip} ({info.get('productName', 'Android')})")
        return d
    except Exception as e:
        logger.error(f"[phone-farm] Failed uiautomator2 connection to {device_ip}: {e}")
        # พยายามสั่ง init/reinstall u2 server agent ในเครื่องมือถือ
        try:
            logger.info(f"[phone-farm] Re-initializing u2 server on {device_ip}...")
            # uiautomator2 python package has command to install server
            # We can use run_adb to start the agent manually if needed
            run_adb(device_ip, "shell", "pm", "grant", "com.github.uiautomator", "android.permission.SYSTEM_ALERT_WINDOW")
        except:
            pass
        raise RuntimeError(f"Cannot connect to Android u2 server at {device_ip}: {e}") from e


def sync_media(device_ip: str, local_path: str) -> str:
    """คัดลอกไฟล์วิดีโอไปยังมือถือและทำการสแกนเข้าระบบคลังภาพแกลเลอรี"""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local media file not found: {local_path}")
        
    filename = f"auto_{uuid.uuid4().hex[:8]}_{os.path.basename(local_path)}"
    # บังคับบันทึกใน DCIM เพื่อให้แอปส่วนใหญ่สแกนหาเจอได้ง่ายที่สุด
    remote_path = f"/sdcard/DCIM/Camera/{filename}"
    
    logger.info(f"[phone-farm] Pushing media: {local_path} -> {remote_path}")
    ok, err = run_adb(device_ip, "push", local_path, remote_path)
    if not ok:
        # Fallback ในกรณีไม่มีโฟลเดอร์ Camera
        remote_path = f"/sdcard/DCIM/{filename}"
        logger.info(f"[phone-farm] Pushing to fallback path: {remote_path}")
        ok, err = run_adb(device_ip, "push", local_path, remote_path)
        if not ok:
            raise RuntimeError(f"ADB push failed: {err}")
            
    # สั่งให้ระบบปฏิบัติการแอนดรอยด์สแกนไฟล์เข้าไปใน MediaStore (แกลเลอรีของมือถือ)
    logger.info(f"[phone-farm] Scanning media file in Android Gallery...")
    run_adb(device_ip, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_path}")
    run_adb(device_ip, "shell", "media", "scan-file", remote_path)
    
    time.sleep(2)  # รอให้ Android สแกนเข้าแกลเลอรีให้เรียบร้อย
    return remote_path


def human_type(d: u2.Device, text: str):
    """พิมพ์ข้อความ — รองรับไทย/emoji ผ่าน FastInputIME (Unicode).

    เดิมใช้ send_keys ทีละตัวบน IME ปกติ (ADB input text) ซึ่งรองรับแค่ ASCII
    → แคปชั่นไทยออกมาเป็นตัวมั่ว. แก้: เปิด FastInputIME ของ uiautomator2 ก่อน
    (รองรับ Unicode/emoji) แล้วพิมพ์ทีละคำ + หน่วงสุ่มให้ดูเป็นมนุษย์ (anti-detection).
    """
    # uiautomator2 ติดตั้ง IME ของตัวเอง (AdbKeyboard) และตั้งเป็น default ให้แล้ว → send_keys รองรับ unicode/ไทย
    try:
        d.send_keys(text, clear=True)
        time.sleep(0.8)
        return
    except Exception as e:
        logger.warning(f"[phone-farm] send_keys ล้มเหลว ({e}) → fallback ADB_INPUT_B64")
    # fallback: ส่งผ่าน AdbKeyboard broadcast แบบ base64 (กันตัวอักษรไทย/emoji เพี้ยน)
    try:
        import base64
        b64 = base64.b64encode(text.encode("utf-8")).decode()
        run_adb(d.serial, "shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64)
        time.sleep(1)
    except Exception as e2:
        logger.error(f"[phone-farm] พิมพ์ caption ล้มเหลว: {e2}")
        time.sleep(1)


def _click_first(selectors, timeout: int = 3) -> bool:
    """กด selector ตัวแรกที่เจอบนจอ (รองรับ UI หลายเวอร์ชัน) — คืน True ถ้ากดได้."""
    for sel in selectors:
        try:
            if sel.exists(timeout=timeout):
                sel.click()
                return True
        except Exception:
            continue
    return False


def capture_debug_screenshot(d: u2.Device, platform: str):
    """แคปหน้าจอเก็บไว้เวลาเจอบั๊กปุ่มกดไม่เจอบนมือถือ"""
    try:
        media_dir = settings.media_dir
        if media_dir == "/app/data/media":
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            media_dir = os.path.join(project_root, "data", "media")
        os.makedirs(media_dir, exist_ok=True)
        scr_path = os.path.join(media_dir, f"phone_error_{platform}_{uuid.uuid4().hex[:8]}.png")
        d.screenshot(scr_path)
        logger.info(f"[phone-farm] Screenshot saved for phone debugging: {scr_path}")
    except Exception as e:
        logger.warning(f"[phone-farm] Capture screenshot failed: {e}")


def post_facebook_reel(device_ip: str, local_path: str, caption: str) -> dict:
    """จำลองควบคุม Facebook โพสต์ Reels"""
    lock = get_device_lock(device_ip)
    with lock:
        d = connect_device(device_ip)
        remote_path = sync_media(device_ip, local_path)
        
        try:
            logger.info("[phone-farm] [Facebook] Launching App...")
            d.app_start("com.facebook.katana", stop=True)
            time.sleep(7)

            # 1) เปิดหน้าสร้าง Reel — ปุ่มบนแถบสตอรี่ของฟีด (รองรับทั้งไทย/อังกฤษ ป้ายเปลี่ยนได้)
            logger.info("[phone-farm] [Facebook] Open Reel composer...")
            if not _click_first([
                d(description="สร้างคลิป Reels"), d(text="สร้างคลิป Reels"),
                d(descriptionContains="คลิป Reels"), d(textContains="คลิป Reels"),
                d(description="Create reel"), d(text="Create reel"),
                d(descriptionContains="Create reel"), d(textContains="Create reel"),
                d(descriptionContains="Create a reel"),
                d(descriptionContains="สร้างรีล"),
                d(descriptionContains="reel"), d(descriptionContains="Reel"),
            ], timeout=4):
                raise RuntimeError("Cannot locate Facebook Reels creation button")
            time.sleep(5)

            # 2) เลือกวิดีโอที่เพิ่ง push — ในกริด composer ช่องวิดีโอจะระบุ desc ว่า 'ด้วย วิดีโอ'
            #    (ตัวล่าสุด = ซ้ายบนสุด) ; เก่า: ใช้ ImageView ซึ่งเวอร์ชันใหม่ไม่มี
            logger.info("[phone-farm] [Facebook] Selecting pushed video...")
            if not _click_first([
                d(descriptionContains="ด้วย วิดีโอ"),
                d(descriptionContains="วิดีโอ,"),
                d(descriptionContains="with video"),
                d(descriptionContains="video,"),
            ], timeout=10):
                # fallback: ช่องกริดแรก
                try:
                    d(className="android.view.ViewGroup", clickable=True, instance=0).click(timeout=8)
                except Exception:
                    d.click(120, 540)
            time.sleep(7)

            # 3) หน้า edit (InspirationCamera) → ปุ่ม 'ถัดไป'/'Next' มุมขวาล่าง
            logger.info("[phone-farm] [Facebook] Editor -> Next...")
            _click_first([d(description="ถัดไป"), d(text="ถัดไป"),
                          d(description="Next"), d(text="Next")], timeout=8)
            time.sleep(6)

            # 4) หน้าแคปชั่น (Immersive) → ช่อง 'อธิบายคลิป Reels ของคุณ'
            #    หลังกดถัดไปมี transition (โหลด) ~หลายวิ → รอจนช่องแคปชั่นโผล่ (สูงสุด ~20 วิ)
            logger.info("[phone-farm] [Facebook] Waiting for caption screen...")
            cap = None
            cap_keys = ["อธิบายคลิป", "เพิ่มคำอธิบาย", "Describe your reel", "Describe", "description"]
            for _ in range(10):
                for key in cap_keys:
                    c = d(descriptionContains=key)
                    if c.exists(timeout=1):
                        cap = c
                        break
                if cap is not None:
                    break
                time.sleep(2)
            if cap is not None:
                logger.info("[phone-farm] [Facebook] Entering caption...")
                cap.click()
                time.sleep(1.2)
                human_type(d, caption)
                d.press("back")   # ปิดคีย์บอร์ดให้เห็นปุ่ม 'แชร์เลย'
                time.sleep(1.5)
            else:
                logger.warning("[phone-farm] [Facebook] caption field not found — typing blindly")
                d.click(360, 300); time.sleep(1); human_type(d, caption); d.press("back"); time.sleep(1.5)

            # 5) กด 'แชร์เลย' (ปุ่มโพสต์สุดท้าย — มุมขวาล่าง)
            logger.info("[phone-farm] [Facebook] Sharing...")
            if not _click_first([
                d(description="แชร์เลย"), d(text="แชร์เลย"),
                d(description="Share now"), d(text="Share now"),
                d(description="Share Now"), d(description="แชร์"), d(text="Share"),
            ], timeout=6):
                d.click(420, 1468)   # พิกัดปุ่ม 'แชร์เลย' โดยประมาณ (จอ 720x1608)
            # รออัปโหลด/เผยแพร่ให้เสร็จก่อนปิดแอป (รีลวิดีโอใช้เวลา — ปิดเร็วไป = โพสต์ไม่ขึ้น)
            time.sleep(30)
            logger.info("[phone-farm] [Facebook] Post submitted (waited for upload).")
            return {"ok": True, "error": ""}
            
        except Exception as e:
            logger.error(f"[phone-farm] [Facebook] Automation failed: {e}")
            capture_debug_screenshot(d, "facebook")
            return {"ok": False, "error": str(e)}
        finally:
            d.app_stop("com.facebook.katana")


def post_instagram_reel(device_ip: str, local_path: str, caption: str) -> dict:
    """จำลองควบคุม Instagram โพสต์ Reels"""
    lock = get_device_lock(device_ip)
    with lock:
        d = connect_device(device_ip)
        remote_path = sync_media(device_ip, local_path)
        
        try:
            logger.info("[phone-farm] [Instagram] Launching App...")
            d.app_start("com.instagram.android", stop=True)
            time.sleep(6)
            
            # กดปุ่มสร้าง (+) หรือปัดขวา
            logger.info("[phone-farm] [Instagram] Accessing Creation Screen...")
            plus_btn = d(descriptionContains="Create") if d(descriptionContains="Create").exists() else d(descriptionContains="สร้าง")
            if plus_btn.exists(timeout=3):
                plus_btn.click()
            else:
                # ปัดขวาเพื่อเข้ากล้อง/ Reels
                d.swipe_ext("right")
                time.sleep(2)
                
            time.sleep(3)
            
            # สลับโหมดเป็น Reels (หากเปิดเป็น Post ธรรมดาอยู่)
            reel_tab = d(text="REEL") if d(text="REEL").exists() else d(text="คลิปรีล")
            if reel_tab.exists(timeout=2):
                reel_tab.click()
                time.sleep(1)
                
            # เลือกภาพ/วิดีโอล่าสุดจากแกลเลอรี
            logger.info("[phone-farm] [Instagram] Selecting media...")
            d(className="android.widget.ImageView", instance=0).click(timeout=10)
            time.sleep(3)
            
            # คลิก "ถัดไป" / "Next" (มุมขวาบน)
            logger.info("[phone-farm] [Instagram] Clicking Next...")
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=5):
                next_btn.click()
                time.sleep(2)
            else:
                # พิกัดขวาบนโดยประมาณ
                w, h = d.window_size()
                d.click(w - 80, 80)
                time.sleep(2)
                
            # คลิก Next อีกครั้ง (ขั้นตอนใส่เอฟเฟกต์/เพลง)
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=4):
                next_btn.click()
                time.sleep(2)
            else:
                w, h = d.window_size()
                d.click(w - 80, h - 80) # ขวาล่าง
                time.sleep(2)
                
            # หน้าพิมพ์คำบรรยาย
            logger.info("[phone-farm] [Instagram] Entering caption...")
            cap_box = d(descriptionContains="Write a caption") if d(descriptionContains="Write a caption").exists() else d(descriptionContains="เขียนคำอธิบาย")
            if not cap_box.exists():
                cap_box = d(resourceId="com.instagram.android:id/caption_text_view")
                
            if cap_box.exists(timeout=3):
                cap_box.click()
                human_type(d, caption)
            else:
                # เดาตำแหน่งกล่องพิมพ์แคปชั่น
                d.click(200, 300)
                time.sleep(1)
                human_type(d, caption)
                
            # กดแชร์รีล (Share / แชร์)
            logger.info("[phone-farm] [Instagram] Sharing Reel...")
            share_btn = d(text="Share") if d(text="Share").exists() else d(text="แชร์")
            if share_btn.exists(timeout=3):
                share_btn.click()
            else:
                w, h = d.window_size()
                d.click(w // 2, h - 100) # กดปุ่มแชร์ขวาหรือล่างกลาง
                
            time.sleep(5)
            logger.info("[phone-farm] [Instagram] Post successfully submitted!")
            return {"ok": True, "error": ""}
            
        except Exception as e:
            logger.error(f"[phone-farm] [Instagram] Automation failed: {e}")
            capture_debug_screenshot(d, "instagram")
            return {"ok": False, "error": str(e)}
        finally:
            d.app_stop("com.instagram.android")


def post_youtube_shorts(device_ip: str, local_path: str, caption: str) -> dict:
    """จำลองควบคุม YouTube โพสต์ Shorts"""
    lock = get_device_lock(device_ip)
    with lock:
        d = connect_device(device_ip)
        remote_path = sync_media(device_ip, local_path)
        
        try:
            logger.info("[phone-farm] [YouTube] Launching App...")
            d.app_start("com.google.android.youtube", stop=True)
            time.sleep(6)
            
            # คลิกปุ่ม (+) สร้างคลิปที่ด้านล่างสุดของฟีด
            logger.info("[phone-farm] [YouTube] Clicking Create (+) button...")
            create_btn = d(resourceId="com.google.android.youtube:id/create_button")
            if not create_btn.exists():
                create_btn = d(descriptionContains="Create") if d(descriptionContains="Create").exists() else d(descriptionContains="สร้าง")
                
            if create_btn.exists(timeout=4):
                create_btn.click()
            else:
                # สุ่มสัมผัสล่างสุดตรงกลาง (จุดมาตรฐานของปุ่มสร้างยูทูป)
                w, h = d.window_size()
                d.click(w // 2, h - 60)
                
            time.sleep(3)
            
            # เลือกเมนู "สร้าง Short" หรือ "อัปโหลดวิดีโอ" (YouTube Shorts แนะนำเมนูสร้าง Short เพื่อตัดสัดส่วนวิดีโอและซับถูกต้อง)
            logger.info("[phone-farm] [YouTube] Selecting 'Upload a video' or 'Create a Short'...")
            opts = [
                d(textContains="Create a Short"),
                d(textContains="สร้าง Short"),
                d(textContains="Upload a video"),
                d(textContains="อัปโหลดวิดีโอ")
            ]
            
            selected_mode = False
            for opt in opts:
                if opt.exists(timeout=2):
                    opt.click()
                    selected_mode = True
                    break
            
            if not selected_mode:
                # ลองกดพิกัดรายการเมนูที่ 2 (Upload a video)
                w, h = d.window_size()
                d.click(w // 2, h // 2 + 100)
                
            time.sleep(3)
            
            # เลือกวิดีโอล่าสุดจากแกลเลอรี
            logger.info("[phone-farm] [YouTube] Selecting video...")
            # ในหน้าอัปโหลดของ YouTube มักจะขึ้นแกลเลอรีวิดีโอล่าสุด สามารถคลิก Item ล่าสุดได้เลย
            d(className="android.widget.ImageView", instance=0).click(timeout=10)
            time.sleep(3)
            
            # กดถัดไป / Next (ขั้นแรก)
            logger.info("[phone-farm] [YouTube] Pressing Next (1)...")
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=5):
                next_btn.click()
                time.sleep(2)
            else:
                # พิกัดขวาบนหรือขวาล่าง
                w, h = d.window_size()
                d.click(w - 80, h - 80)
                time.sleep(2)
                
            # กดถัดไป / Next (ขั้นสองหลังปรับแต่ง)
            logger.info("[phone-farm] [YouTube] Pressing Next (2)...")
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=4):
                next_btn.click()
                time.sleep(3)
            else:
                w, h = d.window_size()
                d.click(w - 80, 80) # ขวาบน
                time.sleep(3)
                
            # หน้ากรอกรายละเอียด (Details)
            logger.info("[phone-farm] [YouTube] Entering caption...")
            cap_box = d(resourceId="com.google.android.youtube:id/caption_text_box")
            if not cap_box.exists():
                cap_box = d(textContains="คำอธิบายภาพ") if d(textContains="คำอธิบายภาพ").exists() else d(textContains="Caption")
                
            if cap_box.exists(timeout=3):
                cap_box.click()
                human_type(d, caption)
            else:
                d.click(200, 250) # เดาตำแหน่ง
                time.sleep(1)
                human_type(d, caption)
                
            # กดปุ่ม "อัปโหลดวิดีโอสั้น" / "Upload Short"
            logger.info("[phone-farm] [YouTube] Uploading Short...")
            upload_btn = d(text="Upload Short") if d(text="Upload Short").exists() else d(text="อัปโหลดวิดีโอสั้น")
            if upload_btn.exists(timeout=3):
                upload_btn.click()
            else:
                w, h = d.window_size()
                d.click(w // 2, h - 80) # กดปุ่มใหญ่ด้านล่าง
                
            time.sleep(5)
            logger.info("[phone-farm] [YouTube] Post successfully submitted!")
            return {"ok": True, "error": ""}
            
        except Exception as e:
            logger.error(f"[phone-farm] [YouTube] Automation failed: {e}")
            capture_debug_screenshot(d, "youtube")
            return {"ok": False, "error": str(e)}
        finally:
            d.app_stop("com.google.android.youtube")


def post_shopee_video(device_ip: str, local_path: str, caption: str) -> dict:
    """โพสต์ Shopee Video (com.shopee.th) — จูนตาม UI จริงของแอป (Live & Video).

    flow: เปิดแอป → back ปิด popup → แท็บ 'Live & Video' → ปุ่มสร้างมุมขวาบน →
    'คลังภาพ' → แตะวิดีโอแรก → ถัดไป → ถัดไป → ใส่แคปชั่น(+ลิงก์ affiliate) → โพสต์.
    """
    lock = get_device_lock(device_ip)
    with lock:
        d = connect_device(device_ip)
        # pre-grant สิทธิ์ กล้อง/ไมค์/สื่อ — กัน permission dialog เด้งกลางทาง
        for perm in ("android.permission.CAMERA", "android.permission.RECORD_AUDIO",
                     "android.permission.READ_MEDIA_VIDEO", "android.permission.READ_MEDIA_IMAGES",
                     "android.permission.READ_EXTERNAL_STORAGE"):
            run_adb(device_ip, "shell", "pm", "grant", "com.shopee.th", perm)
        sync_media(device_ip, local_path)

        try:
            logger.info("[phone-farm] [Shopee] Launching App...")
            d.app_start("com.shopee.th", stop=True)
            time.sleep(9)

            # 0) ปิด popup เริ่มต้น (เช่น check-in) — มักเป็น overlay ReactTransparent → กด back
            if "HomeActivity" not in (d.app_current().get("activity") or ""):
                d.press("back"); time.sleep(2)

            # 1) แท็บ Live & Video (ล่าง)
            logger.info("[phone-farm] [Shopee] Open Live & Video tab...")
            if not _click_first([d(descriptionContains="tab_bar_button_video_and_li")], timeout=6):
                d.click(360, 1470)
            time.sleep(6)

            # 2) ปุ่มสร้าง (มุมขวาบน)
            logger.info("[phone-farm] [Shopee] Click create...")
            if not _click_first([d(description="click top right create icon")], timeout=6):
                d.click(671, 113)
            time.sleep(8)
            # เผื่อ permission dialog ยังเด้ง → กดอนุญาต
            _click_first([d(textContains="ขณะใช้แอป"), d(textContains="อนุญาต"),
                          d(textContains="While using")], timeout=2)

            # 3) คลังภาพ (เลือกจากแกลเลอรี)
            logger.info("[phone-farm] [Shopee] Open gallery (คลังภาพ)...")
            if not _click_first([d(text="คลังภาพ"), d(descriptionContains="คลังภาพ")], timeout=6):
                d.click(575, 1301)
            time.sleep(5)

            # 4) แตะวิดีโอแรกในกริด (เลี่ยง dropdown 'ทั้งหมด' ที่ y~200 → แตะ thumbnail y~330)
            logger.info("[phone-farm] [Shopee] Select first video...")
            d.click(134, 330)
            time.sleep(3)

            # 5) ถัดไป (preview → edit)
            _click_first([d(text="ถัดไป"), d(description="ถัดไป"), d(text="Next")], timeout=6)
            time.sleep(6)
            # 6) ถัดไป (edit → post)
            _click_first([d(text="ถัดไป"), d(description="ถัดไป"), d(text="Next")], timeout=6)
            time.sleep(7)

            # 7) ใส่แคปชั่น (มีลิงก์ affiliate) — Shopee EditText บล็อก IME (send_keys พัง) → ใช้ set_text
            logger.info("[phone-farm] [Shopee] Entering caption...")
            cap = d(className="android.widget.EditText")
            if cap.exists(timeout=6):
                try:
                    cap.set_text(caption)        # set_text ทำงานกับช่องดื้อของ Shopee ได้
                except Exception as e:
                    logger.warning(f"[phone-farm] [Shopee] set_text fail ({str(e)[:40]}) → human_type")
                    cap.click(); time.sleep(1); human_type(d, caption); d.press("back")
                time.sleep(1.5)
            else:
                logger.warning("[phone-farm] [Shopee] caption EditText not found — ข้ามแคปชั่น")

            # 8) โพสต์
            logger.info("[phone-farm] [Shopee] Posting...")
            if not _click_first([d(text="โพสต์"), d(description="โพสต์"), d(text="Post")], timeout=6):
                d.click(410, 1464)   # พิกัดปุ่ม 'โพสต์' โดยประมาณ
            time.sleep(22)   # รออัปโหลด/เผยแพร่ก่อนปิดแอป
            logger.info("[phone-farm] [Shopee] Post submitted!")
            return {"ok": True, "error": ""}

        except Exception as e:
            logger.error(f"[phone-farm] [Shopee] Automation failed: {e}")
            capture_debug_screenshot(d, "shopee")
            return {"ok": False, "error": str(e)}
        finally:
            d.app_stop("com.shopee.th")
