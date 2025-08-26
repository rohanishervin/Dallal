import socket
import datetime
import ssl
import time
from typing import Tuple, Optional
from src.config.settings import config

class FIXAdapter:
    def __init__(self):
        self.sender_comp_id = config.fix.sender_comp_id
        self.target_comp_id = config.fix.target_comp_id
        self.SOH = "\x01"
        self.active_sessions = {}

    def __del__(self):
        self.cleanup_sessions()

    def create_fix_message(self, msg_type: str, fields: list) -> str:
        msg_fields = [
            ("35", msg_type),
            ("49", self.sender_comp_id),
            ("56", self.target_comp_id),
            ("34", "1"),
            ("52", datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]),
        ]

        msg_fields.extend(fields)
        body = self.SOH.join(f"{tag}={value}" for tag, value in msg_fields) + self.SOH
        body_length = len(body.encode("ascii"))
        header = f"8=FIX.4.4{self.SOH}9={body_length}{self.SOH}"
        message_without_checksum = header + body
        checksum = sum(message_without_checksum.encode("ascii")) % 256
        checksum_str = str(checksum).zfill(3)
        
        return message_without_checksum + f"10={checksum_str}{self.SOH}"

    def parse_fix_response(self, response: str) -> dict:
        fields = {}
        for field in response.split(self.SOH):
            if "=" in field:
                tag, value = field.split("=", 1)
                fields[tag] = value
        return fields

    def get_connection_params(self) -> Tuple[str, int]:
        return config.fix.host, config.fix.port

    def create_ssl_socket(self, host: str, port: int, timeout: int):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers("AES256-GCM-SHA384")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.settimeout(timeout)
        raw_socket.connect((host, port))
        
        ssl_socket = context.wrap_socket(raw_socket, server_hostname=host)
        return ssl_socket

    def send_logout(self, sock, username: str) -> bool:
        try:
            logout_fields = [("58", "User logout")]
            logout_message = self.create_fix_message("5", logout_fields)
            sock.sendall(logout_message.encode("ascii"))
            
            try:
                sock.settimeout(2)
                response = sock.recv(4096).decode("ascii")
            except socket.timeout:
                pass

            return True
        except Exception:
            return False

    def cleanup_sessions(self):
        for session_id, sock in list(self.active_sessions.items()):
            try:
                self.send_logout(sock, session_id)
                sock.close()
                del self.active_sessions[session_id]
            except Exception:
                pass
        self.active_sessions = {}

    def logon(self, username: str, password: str, device_id: Optional[str] = None, 
              timeout: int = 10) -> Tuple[bool, Optional[str]]:
        sock = None
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

            host, port = self.get_connection_params()

            logon_fields = [
                ("98", "0"),
                ("108", "30"),
                ("141", "Y"),
                ("553", username),
                ("554", password),
            ]

            if device_id:
                logon_fields.append(("10150", device_id))

            if config.fix.protocol_spec:
                logon_fields.append(("10064", config.fix.protocol_spec))

            logon_message = self.create_fix_message("A", logon_fields)

            sock = self.create_ssl_socket(host, port, timeout)

            self.active_sessions[session_id] = sock

            sock.sendall(logon_message.encode("ascii"))
            response = sock.recv(4096).decode("ascii")
            
            if "35=A" in response:
                time.sleep(0.5)
                self.send_logout(sock, username)
                sock.close()
                del self.active_sessions[session_id]
                return True, None
            elif "35=5" in response:
                fields = self.parse_fix_response(response)
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

        except socket.timeout:
            if sock:
                sock.close()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return False, "Connection timed out"
        except Exception as e:
            if sock:
                sock.close()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return False, "Unknown Error occurred"
