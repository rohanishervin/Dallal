import logging
import time
from typing import Dict, Optional, Tuple

from src.config.settings import config

from .fix_connection import FIXConnection
from .fix_message_builder import FIXMessageBuilder

logger = logging.getLogger(__name__)


class FIXSessionManager:
    def __init__(self, connection_type: str = "trade"):
        self.connection_type = connection_type
        self.connection = FIXConnection(connection_type)
        self.message_builder = FIXMessageBuilder(
            config.fix.sender_comp_id, config.fix.target_comp_id, config.fix.protocol_spec
        )
        self.active_sessions: Dict[str, object] = {}
        self.is_logged_in = False

    def cleanup_sessions(self):
        for session_id, sock in list(self.active_sessions.items()):
            try:
                self.send_logout(sock, session_id)
                sock.close()
                del self.active_sessions[session_id]
            except Exception:
                pass
        self.active_sessions = {}

    def send_logout(self, sock, username: str) -> bool:
        try:
            logout_fields = [("58", "User logout")]
            logout_message = self.message_builder.create_fix_message("5", logout_fields)
            sock.sendall(logout_message.encode("ascii"))

            try:
                sock.settimeout(2)
                response = sock.recv(4096).decode("ascii")
            except Exception:
                pass

            return True
        except Exception:
            return False

    def logon(
        self, username: str, password: str, device_id: Optional[str] = None, timeout: int = 10
    ) -> Tuple[bool, Optional[str]]:
        session_id = f"{username}"

        try:
            if str(username) in self.active_sessions:
                try:
                    existing_sock = self.active_sessions[str(username)]
                    self.send_logout(existing_sock, username)
                    existing_sock.close()
                    del self.active_sessions[str(username)]
                except Exception:
                    pass

            logon_fields = [
                ("98", "1"),
                ("108", "30"),
                ("141", "Y"),
                ("553", username),
                ("554", password),
            ]

            if device_id:
                logon_fields.append(("10150", device_id))

            if config.fix.protocol_spec:
                logon_fields.append(("10064", config.fix.protocol_spec))
                logger.info(f"Adding ProtocolSpec to logon: 10064={config.fix.protocol_spec}")
            else:
                logger.warning("No ProtocolSpec configured - will use server default (ext.1.0)")

            logon_message = self.message_builder.create_fix_message("A", logon_fields)
            logger.info(f"Sending logon message: {logon_message.replace(self.message_builder.SOH, '|')}")

            sock = self.connection.connect(timeout)
            if not sock:
                return False, "Connection failed"

            self.active_sessions[session_id] = sock

            sock.sendall(logon_message.encode("ascii"))
            response = sock.recv(4096).decode("ascii")

            if "35=A" in response:
                self.is_logged_in = True
                return True, None
            elif "35=5" in response:
                fields = self.message_builder.parse_fix_response(response)
                reason = fields.get("58", "Unknown reason")
                sock.close()
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                return False, "Invalid credentials"
            else:
                sock.close()
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                return False, "Unexpected response"

        except Exception as e:
            if session_id in self.active_sessions:
                try:
                    self.active_sessions[session_id].close()
                    del self.active_sessions[session_id]
                except Exception:
                    pass
            return False, "Unknown Error occurred"

    def is_session_active(self) -> bool:
        return self.is_logged_in and self.connection.session_socket is not None

    def send_heartbeat(self) -> bool:
        if not self.is_session_active():
            return False

        try:
            heartbeat_message = self.message_builder.create_fix_message("0", [])
            return self.connection.send_message(heartbeat_message)
        except Exception:
            self.is_logged_in = False
            return False

    def logout(self) -> bool:
        if not self.is_session_active():
            return True

        try:
            logout_fields = [("58", "User logout")]
            logout_message = self.message_builder.create_fix_message("5", logout_fields)
            self.connection.send_message(logout_message)

            time.sleep(0.5)
            self.connection.disconnect()
            self.is_logged_in = False
            return True
        except Exception:
            return False

    def send_test_request(self) -> bool:
        try:
            test_req_id = f"TEST_{int(time.time() * 1000)}"
            test_request_fields = [("112", test_req_id)]
            test_message = self.message_builder.create_fix_message("1", test_request_fields)

            if not self.connection.send_message(test_message):
                return False

            response = self.connection.receive_message(timeout=5)
            if not response:
                return False

            parsed_response = self.message_builder.parse_fix_response(response)
            return parsed_response.get("35") == "0"
        except Exception:
            return False
