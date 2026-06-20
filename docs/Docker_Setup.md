# 🐳 คู่มือ Docker + WSL2 (Affiliate Autopilot) — ฉบับกันบูตลูป

> เครื่องนี้: **Windows 11 Home · RAM ~8GB · CPU VT-x เปิด · hypervisor ปิดอยู่ (ตอนนี้เสถียร)**
> เป้าหมาย: ทำให้ `docker compose up` ใช้ได้ เพื่อย้ายเครื่องง่าย — **โดยไม่ให้ Windows บูตลูป**

---

## ⚠️ อ่านก่อน — ทำไมต้องระวัง
- RAM 8GB → ถ้าไม่จำกัด WSL2 จะกิน RAM จนเครื่องค้าง/ลูป → **แก้แล้วด้วยไฟล์ `C:\Users\PronHub\.wslconfig`** (จำกัด 3GB)
- การเปิด virtualization ต้อง reboot 1 ครั้ง — reboot นี้คือจุดเสี่ยงลูป → **มี rollback ไว้ด้านล่าง (ส่วนที่ 5) ทำตามได้ทันทีถ้าลูป**

---

## ✅ ส่วนที่ 0 — เซฟตี้เน็ต (ทำก่อนเสมอ!)
1. **มี `.wslconfig` แล้ว** ที่ `C:\Users\PronHub\.wslconfig` (จำกัด RAM 3GB) ✓ — อย่าลบ
2. **สร้าง System Restore Point** (กันพลาด ย้อนได้):
   - กด Win → พิมพ์ "Create a restore point" → ปุ่ม **Create** → ตั้งชื่อ "ก่อนเปิด Docker"
3. **ปิด Fast Startup** (กัน hibernation ชน virtualization):
   - Control Panel → Power Options → "Choose what the power buttons do" → "Change settings currently unavailable" → **เอาเครื่องหมายถูก "Turn on fast startup" ออก** → Save

---

## 🟢 ส่วนที่ 1 — เปิด WSL2 (Admin PowerShell)
> คลิกขวาที่ Start → **Terminal (Admin)** / **PowerShell (Admin)**

```powershell
wsl --update              # อัปเดต WSL kernel ให้ล่าสุด
wsl --install -d Ubuntu   # ติดตั้ง distro + เปิด feature ที่จำเป็นอัตโนมัติ
```
- ถ้าระบบบอกให้ **reboot** → reboot 1 ครั้ง (ระวัง: ถ้าบูตลูป ดูส่วนที่ 5 ทันที)
- หลัง reboot Ubuntu จะเด้งให้ตั้ง username/password ครั้งแรก — ตั้งอะไรก็ได้ จำไว้

**ตรวจว่าผ่าน:**
```powershell
wsl -l -v        # ต้องเห็น Ubuntu  VERSION 2
wsl --status     # ดูว่า kernel + version 2 พร้อม
```

---

## 🐳 ส่วนที่ 2 — เปิด Docker Desktop (WSL2 backend)
1. เปิด **Docker Desktop** (ติดตั้งไว้แล้ว)
2. Settings (⚙) → **General** → ติ๊ก **"Use the WSL 2 based engine"** ให้ติด
3. Settings → **Resources → WSL Integration** → เปิด integration กับ Ubuntu
4. Apply & Restart → รอ Docker ขึ้น (ไอคอนวาฬเขียว)

**ตรวจว่าผ่าน:**
```powershell
docker version     # ต้องเห็นทั้ง Client + Server (ถ้าเห็น Server = daemon ทำงานแล้ว)
docker run --rm hello-world
```

---

## 🚀 ส่วนที่ 3 — รันโปรเจกต์ด้วย Docker
ในโฟลเดอร์ `affiliate-autopilot`:
```powershell
docker compose build           # build image backend (ครั้งแรกนานหน่อย)
docker compose up -d           # รัน backend + n8n + postgres
docker compose logs -f backend # ดู log
```
- เว็บ: **http://localhost:8088** · n8n: http://localhost:5678
- ข้อมูล (sqlite + คลิป) อยู่ที่ `./data` (mount นอก container → **ย้ายเครื่องก๊อปโฟลเดอร์นี้ไปได้เลย**)
- หยุด: `docker compose down` (ข้อมูลไม่หาย)

### 🎥 เรื่องวีดีโอ Google Flow ใน Docker (สำคัญ)
Flow ต้องต่อ **Chrome ที่ล็อกอิน Google บนเครื่องโฮสต์** — container ต่อผ่าน `host.docker.internal:9222`
ต้องเปิด Chrome บนโฮสต์ให้ container เข้าถึงได้:
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 `
  --user-data-dir="C:\Users\PronHub\affiliate-autopilot\data\chrome_profile" `
  https://labs.google/fx/tools/flow
```
> ⚠️ `--remote-debugging-address=0.0.0.0` = ยอมให้ container ต่อได้ (ค่า default ต่อได้แค่ในเครื่อง)
> 💡 **บน cloud/เซิร์ฟเวอร์ที่ไม่มีหน้าจอ:** Flow ใช้ไม่ได้ → ตั้ง `ENABLE_VIDEO=true` + ใช้ **Veo API** แทน (ใน `.env`)

---

## 🆘 ส่วนที่ 5 — ROLLBACK: ถ้า Windows บูตลูป (ทำตามนี้ทันที)
> อาการ: เปิดเครื่องแล้ววนรีสตาร์ท/ค้างหน้าโลโก้ ไม่เข้า Windows

**A. เข้า Recovery (WinRE):**
- เปิดเครื่อง → พอเห็นโลโก้ Windows **กดปุ่ม Power ค้างปิดเครื่อง** → ทำซ้ำ **3 ครั้ง** → ครั้งที่ 3 จะเข้า "Automatic Repair"
- เลือก **Advanced options → Troubleshoot → Advanced options → Command Prompt**

**B. ปิด hypervisor (ตัวที่ทำให้ลูป) — พิมพ์:**
```
bcdedit /set hypervisorlaunchtype off
```
- ปิด Command Prompt → **Continue / Restart** → เครื่องจะบูตเข้า Windows ปกติ (เสถียร)
- ผล: WSL2/Docker จะใช้ไม่ได้ชั่วคราว **แต่เครื่องกลับมาทำงาน** + โปรเจกต์รัน native ได้ตามเดิม (`./scripts/start.ps1`)

**C. เปิดกลับ (ภายหลังเมื่อพร้อมแก้):** Admin PowerShell →
```powershell
bcdedit /set hypervisorlaunchtype auto
```

> 🛟 **ถ้ายังไม่หาย:** System Restore Point ที่สร้างไว้ (ส่วนที่ 0) → WinRE → Troubleshoot → System Restore → เลือกจุด "ก่อนเปิด Docker"

---

## 🔁 ทางเลือกที่ไม่ต้องเสี่ยง — รัน NATIVE (แนะนำสำหรับเครื่องนี้)
ถ้าไม่อยากเสี่ยง virtualization บนเครื่อง 8GB เลย — โปรเจกต์รัน **native ได้ครบทุกฟีเจอร์** (รวม Flow):
```powershell
git clone <repo>            # เครื่องใหม่
cd affiliate-autopilot
./scripts/setup.ps1         # สร้าง venv + ลง dependency (ครั้งเดียว)
# แก้ .env ใส่ key
./scripts/start.ps1         # รันเซิร์ฟเวอร์ + Chrome(Flow) + เปิดเว็บ
```
- ย้ายเครื่อง = git clone + setup.ps1 + ก๊อปโฟลเดอร์ `data/` (ข้อมูล+คลิป) ไปด้วย
- เบากว่า Docker มาก เหมาะกับ RAM 8GB · Flow วีดีโอทำงานตรงๆ ไม่ต้องตั้ง proxy

---

## 📋 คำสั่ง Docker ที่ใช้บ่อย
| อยากทำ | คำสั่ง |
|--------|--------|
| รัน | `docker compose up -d` |
| หยุด | `docker compose down` |
| ดู log | `docker compose logs -f backend` |
| build ใหม่หลังแก้โค้ด | `docker compose up -d --build` |
| WSL กิน RAM เยอะ/ค้าง | `wsl --shutdown` (แล้วเปิด Docker ใหม่) |
| เช็คสถานะ | `docker ps` · `wsl -l -v` |
