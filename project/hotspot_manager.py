import subprocess
import os
import time
import logging

logger = logging.getLogger(__name__)

class HotspotManager:
    def __init__(self, interface="wlan0"):
        self.interface = interface
        self.hostapd_conf_path = "/tmp/hostapd.conf"
        self.dnsmasq_conf_path = "/tmp/dnsmasq.conf"
        self.dnsmasq_process = None
        self.hostapd_process = None

    def start_hotspot(self, ssid, password):
        """Starts the hotspot with the given SSID and password."""
        logger.info(f"Starting hotspot: {ssid}")
        
        # 1. Stop existing services to avoid conflicts
        self.stop_hotspot()
        self._kill_conflicting_services()

        # 2. Configure IP address for the interface
        try:
            subprocess.run(["sudo", "ip", "link", "set", self.interface, "down"], check=True)
            subprocess.run(["sudo", "ip", "addr", "flush", "dev", self.interface], check=True)
            subprocess.run(["sudo", "ip", "addr", "add", "192.168.4.1/24", "dev", self.interface], check=True)
            subprocess.run(["sudo", "ip", "link", "set", self.interface, "up"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure network interface: {e}")
            return False

        # 3. Create config files
        self._create_hostapd_conf(ssid, password)
        self._create_dnsmasq_conf()

        # 4. Start dnsmasq
        try:
            self.dnsmasq_process = subprocess.Popen(
                ["sudo", "dnsmasq", "-C", self.dnsmasq_conf_path, "-d"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Failed to start dnsmasq: {e}")
            return False

        # 5. Start hostapd
        try:
            self.hostapd_process = subprocess.Popen(
                ["sudo", "hostapd", self.hostapd_conf_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Failed to start hostapd: {e}")
            self.stop_hotspot() # Cleanup dnsmasq if hostapd fails
            return False
            
        logger.info("Hotspot started successfully.")
        return True

    def stop_hotspot(self):
        """Stops the hotspot services."""
        logger.info("Stopping hotspot...")
        
        if self.hostapd_process:
            self.hostapd_process.terminate()
            self.hostapd_process.wait()
            self.hostapd_process = None
            
        if self.dnsmasq_process:
            self.dnsmasq_process.terminate()
            self.dnsmasq_process.wait()
            self.dnsmasq_process = None

        # Clean up processes just in case
        subprocess.run(["sudo", "killall", "hostapd"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "killall", "dnsmasq"], stderr=subprocess.DEVNULL)
        
        # Reset Interface - optional, might not want to if we want it to reconnect to home wifi
        # But for this task, we just ensure it's not holding the static IP confusingly?
        # Actually, best to leave it or flush it.
        # subprocess.run(["sudo", "ip", "addr", "flush", "dev", self.interface], stderr=subprocess.DEVNULL)
        
        logger.info("Hotspot stopped.")

    def _kill_conflicting_services(self):
        """Kills conflicting services like NetworkManager or wpa_supplicant on the interface."""
        # This is aggressive but necessary for hostapd to take control
        # We try to use nmcli first if available to be polite
        try:
             subprocess.run(["sudo", "nmcli", "dev", "set", self.interface, "managed", "no"], stderr=subprocess.DEVNULL)
        except:
            pass
            
        subprocess.run(["sudo", "killall", "wpa_supplicant"], stderr=subprocess.DEVNULL)

    def _create_hostapd_conf(self, ssid, password):
        content = f"""
interface={self.interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        with open(self.hostapd_conf_path, "w") as f:
            f.write(content)

    def _create_dnsmasq_conf(self):
        content = f"""
interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
        with open(self.dnsmasq_conf_path, "w") as f:
            f.write(content)
    def get_active_clients(self):
        """Returns the number of connected clients by reading dnsmasq leases."""
        leases_file = "/var/lib/misc/dnsmasq.leases"
        # On some systems it might be elsewhere, fallback to our tmp config location if we configured it there? 
        # No, dnsmasq usually writes to its default unless told otherwise. 
        # Let's check if we can specify leasefile in config.
        # But for now, standard location check.
        
        count = 0
        try:
            if os.path.exists(leases_file):
                with open(leases_file, 'r') as f:
                    count = sum(1 for line in f if line.strip())
        except Exception as e:
            logger.error(f"Error reading leases: {e}")
            
        return count
