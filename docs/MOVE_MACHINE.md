# 🚚 ย้ายเครื่อง / รันหลายเครื่องด้วย Docker — Affiliate Autopilot

เป้าหมาย: **ย้ายไปเครื่องใหม่ = ก๊อป 2 อย่าง + 1 คำสั่ง** แล้วได้ระบบ + ข้อมูล + ฐานข้อมูลครบเหมือนเดิม

---

## 🧠 ก่อนอื่น — "state" ของระบบนี้อยู่ที่ไหนบ้าง (สำคัญ)

| ข้อมูล | เก็บที่ | ย้ายยังไง |
|--------|---------|-----------|
| โค้ด + Dockerfile + compose + n8n workflows | repo (git) | `git clone` / ก๊อปโฟลเดอร์ |
| **API keys + 🔑 encryption key** | `.env` (ถูก gitignore) | **ก๊อปไฟล์ `.env` ด้วยมือ** |
| ข้อมูลแอป + สื่อ (รูป/คลิป) + SQLite | `./data/affiliate.db`, `./data/media` | ก๊อปโฟลเดอร์ `./data` |
| **workflow + credential ของ n8n** | Postgres (`db_data` volume) | ก๊อป `./data/db_init/01-restore.sql` (อยู่ใน `./data`) |

> 💡 จุดที่คนพลาดบ่อย 2 อย่าง: (1) ลืมก๊อป `.env` → คีย์หาย, (2) ย้าย Postgres แต่ไม่ตรึง `N8N_ENCRYPTION_KEY` → credential ถอดรหัสไม่ได้
> โปรเจกต์นี้แก้ให้แล้ว: key ถูกตรึงใน `.env` และ DB ถูก auto-restore จาก `./data/db_init/`

---

## ✅ ตอนใช้งานปกติ (เครื่องเดิม)

```powershell
docker compose up -d --build      # รัน backend + n8n + postgres
# Dashboard → http://localhost:8088   ·   n8n → http://localhost:5678
docker compose logs -f backend    # ดู log
docker compose down               # หยุด (ข้อมูลไม่หาย)
```

**ก่อนจะย้าย / เป็นระยะ — backup ฐานข้อมูล n8n:**
```powershell
.\scripts\backup.ps1
```
สคริปต์นี้ดึงข้อมูล n8n จาก Postgres มาเขียนเป็น `./data/db_init/01-restore.sql`
(= ไฟล์ที่เครื่องใหม่จะ import ให้อัตโนมัติ) + เก็บสำเนา timestamp ใน `./data/backups/`

---

## 🚚 ย้ายไปเครื่องใหม่ (3 ขั้น)

**บนเครื่องเดิม**
```powershell
.\scripts\backup.ps1              # 1) อัปเดต seed ของ DB ล่าสุด
```

**ก๊อปไปเครื่องใหม่** — เอาไป 2 อย่าง:
1. โฟลเดอร์โปรเจกต์ทั้งก้อน (หรือ `git clone` แล้วก๊อปเพิ่ม **`./data`** + **`.env`** ทับ)
2. ต้องมี `./data` (ข้อมูล+สื่อ+seed DB) และ `.env` (คีย์) ไปด้วยเสมอ

**บนเครื่องใหม่**
```powershell
docker compose up -d --build      # 2) Postgres ว่าง → import ./data/db_init/01-restore.sql อัตโนมัติ
                                  #    n8n ใช้ N8N_ENCRYPTION_KEY จาก .env → credential ใช้ได้ทันที
```
เปิด http://localhost:8088 และ http://localhost:5678 → ครบเหมือนเครื่องเดิม ✅

> ⚠️ ถ้าเผลอ `up` ทั้งที่ `01-restore.sql` ยังไม่อยู่ในเครื่อง → Postgres จะสร้าง DB ว่างไปแล้ว
> auto-restore จะไม่ทำงาน (มันรันเฉพาะ "ครั้งแรกที่ volume ว่าง") ให้กู้ด้วยมือ:
> ```powershell
> .\scripts\restore.ps1            # import seed เข้า DB ที่รันอยู่
> docker compose restart n8n
> ```
> หรือเริ่มสะอาดใหม่: `docker compose down -v` แล้ว `up` อีกครั้ง (⚠️ `-v` ลบ DB volume)

---

## 🖥️ รันหลายเครื่องพร้อมกัน (ไม่ใช่แค่ย้าย)

- ใช้ **`N8N_ENCRYPTION_KEY` + `POSTGRES_PASSWORD` ชุดเดียวกัน** ทุกเครื่อง (ก๊อป `.env` เดียวกัน)
- แต่ละเครื่องมี Postgres ของตัวเอง → **อย่าให้ 2 เครื่องเขียน workflow ชนกัน** ถ้าจะ sync ให้ backup จากเครื่องหลัก → restore เครื่องรอง
- ถ้าต้องการ DB กลางจริงจัง (หลายเครื่องใช้ DB เดียว) ค่อยแยก Postgres ออกเป็นบริการกลาง — บอกได้ เดี๋ยวจัดให้

---

## 🎥 หมายเหตุ: วีดีโอ Google Flow บนเครื่องใหม่
Flow ต้องต่อ Chrome ที่ล็อกอิน Google บนโฮสต์ (ดู `docs/Docker_Setup.md`).
บนเซิร์ฟเวอร์ที่ไม่มีหน้าจอ → ตั้ง `ENABLE_VIDEO=true` + ใช้ **Veo API** แทน

---

## 📋 สรุปคำสั่ง
| อยากทำ | คำสั่ง |
|--------|--------|
| รัน | `docker compose up -d --build` |
| หยุด | `docker compose down` |
| backup DB ก่อนย้าย | `.\scripts\backup.ps1` |
| restore DB (เครื่องที่ up ไปแล้ว) | `.\scripts\restore.ps1` |
| เริ่ม DB ใหม่สะอาด | `docker compose down -v` แล้ว `up` |
| ดู log | `docker compose logs -f backend` |
