"""โครงข้อมูล (SQLModel + SQLite) — ไฟล์เดียวจบ: models + engine + helpers."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Session, create_engine, select

from .config import settings

engine = create_engine(
    f"sqlite:///{settings.data_dir}/affiliate.db",
    connect_args={"check_same_thread": False},
)


# ---------------------------------------------------------------- models
class Store(SQLModel, table=True):
    """ร้าน Shopee Food ที่ scraper ดึงมา (ผ่านการกรอง rating/รีวิวแล้ว)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    area: str = ""
    rating: float = 0.0
    review_count: int = 0
    price_range: str = ""
    menu_json: str = "[]"            # ["ผัดไทย", ...]
    image_urls_json: str = "[]"      # รูปจาก Shopee (ใช้ฟรีช่วงแรก)
    affiliate_link: str = ""
    shopee_url: str = ""
    status: str = "new"              # new | active | paused
    low_ctr_days: int = 0            # นับวัน CTR ต่ำติดกัน → ถึงเกณฑ์แล้ว pause
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentJob(SQLModel, table=True):
    """ผลลัพธ์จาก Claude ต่อ 1 ร้าน — เก็บ analysis + ตาราง schedule."""
    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id")
    status: str = "generated"        # generated | media_ready | posted | failed
    analysis_json: str = "{}"
    schedule_json: str = "[]"
    model_used: str = ""
    cost_baht: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Variant(SQLModel, table=True):
    """หนึ่งชิ้นคอนเทนต์ A หรือ B (ต่อ platform) — หัวใจของ A/B test."""
    id: Optional[int] = Field(default=None, primary_key=True)
    content_job_id: int = Field(foreign_key="contentjob.id")
    store_id: int = Field(foreign_key="store.id")
    label: str                       # "A" | "B"
    platform: str                    # facebook | instagram | youtube
    hook: str = ""
    caption: str = ""
    hashtags_json: str = "[]"
    cta: str = ""
    voiceover_script: str = ""
    image_prompt: str = ""
    video_prompt: str = ""
    media_type: str = "image"        # image | video
    media_path: str = ""             # ไฟล์ที่ Gemini สร้าง
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Post(SQLModel, table=True):
    """รายการโพสต์จริงที่ยิงออกไปแต่ละ platform/บัญชี."""
    id: Optional[int] = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="variant.id")
    store_id: int = Field(foreign_key="store.id")
    platform: str
    method: str = "api"              # api | phone
    account: str = ""                # page id / device serial
    external_id: str = ""            # id โพสต์ฝั่ง platform
    status: str = "queued"           # queued | posted | failed
    error: str = ""
    posted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Metric(SQLModel, table=True):
    """ตัวเลขผลตอบรับของแต่ละโพสต์ (n8n / connector ดึงมาเติม)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id")
    variant_id: int = Field(foreign_key="variant.id")
    store_id: int = Field(foreign_key="store.id")
    impressions: int = 0
    clicks: int = 0
    engagement: int = 0
    ctr: float = 0.0
    captured_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------- helpers
def init_db() -> None:
    import os
    os.makedirs(settings.media_dir, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)


def jloads(s: str, default):
    try:
        return json.loads(s)
    except Exception:
        return default
