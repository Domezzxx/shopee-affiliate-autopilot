"""FastAPI app — เสิร์ฟ Dashboard (WebApp) + REST API + ไฟล์สื่อ + background auto-optimize."""
from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import settings
from .db import init_db
from .services import pipeline

app = FastAPI(title="Affiliate Autopilot", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC = os.path.join(os.path.dirname(__file__), "static")


@app.on_event("startup")
async def _startup():
    init_db()
    asyncio.create_task(_auto_optimize_loop())


async def _auto_optimize_loop():
    """รัน auto-optimize เป็นรอบ (ขั้น 5) — หยุดร้าน CTR ต่ำเอง. ข้ามถ้าปิดระบบอยู่."""
    from .services import system_state
    interval = settings.auto_optimize_interval_min * 60
    while True:
        await asyncio.sleep(interval)
        if not system_state.is_enabled():
            continue                      # ปิดระบบ → ไม่ทำงานอัตโนมัติ
        try:
            pipeline.auto_optimize()
        except Exception as e:  # pragma: no cover
            print(f"[auto-optimize] {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)

# สื่อที่ Gemini สร้าง (ภาพ/วีดีโอ) — ให้ dashboard preview + connector ใช้เป็น url
app.mount("/media", StaticFiles(directory=settings.media_dir, check_dir=False), name="media")
# หน้า WebApp
app.mount("/static", StaticFiles(directory=STATIC, check_dir=False), name="static")


@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC, "index.html"))
