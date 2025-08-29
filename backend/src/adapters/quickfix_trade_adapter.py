import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import quickfix as fix

from .quickfix_base_adapter import FIXMessageParser, QuickFIXBaseAdapter

logger = logging.getLogger(__name__)


class QuickFIXTradeAdapter(QuickFIXBaseAdapter):
    def __init__(self):
        super().__init__("trade")

    def fromAdmin(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_Reject:
            logger.error("✗ Trade session logon rejected!")
            if message.isSetField(fix.Text()):
                text = fix.Text()
                message.getField(text)
                logger.error(f"Reason: {text.getValue()}")

    def toApp(self, message, sessionID):
        logger.debug(f"→ Trade: {message}")

    def fromApp(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)
        msg_type_str = msg_type.getValue()

        logger.debug(f"← Trade message type: {msg_type_str}")

        if msg_type_str == "y":
            self._handle_security_list_response(message)
        elif msg_type_str == "U1002":
            self._handle_market_history_response(message)
        elif msg_type_str == "j":
            self._handle_business_message_reject(message)
        elif msg_type_str == "U1001":
            self._handle_market_history_reject(message)

    def _handle_security_list_response(self, message):
        try:
            request_id = ""
            if message.isSetField(320):
                request_id_field = fix.SecurityReqID()
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            parsed_data = self._parse_security_list_message(message)

            if request_id in self.response_events:
                self.request_responses[request_id] = (True, parsed_data, None)
                self.response_events[request_id].set()
        except Exception as e:
            logger.error(f"Error handling security list response: {e}")

    def _handle_market_history_response(self, message):
        try:
            request_id = ""
            if message.isSetField(10011):
                request_id_field = fix.StringField(10011)
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            parsed_data = self._parse_market_history_message(message)

            if request_id in self.response_events:
                self.request_responses[request_id] = (True, parsed_data, None)
                self.response_events[request_id].set()
        except Exception as e:
            logger.error(f"Error handling market history response: {e}")

    def _handle_business_message_reject(self, message):
        try:
            ref_msg_type = ""
            error_msg = ""
            reject_reason = ""

            if message.isSetField(372):
                ref_msg_type_field = fix.RefMsgType()
                message.getField(ref_msg_type_field)
                ref_msg_type = ref_msg_type_field.getValue()

            if message.isSetField(58):
                text_field = fix.Text()
                message.getField(text_field)
                error_msg = text_field.getValue()

            if message.isSetField(380):
                reason_field = fix.BusinessRejectReason()
                message.getField(reason_field)
                reject_reason = reason_field.getValue()

            for request_id, event in self.response_events.items():
                if not event.is_set():
                    error = f"Request rejected: {error_msg} (Reason: {reject_reason}, RefMsgType: {ref_msg_type})"
                    self.request_responses[request_id] = (False, None, error)
                    event.set()
                    break
        except Exception as e:
            logger.error(f"Error handling business message reject: {e}")

    def _handle_market_history_reject(self, message):
        try:
            request_id = ""
            reject_reason = ""
            error_text = ""

            if message.isSetField(10011):
                request_id_field = fix.StringField(10011)
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            if message.isSetField(10021):
                reason_field = fix.StringField(10021)
                message.getField(reason_field)
                reject_reason = reason_field.getValue()

            if message.isSetField(58):
                text_field = fix.Text()
                message.getField(text_field)
                error_text = text_field.getValue()

            if request_id in self.response_events:
                error = f"Request rejected: {error_text} (Reason code: {reject_reason})"
                self.request_responses[request_id] = (False, None, error)
                self.response_events[request_id].set()
        except Exception as e:
            logger.error(f"Error handling market history reject: {e}")

    def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            if not request_id:
                request_id = f"SLR_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("x"))

            message.setField(fix.SecurityReqID(request_id))
            message.setField(fix.SecurityListRequestType(4))

            event = threading.Event()
            self.response_events[request_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Security List Request: {request_id}")

            if event.wait(15):
                result = self.request_responses.pop(request_id, (False, None, "No response"))
                self.response_events.pop(request_id, None)
                return result
            else:
                self.response_events.pop(request_id, None)
                return False, None, "Request timed out"

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
            return False, None, "Trade session not connected"

        try:
            if not request_id:
                request_id = f"MHR_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("U1000"))

            message.setField(fix.StringField(10011, request_id))
            message.setField(fix.Symbol(symbol))
            message.setField(fix.StringField(10035, str(-max_bars)))
            message.setField(fix.StringField(10001, end_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]))
            message.setField(fix.StringField(10010, price_type))
            message.setField(fix.StringField(10012, period_id))
            message.setField(fix.StringField(10018, "G"))
            message.setField(fix.StringField(10020, graph_type))

            event = threading.Event()
            self.response_events[request_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Market History Request: {request_id}")

            if event.wait(30):
                result = self.request_responses.pop(request_id, (False, None, "No response"))
                self.response_events.pop(request_id, None)
                return result
            else:
                self.response_events.pop(request_id, None)
                return False, None, "Request timed out"

        except Exception as e:
            logger.error(f"Market history request failed: {e}")
            return False, None, f"Request failed: {e}"

    def _parse_security_list_message(self, message) -> dict:
        try:
            result = {
                "request_id": "",
                "response_id": "",
                "result": "",
                "symbols": [],
            }

            if message.isSetField(320):
                request_id_field = fix.SecurityReqID()
                message.getField(request_id_field)
                result["request_id"] = request_id_field.getValue()

            if message.isSetField(322):
                response_id_field = fix.StringField(322)
                message.getField(response_id_field)
                result["response_id"] = response_id_field.getValue()

            if message.isSetField(560):
                result_field = fix.StringField(560)
                message.getField(result_field)
                result["result"] = result_field.getValue()

            num_symbols = 0
            if message.isSetField(146):
                num_symbols_field = fix.NoRelatedSym()
                message.getField(num_symbols_field)
                num_symbols = num_symbols_field.getValue()

            symbols = []
            for i in range(1, num_symbols + 1):
                group = fix.Group(146, 55)
                message.getGroup(i, group)

                symbol_data = {}

                if group.isSetField(55):
                    symbol_field = fix.Symbol()
                    group.getField(symbol_field)
                    symbol_data["symbol"] = symbol_field.getValue()

                field_mappings = {
                    48: "security_id",
                    22: "security_id_source",
                    107: "security_desc",
                    15: "currency",
                    120: "settle_currency",
                    10127: "trade_enabled",
                    355: "description",
                    561: "round_lot",
                    562: "min_trade_vol",
                    10058: "max_trade_volume",
                    10062: "trade_vol_step",
                    10057: "px_precision",
                    231: "contract_multiplier",
                    10137: "currency_precision",
                    10138: "settl_currency_precision",
                    10134: "margin_factor_fractional",
                    12: "commission",
                    13: "comm_type",
                    10212: "swap_type",
                    10125: "swap_size_short",
                    10126: "swap_size_long",
                    10155: "default_slippage",
                    10170: "status_group_id",
                }

                for tag, field_name in field_mappings.items():
                    if group.isSetField(tag):
                        field = fix.StringField(tag)
                        group.getField(field)
                        value = field.getValue()

                        if field_name == "trade_enabled":
                            symbol_data[field_name] = value == "Y"
                        else:
                            symbol_data[field_name] = value

                symbols.append(symbol_data)

            result["symbols"] = symbols
            logger.info(f"Parsed {len(symbols)} symbols from Security List response")
            return result

        except Exception as e:
            logger.error(f"Failed to parse security list message: {e}")
            return {"error": f"Failed to parse security list response: {e}"}

    def _parse_market_history_message(self, message) -> dict:
        try:
            result = {
                "request_id": "",
                "symbol": "",
                "period_id": "",
                "price_type": "",
                "data_from": "",
                "data_to": "",
                "all_history_from": "",
                "all_history_to": "",
                "bars": [],
            }

            field_mappings = {
                10011: "request_id",
                55: "symbol",
                10012: "period_id",
                10010: "price_type",
                10000: "data_from",
                10001: "data_to",
                10002: "all_history_from",
                10003: "all_history_to",
            }

            for tag, field_name in field_mappings.items():
                if message.isSetField(tag):
                    field = fix.StringField(tag)
                    message.getField(field)
                    result[field_name] = field.getValue()

            num_bars = 0
            if message.isSetField(10004):
                num_bars_field = fix.StringField(10004)
                message.getField(num_bars_field)
                num_bars = int(num_bars_field.getValue())

            bars = []
            for i in range(1, num_bars + 1):
                group = fix.Group(10004, 10009)
                message.getGroup(i, group)

                bar_data = {}

                bar_field_mappings = {
                    10005: ("bar_hi", float),
                    10006: ("bar_low", float),
                    10007: ("bar_open", float),
                    10008: ("bar_close", float),
                    10009: ("bar_time", str),
                    10040: ("bar_volume", int),
                    10041: ("bar_volume_ex", float),
                }

                for tag, (field_name, converter) in bar_field_mappings.items():
                    if group.isSetField(tag):
                        field = fix.StringField(tag)
                        group.getField(field)
                        value = field.getValue()
                        try:
                            bar_data[field_name] = converter(value) if value else None
                        except (ValueError, TypeError):
                            bar_data[field_name] = None

                bars.append(bar_data)

            result["bars"] = bars
            logger.info(f"Parsed {len(bars)} bars from Market History response")
            return result

        except Exception as e:
            logger.error(f"Failed to parse market history message: {e}")
            return {"error": f"Failed to parse market history response: {e}"}
