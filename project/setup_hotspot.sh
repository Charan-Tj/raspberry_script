#!/bin/bash

# Configuration
SSID="Pi_Share"
PASSWORD="raspberry_pi"
IFACE="wlan0"
IP_ADDR="192.168.4.1/24"

echo "Setting up Hotspot: $SSID"

# Check if nmcli is installed
if ! command -v nmcli &> /dev/null; then
    echo "Error: nmcli (NetworkManager) is not installed. This script requires Raspberry Pi OS Bookworm or newer."
    exit 1
fi

# Delete existing connection if it exists
nmcli con delete "$SSID" &> /dev/null

# Create the hotspot connection
# 802-11-wireless.mode ap: Access Point mode
# ipv4.method shared: Acts as a router (NAT), providing internet if Pi has it via Ethernet
nmcli con add type wifi ifname "$IFACE" con-name "$SSID" autoconnect yes ssid "$SSID"
nmcli con modify "$SSID" 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
nmcli con modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSWORD"

# Set static IP for the hotspot gateway
nmcli con modify "$SSID" ipv4.addresses "$IP_ADDR"

# Bring up the connection
nmcli con up "$SSID"

echo "Hotspot '$SSID' created successfully!"
echo "IP Address: $IP_ADDR"
echo "Password: $PASSWORD"
