# -*- coding: utf-8 -*-
"""ถ่าย screenshot หน้า Flow ปัจจุบัน + crop โซนขวา (chat panel)."""
import sys
from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else "data/flow_now.png"
pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]
page = next((p for p in ctx.pages if "flow" in p.url or "labs.google" in p.url), None)
page.bring_to_front()
page.screenshot(path=out)
print("saved:", out)
pw.stop()
