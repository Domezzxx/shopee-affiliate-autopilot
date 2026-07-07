# -*- coding: utf-8 -*-
"""ค่าที่ปรับได้ตอนรัน (override .env) เก็บใน data/runtime.json — เช่น เลือก AI provider จากหน้าเว็บ."""
from __future__ import annotations

import json
import os

from ..config import settings


def _path() -> str:
    return os.path.join(settings.data_dir, "runtime.json")


def _load() -> dict:
    try:
        with open(_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get(key: str, default=None):
    return _load().get(key, default)


def set(key: str, value):
    d = _load()
    if value is None or value == "":
        d.pop(key, None)
    else:
        d[key] = value
    try:
        os.makedirs(settings.data_dir, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception as e:  # pragma: no cover
        print(f"[runtime] save fail: {e}")
    return value
