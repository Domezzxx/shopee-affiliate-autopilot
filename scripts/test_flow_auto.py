import os
import sys

# Add project root to sys.path to allow imports from backend
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.engines.flow_automation import generate_video_flow
from app.config import settings

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("==================================================")
    print("  Google Flow Browser Automation Test Script  ")
    print("==================================================")
    print(f"CDP URL: {settings.flow_cdp_url}")
    print(f"Target Directory: {settings.media_dir}")
    print("--------------------------------------------------")
    print("Before running, make sure:")
    print("1. Chrome is open and logged into https://labs.google/fx/tools/flow")
    print("2. You started Chrome with remote debugging on port 9222:")
    print("   Run .\\scripts\\start_chrome_debug.ps1 in PowerShell")
    print("--------------------------------------------------")
    
    test_prompt = (
        "Appetizing close-up shot of a steaming hot bowl of Pad Thai, "
        "glistering sauce, fresh lime slice on the side, 9:16 vertical video"
    )
    
    try:
        print("[TEST] Running generate_video_flow...")
        video_path = generate_video_flow(test_prompt)
        print("\n==================================================")
        print("[SUCCESS] Video generated successfully!")
        print(f"File saved to: {video_path}")
        print("==================================================")
    except Exception as e:
        print("\n==================================================")
        print("[FAILURE] Video generation failed!")
        print(f"Error details: {e}")
        print("\nTroubleshooting tips:")
        print("- Verify that Chrome is actually running and you can access http://localhost:9222/json in your browser.")
        print("- Make sure you have enough credits in your Google Flow account.")
        print("- If the webpage changed, you may need to update the selectors in your .env file.")
        print("==================================================")

if __name__ == "__main__":
    main()
