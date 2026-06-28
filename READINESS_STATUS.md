# สถานะความพร้อมระบบ — Affiliate Autopilot
อัปเดต: 27 มิ.ย. 2026

> หมายเหตุ: บูตจริงในแซนด์บ็อกซ์ไม่ได้ (เครือข่ายติดตั้ง dependencies ไม่เสถียร) จึงตรวจแบบ static
> (อ่านโค้ด config/pipeline + เช็คค่าใน `.env`) — รันจริงให้ทำที่เครื่องคุณด้วย `.\run_local.ps1`

## ค่าใน .env ตอนนี้

| คีย์ | สถานะ | ผลต่อระบบ |
|------|-------|-----------|
| CONTENT_PROVIDER | ✅ gemini | เลือก Gemini เป็นคนเขียนคอนเทนต์ |
| GEMINI_API_KEY | ❌ ว่าง | **บล็อกหลัก** — คอนเทนต์ + ภาพ ตกไปโหมด mock |
| ANTHROPIC_API_KEY | ✅ ตั้งแล้ว | ใช้ได้ถ้าสลับ provider=claude |
| META_APP_ID / SECRET | ✅ | ฐานสำหรับสร้าง token |
| META_PAGE_ID | ✅ 793043437219272 | โพสต์ Facebook ได้ |
| META_ACCESS_TOKEN | ⚠️ ตั้งแล้ว (อายุสั้น ~1-2ชม.) | ต้องแลกเป็น long-lived |
| META_IG_USER_ID | ❌ ว่าง | โพสต์ Instagram ไม่ได้ |
| PUBLIC_BASE_URL | ❌ ว่าง | IG ต้องมี public URL ของสื่อ |
| YOUTUBE_CLIENT_ID / SECRET | ✅ | ฐาน OAuth |
| YOUTUBE_REFRESH_TOKEN | ❌ ว่าง | โพสต์ YouTube ไม่ได้ |
| SCRAPER_MODE | ✅ scraperapi | — |
| SCRAPER_API_KEY | ❌ ว่าง | **ดึงร้าน Shopee ไม่ได้** → ไม่มีข้อมูลเข้าระบบ |
| SHOPEE_AFFILIATE_* | ❌ ว่าง | ยังใส่ลิงก์เองได้ (ไม่เร่งด่วน) |

## พร้อม/ไม่พร้อม แต่ละขั้นของวงจร

1. ดึงร้าน (scrape) — ❌ ไม่มี SCRAPER_API_KEY
2. เขียนคอนเทนต์ (AI) — ❌ GEMINI_API_KEY ว่าง (หรือสลับเป็น claude ก็ได้)
3. ทำภาพ — ❌ ต้องมี GEMINI_API_KEY
4. ทำวีดีโอ (Google Flow) — ⚠️ ไม่ใช้ key แต่ต้องเปิด Chrome debug + ล็อกอิน Flow
5. เสียงพากย์ไทย (edge-tts) — ✅ ฟรี ไม่ต้องใช้ key
6. โพสต์ Facebook — ✅ พร้อม (แต่ token อายุสั้น)
7. โพสต์ Instagram — ❌ ขาด IG_USER_ID + PUBLIC_BASE_URL
8. โพสต์ YouTube — ❌ ขาด REFRESH_TOKEN

## สิ่งที่ต้องทำ เรียงตามความคุ้ม

**P0 — ทำให้วงจรเดินได้**
1. วาง **GEMINI_API_KEY** (คัดลอกคีย์ที่มีอยู่แล้วใน AI Studio) → ปลดล็อกข้อ 2+3 ทันที
2. ขอ **SCRAPER_API_KEY** ฟรีที่ scraperapi.com (1,000 ครั้ง/เดือน) → ปลดล็อกข้อ 1
   - หรือทดสอบก่อนโดย POST ร้านเข้า `/api/ingest` เองโดยไม่ต้องมี scraper

**P1 — ทำให้ Facebook ใช้ได้ยาว + เปิด IG**
3. แลก META_ACCESS_TOKEN เป็น **long-lived** (60 วัน)
4. ผูกบัญชี IG Business กับเพจ → เอา **META_IG_USER_ID**
5. ตั้ง **PUBLIC_BASE_URL** (รัน `./scripts/start_tunnel.ps1` ได้ URL อัตโนมัติ)

**P2 — YouTube**
6. รัน `python scripts/youtube_oauth.py` เพื่อได้ **YOUTUBE_REFRESH_TOKEN**

## วิธีรันจริงที่เครื่องคุณ
```powershell
cd C:\Users\ChaiwatA\shopee-affiliate-autopilot
.\run_local.ps1
# เปิด Dashboard: http://127.0.0.1:8088
```
รันได้เลยแม้ยังไม่ครบคีย์ — ส่วนที่ขาดจะเป็นโหมด mock ให้เห็น flow ก่อน
