# 📘 คู่มือขอ API — Affiliate Autopilot (สำหรับพี่กอล์ฟ)

> ระบบทำคลิปรีวิวอาหาร + โพสต์อัตโนมัติ · ต้องใส่ "กุญแจ (API key)" ของแต่ละบริการก่อนใช้งานจริง
> **ทุก key ใส่ในไฟล์เดียว: `.env`** (อยู่ในโฟลเดอร์โปรเจกต์ `affiliate-autopilot\.env`)

---

## ⭐ สรุปเร็ว — ขอตัวไหนก่อน

| ลำดับ | API | ใช้ทำอะไร | ฟรี/จ่าย | จำเป็นไหม |
|------|-----|----------|---------|-----------|
| 1 | **Gemini** | เขียนแคปชั่น + สร้างภาพ + วีดีโอ | 🟢 ฟรี | **ต้องมี** (หัวใจ) |
| 2 | **YouTube** | โพสต์ Shorts อัตโนมัติ | 🟢 ฟรี | ถ้าจะโพสต์ YouTube |
| 3 | **Pexels** | footage อาหารจริง (วีดีโอ) | 🟢 ฟรี | แนะนำ (คลิปสวยขึ้น) |
| 4 | **Freesound** | เสียงบรรยากาศร้าน (ASMR) | 🟢 ฟรี | แนะนำ |
| 5 | **Apify** | ดึงร้าน/สินค้า Shopee | 🟢 ฟรี $5 | ถ้าจะดึงร้านอัตโนมัติ |
| 6 | **Shopee Affiliate** | สร้างลิงก์ affiliate (คอมมิชชั่นเข้าพี่กอล์ฟ) | 🟢 ฟรี | **ต้องมี** ถ้าจะได้เงิน |
| 7 | **Meta (FB+IG)** | โพสต์ Facebook + Instagram | 🟢 ฟรี* | ถ้าจะโพสต์ FB/IG |
| 8 | Claude (Anthropic) | เขียนแคปชั่น (คุณภาพสูงกว่า) | 🔴 จ่าย | ไม่จำเป็น (มี Gemini แล้ว) |

> \* Meta ฟรี แต่ต้องผ่าน "App Review" ถึงจะโพสต์เพจคนอื่นได้ (เพจตัวเองทดสอบได้เลย)

**ขั้นต่ำที่สุด:** มีแค่ **Gemini** ตัวเดียว ระบบก็ทำคลิปได้แล้ว · อยากโพสต์ค่อยเพิ่ม YouTube/Meta

---

## 💸 แผนค่าใช้จ่าย API — เริ่มได้ "ฟรี 100%"

> สรุปสั้น: **เริ่มต้นไม่ต้องจ่ายเลยสักบาท** ของที่เสียเงินทั้งหมดเป็น "ตัวเลือกตอน scale" ไม่ใช่ของบังคับ

| API | ฟรีได้แค่ไหน | จ่ายเมื่อไหร่ | ค่าใช้จ่ายถ้าจ่าย (ประมาณ) |
|-----|-------------|--------------|--------------------------|
| **Gemini** (ข้อความ+ภาพ) | ฟรี — ลิมิตต่อนาที/วัน พอใช้จริง | เกินลิมิตหนักๆ / ใช้ Veo วีดีโอ | ข้อความ+ภาพ ~ฟรี · Veo วีดีโอ ~฿15-25/วินาที (แพง — เลี่ยงได้) |
| **Google Flow** (วีดีโอ AI) | ฟรี — เครดิตจำกัดต่อวัน | อยากได้เครดิตเยอะ | Google AI Pro ~฿700/เดือน (เครดิต Flow เยอะขึ้น) |
| **YouTube** | ฟรี 100% — อัปได้ ~6 คลิป/วัน | ไม่มี | ฿0 |
| **Pexels** | ฟรี 100% — 20,000 ครั้ง/เดือน | ไม่มี | ฿0 |
| **Freesound** | ฟรี 100% | ไม่มี | ฿0 |
| **Shopee Affiliate** | ฟรี 100% — **ตัวนี้ทำเงินให้!** | ไม่มี | ฿0 (ได้คอมมิชชั่นกลับ) |
| **Meta (FB+IG)** | ฟรี 100% | ไม่มี | ฿0 |
| **Apify** (ดึงร้าน Shopee) | ฟรี $5 เครดิต/เดือน (~พอใช้) | ดึงร้านเยอะมาก/เดือน | แพ็กเริ่มต้น ~฿1,700/เดือน |
| **Claude** (เขียนแคปชั่น) | ❌ ไม่มีฟรี | ถ้าเลือกใช้แทน Gemini | ~฿0.5-2/คลิป (มี Gemini ฟรีแทนได้) |

### 📊 3 แผนตามงบ

**🟢 แผนฟรีล้วน — ฿0/เดือน** (แนะนำเริ่มตรงนี้)
- Gemini (ฟรี) + Google Flow (ฟรี) + YouTube + Pexels + Freesound + Shopee Affiliate
- ทำคลิป + โพสต์ YouTube + มีลิงก์ทำเงิน ได้ครบ
- ข้อจำกัด: เครดิต Flow/Gemini จำกัดต่อวัน → ทำได้ ~ไม่กี่คลิป/วัน (พอสำหรับเริ่ม + ทดสอบตลาด)

**🟡 แผนกึ่งโปร — ~฿700/เดือน**
- เพิ่ม **Google AI Pro** (เครดิต Flow เยอะ → ทำคลิปวีดีโอได้มากขึ้น/สวยขึ้น)
- ดึงร้านใช้ Apify ฟรี $5 ก็พอ
- เหมาะตอนเริ่มมีคลิปติด อยากเพิ่มจำนวน/คุณภาพ

**🔴 แผนสเกล — ~฿2,500-4,000/เดือน**
- Google AI Pro (~฿700) + Apify แพ็กจ่าย (~฿1,700) + Claude เขียนแคปชั่นเทพ (~฿200-500)
- โพสต์หลายช่อง/หลายร้าน วันละหลายคลิป อัตโนมัติเต็มสูบ
- เหมาะตอนพิสูจน์แล้วว่าคอมมิชชั่นคุ้มค่าใช้จ่าย

### 💰 จุดคุ้มทุน
คอมมิชชั่น Shopee Affiliate เฉลี่ย ~฿6/คลิก · ถ้าคลิปทำคลิกได้ **วันละ ~120 คลิก = ~฿700/วัน** ก็คืนค่าแผนกึ่งโปรทั้งเดือนแล้ว
> 👉 กลยุทธ์: **เริ่มฟรี → ดูว่าคลิปไหนทำคลิก (ใช้ sub_id track) → ค่อยจ่ายเพื่อ scale เฉพาะตัวที่เวิร์ก**

> ⚠️ ราคาด้านบนเป็นค่าประมาณ (อิงเรตปัจจุบัน ~36 บาท/ดอลลาร์) ผู้ให้บริการอาจปรับเปลี่ยน — เช็คหน้าราคาจริงก่อนสมัครแบบจ่ายเงิน

---

## 📝 วิธีใส่ key ลงไฟล์ `.env`

1. เปิดโฟลเดอร์ `affiliate-autopilot`
2. หาไฟล์ชื่อ **`.env`** (ถ้าไม่มี ก๊อปจาก `.env.example` มาตั้งชื่อ `.env`)
3. เปิดด้วย Notepad → หาบรรทัดของ key นั้น → วางค่าหลังเครื่องหมาย `=` (ห้ามเว้นวรรค ห้ามใส่เครื่องหมายคำพูด)
4. เซฟ → **รีสตาร์ทระบบ** (`./scripts/start.ps1`)

ตัวอย่าง:
```
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXX
```

> ⚠️ ไฟล์ `.env` เป็นความลับ — อย่าส่งให้ใคร อย่าอัปขึ้น GitHub (ระบบกันไว้แล้ว)

---

## 1️⃣ Gemini (Google AI) — 🟢 ฟรี — **สำคัญสุด**
**ใช้:** เขียนแคปชั่น/สคริปต์ + สร้างภาพอาหาร (Nano Banana) + วีดีโอ (Veo)

**ขอที่:** https://aistudio.google.com/apikey
1. ล็อกอินด้วย Google
2. กด **"Create API key"** → **"Create API key in new project"**
3. ก๊อปกุญแจ (ขึ้นต้น `AIza...`)

**ใส่ใน `.env`:**
```
GEMINI_API_KEY=AIza...        ← วางกุญแจตรงนี้
CONTENT_PROVIDER=gemini       ← บอกระบบให้ใช้ Gemini เขียน (ฟรี)
```

---

## 2️⃣ YouTube — 🟢 ฟรี — โพสต์ Shorts
**ใช้:** อัปโหลดคลิปขึ้น YouTube อัตโนมัติ · ต้องทำ 2 ขั้น

### ขั้น A: สร้าง OAuth client (ที่ Google Cloud Console)
**ขอที่:** https://console.cloud.google.com
1. สร้าง Project ใหม่ (มุมบนซ้าย)
2. เมนู **APIs & Services → Library** → ค้น **"YouTube Data API v3"** → กด **Enable**
3. **APIs & Services → OAuth consent screen** → เลือก **External** → ใส่ชื่อแอป + อีเมล → ในหัวข้อ **Test users** กด **+ ADD USERS** ใส่อีเมล Google ที่จะใช้โพสต์ (สำคัญ! ไม่งั้นโดนบล็อก)
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → ประเภท **Desktop app** → ได้ **Client ID** + **Client secret**

### ขั้น B: ขอ refresh token (รันสคริปต์ช่วย)
ใส่ Client ID/secret ลง `.env` ก่อน:
```
YOUTUBE_CLIENT_ID=...apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-...
```
แล้วรัน (ใน PowerShell ที่โฟลเดอร์โปรเจกต์):
```powershell
./venv/Scripts/python.exe scripts/youtube_oauth.py
```
→ เบราว์เซอร์เด้งให้ล็อกอิน + กด Allow → ระบบเขียน `YOUTUBE_REFRESH_TOKEN` ลง `.env` ให้เอง ✅

> เจอ "Google hasn't verified this app" = ปกติ (แอปเราเอง) → กด **Advanced → Go to ... (unsafe)** → Allow

---

## 3️⃣ Pexels — 🟢 ฟรี — footage อาหารจริง
**ใช้:** ดึงคลิปวีดีโออาหารจริง (เส้นยืด/ไอลอย/คนกิน) มาผสมให้คลิปดูเป็นรีวิวจริง

**ขอที่:** https://www.pexels.com/api/
1. กด **"Get Started"** → สมัคร/ล็อกอิน (ใช้ Google ได้)
2. ตอบคำถามสั้นๆ → ได้ **API Key** ทันที

**ใส่ใน `.env`:**
```
PEXELS_API_KEY=...
```

---

## 4️⃣ Freesound — 🟢 ฟรี — เสียงบรรยากาศร้าน
**ใช:** เสียง chatter ในร้าน/ASMR คลอใต้เสียงพากย์ ให้คลิปมีชีวิต

**ขอที่:** https://freesound.org/apiv2/apply/
1. สมัคร/ล็อกอินที่ freesound.org ก่อน
2. ไปหน้า apply → กรอกชื่อแอป + คำอธิบายสั้นๆ → Submit
3. ได้ **API Key** (ช่อง "Client secret/Api key")

**ใส่ใน `.env`:**
```
FREESOUND_API_KEY=...
```

---

## 5️⃣ Apify — 🟢 ฟรี ($5 เครดิต/เดือน) — ดึงร้าน Shopee
**ใช้:** ดึงรายการสินค้า/ร้านจาก Shopee อัตโนมัติ (Shopee กันบอท ต้องใช้ตัวนี้)

**ขอที่:** https://apify.com → สมัคร (ฟรี)
1. ล็อกอิน → มุมขวาบน **Settings → Integrations → API tokens**
2. ก๊อป **Personal API token** (ขึ้นต้น `apify_api_...`)

**ใส่ใน `.env`:**
```
APIFY_TOKEN=apify_api_...
APIFY_ACTOR=xtracto~shopee-search
SCRAPER_MODE=apify
SHOPEE_KEYWORDS=ก๋วยเตี๋ยว        ← เปลี่ยนคำค้นร้านได้
```

---

## 6️⃣ Shopee Affiliate API — 🟢 ฟรี — **ตัวทำเงิน!** 💰
**ใช:** สร้าง **ลิงก์ affiliate ของพี่กอล์ฟ** อัตโนมัติ (ใส่ในคอมเมนต์แรก) → คนกดซื้อ = **พี่กอล์ฟได้คอมมิชชั่น**
> นี่คือหัวใจของการ "หาเงิน" — ถ้าไม่มีตัวนี้ คลิปโพสต์ได้แต่ไม่มีลิงก์ที่ track คอมมิชชั่น

### ขั้น A: สมัครเป็น Shopee Affiliate
**สมัครที่:** https://affiliate.shopee.co.th/ (Shopee Affiliate Program)
1. สมัคร + ยืนยันตัวตน (บัตรประชาชน + บัญชีรับเงิน)
2. รออนุมัติ (ปกติ 1-3 วัน) → เข้าแดชบอร์ด affiliate ได้

### ขั้น B: ขอ Open API (App ID + Secret)
1. เข้าแดชบอร์ด Shopee Affiliate → หาเมนู **"Open API"** หรือ **"API Management"** (อยู่ในส่วนเครื่องมือ/Tools)
2. กดขอใช้ Open API → ได้ **App ID** + **Secret/Key**
   - Endpoint (GraphQL): `https://open-api.affiliate.shopee.co.th/graphql`
   - การยืนยัน: ใช้ลายเซ็น SHA256(AppId + Timestamp + Payload + Secret)
   - ความสามารถ: สร้าง short link + ใส่ sub_id (track ว่าลิงก์ไหนมาจากคลิปไหน) + ดูคอมมิชชั่น/ยอด

**ใส่ใน `.env`:**
```
SHOPEE_AFFILIATE_APP_ID=...
SHOPEE_AFFILIATE_SECRET=...
```

> ✅ **build แล้ว!** engine `backend/app/engines/shopee_affiliate.py` — พอใส่ APP_ID+SECRET ใน `.env`
> ระบบจะ **สร้างลิงก์ affiliate เอง + ใส่ sub_id track อัตโนมัติตอนโพสต์** (sub_id = `s<ร้าน>_<แพลตฟอร์ม>_<A/B>` → รู้ว่าคอมมิชชั่นมาจากคลิปไหน/ช่องไหน)
> ถ้า**ไม่ใส่** key → ระบบ fallback ไปใช้ลิงก์ที่ใส่เองต่อร้าน (ช่อง affiliate_link) เหมือนเดิม — ไม่พัง

**ทดสอบว่าต่อ API ติดไหม** (หลังใส่ key + รันเซิร์ฟเวอร์):
```
POST http://127.0.0.1:8088/api/affiliate/link?url=<URL ร้าน Shopee>&sub_id=test
```
ได้ลิงก์สั้นกลับมา = ต่อสำเร็จ 🎉 (ถ้า error เช็ค key หรือ URL · ดูสเปกลายเซ็น SHA256 ด้านบน)

> 💡 ยังไม่อยากต่อ API ก็ได้: เข้าแดชบอร์ด affiliate → สร้างลิงก์เอง → ก๊อปมาใส่ช่อง "affiliate link" ตอนเพิ่มร้านในเว็บ ก็ได้คอมมิชชั่นเหมือนกัน (แค่ไม่มี sub_id track ละเอียด)

---

## 7️⃣ Meta (Facebook + Instagram) — 🟢 ฟรี — โพสต์ FB/IG
**ใช้:** โพสต์ลง Facebook Page + Instagram อัตโนมัติ · ยุ่งสุดในบรรดาทั้งหมด

**ขอที่:** https://developers.facebook.com
1. ต้องมี **Facebook Page** (เพจ ไม่ใช่โปรไฟล์) + ถ้าจะลง IG ต้องเป็น **IG Business** ผูกกับเพจ
2. **My Apps → Create App → Business**
3. **Tools → Graph API Explorer** → Generate Access Token → ติ๊กสิทธิ์: `pages_manage_posts`, `pages_read_engagement`, `instagram_content_publish`
4. หา **Page ID** (ในหน้าเพจ → About) และ **IG User ID**

**ใส่ใน `.env`:**
```
META_PAGE_ID=...
META_IG_USER_ID=...
META_ACCESS_TOKEN=...
PUBLIC_BASE_URL=          ← เฉพาะ IG (โฮสต์สื่อ public) รัน ./scripts/start_tunnel.ps1 จะใส่ให้
```
> ⚠️ โพสต์เพจตัวเองทดสอบได้เลย · โพสต์โปรดักชันจริงต้องผ่าน **App Review** (~1-2 สัปดาห์)
> 📄 รายละเอียดเพิ่ม: `SETUP_SPRINT3.md`

---

## 8️⃣ Claude (Anthropic) — 🔴 จ่ายเงิน — ไม่จำเป็น
**ใช:** เขียนแคปชั่นคุณภาพสูงกว่า Gemini (ภาษาไทยลื่นกว่า) · **ข้ามได้** เพราะ Gemini ฟรีพอแล้ว

**ขอที่:** https://console.anthropic.com → API Keys → Create Key
```
ANTHROPIC_API_KEY=sk-ant-...
CONTENT_PROVIDER=claude      ← เปลี่ยนเป็น claude ถ้าจะใช้
```

---

## 🔧 ของที่ไม่ใช่ API (setup อื่น)

| สิ่ง | คืออะไร | ทำยังไง |
|------|---------|---------|
| **Google Flow** (วีดีโอ AI ฟรี) | ไม่ใช่ key — ใช้ล็อกอินใน Chrome | รัน `./scripts/start.ps1` (เปิด Chrome ให้) → ล็อกอิน labs.google/flow ครั้งเดียว |
| **AI persona พูดได้** (พ่อครัว) | โมเดล Wav2Lip | รัน `./scripts/setup_persona.ps1` ครั้งเดียว (โหลดโมเดล) |
| **Phone Farm** (โพสต์ผ่านมือถือ) | IP มือถือ Android | `PHONE_FARM_DEVICES=192.168.1.51:5555,...` ใน `.env` |

---

## ✅ เช็คว่าใส่ครบไหม
เปิดระบบ (`./scripts/start.ps1`) แล้วดูบรรทัดสรุป หรือบนหน้าเว็บกดปุ่ม **🚦 เช็คพร้อมโพสต์** / hover ปุ่ม **● ระบบ** จะเห็นว่าตัวไหน ✓ ตัวไหนยังขาด

## 🎯 แนะนำลำดับการขอ (ค่อยๆ ทำ)
1. **Gemini** (ทำคลิปได้เลย) → 2. **Shopee Affiliate** (ได้ลิงก์ทำเงิน 💰) → 3. **Pexels + Freesound** (คลิปสวยขึ้น) → 4. **YouTube** (โพสต์ได้) → 5. **Apify** (ดึงร้านเอง) → 6. **Meta** (เปิด FB/IG ตอนพร้อมจริง)

> 💰 **เน้น:** Gemini (ทำคลิป) + Shopee Affiliate (ลิงก์ทำเงิน) + YouTube (ช่องทางโพสต์) = ครบชุดเริ่มหาเงินได้
