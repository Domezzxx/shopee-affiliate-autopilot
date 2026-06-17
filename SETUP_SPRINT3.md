# 🚀 Sprint 3 — เปิดโพสต์จริง (เช็คลิสต์ทำเอง)

โค้ดโพสต์จริงเสร็จแล้ว (FB/IG/YouTube) — เหลือแค่ใส่ credential ใน `.env` แล้วเช็คด้วยปุ่ม **🚦 เช็คพร้อมโพสต์** บน dashboard (หรือ `GET /api/post/preflight`).

> เช็คได้ทุกขั้น: ปุ่ม preflight จะยิง API จริงบอกว่าแต่ละช่อง 🟢 พร้อม / 🔴 ขาดอะไร

---

## 1) Facebook Page (ง่ายสุด เริ่มจากอันนี้)
อัปโหลดไฟล์ตรง ไม่ต้องมี public URL.

1. มี **Facebook Page** (เพจ ไม่ใช่โปรไฟล์ส่วนตัว)
2. ไป https://developers.facebook.com → My Apps → Create App → ประเภท **Business**
3. เพิ่มผลิตภัณฑ์ **Facebook Login** + ขอ permission:
   - `pages_manage_posts` · `pages_read_engagement` · `pages_show_list`
4. Graph API Explorer → ออก **Page Access Token** (แปลงเป็น long-lived 60 วันด้วย `/oauth/access_token?grant_type=fb_exchange_token`)
5. หา **Page ID**: เปิดเพจ → About → Page ID
6. ใส่ `.env`:
   ```
   META_PAGE_ID=<page id>
   META_ACCESS_TOKEN=<long-lived page token>
   ```
7. ⚠️ **App Review** — โพสต์ลงเพจที่ตัวเองเป็นแอดมินทำได้เลยตอน Dev Mode (test); โพสต์เพจคนอื่น/โปรดักชันต้องผ่าน App Review (~1–2 สัปดาห์)

## 2) Instagram Reels (ต้องมี public URL ของสื่อ)
IG รับเฉพาะ **public URL** ของวีดีโอ — ใช้ tunnel ฟรีที่เตรียมไว้:

1. IG ต้องเป็น **Business/Creator** + ผูกกับ Facebook Page ข้างบน
2. หา **IG User ID** (ผ่าน `/{page-id}?fields=instagram_business_account`)
3. permission เพิ่ม: `instagram_basic` · `instagram_content_publish`
4. **เปิด public URL ฟรี** (หน้าต่างใหม่ ปล่อยทิ้งไว้ขณะโพสต์):
   ```powershell
   ./scripts/start_tunnel.ps1
   ```
   - โหลด `cloudflared.exe` อัตโนมัติ + เปิด `https://xxxx.trycloudflare.com`
   - เขียน `PUBLIC_BASE_URL` ลง `.env` ให้เอง → **restart server**
   - (cloudflared quick tunnel ฟรี ไม่ต้องสมัคร · ใช้ `--protocol http2` กันเครือข่ายบล็อก QUIC)
5. ใส่ `.env`:
   ```
   META_IG_USER_ID=<ig user id>
   # PUBLIC_BASE_URL ใส่ให้แล้วโดย start_tunnel.ps1
   ```

## 3) YouTube Shorts (OAuth refresh token)
1. https://console.cloud.google.com → สร้าง project → เปิด **YouTube Data API v3**
2. OAuth consent screen: External → เพิ่มอีเมลตัวเองใน **Test users**
3. Credentials → OAuth client ID → **Desktop app** → ได้ Client ID + secret
4. รัน helper (เปิดเบราว์เซอร์ให้กดอนุญาต แล้วเขียน `.env` ให้เอง):
   ```powershell
   ./venv/Scripts/python.exe scripts/youtube_oauth.py
   ```
5. ได้ครบ → `YOUTUBE_CLIENT_ID` `YOUTUBE_CLIENT_SECRET` `YOUTUBE_REFRESH_TOKEN`

---

## 4) เปิดโหมดโปรดักชัน
```
POSTING_MODE=hybrid       # API ก่อน พลาดค่อยตกไป phone farm
ENABLE_POST_DELAY=true    # สุ่มหน่วง 15–45 นาทีระหว่างโพสต์ กัน spam
```

## 5) ยิงจริง
1. กด **🚦 เช็คพร้อมโพสต์** → ต้องเห็น 🟢 อย่างน้อย 1 ช่อง
2. กด **▶ รันครบวง** ที่ร้าน → generate + โพสต์จริง + วาง affiliate link คอมเมนต์แรก
3. ดูผลแท็บ **โพสต์** (external_id จริง = สำเร็จ)

> ทุกช่องที่ยังไม่ใส่ credential = ทำงานโหมด **mock** (คืน id ปลอม) ระบบไม่พัง เดินครบวงได้เพื่อทดสอบ flow
