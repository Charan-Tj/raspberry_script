import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import qrcode
import socket
import threading
import time
import os
import requests
import psutil

# --- Configuration ---
# Hotspot Config (Display Only)
WIFI_SSID = "Pi_Share"
WIFI_PASS = "raspberry_pi"
HOTSPOT_IP = "192.168.4.1"
PORT = 8000
UPLOAD_ENDPOINT = "/upload"
API_URL = f"http://127.0.0.1:{PORT}/api"

REFRESH_RATE = 2000 # ms
THEME_BG = "#1e1e1e"
THEME_FG = "#ffffff"
THEME_ACCENT = "#00adb5"
THEME_WARN = "#ff5722"
THEME_SUCCESS = "#4caf50"
THEME_CARD = "#2d2d2d"

def get_ip_address():
    """Get the local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_qr_image(data):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi Share Dashboard")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg=THEME_BG)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.running = True
        self._setup_styles()
        self._build_layout()
        
        self.update_loop()
        threading.Thread(target=self.tail_logs, daemon=True).start()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", background=THEME_BG, foreground=THEME_FG, font=("Segoe UI", 12))
        style.configure("TFrame", background=THEME_BG)
        style.configure("Card.TFrame", background=THEME_CARD, relief="flat", borderwidth=0)
        style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), background=THEME_BG, foreground=THEME_ACCENT)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 16), background=THEME_CARD, foreground="gray")
        style.configure("Status.TLabel", font=("Segoe UI", 20, "bold"), background=THEME_BG)

    def _build_layout(self):
        # Top Bar
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side="top", fill="x", padx=40, pady=20)
        
        ttk.Label(top_frame, text="Pi Share System", style="Header.TLabel").pack(side="left")
        self.lbl_ip = ttk.Label(top_frame, text="IP: Loading...", font=("Consolas", 14), foreground="orange")
        self.lbl_ip.pack(side="right")
        
        # Main Content
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill="both", padx=40, pady=10)

        # Left Column: QR Codes
        left_col = ttk.Frame(main_frame)
        left_col.pack(side="left", expand=True, fill="both", padx=(0, 20))
        self._build_qr_card(left_col)

        # Right Column: Stats & Logs
        right_col = ttk.Frame(main_frame)
        right_col.pack(side="right", fill="both", padx=(20, 0))
        self._build_stats_card(right_col)
        self._build_log_card(right_col)
        
        # Close Button (Safety)
        ttk.Button(self.root, text="Exit", command=self.root.destroy).place(x=10, y=10)

    def _build_qr_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        # Wi-Fi QR
        wifi_data = f"WIFI:S:{WIFI_SSID};T:WPA;P:{WIFI_PASS};;"
        self.wifi_img = ImageTk.PhotoImage(generate_qr_image(wifi_data).resize((220, 220)))
        
        # Upload QR (Dynamic)
        self.upload_img_lbl = ttk.Label(card, background=THEME_CARD)
        
        # Layout
        ttk.Label(card, text="1. Connect Wi-Fi", style="SubHeader.TLabel").grid(row=0, column=0, pady=10)
        ttk.Label(card, image=self.wifi_img, background=THEME_CARD).grid(row=1, column=0, padx=20)
        ttk.Label(card, text=f"SSID: {WIFI_SSID}\nPass: {WIFI_PASS}", font=("Consolas", 10), background=THEME_CARD).grid(row=2, column=0, pady=5)

        ttk.Label(card, text="2. Scan to Upload", style="SubHeader.TLabel").grid(row=0, column=1, pady=10)
        self.upload_img_lbl.grid(row=1, column=1, padx=20)
        self.lbl_url = ttk.Label(card, text="Loading...", font=("Consolas", 10), background=THEME_CARD)
        self.lbl_url.grid(row=2, column=1, pady=5)
        
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

    def _build_stats_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="x", pady=(0, 20))
        
        ttk.Label(card, text="System Health", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))
        self.lbl_cpu = ttk.Label(card, text="CPU: ...", background=THEME_CARD)
        self.lbl_cpu.pack(anchor="w")
        self.lbl_ram = ttk.Label(card, text="RAM: ...", background=THEME_CARD)
        self.lbl_ram.pack(anchor="w")
        self.lbl_disk = ttk.Label(card, text="Storage: ...", background=THEME_CARD)
        self.lbl_disk.pack(anchor="w")
        self.lbl_temp = ttk.Label(card, text="Temp: ...", background=THEME_CARD)
        self.lbl_temp.pack(anchor="w")

    def _build_log_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)
        ttk.Label(card, text="Server Logs", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))
        self.log_text = tk.Text(card, height=10, bg="#111", fg="#ccc", relief="flat", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    def update_loop(self):
        # Update IP and Upload QR
        ip = get_ip_address()
        target_ip = HOTSPOT_IP if ip.startswith("192.168.4.") else ip
        self.lbl_ip.config(text=f"IP: {target_ip}")
        
        upload_url = f"http://{target_ip}:{PORT}{UPLOAD_ENDPOINT}"
        self.lbl_url.config(text=upload_url)
        
        # Refresh Upload QR
        img = generate_qr_image(upload_url).resize((220, 220))
        self.tk_upload_img = ImageTk.PhotoImage(img) # Keep ref
        self.upload_img_lbl.config(image=self.tk_upload_img)

        # Fetch Stats from API if available
        try:
            r = requests.get(f"{API_URL}/status", timeout=0.5)
            if r.status_code == 200:
                data = r.json()
                stats = data.get('stats', {})
                self.lbl_cpu.config(text=f"CPU: {stats.get('cpu_percent', 0)}%")
                self.lbl_ram.config(text=f"RAM: {stats.get('ram_percent', 0)}%")
                self.lbl_disk.config(text=f"Storage: {stats.get('storage_percent', 0)}%")
                self.lbl_temp.config(text=f"Temp: {stats.get('cpu_temp', 'N/A')}°C")
        except:
            pass # API might be down

        self.root.after(REFRESH_RATE, self.update_loop)

    def tail_logs(self):
        log_file = "server.log"
        if not os.path.exists(log_file):
            return
            
        with open(log_file, "r") as f:
            f.seek(0, 2)
            while self.running:
                line = f.readline()
                if line:
                    self.root.after(0, lambda l=line: self.log_text.insert("end", l) or self.log_text.see("end"))
                else:
                    time.sleep(0.5)

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()
