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

## 🔜 Sprint 2 — เชื่อมของจริง (ต่อ credential)
- [ ] ใส่ Anthropic key → เขียนคอนเทนต์จริง + จูน prompt ภาษาไทยให้ไวรัล
- [ ] ใส่ Gemini key → ทดสอบภาพ Nano Banana จริง (9:16) + เปิดวีดีโอ Veo
- [ ] n8n: ทำ node scrape Shopee ให้เสถียร (ต่อ proxy / Apify) + map field ให้ตรง
- [ ] ใส่ affiliate link จริง + logic วางคอมเมนต์แรกอัตโนมัติหลังโพสต์

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
