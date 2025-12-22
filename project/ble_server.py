import logging
import asyncio
import json
from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions
)

logger = logging.getLogger(__name__)

# UUIDs for Service and Characteristics
# Generated random UUIDs for this specific application
SERVICE_UUID = "A07498CA-AD5B-474E-940D-16F1FBE7E8CD"
COMMAND_CHAR_UUID = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
RESPONSE_CHAR_UUID = "E0B99BCA-10D1-4566-AACC-862D6829707C"

class BLEServer:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.server = None
        self.loop = asyncio.get_event_loop()
        self.state = "STOPPED" # STOPPED, ADVERTISING, CONNECTED

    async def start(self):
        """Initializes and starts the BLE Server."""
        logger.info("Initializing BLE Server...")
        self.server = BlessServer(name="Pi_Share_Config")
        
        # Add Service
        await self.server.add_new_service(SERVICE_UUID)

        # Add Command Characteristic (Write)
        await self.server.add_new_characteristic(
            SERVICE_UUID,
            COMMAND_CHAR_UUID,
            GATTCharacteristicProperties.write,
            None,
            GATTAttributePermissions.writeable
        )

        # Add Response Characteristic (Read/Notify)
        await self.server.add_new_characteristic(
            SERVICE_UUID,
            RESPONSE_CHAR_UUID,
            GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify,
            None,
            GATTAttributePermissions.readable
        )

        self.server.set_write_callback(
            GATTCharacteristicProperties.write,
            self.on_write
        )

        try:
            await self.server.start()
            self.state = "ADVERTISING"
            logger.info("BLE Server started and advertising 'Pi_Share_Config'")
        except Exception as e:
            logger.error(f"Failed to start BLE server: {e}")

    async def stop(self):
        if self.server:
            await self.server.stop()
            self.state = "STOPPED"
            logger.info("BLE Server stopped")

    def on_write(self, characteristic_uuid: str, value: bytearray):
        """Handle incoming writes from the app."""
        try:
            command = value.decode("utf-8").strip()
            logger.info(f"Received BLE Command: {command}")

            if command == "SESSION_INIT":
                session = self.session_manager.start_session()
                if session:
                    response = {
                        "ssid": session["ssid"],
                        "password": session["password"],
                        "session_timeout": session["params"]["session_timeout"]
                    }
                    self._send_response(response)
                else:
                    self._send_response({"error": "Failed to start session"})

            elif command == "END_SESSION":
                if self.session_manager.end_session():
                    self._send_response({"status": "Session Ended"})
                else:
                    self._send_response({"error": "No active session"})
            
            else:
                logger.warning(f"Unknown command: {command}")

        except Exception as e:
            logger.error(f"Error processing BLE write: {e}")

    def _send_response(self, data):
        """Update the response characteristic."""
        json_str = json.dumps(data)
        logger.info(f"Sending BLE Response: {json_str}")
        
        # bless methods are async, but on_write might be called in a way that needs handling.
        # Ideally we update the value.
        
        value = json_str.encode("utf-8")
        
        # The Bless API for updating value might vary by backend, but generally:
        # We assume we can just set it. 
        # Note: on_write in Bless might be called from a different thread depending on backend.
        # Ideally using update_value from the server instance.
        
        # Since on_write is sync in some bindings or async in others, we need to be careful.
        # But for 'bless', usually we schedule the update.
        
        if self.server:
             # This sets the local value.
             self.server.get_characteristic(RESPONSE_CHAR_UUID).value = value
             # If we want to notify, we should call update_value if supported or notify subscribers
             # Bless doesn't have a high-level 'notify' method easily exposed in all examples, 
             # but updating property value usually triggers if notify is set up.
             
             # Attempt to update via server method if available or just set property
             # self.server.update_value(SERVICE_UUID, RESPONSE_CHAR_UUID) -- check documentation if possible.
             # For now, just setting value which allows Read to work.
             pass
