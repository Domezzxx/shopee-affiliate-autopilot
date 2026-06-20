# แผน: แชท AI สร้างวีดีโอ — ในเว็บเราเอง (เลิกขับ Chrome ข้าม browser)

> ไอเดียพี่กอล์ฟ: แทนที่จะขับ chat ของ Google Flow ผ่าน browser ให้มี **แชทในเว็บเราเอง**
> → backend เรียกสร้างวีดีโอ AI ตรงๆ → บอทไม่ต้องทำงานข้าม browser

## ทำไมถูกต้อง
ของเดิม (Playwright ขับ Chrome + Flow) = เปราะ · ต้องเปิด Chrome + ล็อกอิน · ขึ้น cloud ไม่ได้ ·
พังเมื่อ Google เปลี่ยน UI · เจอ quota เงียบๆ. แชทของเราเอง = สะอาด คุมได้ deploy ได้

## จุดสำคัญ (ตรงๆ)
**เครดิต Flow ฟรี = ใช้ได้ผ่าน browser เท่านั้น** (ไม่มี API ฟรีสาธารณะ).
ถ้ามีแชทเราเอง → ต้องเรียก video API ตรง = **Veo API (จ่ายเงิน)** หรือเจ้าอื่น.
ทางออก: ทำ **Video Provider แบบเสียบเปลี่ยนได้** — เขียนครั้งเดียว สลับ Veo(จ่าย) / Flow-bridge(ฟรี) ได้

## สถาปัตยกรรม
```
[💬 แชทในแดชบอร์ด]  →  [⚙️ Backend /api/video (คิว+progress)]  →  [🔌 Video Provider]
                                                                    ├─ Veo API (จ่าย, cloud)
                                                                    ├─ Flow-bridge (ฟรี, เครื่องบ้าน)
                                                                    └─ Kling/Runway/Luma (จ่าย, ทางเลือก)
                                                                          ↓
                                                  [🎬 video_flow_*.mp4]  →  build_restaurant ทำคลิปรีวิว
```

## เลือก Provider
| Provider | ราคา | นิ่ง | Cloud | หมายเหตุ |
|----------|------|------|-------|----------|
| Veo API (Gemini) | ~12-15฿/คลิป 8วิ | 100% | ใช่ | media_gemini มี veo path อยู่แล้ว · แนะนำ default |
| Flow-bridge | ฟรี (เครดิต Flow) | กลาง | ไม่ | ห่อ flow_automation เดิมใน worker เครื่องบ้าน |
| Kling/Runway/Luma | จ่าย (ถูกกว่า Veo บ้าง) | ดี | ใช่ | เสียบเพิ่มทีหลัง |

## ส่วนที่ต้องสร้าง
1. แชท UI ในแดชบอร์ด — กล่องแชท พิมพ์ prompt → progress → preview วีดีโอ
2. `engines/video_provider.py` — interface `generate(prompt) -> path` + VeoProvider / FlowBridgeProvider / (อื่น)
3. Endpoints `/api/video/generate` + `/api/video/jobs` (ใช้ progress bar เดิม)
4. คิวงาน 1 งาน/ครั้ง (วีดีโอช้าหลายนาที) + progress
5. ผูกผลเข้า pipeline — วีดีโอ tag เข้าร้าน/เมนู → build_restaurant หยิบใช้ (รองรับ video_flow_* แล้ว)
6. config `VIDEO_PROVIDER=veo|flow|kling` + smart routing (ฟรีก่อน → จ่าย fallback)

## แผนเป็นเฟส
- เฟส 1: Provider abstraction + Veo API + แชท UI + คิว/progress → ใช้งานได้จริงผ่าน API
- เฟส 2: ห่อ Flow เดิมเป็น Flow-bridge provider (ตัวเลือกฟรี) หลัง interface เดียวกัน
- เฟส 3: เสียบเข้า build_restaurant + Auto-Pilot (เลือก provider อัตโนมัติ: ฟรีก่อน → Veo fallback)
- เฟส 4: แยก cloud — web บน Vercel · video worker เครื่องบ้าน (Flow) หรือ Veo ล้วนบน cloud

## ต้นทุน
- Veo: ~12-15฿/คลิป · ร้านละ 1-2 คลิป · 100 ร้าน/เดือน ≈ 1,500-3,000฿/เดือน
- Flow-bridge: ฟรี (จำกัดเครดิตรายวัน ~10-20 คลิป)

## ข้อดี vs ของเดิม
- ไม่ขับ browser ข้ามกัน · ขึ้น cloud ได้ · นิ่ง · สลับผู้ให้บริการได้ · มี UI แชทให้คนใช้ตรงๆ
- ข้อแลก: ถ้าใช้ API = จ่ายเงิน (แต่ Flow-bridge ยังเก็บตัวเลือกฟรีไว้)
