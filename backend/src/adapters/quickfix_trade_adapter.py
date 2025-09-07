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
        elif msg_type_str == "U1006":
            self._handle_account_info_response(message)
        elif msg_type_str == "8":
            self._handle_execution_report(message)
        elif msg_type_str == "9":
            self._handle_order_cancel_reject(message)

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

    def _handle_account_info_response(self, message):
        """Handle Account Info response (U1006)"""
        try:
            request_id = ""
            if message.isSetField(10028):
                request_id_field = fix.StringField(10028)
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            parsed_data = self._parse_account_info_message(message)

            if request_id in self.response_events:
                self.request_responses[request_id] = (True, parsed_data, None)
                self.response_events[request_id].set()
        except Exception as e:
            logger.error(f"Error handling account info response: {e}")

    def _parse_account_info_message(self, message) -> dict:
        """Parse Account Info (U1006) message"""
        try:
            account_info = {}

            # Required fields
            if message.isSetField(10029):  # Leverage
                leverage_field = fix.StringField(10029)
                message.getField(leverage_field)
                account_info["leverage"] = leverage_field.getValue()

            if message.isSetField(10031):  # Balance
                balance_field = fix.StringField(10031)
                message.getField(balance_field)
                account_info["balance"] = balance_field.getValue()

            if message.isSetField(10030):  # Margin
                margin_field = fix.StringField(10030)
                message.getField(margin_field)
                account_info["margin"] = margin_field.getValue()

            if message.isSetField(10032):  # Equity
                equity_field = fix.StringField(10032)
                message.getField(equity_field)
                account_info["equity"] = equity_field.getValue()

            if message.isSetField(15):  # Currency
                currency_field = fix.Currency()
                message.getField(currency_field)
                account_info["currency"] = currency_field.getValue()

            if message.isSetField(1):  # Account
                account_field = fix.Account()
                message.getField(account_field)
                account_info["account"] = account_field.getValue()

            # Optional fields
            if message.isSetField(10033):  # AccountingType
                accounting_type_field = fix.StringField(10033)
                message.getField(accounting_type_field)
                account_info["accounting_type"] = accounting_type_field.getValue()

            if message.isSetField(10112):  # AccountName
                account_name_field = fix.StringField(10112)
                message.getField(account_name_field)
                account_info["account_name"] = account_name_field.getValue()

            if message.isSetField(10028):  # AcInfReqID
                request_id_field = fix.StringField(10028)
                message.getField(request_id_field)
                account_info["request_id"] = request_id_field.getValue()

            return account_info

        except Exception as e:
            logger.error(f"Error parsing account info message: {e}")
            return {"error": f"Failed to parse account info message: {e}"}

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

    def _handle_execution_report(self, message):
        try:
            client_order_id = ""
            if message.isSetField(11):
                client_order_id_field = fix.ClOrdID()
                message.getField(client_order_id_field)
                client_order_id = client_order_id_field.getValue()

            parsed_data = self._parse_execution_report_message(message)

            if client_order_id in self.response_events:
                self.request_responses[client_order_id] = (True, parsed_data, None)
                self.response_events[client_order_id].set()
            else:
                logger.info(f"Received unsolicited execution report for order: {client_order_id}")
        except Exception as e:
            logger.error(f"Error handling execution report: {e}")

    def _handle_order_cancel_reject(self, message):
        try:
            client_order_id = ""
            if message.isSetField(11):
                client_order_id_field = fix.ClOrdID()
                message.getField(client_order_id_field)
                client_order_id = client_order_id_field.getValue()

            error_msg = ""
            if message.isSetField(58):
                text_field = fix.Text()
                message.getField(text_field)
                error_msg = text_field.getValue()

            reject_reason = ""
            if message.isSetField(102):
                reason_field = fix.CxlRejReason()
                message.getField(reason_field)
                reject_reason = reason_field.getValue()

            if client_order_id in self.response_events:
                error = f"Order cancel rejected: {error_msg} (Reason: {reject_reason})"
                self.request_responses[client_order_id] = (False, None, error)
                self.response_events[client_order_id].set()
        except Exception as e:
            logger.error(f"Error handling order cancel reject: {e}")

    def send_new_order_single(
        self,
        client_order_id: str,
        symbol: str,
        order_type: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        time_in_force: str = "1",
        expire_time: Optional[datetime] = None,
        max_visible_qty: Optional[float] = None,
        comment: Optional[str] = None,
        tag: Optional[str] = None,
        magic: Optional[int] = None,
        immediate_or_cancel: bool = False,
        market_with_slippage: bool = False,
        slippage: Optional[float] = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("D"))

            message.setField(fix.ClOrdID(client_order_id))
            message.setField(fix.Symbol(symbol))
            message.setField(fix.OrdType(order_type))
            message.setField(fix.Side(side))
            message.setField(fix.OrderQty(quantity))

            if price is not None:
                message.setField(fix.Price(price))

            if stop_price is not None:
                message.setField(fix.StopPx(stop_price))

            if stop_loss is not None:
                message.setField(fix.StringField(10037, str(stop_loss)))

            if take_profit is not None:
                message.setField(fix.StringField(10038, str(take_profit)))

            message.setField(fix.TimeInForce(time_in_force))

            if expire_time is not None:
                message.setField(fix.ExpireTime(expire_time))

            if max_visible_qty is not None:
                message.setField(fix.StringField(10205, str(max_visible_qty)))

            if comment:
                comment_bytes = comment.encode("utf-8")
                message.setField(fix.StringField(10075, str(len(comment_bytes))))
                message.setField(fix.StringField(10076, comment))

            if tag:
                tag_bytes = tag.encode("utf-8")
                message.setField(fix.StringField(10102, str(len(tag_bytes))))
                message.setField(fix.StringField(10103, tag))

            if magic is not None:
                message.setField(fix.StringField(10104, str(magic)))

            if immediate_or_cancel:
                message.setField(fix.StringField(10162, "Y"))

            if market_with_slippage:
                message.setField(fix.StringField(10163, "Y"))

            if slippage is not None:
                message.setField(fix.StringField(10231, str(slippage)))

            message.setField(fix.TransactTime())

            event = threading.Event()
            self.response_events[client_order_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent New Order Single: {client_order_id}")

            if event.wait(15):
                result = self.request_responses.pop(client_order_id, (False, None, "No response"))
                self.response_events.pop(client_order_id, None)
                return result
            else:
                self.response_events.pop(client_order_id, None)
                return False, None, "Order request timed out"

        except Exception as e:
            logger.error(f"New order single request failed: {e}")
            return False, None, f"Order request failed: {e}"

    def send_order_cancel_request(
        self,
        client_order_id: str,
        original_client_order_id: str,
        symbol: str,
        side: str,
        order_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("F"))

            message.setField(fix.ClOrdID(client_order_id))
            message.setField(fix.OrigClOrdID(original_client_order_id))
            message.setField(fix.Symbol(symbol))
            message.setField(fix.Side(side))

            if order_id:
                message.setField(fix.OrderID(order_id))

            message.setField(fix.TransactTime())

            event = threading.Event()
            self.response_events[client_order_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Order Cancel Request: {client_order_id}")

            if event.wait(15):
                result = self.request_responses.pop(client_order_id, (False, None, "No response"))
                self.response_events.pop(client_order_id, None)
                return result
            else:
                self.response_events.pop(client_order_id, None)
                return False, None, "Cancel request timed out"

        except Exception as e:
            logger.error(f"Order cancel request failed: {e}")
            return False, None, f"Cancel request failed: {e}"

    def send_order_cancel_replace_request(
        self,
        client_order_id: str,
        original_client_order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        time_in_force: str = "1",
        expire_time: Optional[datetime] = None,
        comment: Optional[str] = None,
        tag: Optional[str] = None,
        leaves_qty: Optional[float] = None,
        order_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("G"))

            message.setField(fix.ClOrdID(client_order_id))
            message.setField(fix.OrigClOrdID(original_client_order_id))
            message.setField(fix.Symbol(symbol))
            message.setField(fix.Side(side))
            message.setField(fix.OrdType(order_type))
            message.setField(fix.OrderQty(quantity))

            if order_id:
                message.setField(fix.OrderID(order_id))

            if price is not None:
                message.setField(fix.Price(price))

            if stop_price is not None:
                message.setField(fix.StopPx(stop_price))

            if stop_loss is not None:
                message.setField(fix.StringField(10037, str(stop_loss)))

            if take_profit is not None:
                message.setField(fix.StringField(10038, str(take_profit)))

            message.setField(fix.TimeInForce(time_in_force))

            if expire_time is not None:
                message.setField(fix.ExpireTime(expire_time))

            if comment:
                comment_bytes = comment.encode("utf-8")
                message.setField(fix.StringField(10075, str(len(comment_bytes))))
                message.setField(fix.StringField(10076, comment))

            if tag:
                tag_bytes = tag.encode("utf-8")
                message.setField(fix.StringField(10102, str(len(tag_bytes))))
                message.setField(fix.StringField(10103, tag))

            if leaves_qty is not None:
                message.setField(fix.LeavesQty(leaves_qty))

            message.setField(fix.TransactTime())

            event = threading.Event()
            self.response_events[client_order_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Order Cancel/Replace Request: {client_order_id}")

            if event.wait(15):
                result = self.request_responses.pop(client_order_id, (False, None, "No response"))
                self.response_events.pop(client_order_id, None)
                return result
            else:
                self.response_events.pop(client_order_id, None)
                return False, None, "Modify request timed out"

        except Exception as e:
            logger.error(f"Order cancel/replace request failed: {e}")
            return False, None, f"Modify request failed: {e}"

    def _parse_execution_report_message(self, message) -> dict:
        try:
            result = {}

            field_mappings = {
                37: ("order_id", str),
                11: ("client_order_id", str),
                17: ("exec_id", str),
                39: ("order_status", str),
                150: ("exec_type", str),
                55: ("symbol", str),
                54: ("side", str),
                40: ("order_type", str),
                14: ("cum_qty", float),
                38: ("order_qty", float),
                151: ("leaves_qty", float),
                6: ("avg_price", float),
                44: ("price", float),
                99: ("stop_price", float),
                32: ("last_qty", float),
                31: ("last_price", float),
                60: ("transact_time", str),
                10083: ("order_created", str),
                10084: ("order_modified", str),
                59: ("time_in_force", str),
                126: ("expire_time", str),
                10037: ("stop_loss", float),
                10038: ("take_profit", float),
                12: ("commission", float),
                10096: ("swap", float),
                10072: ("account_balance", float),
                58: ("text", str),
                103: ("reject_reason", str),
                10076: ("comment", str),
                10103: ("tag", str),
                10104: ("magic", int),
            }

            for tag, (field_name, converter) in field_mappings.items():
                if message.isSetField(tag):
                    try:
                        if converter == str:
                            if tag in [11, 37, 17, 55, 58, 10076, 10103]:
                                field = getattr(
                                    fix,
                                    {11: "ClOrdID", 37: "OrderID", 17: "ExecID", 55: "Symbol", 58: "Text"}.get(
                                        tag, "StringField"
                                    ),
                                )()
                                if tag in [10076, 10103, 10104]:
                                    field = fix.StringField(tag)
                            else:
                                field = fix.StringField(tag)
                        elif converter == float:
                            if tag in [6, 44, 99, 32, 31, 12, 10096, 10072, 10037, 10038]:
                                field = getattr(
                                    fix,
                                    {
                                        6: "AvgPx",
                                        44: "Price",
                                        99: "StopPx",
                                        32: "LastQty",
                                        31: "LastPx",
                                        12: "Commission",
                                    }.get(tag, "StringField"),
                                )()
                                if tag in [10096, 10072, 10037, 10038]:
                                    field = fix.StringField(tag)
                            else:
                                field = fix.StringField(tag)
                        elif converter == int:
                            field = fix.StringField(tag)
                        else:
                            field = fix.StringField(tag)

                        message.getField(field)
                        value = field.getValue()

                        if converter != str:
                            try:
                                result[field_name] = converter(value) if value else None
                            except (ValueError, TypeError):
                                result[field_name] = None
                        else:
                            result[field_name] = value
                    except Exception as e:
                        logger.debug(f"Failed to parse field {tag}: {e}")
                        result[field_name] = None

            logger.info(f"Parsed execution report for order: {result.get('client_order_id', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"Failed to parse execution report message: {e}")
            return {"error": f"Failed to parse execution report: {e}"}
