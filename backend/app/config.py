"""โหลด config จาก .env — ทุกค่ามี default ปลอดภัย รันได้ทันทีแม้ยังไม่ใส่ key (mock mode)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI brain — เลือกผู้เขียนคอนเทนต์: "gemini" (ฟรี) หรือ "claude" (จ่ายเงิน คุณภาพสูง)
    content_provider: str = "claude"
    anthropic_api_key: str = ""
    content_model: str = "claude-sonnet-4-6"
    # CONTENT_STYLE: แนวคอนเทนต์ — realistic (อาหาร/สินค้าเหมือนจริง, ค่าเริ่มต้น) |
    #   cartoon2d (การ์ตูน 2D) | pixar3d (Pixar 3D) | story (นิทานเล่าเรื่อง) | podcast (คุยกัน 2 เสียง)
    content_style: str = "realistic"

    # Gemini media + (ตัวเลือก) เขียนข้อความฟรี
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-2.5-flash"
    image_model: str = "gemini-2.5-flash-image"
    video_model: str = "veo-3.0-generate-001"
    enable_video: bool = False
    # VIDEO_MODE: image (ภาพนิ่ง) | ffmpeg (วีดีโอฟรีจากภาพ AI) | veo (วีดีโอจริง เสียเงิน)
    video_mode: str = "image"
    video_seconds: int = 6
    # VIDEO_PROVIDER: เครื่องมือสร้าง 'วิดีโอจริง' —
    #   "flow"     = Google Flow browser automation (ฟรี แต่เปราะ/มีโควตา/พึ่ง Chrome debug)
    #   "veo"      = Veo API โดยตรง (เสถียร + เสียงพูด native ในคลิป, ต้องมีคีย์จริงขึ้นต้น AIzaSy)
    #   "flow_veo" = ลอง Flow ก่อน ถ้าล้มเหลว/โควตาหมดค่อย fallback ไป Veo API
    video_provider: str = "flow"
    veo_aspect_ratio: str = "9:16"    # สัดส่วนคลิป Veo (รีล/Shorts = 9:16)
    veo_poll_seconds: int = 10        # หน่วงต่อรอบ poll สถานะ Veo
    veo_poll_max: int = 30            # จำนวนรอบ poll สูงสุด (10*30 ≈ 5 นาที)
    # POST_MONTAGE: true = โพสต์ 'คลิปรวม' (ต่อคลิปคนพูดหลายภาษาในร้านเดียว → ยาวขึ้น คงเสียงเดิม)
    post_montage: bool = True
    ffmpeg_path: str = ""            # เว้นว่าง = หาให้อัตโนมัติ
    reel_scene_seconds: float = 2.0  # ความยาวต่อช็อตในคลิปรวม (สั้น = ตัดเร็วมีจังหวะ)
    reel_cta_seconds: float = 2.6    # ฉากปิด CTA
    reel_max_seconds: float = 22.0   # ความยาวรีลสูงสุด (เกินนี้ตัด — กันยาวจนคนปัดหนี)

    # Stock video — footage อาหารจริง (เคลื่อนไหว) ผสมในคลิป ให้ดูเป็นรีวิวจริง
    pexels_api_key: str = ""          # ฟรี: https://www.pexels.com/api/ (ภาพ+วีดีโอ)
    stock_video: bool = True          # ผสม footage จริงถ้ามี key
    freesound_api_key: str = ""       # ฟรี: https://freesound.org/apiv2/apply/ (เสียง ASMR ซด/ซิซเซิล)

    # Google Flow automation settings
    flow_cdp_url: str = "http://127.0.0.1:9222"
    flow_selector_input: str = "div[role='textbox'], [role='textbox'], textarea[placeholder*='prompt' i]"
    flow_selector_generate: str = "button:has-text('arrow_forwardสร้าง'), button:has-text('สร้าง'), button:has-text('Generate'), button:has-text('Create')"
    flow_selector_download: str = "button:has-text('ดาวน์โหลด'), button:has-text('Download'), a[download]"

    # Audio — เสียงพากย์ไทย (edge-tts ฟรี) + เพลงประกอบ
    enable_voiceover: bool = True
    tts_voice: str = "th-TH-PremwadeeNeural"   # หรือ th-TH-NiwatNeural (เสียงผู้ชาย)
    enable_music: bool = True
    music_volume: float = 0.16                 # ระดับเพลงคลอใต้เสียงพากย์
    asmr_volume: float = 0.13                  # เสียงบรรยากาศร้าน (chatter เบาๆ) ใต้เสียงพากย์
    stock_video_ratio: int = 2                 # อัตราส่วน วีดีโอจริง:ภาพ (2 = วีดีโอจริงเป็นพระเอก)
    affiliate_commission_per_click: float = 6.0 # ค่าคอมมิชชั่นเฉลี่ยสะสมต่อ 1 คลิก (บาท)

    # Meta (FB + IG)
    meta_page_id: str = ""
    meta_ig_user_id: str = ""
    meta_access_token: str = ""
    public_base_url: str = ""        # สำหรับ IG (ต้องโฮสต์สื่อ public เช่น ngrok/cloud)
    enable_post_delay: bool = False  # โพสต์จริง: สุ่มหน่วงเวลาระหว่างโพสต์ (กัน spam)

    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Phone farm
    phone_farm_devices: str = ""
    host_adb: str = "host.docker.internal:5037"

    # Scraper — แหล่งข้อมูลร้าน Shopee Food (Shopee กัน bot → แนะนำ proxy/Apify)
    scraper_mode: str = "direct"          # direct | scraperapi | scrapingbee | apify
    scraper_api_key: str = ""             # ScraperAPI / ScrapingBee key
    scraper_ultra_premium: bool = False   # Shopee ต้องใช้ (แต่ต้องอัปแผน ScraperAPI แบบจ่ายเงิน)
    scraper_proxy: str = ""               # http://user:pass@host:port (โหมด direct)
    apify_token: str = ""
    apify_actor: str = "xtracto~shopee-search"   # actor บน Apify (ใช้ / หรือ ~ ก็ได้)
    # input ที่ส่งให้ actor — แทน {KEYWORD} และ {LIMIT} อัตโนมัติ (default = xtracto/shopee-search)
    apify_input: str = '{"country":"th","mode":"keyword","keyword":"{KEYWORD}","maxProducts":{LIMIT},"fetchDetail":false}'
    shopee_keywords: str = "ก๋วยเตี๋ยว"   # คำค้น (คั่นหลายคำด้วย ;)
    scraper_limit: int = 30

    # Shopee Affiliate Open API — สร้างลิงก์ affiliate (คอมมิชชั่น) · ขอที่ affiliate.shopee.co.th
    # (placeholder รอ build engine shopee_affiliate.py — ตอนนี้ยังใช้ลิงก์ใส่เองต่อร้าน)
    shopee_affiliate_app_id: str = ""
    shopee_affiliate_secret: str = ""

    # ระบบ
    posting_mode: str = "hybrid"          # hybrid | api | phone
    shopee_min_rating: float = 4.5
    shopee_min_reviews: int = 20
    abtest_min_impressions: int = 500
    abtest_pause_ctr: float = 0.005
    post_delay_min: int = 15
    post_delay_max: int = 45
    auto_optimize_interval_min: int = 360

    # Auto-Pilot — วงจรอัตโนมัติ (scrape→generate→post) ทำเองตามรอบ (Sprint 6 P2)
    autopilot_enabled: bool = False       # เปิด = ระบบประมวลผลร้านใหม่เองตามรอบ
    autopilot_interval_min: int = 120     # รอบ auto-pilot (นาที)
    autopilot_batch: int = 2              # จำนวนร้านต่อรอบ (กัน rate limit + เครดิต)

    # Promo image mode — สร้างภาพโปรโมทนิ่ง (ฟรี ไม่ใช้ Flow) แล้วโพสต์ FB/IG อัตโนมัติ
    promo_mode: bool = False              # true = autopilot สร้าง+โพสต์ภาพโปรโมทแทนสร้างคลิป
    promo_campaign: str = ""              # ป้ายแคมเปญบนโปสเตอร์ (เช่น "ไทยช่วยไทย 60/40") เว้นว่าง=ไม่โชว์
    promo_ai_mode: str = "photo"          # โหมดรูป AI: photo (อาหารจริง) | cartoon (การ์ตูน) | mix

    # Repost mode — โพสต์ซ้ำคลิปเดิม (ตอน media credit หมด: Flow/Gemini รูป) แทนการสร้างใหม่
    repost_mode: bool = False             # true = autopilot โพสต์ซ้ำคลิปเก่าแทนสร้างใหม่
    repost_per_round: int = 3             # จำนวนคลิปซ้ำต่อรอบ
    repost_gap_min: float = 8.0           # หน่วงระหว่างโพสต์ในรอบ (นาที) กันโดนแบนสแปม
    repost_gap_max: float = 20.0

    # Flow quota guard — เมื่อเครดิต Flow หมด พักไม่ยิงซ้ำ (กันเสียเวลา/เครดิต)
    flow_block_hours: int = 6             # บล็อก Flow กี่ชม.หลังเจอเครดิตหมด

    database_url: str = ""
    data_dir: str = "/app/data"

    @property
    def media_dir(self) -> str:
        return f"{self.data_dir}/media"

    @property
    def music_dir(self) -> str:
        return f"{self.data_dir}/music"

    @property
    def phone_list(self) -> list[str]:
        # รับเฉพาะ host:port จริง — กันคอมเมนต์/ค่าขยะที่หลุดจาก .env (เช่น "# เช่น 192.168.1.51:5555")
        import re
        out = []
        for d in self.phone_farm_devices.split(","):
            d = d.strip()
            if not d or d.startswith("#"):
                continue
            # รับ host:port (ADB over network) หรือ USB serial (อักษร/ตัวเลขล้วน ≥6 ตัว) — กันคอมเมนต์/ค่าขยะ
            if re.match(r"^[\w.\-]+:\d+$", d) or re.match(r"^[A-Za-z0-9]{6,}$", d):
                out.append(d)
        return out

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_veo(self) -> bool:
        """มีคีย์ Google AI จริง (ขึ้นต้น AIzaSy) ที่เรียก Veo API ได้ — คีย์ Flow/mock จะไม่ผ่าน."""
        return self.has_gemini and self.gemini_api_key.startswith("AIzaSy")

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_access_token and self.meta_page_id)

    @property
    def content_ready(self) -> bool:
        """AI เขียนคอนเทนต์พร้อมใช้จริง (ตาม provider ที่เลือก) หรือยัง."""
        if self.content_provider == "gemini":
            return self.has_gemini
        return self.has_claude


settings = Settings()
