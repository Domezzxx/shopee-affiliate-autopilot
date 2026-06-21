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

## 🟢 Sprint 3 — โพสต์จริง (โค้ด+เครื่องมือพร้อม เหลือ user ใส่ credential)
- [x] **FB Page โพสต์จริง** — อัปโหลดไฟล์ตรง multipart (วีดีโอ→/videos, ภาพ→/photos) ไม่ต้อง public URL
- [x] **IG Reels** — container (media_type=REELS) + poll status (FINISHED/ERROR/timeout) + media_publish
- [x] **YouTube Shorts** — OAuth refresh → resumable upload (videos.insert) + #Shorts
- [x] **random delay** ระหว่างโพสต์ (`ENABLE_POST_DELAY`) สุ่ม 15-45 นาที กัน spam
- [x] **error handling แน่นขึ้น** — `_err()` ดึงข้อความ Graph API จริง (ไม่ KeyError) + IG บอกสถานะ container ชัด
- [x] **Preflight** — `GET /api/post/preflight` ยิง API จริงเช็คความพร้อมต่อ platform + ปุ่ม **🚦 เช็คพร้อมโพสต์** บน dashboard
- [x] **public URL ฟรีสำหรับ IG** — `scripts/start_tunnel.ps1` (cloudflared quick tunnel, http2, เขียน PUBLIC_BASE_URL ลง .env เอง) — **ทดสอบจริงแล้ว /media เข้าถึง public ได้ HTTP 200**
- [x] **YouTube OAuth helper** — `scripts/youtube_oauth.py` (loopback flow ขอ refresh_token + เขียน .env)
- [x] **เช็คลิสต์ go-live** — `SETUP_SPRINT3.md` (ทำเอง FB/IG/YouTube ทีละขั้น)
- [ ] รอ user: Meta App + permission (pages_manage_posts, instagram_content_publish) + **App Review** (โปรดักชัน)
- [ ] รอ user: รัน `scripts/youtube_oauth.py` (มี Google Cloud OAuth Desktop client)

## ✅ Sprint 3.5 — Video Review Studio (รีวิวอาหารจริง ไม่ใช่สไลด์ — ฟรีล้วน)
> แก้ "คลิปเหมือนสไลด์น่าเบื่อ" → คลิปรีวิวในร้านจริง มี motion + คน + เสียงบรรยากาศ
- [x] **AI persona พูดได้ (Wav2Lip lip-sync, CPU, ฟรี)** — `engines/talking_head.py` (synthesize/overlay_pip วงกลม TikTok/add_persona_pip) + `scripts/setup_persona.ps1` (โหลดโมเดล+แพตช์ torch2.6/librosa). หน้า persona จาก Gemini: `influencer.png` (หนุ่ม PiP) + `chef.png` (ลุงพ่อครัวในร้าน)
- [x] **โหมดรีวิวในร้าน** — พ่อครัวพูดเต็มจอเปิด (blurred-fill 9:16) → ตัดเข้าแอคชั่น + พ่อครัว PiP วงกลม → ปิดชวน (`scripts/_chef_demo.py`)
- [x] **stock video จริง (Pexels)** — `engines/stock_video.py` + `build_queries` map เมนู→คิวรีเฉพาะ (เลี่ยง generic หลุดหัวข้อ/ราเมง). ⚠️ Pexels ไม่มีก๋วยเตี๋ยวเรือจริง → ได้แค่ noodle ใกล้เคียง (อยากเป๊ะต้อง Veo/ถ่ายเอง)
- [x] **เสียงบรรยากาศร้าน (Freesound)** — `engines/stock_sfx.py` (เสียง chatter ในร้านยาวต่อเนื่อง ไม่วนลูป + re-encode กันไฟล์เสีย + retry). แก้บั๊กเสียงประตู 1วิวนรัว
- [x] **`video_ffmpeg.py`:** เกรดสีอาหาร+vignette · xfade + ความเร็วแปรผัน (beat) · `build_review_reel` (เสียงพากย์ก่อน→ตัดภาพพอดี ไม่เหลือช่องว่าง + cap 22วิ) · `_video_clip` footage→9:16 · แยก `_mux_audio` (3-stream amix + retry)
- [x] `media_gemini`: `generate_food_broll` (หลายมุม) + `download_images` (รูป Shopee จริง)
- [x] **Google Flow AI Browser Automation (ฟรีผ่าน Chrome Debugging)** — พัฒนาสคริปต์ Playwright CDP ควบคุม Chrome เจนวิดีโอฟรีผ่านหน้าเว็บ Google Flow ลดต้นทุน Veo API
- [x] (เสร็จใน Sprint 6) เก็บเป็น engine ถาวร `build_restaurant_reel` + ปุ่ม dashboard · Flow video แก้ได้แล้ว (ดู Sprint 6 P2)

## ✅ Sprint 4 — Phone Farm จริง (6 เครื่อง) (เสร็จสมบูรณ์)
- [x] ผูก uiautomator2 ต่อแอป (FB/IG/YouTube) — แตะปุ่ม+พิมพ์แคปชั่นจริง อัปเดตไฟล์มีเดียแกลเลอรีอัตโนมัติ
- [x] จัดคิว + lock ต่อเครื่อง ด้วย Thread Locking กันชนกัน + ตรวจสอบสถานะการเชื่อมต่อ (online/offline)
- [x] anti-detection: จำลองการป้อนตัวอักษรแบบพิมพ์จริงทีละอักษร (Humanized typing) + หน่วงเวลาสุ่มป้องกันการแบน

## ✅ Sprint 6 — Production Auto-Pilot (รวม Flow video + ครบวงจรอัตโนมัติ) — เสร็จครบ P1-P2-P3
> breakthrough: Google Flow เจน **ก๋วยเตี๋ยวเรือ Veo จริง ฟรี** ได้ → หัวใจคอนเทนต์ + รันเองครบวง
- [x] **P1 โหมดรีวิวในร้าน (engine ถาวร)** `talking_head.build_restaurant_reel` (พ่อครัวเต็มจอ→แอคชั่น+PiP+ASMR + progress) + `pipeline.build_restaurant` (Flow video ถ้ามี ไม่งั้น stock) + endpoint + ปุ่ม "🍜 รีวิวในร้าน" · ทดสอบผ่าน
- [x] **P1 รวม Flow video เข้า reel** — `build_restaurant` หยิบ `video_flow_*.mp4` ของร้านเป็น hero footage ก่อน
- [x] **P2 Flow ทำงานได้! (เฉลย: ที่ fail = เครดิตหมด)** — submit ด้วย **Enter** (ปุ่มไม่ trigger generate) + จับช่อง prompt ที่มองเห็น (กัน textbox ซ่อน) + **ตรวจจับ "เครดิต/โควตาหมด"** fail เร็ว + **quota guard** (พัก Flow `flow_block_hours` ชม. → media_gemini ข้ามไป fallback) · มีเครดิตเมื่อไหร่ generate เองได้เลย
- [x] **P2 Auto-Pilot scheduler** — `_autopilot_loop` (ประมวลผลร้าน new เองตามรอบ) + `run_autopilot_once`/`scrape_and_run_all_seq` (รวม scrape+run) + toggle `/system/autopilot` สั่งรันทันที + ปุ่ม 🤖 Auto
- [x] **P3 รายงาน + A/B winner** — `/api/report/daily` (ร้าน/โพสต์/CTR/รายได้/ต้นทุน + ผู้ชนะ A/B) + แท็บ 📊 รายงาน
- [x] **โพสต์ครบวง** — progress bar ต่อ platform (YT/FB/IG ✓/✗ + สรุป) · YouTube ใช้ **reel วีดีโอ** ถ้า media เป็นภาพ · **dedup กันอัปสื่อซ้ำ** (กัน YouTube ลบคลิปซ้ำ) · ทดสอบ YouTube โพสต์จริงผ่าน
- [ ] (เลื่อน) ใช้ variant ผู้ชนะเป็น base รอบถัดไป · รายงานเข้า Telegram

## 🟢 Sprint 7 — Cloud Deploy + Production (เริ่มแล้ว — งาน Antigravity)
> เตรียมขึ้น production จริง ให้รันได้ตลอด ไม่ต้องเปิดเครื่องเอง
- [x] **รองรับ Vercel deploy** (`vercel.json` + `.vercelignore`) + **สลับ SQLite↔PostgreSQL อัตโนมัติ** (db.py — local=SQLite, cloud=Postgres)
- [x] **เปิด Chrome remote-debugging อัตโนมัติ** ถ้า port 9222 ปิด (`flow_automation` + endpoint `/chrome/open` + ปุ่มบน dashboard)
- [x] **ตัวกรอง UI** (กรองคอนเทนต์/โพสต์ใน dashboard)
- [ ] deploy ขึ้น Vercel จริง + ตั้ง PostgreSQL (Supabase/Neon) + env vars
- [ ] แยก worker เครื่องบ้าน (Flow/phone farm ต้องรันบนเครื่องที่มี Chrome+มือถือ) ↔ web บน cloud

## 🔜 Sprint 8 — Scale + ใช้งานจริง
- [ ] ใส่ Meta token จริง (เปิด FB/IG จาก mock) + App Review
- [ ] ดึง metric จริงจาก platform → A/B ตัดสิน → ใช้ winner เป็น base
- [ ] จำกัดโพสต์/วันต่อ platform (กัน spam flag) + เปิด post delay default
- [ ] รายงานเข้า Telegram/LINE + รองรับหลายคีย์เวิร์ด/จังหวัด

## ✅ เสร็จแล้วระหว่างทาง (ย้ายจาก backlog)
- [x] ระบบ approve คอนเทนต์ก่อนโพสต์ (human-in-the-loop) — Store.requires_approval + pending_approval + ปุ่มอนุมัติ
- [x] Shopee Video connector (phone farm `post_shopee_video`)
- [x] รายได้ประเมินต่อร้าน (affiliate_commission_per_click) ใน dashboard

---

## Backlog / ไอเดียเพิ่ม
- เพิ่ม TikTok เป็น connector (phone farm)
- คิดกำไรต่อร้าน real-time + ตัดร้านขาดทุนอัตโนมัติ
- Flow video: cache/reuse ต่อเมนู (ไม่เจนซ้ำ) + หลาย prompt ต่อร้าน
