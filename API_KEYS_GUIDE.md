# คู่มือขอ API Key — Shopee Affiliate Autopilot

> อัปเดต: 27 มิ.ย. 2026
> ขั้นตอน "ล็อกอิน / กดยอมรับเงื่อนไข / ผูกบัตร / คัดลอกคีย์" ต้องทำด้วยตัวคุณเอง
> ค่าทุกตัวกรอกลงไฟล์ `.env` (คัดลอกจาก `.env.example`) — ชื่อตัวแปรในวงเล็บคือ key ใน `.env` ของคุณ
> **ห้าม** push `.env` ขึ้น Git

ลำดับแนะนำสำหรับ "ใช้งานได้พื้นฐาน": Gemini (ฟรี) → Shopee Affiliate → Meta/Instagram → Claude (ค่อยเปิดทีหลังตอนใช้จริง)

---

## 1) Google Gemini (ฟรี — เริ่มอันนี้ก่อน) → `GEMINI_API_KEY`

1. เข้า `https://aistudio.google.com/apikey` ล็อกอินบัญชี Google
2. กด **Create API key** → เลือก/สร้างโปรเจกต์
3. คัดลอกใส่ `.env`: `GEMINI_API_KEY=...`

มี free tier ไม่ต้องผูกบัตร ใช้ได้ทั้งเขียนข้อความ (`gemini-2.5-flash`) และทำภาพ (`gemini-2.5-flash-image`)

---

## 2) Shopee Affiliate Open API → `SHOPEE_AFFILIATE_APP_ID`, `SHOPEE_AFFILIATE_SECRET`

1. เข้า `https://affiliate.shopee.co.th` ล็อกอินด้วยบัญชี Shopee
2. สมัครเข้าโครงการ Affiliate และ**รออนุมัติ** (บางบัญชีทันที บางบัญชีต้องรอ)
3. เมื่ออนุมัติ → เมนู **Open API** (อาจอยู่ใต้ Account / Settings)
4. กด **Create / Generate** → ได้ **App ID** + **App Secret**
5. ใส่ `.env`: `SHOPEE_AFFILIATE_APP_ID=...`, `SHOPEE_AFFILIATE_SECRET=...`

หมายเหตุ: Shopee ไม่มีเอกสาร API สาธารณะสำหรับ affiliate ต้องดู parameter หลังล็อกอินในแดชบอร์ด

---

## 3) Meta (Facebook Graph API) → `META_PAGE_ID`, `META_ACCESS_TOKEN`

1. เข้า `https://developers.facebook.com` ล็อกอิน → ยืนยันเป็น Developer (อาจต้องยืนยันเบอร์/อีเมล)
2. **My Apps → Create App** → เลือกประเภท **Business**
3. **Settings → Basic** จะเห็น **App ID** + **App Secret** (กด Show)
4. ผูกแอปกับ **Facebook Page** ของคุณ แล้วเอา **Page ID** ใส่ `META_PAGE_ID`
5. สร้าง **Long-lived Page Access Token** (ผ่าน Graph API Explorer) ใส่ `META_ACCESS_TOKEN`
6. permission ที่โปรเจกต์ใช้: `pages_manage_posts`, `pages_read_engagement`, `instagram_content_publish` (ต้องผ่าน App Review ก่อนใช้จริงกับบัญชีอื่น)

---

## 4) Instagram (ใช้ App + Token เดียวกับ Meta) → `META_IG_USER_ID`

> สำคัญ: Instagram Basic Display API ปิดตัวแล้ว (4 ธ.ค. 2024) — รองรับเฉพาะบัญชี **Business / Creator** เท่านั้น บัญชีส่วนตัวใช้ไม่ได้

1. แปลงบัญชี IG เป็น **Business/Creator** แล้วเชื่อมกับ Facebook Page เดียวกับข้อ 3
2. ในแอป Meta เพิ่ม product **Instagram**
3. หา **Instagram User ID** (ผ่าน Graph API: `me/accounts` → `instagram_business_account`) ใส่ `META_IG_USER_ID`
4. ใช้ `META_ACCESS_TOKEN` ตัวเดียวกับข้อ 3 (token short-lived ~1 ชม. → แลกเป็น long-lived ~60 วันด้วย grant `ig_exchange_token`)

---

## 5) Claude (Anthropic) — ทำทีหลังตอนใช้จริง → `ANTHROPIC_API_KEY`

> ตอนทดสอบใช้ `CONTENT_PROVIDER=gemini` ได้เลย ไม่ต้องมีคีย์นี้ก่อน

1. เข้า `https://console.anthropic.com` ล็อกอิน/สมัคร
2. เมนู **API Keys → Create Key** → ตั้งชื่อ → **คัดลอกทันที** (โชว์ครั้งเดียว)
3. ใส่ `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. ต้องเติมเครดิต (Billing → ผูกบัตร) ก่อนเรียกใช้จริง

---

## ความปลอดภัยของคีย์

- เก็บใน `.env` เท่านั้น และให้ `.env` อยู่ใน `.gitignore`
- อย่าแชร์คีย์ในแชต/รูป/สกรีนช็อต
- คีย์หลุด → กลับไปหน้าเดิมกด **Revoke / Regenerate** ทันที
- Token ของ Meta/Instagram หมดอายุได้ ต้องตั้ง refresh เป็นรอบ

---

## Sources
- [Shopee Affiliate Integration (wecantrack)](https://wecantrack.com/shopee-integration/)
- [Shopee API Guide 2026 (api2cart)](https://api2cart.com/api-technology/shopee-api/)
- [Instagram Platform Access Token (Meta)](https://developers.facebook.com/docs/instagram-platform/reference/access_token/)
- [Instagram Get Started (Meta)](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started/)
