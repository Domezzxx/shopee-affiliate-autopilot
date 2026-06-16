#!/usr/bin/env python3
"""ขอ YOUTUBE_REFRESH_TOKEN สำหรับอัปโหลด Shorts อัตโนมัติ (รันครั้งเดียว).

เตรียมก่อนรัน (ทำใน Google Cloud Console — ฟรี):
  1. console.cloud.google.com -> สร้าง project
  2. เปิดใช้ "YouTube Data API v3"  (APIs & Services -> Library)
  3. OAuth consent screen: External -> เพิ่มอีเมลตัวเองใน Test users
  4. Credentials -> Create Credentials -> OAuth client ID -> Application type: "Desktop app"
     -> ได้ Client ID + Client secret
  5. นำมาใส่ตอนรันสคริปต์นี้

วิธีรัน (PowerShell ใน venv):
  ./venv/Scripts/python.exe scripts/youtube_oauth.py
ผลลัพธ์: พิมพ์ refresh_token + เขียนลง .env ให้อัตโนมัติ (3 บรรทัด YOUTUBE_*).

ใช้ stdlib ล้วน + รับ code ผ่าน loopback (http://localhost:8765) ไม่ต้องลง lib เพิ่ม.
"""
from __future__ import annotations

import http.server
import json
import os
import threading
import urllib.parse
import urllib.request
import webbrowser

REDIRECT = "http://localhost:8765/"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"

_code: dict[str, str] = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(q)
        _code["code"] = (params.get("code") or [""])[0]
        _code["error"] = (params.get("error") or [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = "สำเร็จ! กลับไปที่หน้าต่าง terminal ได้เลย ปิดแท็บนี้ได้" if _code["code"] else "ล้มเหลว: " + _code["error"]
        self.wfile.write(f"<h2>{msg}</h2>".encode("utf-8"))

    def log_message(self, *_):  # เงียบ log
        pass


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _write_env(cid: str, csec: str, refresh: str) -> bool:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    envf = os.path.join(root, ".env")
    if not os.path.exists(envf):
        return False
    lines = open(envf, encoding="utf-8").read().splitlines()
    want = {"YOUTUBE_CLIENT_ID": cid, "YOUTUBE_CLIENT_SECRET": csec, "YOUTUBE_REFRESH_TOKEN": refresh}
    out, seen = [], set()
    for ln in lines:
        key = ln.split("=", 1)[0] if "=" in ln else ""
        if key in want:
            out.append(f"{key}={want[key]}")
            seen.add(key)
        else:
            out.append(ln)
    for k, v in want.items():
        if k not in seen:
            out.append(f"{k}={v}")
    open(envf, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return True


def main():
    print("=== YouTube OAuth — ขอ refresh token สำหรับอัปโหลด Shorts ===\n")
    cid = input("Client ID: ").strip()
    csec = input("Client secret: ").strip()
    if not (cid and csec):
        print("ต้องใส่ทั้ง Client ID และ secret"); return

    auth_url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent"})

    srv = http.server.HTTPServer(("localhost", 8765), _Handler)
    threading.Thread(target=srv.handle_request, daemon=True).start()

    print("\nเปิดเบราว์เซอร์ให้อนุญาต... (ถ้าไม่เปิดเอง ก็อปลิงก์นี้ไปเปิด)\n" + auth_url + "\n")
    webbrowser.open(auth_url)

    while not (_code.get("code") or _code.get("error")):
        pass
    if _code.get("error") or not _code.get("code"):
        print("ล้มเหลว:", _code.get("error")); return

    tok = _post_form(TOKEN, {
        "code": _code["code"], "client_id": cid, "client_secret": csec,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    refresh = tok.get("refresh_token", "")
    if not refresh:
        print("ไม่ได้ refresh_token (ลองใหม่ + เพิ่มอีเมลใน Test users):", tok); return

    print("\n✅ refresh_token:\n" + refresh + "\n")
    if _write_env(cid, csec, refresh):
        print("เขียนลง .env แล้ว (YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN) — restart server ได้เลย")
    else:
        print("ไม่พบ .env — ใส่เอง 3 บรรทัด:")
        print(f"YOUTUBE_CLIENT_ID={cid}\nYOUTUBE_CLIENT_SECRET={csec}\nYOUTUBE_REFRESH_TOKEN={refresh}")


if __name__ == "__main__":
    main()
