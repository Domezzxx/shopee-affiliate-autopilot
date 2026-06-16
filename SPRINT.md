# 🏃 Sprint Plan — Affiliate Autopilot

โปรเจกต์อิสระของพี่กอล์ฟ (แยกจาก Sentiara). ระบบ automation affiliate Shopee Food.

**สถาปัตยกรรม (ปัจจุบัน):** Gemini เขียนคอนเทนต์ (ฟรี) + ภาพ Nano Banana → ffmpeg ทำวีดีโอ/montage + เสียงพากย์ ·
ดึงร้าน/สินค้าด้วย Apify · โพสต์ Hybrid (API + phone farm) · n8n ขับเคลื่อนทั้ง pipeline · **รัน native ไม่ใช้ Docker**.
**บน GitHub:** https://github.com/Domezzxx/shopee-affiliate-autopilot (private)

---

## ✅ Sprint 1 — Foundation (เสร็จแล้ว)
> วาง flow ครบ 5 ขั้น + WebApp + Docker + รันโหมด mock ได้ทันที (ทดสอบ end-to-end ผ่าน)

- [x] โครง Docker compose (backend + n8n + postgres)
- [x] Backend FastAPI :8088 + SQLModel/SQLite (stores/content/variants/posts/metrics)
- [x] Engine: Claude เขียน A/B 6 ชิ้น/ร้าน (structured JSON) + mock fallback
- [x] Engine: Gemini Nano Banana ภาพ + Veo วีดีโอ 9:16 + placeholder fallback
- [x] Connector Hybrid: FB/IG/YouTube API + phone farm ADB (กระจาย 6 เครื่อง)
- [x] Pipeline: ingest → generate → media → post → A/B → auto-optimize
- [x] Dashboard WebApp (KPI · คอนเทนต์ A/B · โพสต์ · ช่องทาง · Flow)
- [x] n8n workflows: scrape Shopee + run pipeline/optimize
- [x] คู่มือไทย SETUP_TH.md (วิธีขอ key ทุกตัว)

---

## ✅ Sprint 2 — เชื่อม Gemini ของจริง (เสร็จ — รันจริงฟรีแล้ว ฿0)
- [x] จูน prompt ภาษาไทยให้ไวรัล (hook 3 วิแรก, A/B ต่างมุมจริง, โทนต่อ platform)
- [x] **CONTENT_PROVIDER=gemini** — ใช้ Gemini เขียนข้อความฟรี (ไม่ต้องใช้ Claude/จ่ายเงิน)
- [x] **Gemini key เชื่อมแล้ว** → เขียนคอนเทนต์ไทยจริง + ภาพ Nano Banana 9:16 จริง (~2MB/รูป)
- [x] วาง affiliate link เป็นคอมเมนต์แรกอัตโนมัติ (`publish_comment` + แทน {LINK})
- [x] เพิ่มร้านเอง + อัปโหลด CSV (`/api/stores/add`, `/api/ingest/csv`)
- [x] ตัวบอกสถานะ real/mock (`/api/keys/status` + banner)
- [x] DB auto-migrate (เพิ่มคอลัมน์ใหม่ DB เดิมไม่พัง)
- [x] **n8n scrape Shopee เสถียรแล้ว (Apify)** → ดู Sprint 2.6
- [ ] (เลื่อน) Anthropic/Claude — ไม่ฟรี, ใช้ Gemini แทนช่วงทดสอบ ค่อยต่อตอนโปรดักชัน

## ✅ Sprint 2.5 — Media & Video + Infra (เสร็จวันนี้ ฟรีทั้งหมด)
- [x] **รัน native ไม่ใช้ Docker** (เครื่อง AMD เปิด WSL2 แล้วบูตจอดำ → แก้บูต + `run_local.ps1`)
- [x] **ffmpeg แปลงภาพ AI → วีดีโอ Reels 9:16** (Ken Burns ซูม/เลื่อน + ข้อความ hook)
- [x] **คลิปรวม montage A/B** หลายช็อต + ครอสเฟด (`/api/stores/{id}/reel`) + ปุ่มใน Dashboard
- [x] **เสียงพากย์ไทยนิวรัล (edge-tts)** เลือกได้ ผู้หญิง/ผู้ชาย + retry กัน throttle (fallback gTTS)
- [x] **เพลงประกอบ** (ไฟล์ใน `data/music/` หรือเพลงคลอ ambient เริ่มต้น)
- [x] เก็บ `image_path` ต้นฉบับ + เล่น `<video>` ใน Dashboard
- [x] **n8n Full Pipeline (5 เลเยอร์)** import เข้าบัญชี n8n แล้ว (sticky note + manual/schedule)
- [x] ติดตั้งครบ: gh CLI · ffmpeg · n8n (native) · edge-tts/gTTS
- [x] เลือกเสียงพากย์ ผู้หญิง/ผู้ชาย ต่อคลิป (dropdown ใน Dashboard + `?voice=`)

## ✅ Sprint 2.6 — Scraper จริง + GitHub (เสร็จล่าสุด)
- [x] **scraper backend หลายโหมด** (direct/scraperapi/scrapingbee/apify) + retry + graceful + `/api/scrape`
- [x] ยืนยัน: direct & ScraperAPI ฟรี → โดน Shopee บล็อก 403 (Shopee ต้อง premium proxy แบบจ่ายเงิน)
- [x] **Apify ใช้งานได้จริง** — actor `xtracto/shopee-search` (จ่ายต่อผลลัพธ์ ใช้เครดิตฟรี $5) bypass Shopee → **fetched 30 / added 30** สินค้าจริง
- [x] `APIFY_INPUT` template (แทน {KEYWORD}/{LIMIT}) + parser รองรับ field actor + filter review_count=0 ไม่ตัด
- [x] แก้ `run-all` background รันเรียงทีละร้าน (กัน SQLite lock) + เปิด WAL + busy_timeout
- [x] ลบร้านเดโม (ล้าง DB + สื่อ 273 ไฟล์) — ระบบสะอาดพร้อมของจริง
- [x] **Commit + Push GitHub** `Domezzxx/shopee-affiliate-autopilot` (private) — main + sprint2-connect-apis · ไม่มี secret/.env/data หลุด
- [x] แก้บั๊ก `setup_github.ps1` (`ErrorActionPreference=Continue`)
- note: เป็น **สินค้า Shopee** (ไม่ใช่ร้าน Shopee Food เดลิเวอรี่ — ไม่มี actor) · เปลี่ยน `SHOPEE_KEYWORDS` ใน .env เลือก niche ได้

## ✅ Sprint 2.7 — สมองวีดีโอระดับโลก (เสร็จล่าสุด)
> แก้ปัญหา "คลิปน่าเบื่อ" → คอนเทนต์ครีเอเตอร์ระดับโลก
- [x] **ซับไตเติลเด้งตามเสียง (TikTok-style)** — แยกพากย์ทีละบรรทัด (edge-tts) → วัดเวลาจริง (ffprobe) → สร้าง ASS ซิงค์ + แอนิเมชัน pop → burn เข้าวีดีโอ (ไทยไม่มี word-boundary เลยใช้วิธี per-phrase)
- [x] **อัปเกรด prompt สคริปต์** — voiceover เป็น spoken-word (hook สะกิด → จุดขายเจาะจง → CTA), ภาพมีไอ/แสงสวย
- [x] เอา hook box เดิมออกจาก montage (เหลือซับเด้งสะอาดๆ) + แก้ ffmpeg ass filter (cwd=media เลี่ยง C:)
- [x] ทดสอบจริง: "เฮ้ย! ก๋วยเตี๋ยวเรือ 40 บาทจริงดิ?!" + ภาพก๋วยเตี๋ยวมีไอ + ซับขาวเด้ง ✅ (ดูเฟรมยืนยันแล้ว)

## 🟡 Sprint 3 — โพสต์จริง (โค้ดเสร็จแล้ว — รอ credential + App Review)
- [x] **FB Page โพสต์จริง** — อัปโหลดไฟล์ตรง multipart (วีดีโอ→/videos, ภาพ→/photos) ไม่ต้อง public URL
- [x] **IG Reels** — container (media_type=REELS) + poll + media_publish · ⚠️ ต้องตั้ง `PUBLIC_BASE_URL`
- [x] **YouTube Shorts** — OAuth refresh → resumable upload (videos.insert) + #Shorts
- [x] **random delay** ระหว่างโพสต์ (`ENABLE_POST_DELAY`) สุ่ม 15-45 นาที กัน spam
- [ ] รอ user: Meta App + permission (pages_manage_posts, instagram_content_publish) + **App Review**
- [ ] รอ user: YouTube OAuth (client_id/secret + refresh_token)
- [ ] รอ user: **PUBLIC_BASE_URL** สำหรับ IG (โฮสต์ /media ให้ public เช่น ngrok/cloudflared)

## 🔜 Sprint 4 — Phone Farm จริง (6 เครื่อง)
- [ ] ผูก uiautomator2 / Appium ต่อแอป (FB/IG/YouTube) — แตะปุ่ม+พิมพ์แคปชั่นจริง
- [ ] จัดคิว + lock ต่อเครื่อง กันชนกัน + เช็คสุขภาพเครื่อง (online/offline)
- [ ] anti-detection: สลับบัญชี, สุ่ม delay, จำลอง human behavior

## 🔜 Sprint 5 — Optimize + Scale
- [ ] ดึง metric จริงจาก platform (FB Insights / IG / YouTube Analytics) เข้า /api/metrics
- [ ] A/B ตัดสินอัตโนมัติ → ครั้งต่อไปใช้ variant ผู้ชนะเป็น base
- [ ] รายงานสรุป/วัน (Telegram/LINE) + กราฟใน dashboard
- [ ] รองรับหลายจังหวัด/หลายคีย์เวิร์ด

---

## Backlog / ไอเดียเพิ่ม
- เพิ่ม TikTok + Shopee Video (ตาม flowchart เดิม) เป็น connector
- ระบบ approve คอนเทนต์ก่อนโพสต์ (human-in-the-loop) สำหรับร้านสำคัญ
- คิดราคา/กำไรต่อร้าน real-time + ตัดร้านขาดทุนอัตโนมัติ
