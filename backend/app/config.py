"""โหลด config จาก .env — ทุกค่ามี default ปลอดภัย รันได้ทันทีแม้ยังไม่ใส่ key (mock mode)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI brain
    anthropic_api_key: str = ""
    content_model: str = "claude-sonnet-4-6"

    # Gemini media
    gemini_api_key: str = ""
    image_model: str = "gemini-2.5-flash-image"
    video_model: str = "veo-3.0-generate-001"
    enable_video: bool = False

    # Meta (FB + IG)
    meta_page_id: str = ""
    meta_ig_user_id: str = ""
    meta_access_token: str = ""

    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Phone farm
    phone_farm_devices: str = ""
    host_adb: str = "host.docker.internal:5037"

    # ระบบ
    posting_mode: str = "hybrid"          # hybrid | api | phone
    shopee_min_rating: float = 4.5
    shopee_min_reviews: int = 20
    abtest_min_impressions: int = 500
    abtest_pause_ctr: float = 0.005
    post_delay_min: int = 15
    post_delay_max: int = 45
    auto_optimize_interval_min: int = 360

    data_dir: str = "/app/data"

    @property
    def media_dir(self) -> str:
        return f"{self.data_dir}/media"

    @property
    def phone_list(self) -> list[str]:
        return [d.strip() for d in self.phone_farm_devices.split(",") if d.strip()]

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_access_token and self.meta_page_id)


settings = Settings()
