import os
import sys
import argparse

# Add project root to sys.path to allow imports from backend
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.config import settings
from app.connectors.phone_automator import connect_device, sync_media, post_facebook_reel, post_instagram_reel, post_youtube_shorts

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Test script for Phone Farm Automation using uiautomator2")
    parser.add_argument("--device", help="ADB serial or IP:PORT of the phone to test (defaults to settings.phone_list[0])")
    parser.add_argument("--platform", choices=["facebook", "instagram", "youtube", "check"], default="check",
                        help="Platform to test: facebook, instagram, youtube, or check (default)")
    parser.add_argument("--video", help="Path to a test video file to push and upload")
    parser.add_argument("--caption", default="ของดีบอกต่อ! ก๋วยเตี๋ยวเรือเจ้านี้อร่อยมาก สั่งเลยคอมเมนต์แรก 🍜🔥 #รีวิว #ShopeeFood",
                        help="Caption to write on post")
                        
    args = parser.parse_args()
    
    print("==================================================")
    print("  Phone Farm Automation Test Script  ")
    print("==================================================")
    
    devices = settings.phone_list
    target_device = args.device or (devices[0] if devices else None)
    
    if not target_device:
        print("[ERROR] No phone farm devices found in config. Please set PHONE_FARM_DEVICES in your .env file.")
        print("Example: PHONE_FARM_DEVICES=192.168.1.51:5555,192.168.1.52:5555")
        sys.exit(1)
        
    print(f"Target Device: {target_device}")
    print(f"Platform: {args.platform}")
    print("--------------------------------------------------")
    
    try:
        # 1) Connect and test uiautomator2 connection
        print("[TEST] Connecting to device and initializing uiautomator2...")
        d = connect_device(target_device)
        print("[SUCCESS] Device connected successfully!")
        print(f"Device Info: {d.info}")
        print("--------------------------------------------------")
        
        if args.platform == "check":
            print("[INFO] Connection check passed. Exiting test.")
            return
            
        # 2) Sync test media
        video_path = args.video
        if not video_path:
            # Look for a default demo video in backend media or scripts
            demo_paths = [
                os.path.join(project_root, "scripts", "test_downloaded_video.mp4"),
                os.path.join(project_root, "data", "media", "video_flow_a116c792.mp4")
            ]
            for p in demo_paths:
                if os.path.exists(p):
                    video_path = p
                    break
                    
        if not video_path or not os.path.exists(video_path):
            print(f"[ERROR] Test video file not found. Please provide --video <path>.")
            sys.exit(1)
            
        print(f"[TEST] Preparing video: {video_path}")
        remote_path = sync_media(target_device, video_path)
        print(f"[SUCCESS] Video synced to device path: {remote_path}")
        print("--------------------------------------------------")
        
        # 3) Run platform posting automation
        print(f"[TEST] Executing automation flow for: {args.platform}...")
        if args.platform == "facebook":
            res = post_facebook_reel(target_device, video_path, args.caption)
        elif args.platform == "instagram":
            res = post_instagram_reel(target_device, video_path, args.caption)
        elif args.platform == "youtube":
            res = post_youtube_shorts(target_device, video_path, args.caption)
            
        if res["ok"]:
            print("\n==================================================")
            print(f"[SUCCESS] Reels/Shorts posted successfully on {args.platform}!")
            print("==================================================")
        else:
            print("\n==================================================")
            print(f"[FAILURE] Automation failed for {args.platform}!")
            print(f"Error: {res['error']}")
            print("==================================================")
            
    except Exception as e:
        print("\n==================================================")
        print(f"[FAILURE] Connection or testing failed!")
        print(f"Error details: {e}")
        print("==================================================")

if __name__ == "__main__":
    main()
