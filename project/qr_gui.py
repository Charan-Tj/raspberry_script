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

class QRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi File Transfer")
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Main Container
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(expand=True, fill="both")

        # Title
        title_label = ttk.Label(main_frame, text="Raspberry Pi File Transfer", font=("Helvetica", 24, "bold"))
        title_label.pack(pady=20)

        # QR Container
        qr_frame = ttk.Frame(main_frame)
        qr_frame.pack(expand=True, fill="both")

        # --- Wi-Fi QR ---
        wifi_data = f"WIFI:S:{WIFI_SSID};T:WPA;P:{WIFI_PASS};;"
        self.wifi_img = ImageTk.PhotoImage(generate_qr_image(wifi_data).resize((300, 300)))
        
        wifi_panel = ttk.Frame(qr_frame)
        wifi_panel.pack(side="left", expand=True, padx=20)
        
        ttk.Label(wifi_panel, text="Step 1: Connect Wi-Fi", font=("Helvetica", 16)).pack(pady=10)
        ttk.Label(wifi_panel, image=self.wifi_img).pack()
        ttk.Label(wifi_panel, text=f"SSID: {WIFI_SSID}\nPass: {WIFI_PASS}", font=("Helvetica", 12), justify="center").pack(pady=10)

        # --- Upload QR ---
        ip = get_ip_address()
        if ip.startswith("192.168.4."):
            target_ip = HOTSPOT_IP
        else:
            target_ip = ip
            
        upload_url = f"http://{target_ip}:{PORT}{UPLOAD_ENDPOINT}"
        self.upload_img = ImageTk.PhotoImage(generate_qr_image(upload_url).resize((300, 300)))

        upload_panel = ttk.Frame(qr_frame)
        upload_panel.pack(side="right", expand=True, padx=20)

        ttk.Label(upload_panel, text="Step 2: Scan to Upload", font=("Helvetica", 16)).pack(pady=10)
        ttk.Label(upload_panel, image=self.upload_img).pack()
        ttk.Label(upload_panel, text=upload_url, font=("Helvetica", 12)).pack(pady=10)

        # Footer
        ttk.Label(main_frame, text="Press ESC to exit", font=("Helvetica", 10)).pack(side="bottom", pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = QRGUI(root)
    root.mainloop()
