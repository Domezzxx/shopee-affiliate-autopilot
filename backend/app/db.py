"""โครงข้อมูล (SQLModel + SQLite) — ไฟล์เดียวจบ: models + engine + helpers + auto-migrate."""
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
    """ร้าน Shopee Food ที่ scraper/ผู้ใช้ ใส่เข้ามา (ผ่านการกรอง rating/รีวิวแล้ว)."""
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
    reel_url: str = ""               # คลิปรวม (montage A/B) ที่สร้างไว้
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
    video_title: str = ""            # ชื่อคลิปไวรัลสไตล์อินฟลูอาหาร (YouTube/TikTok)
    caption: str = ""
    hashtags_json: str = "[]"
    cta: str = ""
    first_comment: str = ""          # ข้อความคอมเมนต์แรก (วาง affiliate link)
    voiceover_script: str = ""
    image_prompt: str = ""
    video_prompt: str = ""
    media_type: str = "image"        # image | video
    media_path: str = ""             # ไฟล์สื่อสุดท้าย (ภาพ/วีดีโอ)
    image_path: str = ""             # ภาพต้นฉบับ (เก็บไว้ทำคลิปรวม montage)
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
    comment_id: str = ""             # id คอมเมนต์แรก (affiliate link)
    comment_status: str = ""         # "" | posted | failed
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
def _migrate() -> None:
    """เพิ่มคอลัมน์ใหม่ให้ DB เดิมที่มีข้อมูลอยู่แล้ว (SQLite ไม่ migrate ให้อัตโนมัติ)."""
    new_cols = {
        "variant": [("first_comment", "TEXT DEFAULT ''"), ("image_path", "TEXT DEFAULT ''"),
                    ("video_title", "TEXT DEFAULT ''")],
        "post": [("comment_id", "TEXT DEFAULT ''"), ("comment_status", "TEXT DEFAULT ''")],
        "store": [("reel_url", "TEXT DEFAULT ''")],
    }
    with engine.begin() as conn:
        for table, cols in new_cols.items():
            existing = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            for col, ddl in cols:
                if col not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")


def init_db() -> None:
    import os
    os.makedirs(settings.media_dir, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _migrate()
    # WAL = อ่าน/เขียนพร้อมกันได้ดีขึ้น · busy_timeout = รอ lock แทน fail ทันที
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA busy_timeout=5000")


def get_session() -> Session:
    return Session(engine)


def jloads(s: str, default):
    try:
        return json.loads(s)
    except Exception:
        return default
