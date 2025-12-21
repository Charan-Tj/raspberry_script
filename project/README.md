# Raspberry Pi File Transfer System

This project allows you to upload files to your Raspberry Pi via a Wi-Fi hotspot using a QR code to connect.

## Prerequisites

- Raspberry Pi with Wi-Fi capability
- Python 3 installed
- Flutter (optional, for the native mobile app)

## Installation

1.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the System

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

1.  **Connect to Pi Hotspot:**
    Ensure your mobile device is connected to the Raspberry Pi's Wi-Fi hotspot (IP `192.168.4.1`).

2.  **Scan & Upload (Web App):**
    - Scan the QR code with your phone's camera.
    - It will open the Web App in your browser.
    - Click "Select File" and then "Upload".

3.  **Scan & Upload (Flutter App):**
    - If you built the Flutter app, open it.
    - Tap "Scan QR Code".
    - Scan the generated QR code.
    - Pick a file and upload.

## Directory Structure

- `main.py`: The FastAPI server.
- `qr_generator.py`: Generates the QR code with the upload URL.
- `templates/index.html`: The Web App interface.
- `received_files/`: Uploaded files will appear here.
- `mobile_app/`: Source code for the Flutter application.
