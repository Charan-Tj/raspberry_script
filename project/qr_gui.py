import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time
import threading
import socket
from datetime import datetime

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/api"
REFRESH_RATE = 1000 # ms
THEME_BG = "#1e1e1e"
THEME_FG = "#ffffff"
THEME_ACCENT = "#00adb5"
THEME_WARN = "#ff5722"
THEME_SUCCESS = "#4caf50"
THEME_CARD = "#2d2d2d"

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi Share Kiosk")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg=THEME_BG)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # State
        self.running = True
        self.logs = []
        
        # Styles
        self._setup_styles()
        
        # Layout
        self._build_layout()
        
        # Background Tasks
        self.update_loop()
        threading.Thread(target=self.tail_logs, daemon=True).start()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure(".", background=THEME_BG, foreground=THEME_FG, font=("Segoe UI", 12))
        style.configure("TFrame", background=THEME_BG)
        
        # Cards
        style.configure("Card.TFrame", background=THEME_CARD, relief="flat", borderwidth=0)
        
        # Labels
        style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), background=THEME_BG, foreground=THEME_ACCENT)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 16), background=THEME_CARD, foreground="gray")
        style.configure("Status.TLabel", font=("Segoe UI", 48, "bold"), background=THEME_BG)
        
        # Buttons
        style.configure("Action.TButton", font=("Segoe UI", 14, "bold"), background=THEME_ACCENT, foreground="white", borderwidth=0)
        style.map("Action.TButton", background=[("active", "#007d85")])
        
        style.configure("Danger.TButton", font=("Segoe UI", 14, "bold"), background=THEME_WARN, foreground="white", borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#d84315")])

    def _build_layout(self):
        # Top Bar
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side="top", fill="x", padx=40, pady=20)
        
        ttk.Label(top_frame, text="Pi Share System", style="Header.TLabel").pack(side="left")
        self.lbl_ip = ttk.Label(top_frame, text="IP: Loading...", font=("Consolas", 14), foreground="orange")
        self.lbl_ip.pack(side="right")

        # Main Content Area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill="both", padx=40, pady=10)
        
        # Left Column: Status & Session
        left_col = ttk.Frame(main_frame)
        left_col.pack(side="left", expand=True, fill="both", padx=(0, 20))
        
        self._build_status_card(left_col)
        self._build_session_card(left_col)

        # Right Column: System Stats & Logs
        right_col = ttk.Frame(main_frame, width=400) # Set width on Frame
        right_col.pack(side="right", fill="both", padx=(20, 0)) # Pack without width
        right_col.pack_propagate(False) # Enforce size if needed, or let content dictate. 
        # Actually simplest is just packing it normally. 
        # If we really want width, we use place or pack_propagate.
        # Let's just remove width=400 from pack and let it be responsive.
        
        # Correct fix:
        right_col = ttk.Frame(main_frame)
        right_col.pack(side="right", fill="both", padx=(20, 0))
        
        self._build_connectivity_card(right_col)
        self._build_stats_card(right_col)
        self._build_log_card(right_col)

    def _build_status_card(self, parent):
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill="x", pady=(0, 20))
        
        self.lbl_main_status = ttk.Label(self.status_frame, text="Initializing...", style="Status.TLabel", foreground="gray")
        self.lbl_main_status.pack(pady=20)
        
        self.lbl_sub_status = ttk.Label(self.status_frame, text="Please wait", font=("Segoe UI", 18))
        self.lbl_sub_status.pack()

    def _build_session_card(self, parent):
        self.card_session = ttk.Frame(parent, style="Card.TFrame", padding=30)
        self.card_session.pack(fill="both", expand=True)
        
        ttk.Label(self.card_session, text="Current Session", style="SubHeader.TLabel", background=THEME_CARD).pack(anchor="w")
        
        # Session Details (Hidden by default)
        self.session_details_frame = ttk.Frame(self.card_session, style="Card.TFrame")
        self.session_details_frame.pack(fill="both", expand=True, pady=20)
        
        self.lbl_timer = ttk.Label(self.session_details_frame, text="--:--", font=("Consolas", 60, "bold"), 
                                   background=THEME_CARD, foreground=THEME_ACCENT)
        self.lbl_timer.pack()
        
        self.lbl_creds = ttk.Label(self.session_details_frame, text="SSID: ... | PASS: ...", 
                                   font=("Consolas", 16), background=THEME_CARD, foreground="white")
        self.lbl_creds.pack(pady=10)
        
        # End Session Button
        self.btn_end = ttk.Button(self.card_session, text="End Session", style="Danger.TButton", command=self.end_session)
        self.btn_end.pack(fill="x", pady=10)
        self.btn_end.state(['disabled'])

    def _build_connectivity_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="x", pady=(0, 20))
        
        ttk.Label(card, text="Connectivity", style="SubHeader.TLabel", background=THEME_CARD).pack(anchor="w", marginBottom=10)
        
        # Grid for icons
        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")
        
        # Row 1: Hotspot
        self.lbl_hotspot = ttk.Label(grid, text="📡 Hotspot: ...", background=THEME_CARD)
        self.lbl_hotspot.pack(anchor="w", pady=2)
        
        # Row 2: BLE
        self.lbl_ble = ttk.Label(grid, text="🔵 Bluetooth: ...", background=THEME_CARD)
        self.lbl_ble.pack(anchor="w", pady=2)
        
        # Row 3: Internet
        self.lbl_net = ttk.Label(grid, text="🌐 Internet: ...", background=THEME_CARD)
        self.lbl_net.pack(anchor="w", pady=2)

    def _build_stats_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="x", pady=(0, 20))
        
        ttk.Label(card, text="System Health", style="SubHeader.TLabel", background=THEME_CARD).pack(anchor="w", marginBottom=10)
        
        self.lbl_cpu = ttk.Label(card, text="CPU: ...", background=THEME_CARD)
        self.lbl_cpu.pack(anchor="w")
        self.lbl_ram = ttk.Label(card, text="RAM: ...", background=THEME_CARD)
        self.lbl_ram.pack(anchor="w")
        self.lbl_temp = ttk.Label(card, text="Temp: ...", background=THEME_CARD)
        self.lbl_temp.pack(anchor="w")

    def _build_log_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)
        
        ttk.Label(card, text="Server Logs", style="SubHeader.TLabel", background=THEME_CARD).pack(anchor="w", marginBottom=10)
        
        self.log_text = tk.Text(card, height=10, bg="#111", fg="#ccc", relief="flat", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    # --- Logic ---

    def update_loop(self):
        self._fetch_api_data()
        self.root.after(REFRESH_RATE, self.update_loop)

    def _fetch_api_data(self):
        try:
            r = requests.get(f"{API_URL}/status/api/status", timeout=0.5) # Using full url to be safe or relative? 
            # Wait, API_URL is http://127.0.0.1:8000/api
            # endpoint is /status
            # requests.get("http://127.0.0.1:8000/api/status")
            r = requests.get(f"{API_URL}/status", timeout=0.5)
            
            if r.status_code == 200:
                data = r.json()
                self._update_ui(data)
            else:
                self._set_error_state("API Error")
        except requests.exceptions.ConnectionError:
            self._set_error_state("Backend Offline")
        except Exception as e:
            print(e)
            self._set_error_state("Error")

    def _update_ui(self, data):
        # Update IP
        self.lbl_ip.config(text=f"IP: {data.get('system_ip', 'Unknown')}")
        
        # Update System Stats
        stats = data.get('stats', {})
        self.lbl_cpu.config(text=f"CPU: {stats.get('cpu_percent', 0)}%")
        self.lbl_ram.config(text=f"RAM: {stats.get('ram_percent', 0)}%")
        self.lbl_temp.config(text=f"Temp: {stats.get('cpu_temp', 'N/A')}°C")

        # Update Connectivity
        conn = data.get('connectivity', {})
        
        # 1. Hotspot
        clients = conn.get('hotspot_clients', 0)
        self.lbl_hotspot.config(text=f"📡 Hotspot: Active ({clients} Clients)")
        
        # 2. BLE
        ble_state = conn.get('ble_state', 'UNKNOWN')
        if ble_state == "ADVERTISING":
             self.lbl_ble.config(text="🔵 Bluetooth: Advertising (Ready)", foreground=THEME_FG)
        elif ble_state == "CONNECTED": # If we tracked connected state
             self.lbl_ble.config(text="🟢 Bluetooth: Device Connected", foreground=THEME_SUCCESS)
        else:
             self.lbl_ble.config(text=f"⚪ Bluetooth: {ble_state}", foreground="gray")
             
        # 3. Internet
        has_net = conn.get('internet_access', False)
        if has_net:
            self.lbl_net.config(text="🌐 Internet: Online", foreground=THEME_SUCCESS)
        else:
            self.lbl_net.config(text="🌐 Internet: Offline", foreground=THEME_WARN)

        # Update Session State
        if data.get('session_active'):
            # Active State
            session = data.get('session', {})
            remaining = session.get('time_remaining', 0)
            mins, secs = divmod(remaining, 60)
            
            self.lbl_main_status.config(text="Session Active", foreground=THEME_SUCCESS)
            self.lbl_sub_status.config(text="User is currently uploading files.")
            
            self.lbl_timer.config(text=f"{mins:02}:{secs:02}")
            self.lbl_creds.config(text=f"SSID: {session.get('ssid')} | PASS: {session.get('password')}")
            
            self.session_details_frame.pack(fill="both", expand=True, pady=20) # Ensure visible
            self.btn_end.state(['!disabled'])
        else:
            # Idle State
            self.lbl_main_status.config(text="Ready to Connect", foreground=THEME_ACCENT)
            self.lbl_sub_status.config(text="Use the mobile app to scan and connect.")
            
            self.session_details_frame.pack_forget() # Hide details
            self.btn_end.state(['disabled'])

    def _set_error_state(self, message):
        self.lbl_main_status.config(text=message, foreground=THEME_WARN)
        self.lbl_sub_status.config(text="Is the server running?")
        self.lbl_ip.config(text="IP: --")

    def end_session(self):
        try:
            requests.post(f"{API_URL}/control/end_session")
        except:
            messagebox.showerror("Error", "Failed to send command")

    def tail_logs(self):
        log_file = "server.log"
        # Wait for file
        while not os.path.exists(log_file):
            time.sleep(1)
            
        with open(log_file, "r") as f:
            f.seek(0, 2)
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
    app = DashboardApp(root)
    root.mainloop()
