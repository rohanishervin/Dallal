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
        elif msg_type_str == "AO":
            self._handle_request_for_positions_ack(message)
        elif msg_type_str == "AP":
            self._handle_position_report(message)

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
        """Parse Account Info (U1006) message with complete field support"""
        try:
            account_info = {}

            # Core required fields
            if message.isSetField(1):  # Account ID
                account_field = fix.Account()
                message.getField(account_field)
                account_info["account_id"] = account_field.getValue()

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

            # Account type and status fields
            if message.isSetField(10033):  # AccountingType
                accounting_type_field = fix.StringField(10033)
                message.getField(accounting_type_field)
                account_info["accounting_type"] = accounting_type_field.getValue()

            if message.isSetField(10100):  # AccountValidFlag
                valid_flag_field = fix.StringField(10100)
                message.getField(valid_flag_field)
                account_info["account_valid"] = valid_flag_field.getValue() == "Y"

            if message.isSetField(10133):  # AccountBlockedFlag
                blocked_flag_field = fix.StringField(10133)
                message.getField(blocked_flag_field)
                account_info["account_blocked"] = blocked_flag_field.getValue() == "Y"

            if message.isSetField(10218):  # AccountReadonlyFlag
                readonly_flag_field = fix.StringField(10218)
                message.getField(readonly_flag_field)
                account_info["account_readonly"] = readonly_flag_field.getValue() == "Y"

            if message.isSetField(10101):  # InvestorLoginFlag
                investor_flag_field = fix.StringField(10101)
                message.getField(investor_flag_field)
                account_info["investor_login"] = investor_flag_field.getValue() == "Y"

            # Risk management fields
            if message.isSetField(10097):  # AccMarginCallLevel
                margin_call_field = fix.StringField(10097)
                message.getField(margin_call_field)
                account_info["margin_call_level"] = margin_call_field.getValue()

            if message.isSetField(10098):  # AccStopOutLevel
                stop_out_field = fix.StringField(10098)
                message.getField(stop_out_field)
                account_info["stop_out_level"] = stop_out_field.getValue()

            # Account details
            if message.isSetField(10112):  # AccountName
                account_name_field = fix.StringField(10112)
                message.getField(account_name_field)
                account_info["account_name"] = account_name_field.getValue()

            if message.isSetField(511):  # RegistEmail
                email_field = fix.StringField(511)
                message.getField(email_field)
                account_info["email"] = email_field.getValue()

            if message.isSetField(10147):  # RegistDate
                regist_date_field = fix.StringField(10147)
                message.getField(regist_date_field)
                account_info["registration_date"] = regist_date_field.getValue()

            if message.isSetField(10208):  # ModifyTime
                modify_time_field = fix.StringField(10208)
                message.getField(modify_time_field)
                account_info["last_modified"] = modify_time_field.getValue()

            # Comments
            if message.isSetField(10076):  # EncodedComment
                comment_field = fix.StringField(10076)
                message.getField(comment_field)
                account_info["comment"] = comment_field.getValue()

            # Throttling information
            if message.isSetField(10226):  # SessionsPerAccount
                sessions_field = fix.StringField(10226)
                message.getField(sessions_field)
                account_info["sessions_per_account"] = sessions_field.getValue()

            if message.isSetField(10227):  # RequestsPerSecond
                requests_field = fix.StringField(10227)
                message.getField(requests_field)
                account_info["requests_per_second"] = requests_field.getValue()

            # Commission and reporting
            if message.isSetField(10242):  # ReportCurrency
                report_currency_field = fix.StringField(10242)
                message.getField(report_currency_field)
                account_info["report_currency"] = report_currency_field.getValue()

            if message.isSetField(10244):  # TokenCommissionCurrency
                token_comm_currency_field = fix.StringField(10244)
                message.getField(token_comm_currency_field)
                account_info["token_commission_currency"] = token_comm_currency_field.getValue()

            if message.isSetField(10245):  # TokenCommissionCurrencyDiscount
                token_comm_discount_field = fix.StringField(10245)
                message.getField(token_comm_discount_field)
                account_info["token_commission_discount"] = token_comm_discount_field.getValue()

            if message.isSetField(10246):  # TokenCommissionEnabled
                token_comm_enabled_field = fix.StringField(10246)
                message.getField(token_comm_enabled_field)
                account_info["token_commission_enabled"] = token_comm_enabled_field.getValue() == "Y"

            # Parse asset information if present
            if message.isSetField(10117):  # NoAssets
                no_assets_field = fix.IntField(10117)
                message.getField(no_assets_field)
                num_assets = no_assets_field.getValue()

                if num_assets > 0:
                    assets = []
                    # Note: Asset parsing would require repeating group handling
                    # This is a simplified version - full implementation would need
                    # proper FIX repeating group parsing
                    account_info["num_assets"] = num_assets
                    account_info["assets"] = assets

            # Parse throttling methods if present
            if message.isSetField(10229):  # ThrottlingMethodsInfo
                throttling_methods_field = fix.IntField(10229)
                message.getField(throttling_methods_field)
                num_methods = throttling_methods_field.getValue()

                if num_methods > 0:
                    throttling_methods = []
                    # Note: Similar to assets, this would require proper repeating group handling
                    account_info["num_throttling_methods"] = num_methods
                    account_info["throttling_methods"] = throttling_methods

            # Request tracking
            if message.isSetField(10028):  # AcInfReqID
                request_id_field = fix.StringField(10028)
                message.getField(request_id_field)
                account_info["request_id"] = request_id_field.getValue()

            logger.info(f"Successfully parsed account info with {len(account_info)} fields")
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

            # Check if this is part of a mass status request
            mass_status_req_id = ""
            if message.isSetField(584):  # MassStatusReqID
                mass_status_field = fix.StringField(584)
                message.getField(mass_status_field)
                mass_status_req_id = mass_status_field.getValue()

            # Handle mass status response
            if (
                mass_status_req_id
                and hasattr(self, "order_collections")
                and mass_status_req_id in self.order_collections
            ):
                self.order_collections[mass_status_req_id]["orders"].append(parsed_data)

                # Check for completion indicators
                tot_num_reports = 0
                last_rpt_requested = False

                if message.isSetField(911):  # TotNumReports
                    tot_reports_field = fix.IntField(911)
                    message.getField(tot_reports_field)
                    tot_num_reports = tot_reports_field.getValue()

                if message.isSetField(912):  # LastRptRequested
                    last_rpt_field = fix.StringField(912)
                    message.getField(last_rpt_field)
                    last_rpt_requested = last_rpt_field.getValue() == "Y"

                logger.debug(
                    f"Mass status execution report {len(self.order_collections[mass_status_req_id]['orders'])}/{tot_num_reports}"
                )

                # Complete the mass status request if this is the last report or we have token report
                if last_rpt_requested or tot_num_reports == 0:
                    complete_data = {
                        "orders": self.order_collections[mass_status_req_id]["orders"],
                        "total_reports": tot_num_reports,
                    }

                    if mass_status_req_id in self.response_events:
                        self.request_responses[mass_status_req_id] = (True, complete_data, None)
                        self.response_events[mass_status_req_id].set()

            # Handle individual order response
            elif client_order_id in self.response_events:
                self.request_responses[client_order_id] = (True, parsed_data, None)
                self.response_events[client_order_id].set()
            else:
                logger.debug(f"Received unsolicited execution report for order: {client_order_id}")
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

    def _handle_request_for_positions_ack(self, message):
        """Handle Request for Positions Ack (AO)"""
        try:
            request_id = ""
            if message.isSetField(710):  # PosReqID
                request_id_field = fix.StringField(710)
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            parsed_data = self._parse_request_for_positions_ack_message(message)

            # Store the ack data and prepare for position reports
            if request_id:
                if not hasattr(self, "position_collections"):
                    self.position_collections = {}
                self.position_collections[request_id] = {
                    "ack_data": parsed_data,
                    "positions": [],
                    "expected_count": parsed_data.get("total_num_pos_reports", 0),
                }

            logger.debug(f"Received Position Request Ack for request {request_id}")

        except Exception as e:
            logger.error(f"Error handling request for positions ack: {e}")

    def _handle_position_report(self, message):
        """Handle Position Report (AP)"""
        try:
            request_id = ""
            if message.isSetField(710):  # PosReqID
                request_id_field = fix.StringField(710)
                message.getField(request_id_field)
                request_id = request_id_field.getValue()

            parsed_data = self._parse_position_report_message(message)

            # Add position to collection
            if request_id and hasattr(self, "position_collections") and request_id in self.position_collections:
                self.position_collections[request_id]["positions"].append(parsed_data)

                # Check if we have all expected positions
                collection = self.position_collections[request_id]
                expected = collection["expected_count"]
                received = len(collection["positions"])

                logger.debug(f"Position Report {received}/{expected} for request {request_id}")

                # If we have all positions or expected count is 0, complete the request
                if received >= expected or expected == 0:
                    complete_data = {"ack_data": collection["ack_data"], "positions": collection["positions"]}

                    if request_id in self.response_events:
                        self.request_responses[request_id] = (True, complete_data, None)
                        self.response_events[request_id].set()

                    # Clean up
                    del self.position_collections[request_id]

        except Exception as e:
            logger.error(f"Error handling position report: {e}")

    def _parse_request_for_positions_ack_message(self, message) -> dict:
        """Parse Request for Positions Ack (AO) message"""
        try:
            result = {}

            field_mappings = {
                721: ("pos_maint_rpt_id", str),  # PosMaintRptID
                710: ("pos_req_id", str),  # PosReqID
                728: ("pos_req_result", str),  # PosReqResult
                729: ("pos_req_status", str),  # PosReqStatus
                1: ("account", str),  # Account
                581: ("account_type", str),  # AccountType
                727: ("total_num_pos_reports", int),  # TotalNumPosReports
            }

            for tag, (field_name, converter) in field_mappings.items():
                if message.isSetField(tag):
                    try:
                        if converter == str:
                            if tag in [1]:  # Account
                                field = fix.Account()
                            else:
                                field = fix.StringField(tag)
                            message.getField(field)
                            result[field_name] = field.getValue()
                        elif converter == int:
                            field = fix.IntField(tag)
                            message.getField(field)
                            result[field_name] = field.getValue()
                    except Exception as e:
                        logger.warning(f"Failed to parse field {tag}: {e}")

            return result

        except Exception as e:
            logger.error(f"Failed to parse Request for Positions Ack message: {e}")
            return {}

    def _parse_position_report_message(self, message) -> dict:
        """Parse Position Report (AP) message"""
        try:
            result = {}

            field_mappings = {
                721: ("pos_maint_rpt_id", str),  # PosMaintRptID (Position ID)
                710: ("pos_req_id", str),  # PosReqID
                263: ("subscription_request_type", str),  # SubscriptionRequestType
                727: ("total_num_pos_reports", int),  # TotalNumPosReports
                728: ("pos_req_result", str),  # PosReqResult
                715: ("clearing_business_date", str),  # ClearingBusinessDate
                1: ("account", str),  # Account
                581: ("account_type", str),  # AccountType
                55: ("symbol", str),  # Symbol
                15: ("currency", str),  # Currency
                730: ("settl_price", float),  # SettlPrice (Average weighted price)
                734: ("prior_settl_price", float),  # PriorSettlPrice
                731: ("settl_price_type", str),  # SettlPriceType
                704: ("long_qty", float),  # LongQty
                705: ("short_qty", float),  # ShortQty
                10107: ("long_price", float),  # LongPrice
                10108: ("short_price", float),  # ShortPrice
                12: ("commission", float),  # Commission
                479: ("comm_currency", str),  # CommCurrency
                13: ("comm_type", str),  # CommType
                10113: ("agent_commission", float),  # AgentCommission
                10115: ("agent_comm_currency", str),  # AgentCommCurrency
                10114: ("agent_comm_type", str),  # AgentCommType
                10096: ("swap", float),  # Swap
                10099: ("pos_report_type", str),  # PosReportType
                10072: ("acc_balance", float),  # AccBalance
                10073: ("acc_tr_amount", float),  # AccTrAmount
                10074: ("acc_tr_curry", str),  # AccTrCurry
            }

            for tag, (field_name, converter) in field_mappings.items():
                if message.isSetField(tag):
                    try:
                        if converter == str:
                            if tag in [1, 55, 15]:  # Account, Symbol, Currency
                                field_class = {1: fix.Account, 55: fix.Symbol, 15: fix.Currency}[tag]
                                field = field_class()
                            else:
                                field = fix.StringField(tag)
                            message.getField(field)
                            result[field_name] = field.getValue()
                        elif converter == float:
                            field = fix.DoubleField(tag)
                            message.getField(field)
                            result[field_name] = field.getValue()
                        elif converter == int:
                            field = fix.IntField(tag)
                            message.getField(field)
                            result[field_name] = field.getValue()
                    except Exception as e:
                        logger.warning(f"Failed to parse position field {tag}: {e}")

            return result

        except Exception as e:
            logger.error(f"Failed to parse Position Report message: {e}")
            return {}

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
                # Core order identification fields
                37: ("order_id", str),
                11: ("client_order_id", str),
                17: ("exec_id", str),
                568: ("trade_request_id", str),
                # Mass status request fields
                584: ("mass_status_req_id", str),
                911: ("tot_num_reports", int),
                912: ("last_rpt_requested", str),
                # Order status and execution
                39: ("order_status", str),
                150: ("exec_type", str),
                # Order details
                55: ("symbol", str),
                54: ("side", str),
                40: ("order_type", str),
                10149: ("parent_order_type", str),
                # Quantities
                14: ("cum_qty", float),
                38: ("order_qty", float),
                151: ("leaves_qty", float),
                10205: ("max_visible_qty", float),
                # Prices
                6: ("avg_price", float),
                44: ("price", float),
                99: ("stop_price", float),
                32: ("last_qty", float),
                31: ("last_price", float),
                10158: ("req_open_price", float),
                10159: ("req_open_qty", float),
                # Time management
                60: ("transact_time", str),
                10083: ("order_created", str),
                10084: ("order_modified", str),
                59: ("time_in_force", str),
                126: ("expire_time", str),
                # Risk management
                10037: ("stop_loss", float),
                10038: ("take_profit", float),
                # Order flags
                10162: ("immediate_or_cancel_flag", str),
                10163: ("market_with_slippage_flag", str),
                10206: ("comm_open_reduced_flag", str),
                10207: ("comm_close_reduced_flag", str),
                # Financial information
                12: ("commission", float),
                13: ("comm_type", str),
                10113: ("agent_commission", float),
                10114: ("agent_comm_type", str),
                10096: ("swap", float),
                10072: ("account_balance", float),
                10073: ("acc_tr_amount", float),
                10074: ("acc_tr_curry", str),
                10231: ("slippage", float),
                # Order management
                58: ("text", str),
                103: ("reject_reason", str),
                10045: ("close_pos_req_id", str),
                # Metadata
                10076: ("comment", str),
                10103: ("tag", str),
                10104: ("magic", int),
                10105: ("margin_rate_initial", float),
                10109: ("parent_order_id", str),
                # Asset information (repeating group - we'll handle the first one)
                10117: ("num_assets", int),
                10118: ("asset_balance", float),
                10154: ("asset_locked_amt", float),
                10119: ("asset_trade_amt", float),
                10120: ("asset_currency", str),
            }

            for tag, (field_name, converter) in field_mappings.items():
                if message.isSetField(tag):
                    try:
                        # Use standard FIX field types for common fields, StringField for extensions
                        if tag in [11, 37, 17, 55, 58]:
                            # Use proper FIX field types for standard fields
                            field_type_map = {
                                11: fix.ClOrdID,
                                37: fix.OrderID,
                                17: fix.ExecID,
                                55: fix.Symbol,
                                58: fix.Text,
                            }
                            field = field_type_map[tag]()
                        elif tag in [6, 44, 99, 32, 31, 12]:
                            # Use proper FIX field types for standard price/quantity fields
                            field_type_map = {
                                6: fix.AvgPx,
                                44: fix.Price,
                                99: fix.StopPx,
                                32: fix.LastQty,
                                31: fix.LastPx,
                                12: fix.Commission,
                            }
                            field = field_type_map[tag]()
                        elif tag in [911]:
                            # Integer fields
                            field = fix.IntField(tag)
                        else:
                            # Use StringField for all extension fields and other fields
                            field = fix.StringField(tag)

                        message.getField(field)
                        value = field.getValue()

                        # Convert value based on expected type
                        if converter == str:
                            result[field_name] = value if value else None
                        elif converter == float:
                            try:
                                result[field_name] = float(value) if value else None
                            except (ValueError, TypeError):
                                result[field_name] = None
                        elif converter == int:
                            try:
                                result[field_name] = int(value) if value else None
                            except (ValueError, TypeError):
                                result[field_name] = None
                        else:
                            result[field_name] = value

                    except Exception as e:
                        logger.debug(f"Failed to parse field {tag} ({field_name}): {e}")
                        result[field_name] = None

            logger.info(f"Parsed execution report for order: {result.get('client_order_id', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"Failed to parse execution report message: {e}")
            return {"error": f"Failed to parse execution report: {e}"}

    def send_order_mass_status_request(self, request_id: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send Order Mass Status Request (AF) to get all open orders"""
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("AF"))  # Order Mass Status Request

            # Set required fields according to FIX specification
            message.setField(fix.StringField(584, request_id))  # MassStatusReqID
            message.setField(fix.StringField(585, "7"))  # MassStatusReqType: StatusAllOrders

            # Initialize collection for execution reports
            if not hasattr(self, "order_collections"):
                self.order_collections = {}
            self.order_collections[request_id] = {"orders": [], "completed": False}

            event = threading.Event()
            self.response_events[request_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Order Mass Status Request: {request_id}")

            # Wait for response - may take longer for multiple orders
            if event.wait(30):
                result = self.request_responses.pop(request_id, (False, None, "No response"))
                self.response_events.pop(request_id, None)

                # Clean up order collection
                if hasattr(self, "order_collections") and request_id in self.order_collections:
                    del self.order_collections[request_id]

                return result
            else:
                self.response_events.pop(request_id, None)
                if hasattr(self, "order_collections") and request_id in self.order_collections:
                    del self.order_collections[request_id]
                return False, None, "Order mass status request timed out"

        except Exception as e:
            logger.error(f"Order mass status request failed: {e}")
            return False, None, f"Order mass status request failed: {e}"

    def send_request_for_positions(
        self, request_id: str, account_id: str
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send Request for Positions (AN) to get all open positions"""
        if not self.is_connected():
            return False, None, "Trade session not connected"

        try:
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType("AN"))  # Request for Positions

            # Set required fields according to FIX specification
            message.setField(fix.StringField(710, request_id))  # PosReqID
            message.setField(fix.StringField(724, "0"))  # PosReqType: Positions
            message.setField(fix.StringField(263, "0"))  # SubscriptionRequestType: Snapshot only
            message.setField(fix.Account(account_id))  # Account
            message.setField(fix.StringField(581, "1"))  # AccountType: Account Customer

            # Set timestamps
            now = datetime.utcnow()
            transact_time = now.strftime("%Y%m%d-%H:%M:%S")
            message.setField(fix.TransactTime())  # TransactTime
            message.setField(fix.StringField(715, transact_time))  # ClearingBusinessDate

            event = threading.Event()
            self.response_events[request_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Request for Positions: {request_id}")

            # Wait for response - may take longer for multiple positions
            if event.wait(30):
                result = self.request_responses.pop(request_id, (False, None, "No response"))
                self.response_events.pop(request_id, None)
                return result
            else:
                self.response_events.pop(request_id, None)
                return False, None, "Request for positions timed out"

        except Exception as e:
            logger.error(f"Request for positions failed: {e}")
            return False, None, f"Request for positions failed: {e}"
