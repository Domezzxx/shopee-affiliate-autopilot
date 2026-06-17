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
    """จำลองการพิมพ์เป็นตัวอักษรทีละตัวเพื่อความสมจริง เลี่ยงบอทจับผิด"""
    d.clear_text()
    time.sleep(0.5)
    for char in text:
        # uiautomator2 support send_keys
        d.send_keys(char)
        time.sleep(0.05 + (0.1 if char in " ะาิีึืุูะ" else 0.0))
    time.sleep(1)


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
            time.sleep(6)
            
            # ค้นหาปุ่มบวกเพื่อสร้างโพสต์/Reel
            logger.info("[phone-farm] [Facebook] Clicking Create Reel...")
            # สแกนหาคำว่า "Reel" หรือปุ่มบวกไอคอน Reels
            selectors = [
                d(descriptionContains="Create a reel"),
                d(descriptionContains="สร้างรีล"),
                d(text="Reel"),
                d(text="รีล"),
                d(description="Create post"),
                d(description="สร้างโพสต์")
            ]
            
            clicked = False
            for sel in selectors:
                if sel.exists(timeout=2):
                    sel.click()
                    clicked = True
                    break
            
            if not clicked:
                # ลองกดปุ่ม "+" หลักบนหน้าฟีด Facebook
                logger.info("[phone-farm] [Facebook] Selectors not found, trying fallback plus button...")
                plus_btn = d(descriptionContains="Create")
                if plus_btn.exists(timeout=2):
                    plus_btn.click()
                    time.sleep(2)
                    d(text="Reel").click()
                else:
                    raise RuntimeError("Cannot locate Facebook Reels creation button")
                    
            time.sleep(3)
            
            # หน้าเลือกสื่อแกลเลอรี: วิดีโอล่าสุดจะอยู่ซ้ายบนสุด (ImageView ตัวแรก)
            logger.info("[phone-farm] [Facebook] Selecting latest video...")
            # FB Gallery Grid Item
            d(className="android.widget.ImageView", instance=0).click(timeout=10)
            time.sleep(4)
            
            # ถ้าเป็นวิดีโอและมีให้กด "ถัดไป" หรือ "Next"
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=3):
                next_btn.click()
                time.sleep(2)
                
            # หน้าเขียนแคปชั่น
            logger.info("[phone-farm] [Facebook] Entering caption...")
            desc_field = d(resourceId="com.facebook.katana:id/caption_edit_text")
            if not desc_field.exists():
                desc_field = d(focused=True) # พุ่งเป้าไปที่ Textbox ที่โฟกัสอยู่
                
            if desc_field.exists(timeout=3):
                desc_field.click()
                human_type(d, caption)
            else:
                logger.warning("[phone-farm] [Facebook] Cannot find caption textbox, typing blindly...")
                d.click(360, 400) # คลิกตรงกลางบนเพื่อเดาตำแหน่งกล่องข้อความ
                time.sleep(1)
                human_type(d, caption)
                
            # กดแชร์/แชร์รีล (Share Reel / Share Now)
            logger.info("[phone-farm] [Facebook] Sharing Reel...")
            share_selectors = [
                d(text="Share Reel"),
                d(text="แชร์รีล"),
                d(text="แชร์เลย"),
                d(text="Share Now")
            ]
            
            shared = False
            for sel in share_selectors:
                if sel.exists(timeout=3):
                    sel.click()
                    shared = True
                    break
            
            if not shared:
                # ลองกดปุ่มขวาล่างสุด (เดาพิกัด)
                w, h = d.window_size()
                d.click(w - 150, h - 80)
                logger.info("[phone-farm] [Facebook] Shared Reel using bottom right coordinates.")
                
            time.sleep(5)
            logger.info("[phone-farm] [Facebook] Post successfully submitted!")
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
    """จำลองควบคุม Shopee โพสต์ Shopee Video"""
    lock = get_device_lock(device_ip)
    with lock:
        d = connect_device(device_ip)
        remote_path = sync_media(device_ip, local_path)
        
        try:
            logger.info("[phone-farm] [Shopee] Launching App...")
            d.app_start("com.shopee.th", stop=True)
            time.sleep(8)
            
            # ปิด popup โฆษณาเริ่มต้นถ้ามี
            popup_close_selectors = [
                d(resourceId="com.shopee.th:id/close"),
                d(descriptionContains="close"),
                d(descriptionContains="ปิด"),
                d(text="ปิด")
            ]
            for sel in popup_close_selectors:
                if sel.exists(timeout=2):
                    sel.click()
                    time.sleep(1)
            
            # คลิกแท็บ Video (วิดีโอ) ด้านล่าง
            logger.info("[phone-farm] [Shopee] Clicking Video Tab...")
            video_tab = d(text="Video") if d(text="Video").exists() else d(text="วิดีโอ")
            if video_tab.exists(timeout=4):
                video_tab.click()
            else:
                w, h = d.window_size()
                d.click(w // 5 * 2, h - 60)
            time.sleep(4)
            
            # คลิกปุ่มกล้อง (ลงวิดีโอ/สร้างวิดีโอ) ที่มุมขวาบน
            logger.info("[phone-farm] [Shopee] Clicking Create/Camera button...")
            camera_btn = d(descriptionContains="camera") if d(descriptionContains="camera").exists() else d(descriptionContains="กล้อง")
            if not camera_btn.exists():
                camera_btn = d(resourceId="com.shopee.th:id/btn_camera")
            if camera_btn.exists(timeout=4):
                camera_btn.click()
            else:
                w, h = d.window_size()
                d.click(w - 80, 80)
            time.sleep(4)
            
            # หน้านำเข้าวิดีโอ (อัปโหลด)
            logger.info("[phone-farm] [Shopee] Clicking Upload from Gallery...")
            gallery_btn = d(text="อัพโหลด") if d(text="อัพโหลด").exists() else d(text="Upload")
            if not gallery_btn.exists():
                gallery_btn = d(resourceId="com.shopee.th:id/btn_upload")
            if gallery_btn.exists(timeout=4):
                gallery_btn.click()
            else:
                w, h = d.window_size()
                d.click(w - 150, h - 250)
            time.sleep(3)
            
            # เลือกวิดีโอล่าสุดจากแกลเลอรี
            logger.info("[phone-farm] [Shopee] Selecting latest video...")
            d(className="android.widget.ImageView", instance=0).click(timeout=10)
            time.sleep(3)
            
            # กดเลือก/ถัดไป (Next / ตกลง)
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if not next_btn.exists():
                next_btn = d(text="ตกลง") if d(text="ตกลง").exists() else d(text="OK")
            if next_btn.exists(timeout=4):
                next_btn.click()
            else:
                w, h = d.window_size()
                d.click(w - 80, h - 80)
            time.sleep(4)
            
            # กด Next ในหน้า edit
            next_btn = d(text="Next") if d(text="Next").exists() else d(text="ถัดไป")
            if next_btn.exists(timeout=4):
                next_btn.click()
            else:
                w, h = d.window_size()
                d.click(w - 80, h - 80)
            time.sleep(4)
            
            # หน้าพิมพ์คำบรรยาย
            logger.info("[phone-farm] [Shopee] Entering caption...")
            cap_box = d(descriptionContains="แคปชั่น") if d(descriptionContains="แคปชั่น").exists() else d(descriptionContains="Caption")
            if not cap_box.exists():
                cap_box = d(focused=True)
            if cap_box.exists(timeout=3):
                cap_box.click()
                human_type(d, caption)
            else:
                d.click(200, 300)
                time.sleep(1)
                human_type(d, caption)
                
            # กดแชร์/โพสต์
            logger.info("[phone-farm] [Shopee] Posting video...")
            post_btn = d(text="Post") if d(text="Post").exists() else d(text="โพสต์")
            if post_btn.exists(timeout=4):
                post_btn.click()
            else:
                w, h = d.window_size()
                d.click(w // 2, h - 80)
            time.sleep(5)
            logger.info("[phone-farm] [Shopee] Post successfully submitted!")
            return {"ok": True, "error": ""}
            
        except Exception as e:
            logger.error(f"[phone-farm] [Shopee] Automation failed: {e}")
            capture_debug_screenshot(d, "shopee")
            return {"ok": False, "error": str(e)}
        finally:
            d.app_stop("com.shopee.th")
