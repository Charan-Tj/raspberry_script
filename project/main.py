import os
import socket
import psutil
import fcntl
import struct
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from session_manager import SessionManager
from ble_server import BLEServer

# Configure Logging
LOG_FILE = "server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directory to save uploaded files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "received_files")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global State
session_manager = SessionManager()
ble_server = BLEServer(session_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up System...")
    # Start BLE Server in background
    asyncio.create_task(ble_server.start())
    yield
    # Shutdown
    logger.info("Shutting down System...")
    await ble_server.stop()
    session_manager.end_session() # Ensure hotspot is off

app = FastAPI(lifespan=lifespan)

# Setup templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

def get_ip_address():
    """Get the local IP address, prioritizing the Hotspot interface (wlan0)."""
    try:
        # Method 1: Try to get IP of wlan0 specifically (Linux/Pi)
        ifname = "wlan0"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname.encode('utf-8')[:15])
            )[20:24])
        except Exception:
            pass # wlan0 not found or not active, fall back to general method

        # Method 2: Connect to external server to find default route IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.get("/stats")
async def get_stats():
    """Return system statistics."""
    try:
        storage = psutil.disk_usage('/')
        mem = psutil.virtual_memory()
        
        # CPU Temp (Raspberry Pi specific)
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = round(int(f.read()) / 1000, 1)
        except:
            temp = "N/A"

        return {
            "storage_used": f"{storage.used / (1024**3):.1f} GB",
            "storage_total": f"{storage.total / (1024**3):.1f} GB",
            "storage_percent": storage.percent,
            "ram_percent": mem.percent,
            "cpu_temp": temp
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/upload", response_class=HTMLResponse)
async def get_upload_page(request: Request):
    # Optional: Check session here too if we want to hide the page
    # if not session_manager.is_session_active():
    #     return HTMLResponse(content="<h1>Session Expired</h1><p>Please scan QR code again.</p>", status_code=403)
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Enforce Session
    if not session_manager.is_session_active():
        logger.warning("Upload attempt without active session.")
        return JSONResponse(
            content={"status": "error", "message": "No active session. Please scan QR code to start a session."},
            status_code=403
        )

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {file.filename}")
        return JSONResponse(content={"status": "success", "filename": file.filename, "message": "File uploaded successfully"})
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
@app.get("/api/status")
async def get_api_status():
    """API Endpoint for GUI to fetch full system state."""
    
    # 1. System Stats
    try:
        storage = psutil.disk_usage('/')
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = round(int(f.read()) / 1000, 1)
        except:
            temp = "N/A"
            
        stats = {
            "storage_percent": storage.percent,
            "ram_percent": mem.percent,
            "cpu_percent": cpu,
            "cpu_temp": temp
        }
    except Exception:
        stats = {}

    # 2. Network Info
    ip = get_ip_address()
    
    # 3. Session Info
    session_active = session_manager.is_session_active()
    session_data = {}
    
    if session_active:
        # Check time remaining
        elapsed = time.time() - session_manager.active_session['start_time']
        timeout = session_manager.active_session['params']['session_timeout']
        remaining = max(0, timeout - elapsed)
        
        session_data = {
            "id": session_manager.active_session['id'],
            "ssid": session_manager.active_session['ssid'],
            "password": session_manager.active_session['password'],
            "time_remaining": int(remaining)
        }

    # 4. Connectivity Info
    internet_access = False
    try:
        # Quick check to see if we can reach Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=0.1)
        internet_access = True
    except OSError:
        pass

    connectivity = {
        "internet_access": internet_access,
        "hotspot_clients": session_manager.hotspot.get_active_clients(),
        "ble_state": ble_server.state
    }

    return JSONResponse(content={
        "system_ip": ip,
        "hotspot_active": True, 
        "session_active": session_active,
        "session": session_data,
        "stats": stats,
        "connectivity": connectivity
    })

@app.post("/api/control/start_session")
async def start_session_api():
    """Start a new session manually from GUI."""
    session = session_manager.start_session()
    if session:
        logger.info(f"Session started manually: {session['id']}")
        return JSONResponse(content={"status": "success", "session_id": session["id"]})
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to start session"}, status_code=500)

@app.post("/api/control/end_session")
async def end_session_api():
    """Force end the current session from GUI."""
    if session_manager.end_session():
        logger.info("Session ended via GUI.")
        return JSONResponse(content={"status": "success", "message": "Session ended"})
    else:
        return JSONResponse(content={"status": "error", "message": "No active session"}, status_code=400)

if __name__ == "__main__":
    # Listen on all interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
