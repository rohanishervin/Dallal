import logging
from datetime import datetime
from typing import Optional, Tuple

from .fix_market_data import FIXMarketData
from .fix_session_manager import FIXSessionManager

logger = logging.getLogger(__name__)


class FIXAdapter:
    def __init__(self, connection_type: str = "trade"):
        self.connection_type = connection_type
        self.session_manager = FIXSessionManager(connection_type)
        self.market_data = FIXMarketData(self.session_manager)

    def __del__(self):
        self.cleanup_sessions()

    def cleanup_sessions(self):
        self.session_manager.cleanup_sessions()

    def logon(
        self, username: str, password: str, device_id: Optional[str] = None, timeout: int = 10
    ) -> Tuple[bool, Optional[str]]:
        return self.session_manager.logon(username, password, device_id, timeout)

    def is_session_active(self) -> bool:
        return self.session_manager.is_session_active()

    def send_heartbeat(self) -> bool:
        return self.session_manager.send_heartbeat()

    def logout(self) -> bool:
        return self.session_manager.logout()

    def send_test_request(self) -> bool:
        return self.session_manager.send_test_request()

    def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        return self.market_data.send_security_list_request(request_id)

    def send_market_history_request(
        self,
        symbol: str,
        period_id: str,
        max_bars: int,
        end_time: datetime,
        price_type: str = "B",
        graph_type: str = "B",
        request_id: str = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        return self.market_data.send_market_history_request(
            symbol, period_id, max_bars, end_time, price_type, graph_type, request_id
        )

    def parse_security_list_response(self, response_fields: dict) -> dict:
        return self.market_data.parse_security_list_response(response_fields)

    def parse_security_list_from_raw_message(self, raw_message: str) -> dict:
        return self.market_data.parse_security_list_from_raw_message(raw_message)

    def create_fix_message(self, msg_type: str, fields: list) -> str:
        return self.session_manager.message_builder.create_fix_message(msg_type, fields)

    def parse_fix_response(self, response: str) -> dict:
        return self.session_manager.message_builder.parse_fix_response(response)

    def get_connection_params(self) -> Tuple[str, int]:
        return self.session_manager.connection.get_connection_params()

    def create_ssl_socket(self, host: str, port: int, timeout: int):
        return self.session_manager.connection.create_ssl_socket(host, port, timeout)

    def send_logout(self, sock, username: str) -> bool:
        return self.session_manager.send_logout(sock, username)

    def recv_complete_fix_message(self, timeout: int = 15) -> Optional[str]:
        return self.session_manager.connection.recv_complete_fix_message(timeout)

    @property
    def active_sessions(self):
        return self.session_manager.active_sessions

    @active_sessions.setter
    def active_sessions(self, value):
        self.session_manager.active_sessions = value

    @property
    def session_socket(self):
        return self.session_manager.connection.session_socket

    @session_socket.setter
    def session_socket(self, value):
        self.session_manager.connection.session_socket = value

    @property
    def next_seq_num(self):
        return self.session_manager.message_builder.next_seq_num

    @next_seq_num.setter
    def next_seq_num(self, value):
        self.session_manager.message_builder.next_seq_num = value

    @property
    def is_logged_in(self):
        return self.session_manager.is_logged_in

    @is_logged_in.setter
    def is_logged_in(self, value):
        self.session_manager.is_logged_in = value
