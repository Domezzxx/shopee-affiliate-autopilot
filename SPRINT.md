# 🏃 Sprint Plan — Affiliate Autopilot

โปรเจกต์อิสระของพี่กอล์ฟ (แยกจาก Sentiara). ระบบ automation affiliate Shopee Food.

**สถาปัตยกรรมที่ล็อกแล้ว:** Hybrid posting (Official API + phone farm 6 เครื่อง) ·
Claude เขียนคอนเทนต์ + Gemini ทำภาพ/วีดีโอ · n8n web scraper อัตโนมัติ.

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
- [ ] (เลื่อน) Anthropic/Claude — ไม่ฟรี, ใช้ Gemini แทนช่วงทดสอบ ค่อยต่อตอนโปรดักชัน
- [ ] (เลื่อน) n8n scrape Shopee ให้เสถียร + proxy/Apify

## ✅ Sprint 2.5 — Media & Video + Infra (เสร็จวันนี้ ฟรีทั้งหมด)
- [x] **รัน native ไม่ใช้ Docker** (เครื่อง AMD เปิด WSL2 แล้วบูตจอดำ → แก้บูต + `run_local.ps1`)
- [x] **ffmpeg แปลงภาพ AI → วีดีโอ Reels 9:16** (Ken Burns ซูม/เลื่อน + ข้อความ hook)
- [x] **คลิปรวม montage A/B** หลายช็อต + ครอสเฟด (`/api/stores/{id}/reel`) + ปุ่มใน Dashboard
- [x] **เสียงพากย์ไทยนิวรัล (edge-tts)** เลือกได้ ผู้หญิง/ผู้ชาย + retry กัน throttle (fallback gTTS)
- [x] **เพลงประกอบ** (ไฟล์ใน `data/music/` หรือเพลงคลอ ambient เริ่มต้น)
- [x] เก็บ `image_path` ต้นฉบับ + เล่น `<video>` ใน Dashboard
- [x] **n8n Full Pipeline (5 เลเยอร์)** import เข้าบัญชี n8n แล้ว (sticky note + manual/schedule)
- [x] ติดตั้งครบ: gh CLI · ffmpeg · n8n (native) · edge-tts/gTTS
- [ ] ⚠️ **ยังไม่ commit ลง git** (อยู่ branch sprint2-connect-apis)

## 🔜 Sprint 3 — โพสต์จริง (Meta/YouTube API)
- [ ] Meta App + permission (pages_manage_posts, instagram_content_publish) + App Review
- [ ] FB Reels / IG Reels publish ผ่าน Graph API (รองรับวีดีโอ)
- [ ] YouTube OAuth refresh flow + resumable upload (Shorts)
- [ ] random delay 15–45 นาที + กระจายเวลาโพสต์ตามตาราง Claude

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
