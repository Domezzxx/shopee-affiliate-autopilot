# -*- coding: utf-8 -*-
"""Launcher เซิร์ฟเวอร์ตัวเดียว (ตั้ง DATA_DIR ในตัว) — ใช้กับ preview/launch.json ให้ process สะอาด."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)                       # สำคัญ! ให้ pydantic โหลด .env (keys) จากโฟลเดอร์โปรเจกต์เจอ
os.environ.setdefault("DATA_DIR", os.path.join(ROOT, "data").replace("\\", "/"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.join(ROOT, "backend"))

import time

import uvicorn

if __name__ == "__main__":
    # self-heal: ถ้า uvicorn คืนค่า/พังด้วยเหตุใด → เปิดใหม่เองทันที (กันล่ม)
    # (Watchdog ภายนอกจัดการกรณี process ตายทั้งตัว/ค้าง — ดู scripts/watchdog.ps1)
    while True:
        try:
            uvicorn.run("app.main:app", host="127.0.0.1", port=8088,
                        log_level="warning", access_log=False)
        except Exception as e:  # pragma: no cover
            print(f"[run_server] uvicorn crashed: {e}", flush=True)
        print("[run_server] server stopped — restarting in 3s...", flush=True)
        time.sleep(3)
