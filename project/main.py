import os
import socket
import psutil
import fcntl
import struct
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up System (Clean Version 5)...")
    yield
    # Shutdown
    logger.info("Shutting down System...")

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
            pass 

        # Method 2: Connect to external server
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
        
        # CPU Temp
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
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {file.filename}")
        return JSONResponse(content={"status": "success", "filename": file.filename, "message": "File uploaded successfully"})
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/status")
async def get_api_status():
    """Simplified API for GUI Status (Stats Only)."""
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
    
    return JSONResponse(content={
        "system_ip": ip,
        "stats": stats,
        "connectivity": {
            "hotspot_active": True, # Assumed active via service
            "internet_access": False
        }
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
