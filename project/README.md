# Raspberry Pi File Transfer System

This project allows you to upload files to your Raspberry Pi via a Wi-Fi hotspot using a QR code to connect.

## Prerequisites

- Raspberry Pi with Wi-Fi capability
- Python 3 installed
- Flutter (optional, for the native mobile app)

## Installation on Raspberry Pi

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Charan-Tj/raspberry_script.git
    cd raspberry_script
    ```

2.  **Set up Virtual Environment (Required for Pi OS Bookworm):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r project/requirements.txt
    ```

## Running the System

**Note:** Always ensure your virtual environment is active (`source venv/bin/activate`) before running these commands.

1.  **Start the QR Code Generator:**
    This will generate `qrcode.png` and try to display it.
    ```bash
    python qr_generator.py
    ```

2.  **Start the Server:**
    This starts the web server to receive files.
    ```bash
    python main.py
    ```

## Usage

1.  **Connect Network:**
    - Ensure your Pi and Phone are on the same network (e.g., Pi connected to Phone Hotspot, or both on home Wi-Fi).

2.  **Scan & Upload:**
    - Run `python project/qr_generator.py` on the Pi.
    - Scan the QR code with your phone.
    - Upload a file via the Web App.

3.  **View Uploaded Files:**
    - **Terminal:** `ls -l project/received_files`
    - **File Manager:** `xdg-open project/received_files`

## Directory Structure

- `main.py`: The FastAPI server.
- `qr_generator.py`: Generates the QR code with the upload URL.
- `templates/index.html`: The Web App interface.
- `received_files/`: Uploaded files will appear here.
- `mobile_app/`: Source code for the Flutter application.
