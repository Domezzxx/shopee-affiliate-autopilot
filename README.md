# 🍜 Affiliate Autopilot

ระบบ **automation affiliate Shopee Food** ครบวงจร — เป็น **WebApp + Docker** รันใน local server.
ดึงร้าน → Claude เขียนคอนเทนต์ A/B → Gemini ทำภาพ/วีดีโอ → โพสต์ FB/IG/YouTube (Hybrid API + 6 มือถือ) →
Dashboard สรุปผล + A/B test + Auto-optimize หยุดร้านไม่เวิร์กเอง.

> 🚀 เริ่มเลย: อ่าน **[SETUP_TH.md](SETUP_TH.md)** — 3 คำสั่งก็รันได้ (รันได้แม้ยังไม่มี API key = โหมด mock)

```powershell
Copy-Item .env.example .env
docker compose up -d --build
# Dashboard → http://localhost:8088   ·   n8n → http://localhost:5678
```

## สถาปัตยกรรม
```
 n8n scraper ──POST /api/ingest──▶ Backend (FastAPI :8088) ──▶ SQLite + สื่อ
   (ทุก 6 ชม.)                         │
                                       ├─ Claude (claude-sonnet-4-6)  → แคปชั่น/สคริปต์/A-B
                                       ├─ Gemini (Nano Banana / Veo)  → ภาพ/วีดีโอ 9:16
                                       ├─ Connector Hybrid            → Graph API / YouTube / phone farm(ADB×6)
                                       └─ Dashboard (WebApp)          → KPI · A/B · Auto-optimize
```

## โครงสร้าง
```
affiliate-autopilot/
├─ docker-compose.yml          # backend + n8n + postgres
├─ .env.example                # ทุก config + วิธีขอ key
├─ SETUP_TH.md                 # คู่มือไทยละเอียด
├─ backend/
│  ├─ Dockerfile · requirements.txt
│  └─ app/
│     ├─ main.py               # FastAPI + เสิร์ฟ WebApp + auto-optimize loop
│     ├─ config.py · db.py     # settings + โครงข้อมูล (SQLModel)
│     ├─ api.py                # REST: ingest/run/posts/metrics/abtest/dashboard
│     ├─ engines/              # content_claude.py · media_gemini.py
│     ├─ connectors/social.py  # FB/IG/YouTube API + phone farm (ADB)
│     ├─ services/pipeline.py  # วงจรหลัก + A/B + auto-optimize
│     └─ static/               # Dashboard (HTML/CSS/JS, ไม่มี build step)
└─ n8n/workflows/              # 1_scrape_shopee · 2_pipeline_and_optimize
```

## API หลัก
| Method | Path | ใช้ทำอะไร |
|--------|------|-----------|
| POST | `/api/ingest` | รับร้านจาก n8n + กรอง |
| POST | `/api/run-all` | รันครบวงร้านใหม่ (ขั้น 2-4) |
| POST | `/api/stores/{id}/run` | รันครบวงร้านเดียว |
| GET  | `/api/content/{store_id}` | ดูคอนเทนต์ + variant + สื่อ |
| POST | `/api/metrics` | ป้อนผลจาก platform (A/B) |
| GET  | `/api/abtest/{store_id}` | ผล A/B + ผู้ชนะ |
| POST | `/api/auto-optimize` | หยุดร้าน CTR ต่ำ |
| GET  | `/api/dashboard` | สรุป KPI |

## หมายเหตุสำคัญ
- **Shopee ไม่มี affiliate API สาธารณะ** → ดึงผ่าน n8n scraper (แก้ node ให้ตรง + แนะนำ proxy)
- **Meta/YouTube** ต้องผ่าน App Review ก่อนโพสต์อัตโนมัติ — ระหว่างนั้นใช้ phone farm
- **phone farm**: โครง ADB + กระจาย 6 เครื่องพร้อม, ขั้น "แตะปุ่มในแอป" ต้องเสริม uiautomator2/Appium
- รันได้ทันทีในโหมด **mock** เพื่อทดสอบ flow ทั้งหมดก่อนเติม key
