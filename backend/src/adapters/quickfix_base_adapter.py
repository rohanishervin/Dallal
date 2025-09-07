import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import quickfix as fix

from src.config.settings import config

from .quickfix_config import QuickFIXConfigManager

logger = logging.getLogger(__name__)


class FIXMessageParser:
    SECURITY_LIST_FIELD_MAPPINGS = {
        320: "request_id",
        322: "response_id",
        560: "result",
        146: "num_symbols",
    }

    SYMBOL_FIELD_MAPPINGS = {
        55: "symbol",
        48: "security_id",
        15: "currency",
        120: "settle_currency",
        10138: "settl_currency_precision",
        10057: "px_precision",
        561: "round_lot",
        562: "min_trade_vol",
        10058: "max_trade_volume",
        10062: "trade_vol_step",
        10059: "profit_calc_mode",
        10060: "margin_calc_mode",
        10061: "margin_hedge",
        10063: "margin_factor",
        13: "comm_type",
        10123: "commission",
        10067: "color_ref",
        10170: "status_group_id",
        10155: "default_slippage",
        354: "encoded_text_len",
        355: "description",
        10134: "margin_factor_fractional",
    }

    MARKET_HISTORY_FIELD_MAPPINGS = {
        10011: "request_id",
        55: "symbol",
        10012: "period_id",
        10010: "price_type",
        10000: "data_from",
        10001: "data_to",
        10002: "all_history_from",
        10003: "all_history_to",
        10004: "num_bars",
    }

    BAR_FIELD_MAPPINGS = {
        10005: "bar_hi",
        10006: "bar_low",
        10007: "bar_open",
        10008: "bar_close",
        10009: "bar_time",
        10040: "bar_volume",
        10041: "bar_volume_ex",
    }

    @staticmethod
    def parse_fields_from_message(message: fix.Message, field_mappings: Dict[int, str]) -> Dict[str, str]:
        result = {}
        for tag, field_name in field_mappings.items():
            if message.isSetField(tag):
                field = fix.StringField(tag)
                message.getField(field)
                result[field_name] = field.getValue()
        return result

    @staticmethod
    def parse_security_list_message(message: fix.Message) -> dict:
        try:
            result = FIXMessageParser.parse_fields_from_message(message, FIXMessageParser.SECURITY_LIST_FIELD_MAPPINGS)

            num_symbols = int(result.get("num_symbols", "0"))
            symbols = []

            for i in range(1, num_symbols + 1):
                symbol_data = {}

                for tag, field_name in FIXMessageParser.SYMBOL_FIELD_MAPPINGS.items():
                    repeated_tag = tag + (i * 1000) if tag >= 10000 else tag + (i * 100)
                    if message.isSetField(repeated_tag):
                        field = fix.StringField(repeated_tag)
                        message.getField(field)
                        value = field.getValue()

                        if field_name in ["trade_enabled"]:
                            symbol_data[field_name] = value.upper() == "Y"
                        elif field_name in ["px_precision", "settl_currency_precision", "comm_type"]:
                            try:
                                symbol_data[field_name] = int(value)
                            except ValueError:
                                symbol_data[field_name] = value
                        elif field_name in [
                            "round_lot",
                            "min_trade_vol",
                            "max_trade_volume",
                            "trade_vol_step",
                            "margin_hedge",
                            "margin_factor",
                            "commission",
                            "default_slippage",
                        ]:
                            try:
                                symbol_data[field_name] = float(value)
                            except ValueError:
                                symbol_data[field_name] = value
                        else:
                            symbol_data[field_name] = value

                if symbol_data:
                    symbols.append(symbol_data)

            result["symbols"] = symbols
            logger.info(f"Parsed {len(symbols)} symbols from Security List response")
            return result

        except Exception as e:
            logger.error(f"Failed to parse security list message: {e}")
            return {"error": f"Failed to parse security list response: {e}"}

    @staticmethod
    def parse_market_history_message(message: fix.Message) -> dict:
        try:
            result = FIXMessageParser.parse_fields_from_message(message, FIXMessageParser.MARKET_HISTORY_FIELD_MAPPINGS)

            num_bars = int(result.get("num_bars", "0"))
            bars = []

            for i in range(1, num_bars + 1):
                bar_data = {}

                for tag, field_name in FIXMessageParser.BAR_FIELD_MAPPINGS.items():
                    repeated_tag = tag + (i * 1000)
                    if message.isSetField(repeated_tag):
                        field = fix.StringField(repeated_tag)
                        message.getField(field)
                        value = field.getValue()

                        if field_name in ["bar_hi", "bar_low", "bar_open", "bar_close"]:
                            try:
                                bar_data[field_name] = float(value)
                            except ValueError:
                                bar_data[field_name] = value
                        elif field_name in ["bar_volume"]:
                            try:
                                bar_data[field_name] = int(value) if value else None
                            except ValueError:
                                bar_data[field_name] = None
                        elif field_name in ["bar_volume_ex"]:
                            try:
                                bar_data[field_name] = float(value) if value else None
                            except ValueError:
                                bar_data[field_name] = None
                        else:
                            bar_data[field_name] = value

                if bar_data:
                    bars.append(bar_data)

            result["bars"] = bars
            logger.info(f"Parsed {len(bars)} bars from Market History response")
            return result

        except Exception as e:
            logger.error(f"Failed to parse market history message: {e}")
            return {"error": f"Failed to parse market history response: {e}"}


class QuickFIXBaseAdapter(fix.Application):
    def __init__(self, connection_type: str):
        super().__init__()
        self.connection_type = connection_type
        self.logged_on = False
        self.logon_event = threading.Event()
        self.logout_event = threading.Event()
        self.initiator = None
        self.session_id = None
        self.username = None
        self.password = None
        self.device_id = None
        self.request_responses = {}
        self.response_events = {}
        self.current_config_file = None

    def connect(
        self, username: str, password: str, device_id: Optional[str] = None, timeout: int = 30
    ) -> Tuple[bool, Optional[str]]:
        try:
            self.username = username
            self.password = password
            self.device_id = device_id

            config_file = f"{self.connection_type}_session.cfg"
            self.current_config_file = QuickFIXConfigManager.update_config_file(config_file, self.connection_type)
            settings = fix.SessionSettings(self.current_config_file)
            store_factory = fix.FileStoreFactory(settings)
            log_factory = fix.FileLogFactory(settings)

            self.initiator = fix.SSLSocketInitiator(self, store_factory, settings, log_factory)

            logger.info(f"Connecting as {username} to {self.connection_type} session...")
            self.initiator.start()

            if self.logon_event.wait(timeout):
                logger.info(f"✓ {self.connection_type.capitalize()} session connected successfully!")
                return True, None
            else:
                logger.error(f"✗ {self.connection_type.capitalize()} session connection timeout")
                return False, "Connection timeout"
        except Exception as e:
            logger.error(f"✗ {self.connection_type.capitalize()} session connection failed: {e}")
            return False, f"Connection failed: {e}"

    def disconnect(self) -> bool:
        try:
            if self.initiator:
                logger.info(f"Disconnecting {self.connection_type} session...")
                self.logout_event.clear()
                self.initiator.stop()
                self.logout_event.wait(10)
                logger.info(f"✓ {self.connection_type.capitalize()} session disconnected")

            if self.current_config_file:
                QuickFIXConfigManager.cleanup_temp_config(self.current_config_file)
                self.current_config_file = None

            return True
        except Exception as e:
            logger.error(f"Error disconnecting {self.connection_type} session: {e}")
            return False

    def is_connected(self) -> bool:
        return self.logged_on

    def onCreate(self, sessionID):
        logger.info(f"{self.connection_type.capitalize()} session created: {sessionID}")
        self.session_id = sessionID

    def onLogon(self, sessionID):
        logger.info(f"✓ {self.connection_type.capitalize()} session logged on: {sessionID}")
        self.logged_on = True
        self.logon_event.set()

    def onLogout(self, sessionID):
        logger.info(f"✗ {self.connection_type.capitalize()} session logged out: {sessionID}")
        self.logged_on = False
        self.logout_event.set()

    def toAdmin(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_Logon:
            message.setField(fix.Username(self.username))
            message.setField(fix.Password(self.password))
            message.setField(fix.StringField(141, "Y"))

            if self.device_id:
                message.setField(fix.StringField(10150, self.device_id))

            if config.fix.protocol_spec:
                message.setField(fix.StringField(10064, config.fix.protocol_spec))

    def fromAdmin(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)
        msg_type_str = msg_type.getValue()

        logger.debug(f"← Admin message type: {msg_type_str}")

        if msg_type_str == fix.MsgType_Logout:
            self.logged_on = False
            self.logout_event.set()

    def toApp(self, message, sessionID):
        logger.debug(f"→ Sending {self.connection_type} message")

    def send_message(self, message: fix.Message) -> bool:
        if not self.is_connected():
            return False
        try:
            fix.Session.sendToTarget(message, self.session_id)
            return True
        except Exception as e:
            logger.error(f"Failed to send {self.connection_type} message: {e}")
            return False

    def send_test_request(self) -> bool:
        if not self.is_connected():
            return False

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_TestRequest))
            message.setField(fix.TestReqID(str(int(time.time() * 1000))))

            fix.Session.sendToTarget(message, self.session_id)
            logger.debug("Sent Test Request")
            return True
        except Exception as e:
            logger.error(f"Test request failed: {e}")
            return False

    def send_heartbeat(self) -> bool:
        if not self.is_connected():
            return False

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_Heartbeat))

            fix.Session.sendToTarget(message, self.session_id)
            logger.debug("Sent Heartbeat")
            return True
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False

    def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.is_connected():
            return False, None, "Session not connected"

        try:
            if request_id is None:
                request_id = f"SLR_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("x"))

            message.setField(fix.SecurityReqID(request_id))
            message.setField(fix.SecurityListRequestType(4))

            event = threading.Event()
            self.request_responses[request_id] = None
            self.response_events[request_id] = event

            success = self.send_message(message)
            if success:
                logger.info(f"Sent Security List Request: {request_id}")
                if event.wait(30):
                    response = self.request_responses.get(request_id)
                    if response:
                        return True, response, None
                    else:
                        return False, None, "No response received"
                else:
                    return False, None, "Request timeout"
            else:
                return False, None, "Failed to send request"

        except Exception as e:
            logger.error(f"Security list request failed: {e}")
            return False, None, f"Request failed: {e}"

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
        if not self.is_connected():
            return False, None, "Session not connected"

        try:
            if request_id is None:
                request_id = f"MHR_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("U1000"))

            message.setField(fix.StringField(10011, request_id))
            message.setField(fix.Symbol(symbol))
            message.setField(fix.StringField(10012, period_id))
            message.setField(fix.StringField(10010, price_type))
            message.setField(fix.StringField(10015, graph_type))
            message.setField(fix.StringField(10016, str(-max_bars)))

            formatted_time = end_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
            message.setField(fix.StringField(10013, formatted_time))

            event = threading.Event()
            self.request_responses[request_id] = None
            self.response_events[request_id] = event

            success = self.send_message(message)
            if success:
                logger.info(f"Sent Market History Request: {request_id}")
                if event.wait(30):
                    response = self.request_responses.get(request_id)
                    if response:
                        return True, response, None
                    else:
                        return False, None, "No response received"
                else:
                    return False, None, "Request timeout"
            else:
                return False, None, "Failed to send request"

        except Exception as e:
            logger.error(f"Market history request failed: {e}")
            return False, None, f"Request failed: {e}"
