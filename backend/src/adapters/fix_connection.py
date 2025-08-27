import logging
import socket
import ssl
from typing import Optional, Tuple

from src.config.settings import config

logger = logging.getLogger(__name__)


class FIXConnection:
    def __init__(self, connection_type: str = "trade"):
        self.connection_type = connection_type
        self.session_socket = None

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

    def connect(self, timeout: int = 10) -> Optional[socket.socket]:
        try:
            host, port = self.get_connection_params()
            self.session_socket = self.create_ssl_socket(host, port, timeout)
            return self.session_socket
        except Exception as e:
            logger.error(f"Failed to establish connection: {str(e)}")
            return None

    def disconnect(self):
        if self.session_socket:
            try:
                self.session_socket.close()
            except Exception:
                pass
            finally:
                self.session_socket = None

    def send_message(self, message: str) -> bool:
        if not self.session_socket:
            return False
        try:
            self.session_socket.sendall(message.encode("ascii"))
            return True
        except Exception:
            return False

    def receive_message(self, buffer_size: int = 4096, timeout: Optional[int] = None) -> Optional[str]:
        if not self.session_socket:
            return None
        try:
            if timeout is not None:
                self.session_socket.settimeout(timeout)
            response = self.session_socket.recv(buffer_size).decode("ascii")
            return response
        except Exception:
            return None

    def recv_complete_fix_message(self, timeout: int = 15) -> Optional[str]:
        if not self.session_socket:
            return None

        SOH = "\x01"
        self.session_socket.settimeout(timeout)
        buffer = ""

        while True:
            try:
                data = self.session_socket.recv(8192).decode("ascii")
                if not data:
                    break

                buffer += data

                messages = []
                remaining_buffer = buffer

                while True:
                    start_pos = remaining_buffer.find("8=")
                    if start_pos == -1:
                        break

                    if start_pos > 0:
                        remaining_buffer = remaining_buffer[start_pos:]

                    length_start = remaining_buffer.find(SOH + "9=")
                    if length_start == -1:
                        break

                    length_start += len(SOH + "9=")
                    length_end = remaining_buffer.find(SOH, length_start)
                    if length_end == -1:
                        break

                    try:
                        body_length = int(remaining_buffer[length_start:length_end])
                    except ValueError:
                        break

                    header_end = length_end + 1
                    total_length = header_end + body_length + 7

                    if len(remaining_buffer) >= total_length:
                        complete_message = remaining_buffer[:total_length]
                        messages.append(complete_message)
                        remaining_buffer = remaining_buffer[total_length:]
                    else:
                        break

                if messages:
                    buffer = remaining_buffer
                    return messages[0]

            except socket.timeout:
                if buffer:
                    logger.warning(f"Timeout with partial buffer: {len(buffer)} bytes")
                return None

        return None
