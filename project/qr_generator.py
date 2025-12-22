import qrcode
from PIL import Image
import socket
import os
import sys

# Configuration
HOTSPOT_IP = "192.168.4.1"
PORT = 8000
UPLOAD_ENDPOINT = "/upload"

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
            pass # wlan0 not found or not active

        # Method 2: Connect to external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_wifi_qr(ssid, password):
    """Generate a QR code to connect to the Wi-Fi network."""
    # WIFI:S:SSID;T:WPA;P:PASSWORD;;
    wifi_data = f"WIFI:S:{ssid};T:WPA;P:{password};;"
    print(f"Generating Wi-Fi QR code for SSID: {ssid}")
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(wifi_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save("wifi_qr.png")
    print("Wi-Fi QR code saved as wifi_qr.png")
    return img

def generate_upload_qr():
    # Construct the URL
    # If running on actual Pi hotspot, use the fixed IP.
    # Otherwise, try to detect IP for testing.
    current_ip = get_ip_address()
    
    # Logic: If we detect we are on the 192.168.4.x network, use that.
    # Otherwise, warn user but use detected IP for flexibility.
    if current_ip.startswith("192.168.4."):
        target_ip = HOTSPOT_IP
    else:
        print(f"Warning: Not on standard Hotspot IP range. Using detected IP: {current_ip}")
        target_ip = current_ip

    url = f"http://{target_ip}:{PORT}{UPLOAD_ENDPOINT}"
    print(f"Generating Upload QR code for: {url}")

    # Generate QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save("upload_qr.png")
    print("Upload QR code saved as upload_qr.png")
    
    return img

def show_qr(img, title="QR Code"):
    # Try to show image using default viewer
    try:
        img.show(title=title)
    except Exception as e:
        print(f"Could not display image directly: {e}")

if __name__ == "__main__":
    # Generate Wi-Fi QR (Matches setup_hotspot.sh config)
    wifi_img = generate_wifi_qr("Pi_Share", "raspberry_pi")
    
    # Generate Upload QR
    upload_img = generate_upload_qr()
    
    print("\nDONE! Two QR codes generated:")
    print("1. wifi_qr.png   -> Scan to connect to Wi-Fi")
    print("2. upload_qr.png -> Scan to open Upload Page")
    
    # Attempt to show them (OS dependent)
    show_qr(wifi_img, "Wi-Fi QR")
    show_qr(upload_img, "Upload QR")
