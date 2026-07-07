import tkinter as tk
from tkinter import messagebox
import subprocess
import webbrowser
import socket
import threading
import sys
import os
import time

PORT = 8088
server_process = None

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_server():
    global server_process
    if is_port_in_use(PORT):
        print(f"Port {PORT} is already in use. Assuming server is already running.")
        return

    proj_dir = os.path.dirname(os.path.abspath(__file__))
    env = os.environ.copy()
    env["DATA_DIR"] = os.path.join(proj_dir, "data").replace('\\', '/')

    # We use python.exe from virtual env to run uvicorn
    python_exe = os.path.join(proj_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # Fallback

    cmd = [
        python_exe, "-m", "uvicorn", "app.main:app",
        "--app-dir", os.path.join(proj_dir, "backend"),
        "--host", "127.0.0.1", "--port", str(PORT)
    ]
    
    try:
        # Launch uvicorn silently in background
        server_process = subprocess.Popen(
            cmd,
            cwd=proj_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print(f"Server started with process ID: {server_process.pid}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start server: {e}")

def shutdown_server():
    global server_process
    if server_process:
        try:
            print("Terminating server process...")
            server_process.terminate()
            server_process.wait(timeout=3)
            print("Server process terminated.")
        except Exception as e:
            print("Error shutting down server:", e)
            # Force kill if needed
            try:
                server_process.kill()
            except:
                pass
        server_process = None

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Affiliate Autopilot")
        self.root.geometry("420x240")
        self.root.configure(bg="#121214")
        self.root.resizable(False, False)

        # Style configurations
        bg_dark = "#121214"
        card_dark = "#1e1e22"
        text_white = "#e4e4e7"
        accent_green = "#10b981"
        accent_blue = "#3b82f6"
        line_gray = "#27272a"

        # Center Window on Screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 420) // 2
        y = (screen_height - 240) // 2
        root.geometry(f"420x240+{x}+{y}")

        # Top Header Bar
        header = tk.Frame(root, bg=card_dark, height=50, bd=0, highlightthickness=0)
        header.pack(fill="x", side="top")

        title_label = tk.Label(header, text="🤖 Shopee Affiliate Autopilot", bg=card_dark, fg=text_white, font=("Inter", 12, "bold"))
        title_label.pack(pady=12, padx=15, side="left")

        # Main Status Card Frame
        card = tk.Frame(root, bg=card_dark, bd=1, highlightbackground=line_gray, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # Status Circle Indicator
        status_frame = tk.Frame(card, bg=card_dark)
        status_frame.pack(pady=15)

        self.status_dot = tk.Label(status_frame, text="●", bg=card_dark, fg=accent_green, font=("Inter", 14))
        self.status_dot.pack(side="left", padx=5)

        self.status_text = tk.Label(status_frame, text=f"Server is Active (Port {PORT})", bg=card_dark, fg=text_white, font=("Inter", 10, "bold"))
        self.status_text.pack(side="left", padx=5)

        # Dashboard URL Label Link
        url_label = tk.Label(card, text=f"http://127.0.0.1:{PORT}", bg=card_dark, fg=accent_blue, font=("Inter", 10, "underline"), cursor="hand2")
        url_label.pack(pady=2)
        url_label.bind("<Button-1>", lambda e: self.open_browser())

        # Buttons Panel
        btn_frame = tk.Frame(card, bg=card_dark)
        btn_frame.pack(pady=15, fill="x", padx=20)

        self.btn_open = tk.Button(
            btn_frame, text="🌐 Open Dashboard", bg=accent_blue, fg="white", font=("Inter", 10, "bold"),
            activebackground="#2563eb", activeforeground="white", relief="flat", bd=0, padx=15, pady=8,
            command=self.open_browser
        )
        self.btn_open.pack(side="left", expand=True, fill="x", padx=5)

        self.btn_exit = tk.Button(
            btn_frame, text="🛑 Shutdown & Exit", bg="#ef4444", fg="white", font=("Inter", 10, "bold"),
            activebackground="#dc2626", activeforeground="white", relief="flat", bd=0, padx=15, pady=8,
            command=self.on_exit
        )
        self.btn_exit.pack(side="right", expand=True, fill="x", padx=5)

        # Set up shutdown on window close [X]
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Auto-launch default browser on startup after a brief delay
        self.root.after(1000, self.open_browser)

    def open_browser(self):
        webbrowser.open(f"http://127.0.0.1:{PORT}/")

    def on_exit(self):
        if messagebox.askokcancel("Exit", "Do you want to stop the server and exit the application?"):
            shutdown_server()
            self.root.destroy()

if __name__ == "__main__":
    # Start the backend server in background before loading the GUI
    print("Starting background server thread...")
    start_server()
    
    # Run the Tkinter GUI main loop
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()
