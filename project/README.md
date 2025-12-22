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

## Version 2: Auto-Hotspot & Auto-Start

To make the Pi automatically create a hotspot and start the server on boot:

1.  **Setup Hotspot:**
    *   **Warning:** This will disconnect your current Wi-Fi.
    *   Run the setup script:
        ```bash
        sudo bash project/setup_hotspot.sh
        ```
    *   This creates a Wi-Fi network named **Pi_Share** (Password: `raspberry_pi`).

2.  **Enable Auto-Start Service:**
    *   Copy the service file:
        ```bash
        sudo cp project/pi_share.service /etc/systemd/system/
        ```
    *   Reload systemd and enable the service:
        ```bash
        sudo systemctl daemon-reload
        sudo systemctl enable pi_share.service
        sudo systemctl start pi_share.service
        ```

## Usage

1.  **Connect Network:**
    - Connect your phone to the **Pi_Share** Wi-Fi network.
    - Password: `raspberry_pi`

2.  **Scan & Upload:**
    - The Pi will generate two QR codes:
        *   **`wifi_qr.png`**: Scan this to automatically connect to the `Pi_Share` Wi-Fi.
        *   **`upload_qr.png`**: Scan this to open the upload page.
    - Run `python project/qr_generator.py` to regenerate them if needed.

3.  **View Uploaded Files:**
    - **Terminal:** `ls -l project/received_files`
    - **File Manager:** `xdg-open project/received_files`

## Directory Structure

- `main.py`: The FastAPI server.
- `qr_generator.py`: Generates the QR code with the upload URL.
- `templates/index.html`: The Web App interface.
- `received_files/`: Uploaded files will appear here.
- `mobile_app/`: Source code for the Flutter application.
