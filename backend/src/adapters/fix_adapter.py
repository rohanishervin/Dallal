import socket
import datetime
import ssl
import time
import logging
from typing import Tuple, Optional
from src.config.settings import config

logger = logging.getLogger(__name__)

class FIXAdapter:
    def __init__(self, connection_type: str = "trade"):
        self.sender_comp_id = config.fix.sender_comp_id
        self.target_comp_id = config.fix.target_comp_id
        self.protocol_spec = config.fix.protocol_spec
        self.connection_type = connection_type  # "feed" or "trade"
        self.SOH = "\x01" # Field separator
        self.active_sessions = {}
        self.session_socket = None
        self.next_seq_num = 1
        self.is_logged_in = False

    def __del__(self):
        self.cleanup_sessions()

    def create_fix_message(self, msg_type: str, fields: list) -> str:
        msg_fields = [
            ("35", msg_type),
            ("49", self.sender_comp_id),
            ("56", self.target_comp_id),
            ("34", str(self.next_seq_num)),
            ("52", datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]),
        ]

        msg_fields.extend(fields)
        body = self.SOH.join(f"{tag}={value}" for tag, value in msg_fields) + self.SOH
        body_length = len(body.encode("ascii"))
        header = f"8={self.protocol_spec}{self.SOH}9={body_length}{self.SOH}"
        message_without_checksum = header + body
        checksum = sum(message_without_checksum.encode("ascii")) % 256
        checksum_str = str(checksum).zfill(3)
        
        self.next_seq_num += 1
        return message_without_checksum + f"10={checksum_str}{self.SOH}"

    def parse_fix_response(self, response: str) -> dict:
        fields = {}
        for field in response.split(self.SOH):
            if "=" in field:
                tag, value = field.split("=", 1)
                fields[tag] = value
        return fields

    def get_connection_params(self) -> Tuple[str, int]:
        if self.connection_type == "feed":
            return config.fix.host, config.fix.feed_port
        elif self.connection_type == "trade":
            return config.fix.host, config.fix.trade_port
        else:
            raise ValueError(f"Invalid connection type: {self.connection_type}. Must be 'feed' or 'trade'")

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
                ("98", "1"), # 98=1 means encryption is enabled
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

            logon_message = self.create_fix_message("A", logon_fields)
            logger.info(f"Sending logon message: {logon_message.replace(self.SOH, '|')}")

            sock = self.create_ssl_socket(host, port, timeout)

            self.active_sessions[session_id] = sock
            self.session_socket = sock

            sock.sendall(logon_message.encode("ascii"))
            response = sock.recv(4096).decode("ascii")
            
            if "35=A" in response:
                self.is_logged_in = True
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

    def is_session_active(self) -> bool:
        """Check if the FIX session is active and healthy"""
        return self.is_logged_in and self.session_socket is not None

    def send_heartbeat(self) -> bool:
        """Send a heartbeat message to keep the session alive"""
        if not self.is_session_active():
            return False

        try:
            heartbeat_message = self.create_fix_message("0", [])
            self.session_socket.sendall(heartbeat_message.encode("ascii"))
            return True
        except Exception:
            self.is_logged_in = False
            return False

    def logout(self) -> bool:
        """Properly logout from the FIX session"""
        if not self.is_session_active():
            return True

        try:
            logout_fields = [("58", "User logout")]
            logout_message = self.create_fix_message("5", logout_fields)
            self.session_socket.sendall(logout_message.encode("ascii"))
            
            time.sleep(0.5)
            self.session_socket.close()
            self.is_logged_in = False
            self.session_socket = None
            return True
        except Exception:
            return False

    def send_test_request(self) -> bool:
        """Send a Test Request to verify session is working"""
        try:
            test_req_id = f"TEST_{int(time.time() * 1000)}"
            test_request_fields = [("112", test_req_id)]
            test_message = self.create_fix_message("1", test_request_fields)
            
            self.session_socket.sendall(test_message.encode("ascii"))
            self.session_socket.settimeout(5)
            response = self.session_socket.recv(4096).decode("ascii")
            
            parsed_response = self.parse_fix_response(response)
            return parsed_response.get("35") == "0"  # Heartbeat response
        except Exception:
            return False

    def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send Security List Request (x) to get available trading instruments"""
        if not self.is_session_active():
            logger.warning("Attempted security list request with inactive session")
            return False, None, "FIX session not active"

        try:
            if not request_id:
                request_id = f"SLR_{int(time.time() * 1000)}"

            security_list_fields = [
                ("320", request_id),
                ("559", "4")
            ]

            request_message = self.create_fix_message("x", security_list_fields)
            logger.info(f"Sending security list request: {request_message.replace(self.SOH, '|')}")
            
            self.session_socket.sendall(request_message.encode("ascii"))

            messages_received = []
            self.session_socket.settimeout(15)
            
            while True:
                try:
                    response = self.session_socket.recv(8192).decode("ascii")
                    logger.info(f"Received FIX response: {response.replace(self.SOH, '|')}")
                    parsed_response = self.parse_fix_response(response)
                    logger.info(f"Parsed response fields: {parsed_response}")
                    
                    messages_received.append(parsed_response)
                    
                    msg_type = parsed_response.get("35")
                    
                    if msg_type == "y":
                        logger.info("Received Security List (y) response")
                        return True, self.parse_security_list_response(parsed_response), None
                    elif msg_type == "j":
                        logger.warning("Received Business Message Reject (j)")
                        error_msg = parsed_response.get("58", "Business message reject")
                        reject_reason = parsed_response.get("380", "Unknown reason")
                        ref_msg_type = parsed_response.get("372", "Unknown")
                        return False, None, f"Request rejected: {error_msg} (Reason: {reject_reason}, RefMsgType: {ref_msg_type})"
                    elif msg_type == "0":
                        logger.info("Received Heartbeat (0), continuing to wait for Security List response...")
                        continue
                    elif msg_type == "1":
                        logger.info("Received Test Request (1), sending Heartbeat response...")
                        test_req_id = parsed_response.get("112")
                        heartbeat_fields = [("112", test_req_id)] if test_req_id else []
                        heartbeat_message = self.create_fix_message("0", heartbeat_fields)
                        self.session_socket.sendall(heartbeat_message.encode("ascii"))
                        continue
                    else:
                        logger.warning(f"Unexpected message type: {msg_type}, continuing to wait...")
                        continue
                        
                except socket.timeout:
                    logger.error("Security list request timed out")
                    logger.info(f"Messages received during request: {messages_received}")
                    return False, None, "Request timed out - no Security List response received"

        except Exception as e:
            logger.error(f"Security list request failed: {str(e)}")
            return False, None, f"Request failed: {str(e)}"

    def parse_security_list_response(self, response_fields: dict) -> dict:
        """Parse Security List (y) response into structured data"""
        try:
            result = {
                "request_id": response_fields.get("320"),
                "response_id": response_fields.get("322"),
                "result": response_fields.get("560"),
                "symbols": []
            }

            num_symbols = int(response_fields.get("146", "0"))
            
            symbols = []
            current_symbol = {}
            
            for tag, value in response_fields.items():
                if tag == "55":
                    if current_symbol:
                        symbols.append(current_symbol)
                    current_symbol = {"symbol": value}
                elif tag == "48" and current_symbol:
                    current_symbol["security_id"] = value
                elif tag == "22" and current_symbol:
                    current_symbol["security_id_source"] = value
                elif tag == "107" and current_symbol:
                    current_symbol["security_desc"] = value
                elif tag == "15" and current_symbol:
                    current_symbol["currency"] = value
                elif tag == "120" and current_symbol:
                    current_symbol["settle_currency"] = value
                elif tag == "10127" and current_symbol:
                    current_symbol["trade_enabled"] = value == "Y"
                elif tag == "354" and current_symbol:
                    current_symbol["description_len"] = value
                elif tag == "355" and current_symbol:
                    current_symbol["description"] = value

            if current_symbol:
                symbols.append(current_symbol)

            result["symbols"] = symbols
            return result

        except Exception as e:
            return {"error": f"Failed to parse security list response: {str(e)}"}
