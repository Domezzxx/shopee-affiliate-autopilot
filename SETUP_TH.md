# 🍜 Affiliate Autopilot — คู่มือติดตั้ง (พี่กอล์ฟ)

ระบบ automation affiliate Shopee Food อัตโนมัติครบวง: ดึงร้าน → Claude เขียนคอนเทนต์ →
Gemini ทำภาพ/วีดีโอ → โพสต์ FB/IG/YouTube → A/B test → Dashboard สรุปผล → หยุดร้านไม่เวิร์กเอง

---

## 0) สิ่งที่ต้องมี (ติดตั้งก่อน)

| ของ | ใช้ทำอะไร | ลิงก์ |
|-----|-----------|-------|
| **Docker Desktop** | รันทั้งระบบในคลิกเดียว | https://www.docker.com/products/docker-desktop |
| **Anthropic API key** | Claude เขียนแคปชั่น/A-B | https://console.anthropic.com → API Keys |
| **Gemini API key** | ภาพ Nano Banana + วีดีโอ Veo | https://aistudio.google.com/apikey |
| Meta token (FB+IG) | โพสต์ผ่าน API | https://developers.facebook.com (ทีหลังได้) |
| (ถ้าใช้) 6 มือถือ Android | phone farm สำรอง | เปิด USB debugging |

> **รันได้ทันทีแม้ยังไม่ใส่ key เลย** — ระบบจะเข้าโหมด *mock* (ภาพ placeholder, โพสต์ปลอม)
> เพื่อให้พี่กอล์ฟเห็นภาพรวม + ทดสอบ Dashboard ก่อน แล้วค่อยเติม key ทีละตัว

---

## 1) ติดตั้ง + รัน (3 คำสั่ง)

เปิด PowerShell ในโฟลเดอร์ `affiliate-autopilot`:

```powershell
Copy-Item .env.example .env          # 1. สร้างไฟล์ config
notepad .env                          # 2. เติม API key (หรือข้ามไปก่อนก็ได้)
docker compose up -d --build          # 3. รันทั้งระบบ
```

เสร็จแล้วเปิด:
- **Dashboard (WebApp):** http://localhost:8088
- **n8n (automation):** http://localhost:5678

---

## 2) ลองเดโมทันที (ไม่ต้องมี key)

1. เปิด http://localhost:8088
2. แท็บ **"Flow ระบบ"** — ดูภาพรวม 5 ขั้น
3. ยังไม่มีร้าน → เพิ่มร้านทดสอบ (PowerShell):
   ```powershell
   $body = '{"stores":[{"name":"ก๋วยเตี๋ยวเรือป้านิด","area":"อุดรธานี","rating":4.8,"review_count":230,"menu":["ก๋วยเตี๋ยวเรือ","เกาเหลา"],"price_range":"40-60 บาท"}]}'
   Invoke-RestMethod -Uri http://localhost:8088/api/ingest -Method Post -Body $body -ContentType "application/json"
   ```
4. กดปุ่ม **"▶ รันครบวงทุกร้านใหม่"** → Claude เขียน + Gemini ทำภาพ + โพสต์ (mock)
5. กด **"🎲 จำลองผล"** → เห็น A/B test เลือกผู้ชนะ + CTR ต่อ platform
6. กด **"⚙ Auto-optimize"** → ระบบหยุดร้าน CTR ต่ำเอง

---

## 3) เปิดใช้งานจริง — เติม key ทีละตัว

### 3.1 Claude (เขียนคอนเทนต์) — สำคัญสุด
ใส่ใน `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
CONTENT_MODEL=claude-sonnet-4-6
```
> ราคา ~0.40–0.60 บาท/ร้าน (200 ร้าน/วัน ≈ 100 บาท/วัน) อยากเทพสุด → `claude-opus-4-8`

### 3.2 Gemini (ภาพ/วีดีโอ)
```
GEMINI_API_KEY=...
ENABLE_VIDEO=false      # เริ่มด้วยภาพก่อน (ถูก). พร้อมแล้วค่อย true ทำวีดีโอ Veo
```

### 3.3 Facebook + Instagram (Meta Graph API)
1. สร้าง App ที่ https://developers.facebook.com → เพิ่ม product "Facebook Login" + "Instagram"
2. เชื่อม Facebook **Page** + Instagram **Business** account
3. ขอ permission: `pages_manage_posts`, `instagram_content_publish`, `pages_read_engagement`
4. แลก **Long-lived Page Access Token** แล้วใส่:
```
META_PAGE_ID=...
META_IG_USER_ID=...
META_ACCESS_TOKEN=...
```
> ⚠️ Meta ต้องผ่าน App Review ก่อนโพสต์อัตโนมัติจริง — ระหว่างรอ ใช้ phone farm ไปก่อนได้

### 3.4 YouTube (Shorts)
ขอ OAuth ที่ Google Cloud Console → YouTube Data API v3 → เอา refresh token ใส่
`YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN` (โครงพร้อม, ส่วน upload ต้องไฟล์วีดีโอจริง = เปิด ENABLE_VIDEO)

หลังแก้ `.env` ทุกครั้ง: `docker compose up -d` (รีโหลด env)

---

## 4) 6 มือถือ (Phone Farm) — โพสต์สำรองเมื่อ API ไม่ครอบ

ใช้ตอน: API โดน review ยังไม่ผ่าน / อยากกระจายหลายบัญชี / Reels-Shorts ที่ API ลงยาก

1. ทุกเครื่อง: เปิด **Developer options → USB debugging**
2. ต่อ ADB over WiFi (ทำครั้งเดียวต่อเครื่อง ผ่าน USB ก่อน):
   ```powershell
   adb tcpip 5555
   adb connect 192.168.1.51:5555
   ```
3. ใส่ทุกเครื่องใน `.env`:
   ```
   PHONE_FARM_DEVICES=192.168.1.51:5555,192.168.1.52:5555,192.168.1.53:5555,192.168.1.54:5555,192.168.1.55:5555,192.168.1.56:5555
   POSTING_MODE=hybrid
   ```
4. ระบบจะ: push ไฟล์สื่อเข้าเครื่อง → เปิดแอป → (ขั้นแตะโพสต์/พิมพ์แคปชั่น ต้องผูก
   **uiautomator2** หรือ **Appium** เฉพาะแต่ละแอป — ดู `backend/app/connectors/social.py` ฟังก์ชัน `_post_phone`)

> โครง ADB + กระจายโหลด 6 เครื่องพร้อมแล้ว — ส่วน "แตะปุ่มในแอป" เป็นงาน UI automation
> ที่ต้องจูนตามเวอร์ชันแอป (เปราะ) จึงแยกเป็น step ให้เสริมทีหลัง

---

## 5) ตั้ง n8n (ดึงร้านอัตโนมัติ + รันครบวงทุก 6 ชม.)

1. เปิด http://localhost:5678 → สร้าง account
2. **Import** 2 workflow จาก `n8n/workflows/`:
   - `1_scrape_shopee.json` — ดึงร้าน Shopee → ส่งเข้า backend
   - `2_pipeline_and_optimize.json` — รันครบวง + auto-optimize
3. เปิด workflow `1` → แก้ node "ดึงร้าน" ให้ตรง (Shopee กัน bot — แนะนำต่อ proxy หรือ Apify)
4. กด **Active** ทั้ง 2 workflow

> backend เรียกจาก n8n ใช้ `http://backend:8088` (ชื่อ service ใน Docker network เดียวกัน)

---

## 6) สรุปต้นทุน/รายได้ (ตามแผนพี่กอล์ฟ)

| | ต่อเดือน |
|---|---|
| Claude (เขียน) | ~3,000 บาท |
| Gemini ภาพ (Nano Banana) | ~1,000–2,000 บาท |
| Gemini วีดีโอ (Veo) ถ้าเปิด | ~6,000+ บาท |
| n8n + server (รันเอง) | ฟรี |
| **รวม** | **~4,000–11,000 บาท/เดือน** |
| **รายได้คาด** (200 ร้าน × 5 โพสต์ × CTR 1% × conv 3%) | **~100,000+ บาท/เดือน** |

---

## ปัญหาที่เจอบ่อย
- **`docker compose` ไม่รู้จัก** → ติดตั้ง Docker Desktop แล้วเปิดโปรแกรมค้างไว้
- **backend ไม่ขึ้น** → `docker compose logs backend`
- **A/B ยังไม่ตัดสิน** → ต้อง impressions ครบ `ABTEST_MIN_IMPRESSIONS` (กด "จำลองผล" เพื่อเทสต์)
- **อยากปิดวีดีโอชั่วคราว** → `ENABLE_VIDEO=false` (ประหยัดสุด)
