import uuid
import secrets
import string
import time
import logging
import threading
from hotspot_manager import HotspotManager

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.hotspot = HotspotManager()
        self.active_session = None
        self.session_lock = threading.Lock()
        self.hotspot_ssid = "PI_Share"
        self.session_timeout = 120 # Seconds

    def start_session(self):
        """Starts a new session, creating a hotspot with new credentials."""
        with self.session_lock:
            # End existing session if any
            if self.active_session:
                self.end_session()

            session_id = str(uuid.uuid4())
            password = self._generate_password()
            
            logger.info(f"Starting Session: {session_id}")
            
            if self.hotspot.start_hotspot(self.hotspot_ssid, password):
                self.active_session = {
                    "id": session_id,
                    "password": password,
                    "ssid": self.hotspot_ssid,
                    "start_time": time.time(),
                    "params": {"session_timeout": self.session_timeout}
                }
                # Start timeout timer
                threading.Timer(self.session_timeout, self._check_timeout, args=[session_id]).start()
                return self.active_session
            else:
                logger.error("Failed to start hotspot for session.")
                return None

    def end_session(self):
        """Ends the current session and stops the hotspot."""
        with self.session_lock:
            if self.active_session:
                logger.info(f"Ending Session: {self.active_session['id']}")
                self.hotspot.stop_hotspot()
                self.active_session = None
                return True
            return False

    def is_session_active(self):
        """Checks if a session is currently active."""
        return self.active_session is not None

    def _generate_password(self, length=8):
        """Generates a random 8-character password."""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))

    def _check_timeout(self, session_id):
        """Called by timer to auto-close session if expired."""
        with self.session_lock:
            if self.active_session and self.active_session["id"] == session_id:
                logger.info(f"Session {session_id} timed out.")
                # self.end_session() # Cannot call recursively with lock properly if not careful, but end_session uses lock.
                # Actually, since we are already in lock, we can't call end_session which also grabs lock.
                # Let's adjust locking strategy or just call internal cleanup.
                
                # Correct way: Re-acquire lock inside end_session is fine if RLock, but we used Lock.
                # Better: release lock before calling end_session or use RLock.
                pass
        
        # Call end_session outside the lock held in this method?
        # No, _check_timeout is called by thread.
        # Let's just call end_session() and let it handle locking.
        # But we need to check if it's the SAME session ID before closing.
        
        # Revised approach:
        current_session_id = None
        with self.session_lock:
            if self.active_session:
                current_session_id = self.active_session["id"]
        
        if current_session_id == session_id:
             self.end_session()
