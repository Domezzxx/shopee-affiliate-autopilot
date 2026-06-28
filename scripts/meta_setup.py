#!/usr/bin/env python3
"""Exchange Meta short-lived token -> long-lived, get Page token and IG Business ID,
and write results into .env in the repo root.

Usage: python scripts/meta_setup.py
"""
from __future__ import annotations

import os
import sys
import shutil
from typing import Dict

import httpx


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
BACKUP_PATH = ENV_PATH + ".meta_setup.bak"
GRAPH = "https://graph.facebook.com/v21.0"


def load_env(path: str) -> Dict[str, str]:
    vals: Dict[str, str] = {}
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v
    return vals


def write_env_updates(path: str, updates: Dict[str, str]):
    # Backup
    shutil.copy2(path, BACKUP_PATH)
    lines = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line or line.strip().startswith("#") or "=" not in line:
                lines.append(raw)
                continue
            k, _ = line.split("=", 1)
            k = k.strip()
            if k in updates:
                lines.append(f"{k}={updates[k]}\n")
                del updates[k]
            else:
                lines.append(raw)
    # append any remaining keys
    if updates:
        lines.append("\n# --- added by meta_setup.py ---\n")
        for k, v in updates.items():
            lines.append(f"{k}={v}\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def exchange_user_token(app_id: str, app_secret: str, short_token: str) -> str:
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }
    r = httpx.get(f"{GRAPH}/oauth/access_token", params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    return j["access_token"]


def get_page_access_token(page_id: str, user_token: str) -> str:
    r = httpx.get(f"{GRAPH}/{page_id}", params={"fields": "access_token", "access_token": user_token}, timeout=30)
    r.raise_for_status()
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"no access_token in page response: {j}")
    return j["access_token"]


def get_ig_business_id(page_id: str, page_token: str) -> str | None:
    r = httpx.get(f"{GRAPH}/{page_id}", params={"fields": "instagram_business_account", "access_token": page_token}, timeout=30)
    r.raise_for_status()
    j = r.json()
    ib = j.get("instagram_business_account")
    if isinstance(ib, dict) and "id" in ib:
        return str(ib["id"])
    return None


def main():
    try:
        env = load_env(ENV_PATH)
    except FileNotFoundError:
        print(".env not found in repo root. Create it from .env.example first.")
        sys.exit(1)

    app_id = env.get("META_APP_ID")
    app_secret = env.get("META_APP_SECRET")
    page_id = env.get("META_PAGE_ID")
    short_token = env.get("META_ACCESS_TOKEN")

    if not all([app_id, app_secret, page_id, short_token]):
        print("Missing required keys in .env: META_APP_ID, META_APP_SECRET, META_PAGE_ID, META_ACCESS_TOKEN")
        sys.exit(1)

    print("Exchanging short-lived token for long-lived user token (fallback to existing token if exchange fails)...")
    user_ll = None
    try:
        user_ll = exchange_user_token(app_id, app_secret, short_token)
    except Exception as e:
        print("Token exchange failed (will try using provided token as-is):", e)

    print("Fetching Page Access Token...")
    page_token = None
    # Try with exchanged user token first
    if user_ll:
        try:
            page_token = get_page_access_token(page_id, user_ll)
        except Exception as e:
            print("Failed to get Page access token from exchanged user token:", e)
    # Fallback: try using provided token directly (maybe it's already a page token)
    if not page_token:
        try:
            page_token = get_page_access_token(page_id, short_token)
            print("Using provided token as Page token (no exchange).")
        except Exception as e:
            print("Failed to get Page access token from provided token:", e)
            # As a last resort, assume the provided token is the page token itself
            page_token = short_token

    print("Fetching IG Business Account ID (if any)...")
    try:
        ig_id = get_ig_business_id(page_id, page_token)
    except Exception as e:
        print("Failed to query IG Business account:", e)
        ig_id = None

    updates = {"META_ACCESS_TOKEN": page_token}
    if ig_id:
        updates["META_IG_USER_ID"] = ig_id

    print(f"Backing up .env to {os.path.basename(BACKUP_PATH)} and writing updates...")
    write_env_updates(ENV_PATH, updates)

    print("Done. Summary:")
    print(f" - Wrote META_ACCESS_TOKEN (Page token) to .env")
    if ig_id:
        print(f" - Wrote META_IG_USER_ID={ig_id} to .env")
    else:
        print(" - No IG Business Account found for this Page.")

    print("\nNext steps:")
    print(" - Restart the backend server so it picks up the new .env (e.g. stop/start run_server.py).")
    print("   Example: python scripts/run_server.py (or restart your service)\n")
    print(" - After restart, call the preflight endpoint to confirm FB+IG are live:")
    print("   curl http://127.0.0.1:8088/post/preflight | jq")


if __name__ == "__main__":
    main()
