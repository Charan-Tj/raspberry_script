import subprocess
import logging
import os

logger = logging.getLogger(__name__)

class HotspotManager:
    def __init__(self, interface="wlan0"):
        self.interface = interface
        self.connection_name = "Pi_Share"

    def start_hotspot(self, ssid, password):
        """Starts the hotspot using NetworkManager (nmcli)."""
        logger.info(f"Starting hotspot: {ssid}")
        
        try:
            # 1. Update the existing connection or create it
            # We assume the connection might exist from setup_hotspot.sh, but we need to update creds.
            
            # Check if connection exists
            check = subprocess.run(["nmcli", "con", "show", self.connection_name], capture_output=True)
            
            if check.returncode != 0:
                # Create if not exists (Basic fallback, though setup_hotspot.sh is preferred)
                logger.info("Creating new hotspot connection profile...")
                subprocess.run([
                    "sudo", "nmcli", "con", "add", "type", "wifi", "ifname", self.interface, 
                    "con-name", self.connection_name, "autoconnect", "yes", "ssid", ssid
                ], check=True)
                subprocess.run([
                    "sudo", "nmcli", "con", "modify", self.connection_name, 
                    "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg", "ipv4.method", "shared"
                ], check=True)
                subprocess.run([
                    "sudo", "nmcli", "con", "modify", self.connection_name, 
                    "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password
                ], check=True)
            else:
                # Update SSID and Password
                logger.info("Updating existing hotspot profile...")
                subprocess.run(["sudo", "nmcli", "con", "modify", self.connection_name, "ssid", ssid], check=True)
                subprocess.run(["sudo", "nmcli", "con", "modify", self.connection_name, "wifi-sec.psk", password], check=True)
            
            # 2. Bring up the connection
            subprocess.run(["sudo", "nmcli", "con", "up", self.connection_name], check=True)
            
            logger.info("Hotspot started successfully via nmcli.")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start hotspot via nmcli: {e}")
            return False

    def stop_hotspot(self):
        """Stops the hotspot."""
        logger.info("Stopping hotspot...")
        try:
            subprocess.run(["sudo", "nmcli", "con", "down", self.connection_name], check=True)
            logger.info("Hotspot stopped.")
        except subprocess.CalledProcessError:
            logger.warning("Failed to stop hotspot (maybe already stopped).")

    def get_active_clients(self):
        """
        Returns number of clients. 
        With nmcli shared mode, dnsmasq is managed by NM. 
        Leases file might be in /var/lib/NetworkManager/dnsmasq-*.lease or similar.
        """
        # Attempt to find NM leases
        count = 0
        try:
            # Common path for NM dnsmasq leases
            res = subprocess.run(["iw", "dev", self.interface, "station", "dump"], capture_output=True, text=True)
            # Count "Station <MAC>" lines
            count = res.stdout.count("Station ")
        except Exception as e:
            logger.error(f"Error counting clients: {e}")
            
        return count
