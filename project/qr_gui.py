import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import qrcode
import socket
import os
import sys

# Configuration
HOTSPOT_IP = "192.168.4.1"
PORT = 8000
UPLOAD_ENDPOINT = "/upload"
WIFI_SSID = "Pi_Share"
WIFI_PASS = "raspberry_pi"

def get_ip_address():
    """Get the local IP address, prioritizing the Hotspot interface (wlan0)."""
    try:
        # Method 1: Try to get IP of wlan0 specifically (Linux/Pi)
        import fcntl
        import struct
        
        ifname = "wlan0"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname.encode('utf-8')[:15])
            )[20:24])
        except Exception:
            pass 

        # Method 2: Connect to external server
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

import psutil
import threading
import time

# ... (Previous imports and config)

class QRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi File Transfer Dashboard")
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Main Layout (Grid)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=2) # QR Area
        self.root.rowconfigure(1, weight=1) # Stats Area
        self.root.rowconfigure(2, weight=1) # Logs Area

        # --- 1. QR Codes (Top) ---
        qr_frame = ttk.Frame(root)
        qr_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=10)
        
        # Wi-Fi QR
        wifi_data = f"WIFI:S:{WIFI_SSID};T:WPA;P:{WIFI_PASS};;"
        self.wifi_img = ImageTk.PhotoImage(generate_qr_image(wifi_data).resize((250, 250)))
        ttk.Label(qr_frame, text="1. Connect Wi-Fi", font=("Helvetica", 14, "bold")).pack(side="left", padx=50)
        ttk.Label(qr_frame, image=self.wifi_img).pack(side="left")

        # Upload QR
        ip = get_ip_address()
        target_ip = HOTSPOT_IP if ip.startswith("192.168.4.") else ip
        upload_url = f"http://{target_ip}:{PORT}{UPLOAD_ENDPOINT}"
        self.upload_img = ImageTk.PhotoImage(generate_qr_image(upload_url).resize((250, 250)))
        ttk.Label(qr_frame, image=self.upload_img).pack(side="right")
        ttk.Label(qr_frame, text="2. Scan to Upload", font=("Helvetica", 14, "bold")).pack(side="right", padx=50)

        # --- 2. System Stats (Middle) ---
        stats_frame = ttk.LabelFrame(root, text="System Status", padding=10)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20)
        
        self.lbl_cpu = ttk.Label(stats_frame, text="CPU: ...", font=("Helvetica", 12))
        self.lbl_cpu.pack(side="left", expand=True)
        
        self.lbl_ram = ttk.Label(stats_frame, text="RAM: ...", font=("Helvetica", 12))
        self.lbl_ram.pack(side="left", expand=True)
        
        self.lbl_disk = ttk.Label(stats_frame, text="Storage: ...", font=("Helvetica", 12))
        self.lbl_disk.pack(side="left", expand=True)

        # --- 3. Server Logs (Bottom) ---
        log_frame = ttk.LabelFrame(root, text="Live Server Logs", padding=10)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, font=("Courier", 10))
        self.log_text.pack(fill="both", expand=True)

        # Start Threads
        self.running = True
        threading.Thread(target=self.update_stats, daemon=True).start()
        threading.Thread(target=self.tail_logs, daemon=True).start()

    def update_stats(self):
        while self.running:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Update UI in main thread
            self.root.after(0, lambda: self.lbl_cpu.config(text=f"CPU: {cpu}%"))
            self.root.after(0, lambda: self.lbl_ram.config(text=f"RAM: {ram}%"))
            self.root.after(0, lambda: self.lbl_disk.config(text=f"Storage: {disk}% Used"))
            time.sleep(2)

    def tail_logs(self):
        log_file = "server.log"
        if not os.path.exists(log_file):
            open(log_file, 'a').close()
            
        with open(log_file, "r") as f:
            f.seek(0, 2) # Go to end
            while self.running:
                line = f.readline()
                if line:
                    self.root.after(0, lambda l=line: self.append_log(l))
                else:
                    time.sleep(0.5)

    def append_log(self, line):
        self.log_text.insert("end", line)
        self.log_text.see("end")

if __name__ == "__main__":
    root = tk.Tk()
    app = QRGUI(root)
    root.mainloop()
