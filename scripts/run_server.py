# -*- coding: utf-8 -*-
"""Launcher เซิร์ฟเวอร์ตัวเดียว (ตั้ง DATA_DIR ในตัว) — ใช้กับ preview/launch.json ให้ process สะอาด."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)                       # สำคัญ! ให้ pydantic โหลด .env (keys) จากโฟลเดอร์โปรเจกต์เจอ
os.environ.setdefault("DATA_DIR", os.path.join(ROOT, "data").replace("\\", "/"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.join(ROOT, "backend"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8088, log_level="info")
