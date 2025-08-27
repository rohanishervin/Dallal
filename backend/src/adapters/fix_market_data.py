import logging
import time
from typing import Dict, Optional, Tuple

from .fix_session_manager import FIXSessionManager

logger = logging.getLogger(__name__)


class FIXMarketData:
    def __init__(self, session_manager: FIXSessionManager):
        self.session_manager = session_manager

    def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        if not self.session_manager.is_session_active():
            logger.warning("Attempted security list request with inactive session")
            return False, None, "FIX session not active"

        try:
            if not request_id:
                request_id = f"SLR_{int(time.time() * 1000)}"

            security_list_fields = [("320", request_id), ("559", "4")]

            request_message = self.session_manager.message_builder.create_fix_message("x", security_list_fields)
            logger.info(
                f"Sending security list request: {request_message.replace(self.session_manager.message_builder.SOH, '|')}"
            )

            if not self.session_manager.connection.send_message(request_message):
                return False, None, "Failed to send request"

            messages_received = []

            while True:
                try:
                    response = self.session_manager.connection.recv_complete_fix_message(15)
                    if not response:
                        logger.error("Security list request timed out")
                        logger.info(f"Messages received during request: {messages_received}")
                        return False, None, "Request timed out - no Security List response received"

                    msg_display = response.replace(self.session_manager.message_builder.SOH, "|")
                    if len(msg_display) > 100:
                        parsed_for_type = self.session_manager.message_builder.parse_fix_response(response)
                        msg_type = parsed_for_type.get("35", "unknown")
                        msg_display = f"MsgType={msg_type}, Length={len(response)}, Last20chars: ...{msg_display[-20:]}"
                    logger.info(f"Received FIX response: {msg_display}")

                    parsed_response = self.session_manager.message_builder.parse_fix_response(response)
                    messages_received.append(parsed_response)

                    msg_type = parsed_response.get("35")

                    if msg_type == "y":
                        logger.info("Received Security List (y) response")
                        return True, self.parse_security_list_from_raw_message(response), None
                    elif msg_type == "j":
                        logger.warning("Received Business Message Reject (j)")
                        error_msg = parsed_response.get("58", "Business message reject")
                        reject_reason = parsed_response.get("380", "Unknown reason")
                        ref_msg_type = parsed_response.get("372", "Unknown")
                        return (
                            False,
                            None,
                            f"Request rejected: {error_msg} (Reason: {reject_reason}, RefMsgType: {ref_msg_type})",
                        )
                    elif msg_type == "0":
                        logger.info("Received Heartbeat (0), continuing to wait for Security List response...")
                        continue
                    elif msg_type == "1":
                        logger.info("Received Test Request (1), sending Heartbeat response...")
                        test_req_id = parsed_response.get("112")
                        heartbeat_fields = [("112", test_req_id)] if test_req_id else []
                        heartbeat_message = self.session_manager.message_builder.create_fix_message(
                            "0", heartbeat_fields
                        )
                        self.session_manager.connection.send_message(heartbeat_message)
                        continue
                    else:
                        logger.warning(f"Unexpected message type: {msg_type}, continuing to wait...")
                        continue

                except Exception as recv_error:
                    logger.error(f"Error receiving message: {str(recv_error)}")
                    return False, None, f"Receive error: {str(recv_error)}"

        except Exception as e:
            logger.error(f"Security list request failed: {str(e)}")
            return False, None, f"Request failed: {str(e)}"

    def parse_security_list_response(self, response_fields: dict) -> dict:
        try:
            result = {
                "request_id": response_fields.get("320"),
                "response_id": response_fields.get("322"),
                "result": response_fields.get("560"),
                "symbols": [],
            }

            num_symbols = int(response_fields.get("146", "0"))
            logger.info(f"Expected number of symbols: {num_symbols}")

            return result

        except Exception as e:
            logger.error(f"Failed to parse security list response: {str(e)}")
            return {"error": f"Failed to parse security list response: {str(e)}"}

    def parse_security_list_from_raw_message(self, raw_message: str) -> dict:
        try:
            SOH = self.session_manager.message_builder.SOH
            response_fields = self.session_manager.message_builder.parse_fix_response(raw_message)
            result = {
                "request_id": response_fields.get("320"),
                "response_id": response_fields.get("322"),
                "result": response_fields.get("560"),
                "symbols": [],
            }

            num_symbols = int(response_fields.get("146", "0"))
            logger.info(f"Expected number of symbols: {num_symbols}")

            fields = []
            for field in raw_message.split(SOH):
                if "=" in field:
                    tag, value = field.split("=", 1)
                    fields.append((tag, value))

            symbols = []
            current_symbol = {}
            in_symbol_group = False

            for tag, value in fields:
                if tag in ["8", "9", "35", "34", "49", "52", "56"]:
                    continue
                elif tag == "320":
                    continue
                elif tag == "322":
                    continue
                elif tag == "560":
                    continue
                elif tag == "146":
                    in_symbol_group = True
                    continue
                elif tag == "10":
                    break

                if not in_symbol_group:
                    continue

                if tag == "55":
                    if current_symbol:
                        symbols.append(current_symbol)
                    current_symbol = {"symbol": value}
                elif current_symbol:
                    if tag == "48":
                        current_symbol["security_id"] = value
                    elif tag == "22":
                        current_symbol["security_id_source"] = value
                    elif tag == "107":
                        current_symbol["security_desc"] = value
                    elif tag == "15":
                        current_symbol["currency"] = value
                    elif tag == "120":
                        current_symbol["settle_currency"] = value
                    elif tag == "10127":
                        current_symbol["trade_enabled"] = value == "Y"
                    elif tag == "354":
                        current_symbol["description_len"] = value
                    elif tag == "355":
                        current_symbol["description"] = value
                    elif tag == "350":
                        current_symbol["encoded_security_desc_len"] = value
                    elif tag == "351":
                        current_symbol["encoded_security_desc"] = value
                    elif tag == "561":
                        current_symbol["round_lot"] = value
                    elif tag == "562":
                        current_symbol["min_trade_vol"] = value
                    elif tag == "10058":
                        current_symbol["max_trade_volume"] = value
                    elif tag == "10062":
                        current_symbol["trade_vol_step"] = value
                    elif tag == "10057":
                        current_symbol["px_precision"] = value
                    elif tag == "231":
                        current_symbol["contract_multiplier"] = value
                    elif tag == "10137":
                        current_symbol["currency_precision"] = value
                    elif tag == "10135":
                        current_symbol["currency_sort_order"] = value
                    elif tag == "10138":
                        current_symbol["settl_currency_precision"] = value
                    elif tag == "10136":
                        current_symbol["settl_currency_sort_order"] = value
                    elif tag == "10134":
                        current_symbol["margin_factor_fractional"] = value
                    elif tag == "10194":
                        current_symbol["stop_order_margin_reduction"] = value
                    elif tag == "10209":
                        current_symbol["hidden_limit_order_margin_reduction"] = value
                    elif tag == "12":
                        current_symbol["commission"] = value
                    elif tag == "13":
                        current_symbol["comm_type"] = value
                    elif tag == "10124":
                        current_symbol["comm_charge_type"] = value
                    elif tag == "10143":
                        current_symbol["comm_charge_method"] = value
                    elif tag == "10210":
                        current_symbol["min_commission"] = value
                    elif tag == "10211":
                        current_symbol["min_commission_currency"] = value
                    elif tag == "10212":
                        current_symbol["swap_type"] = value
                    elif tag == "10125":
                        current_symbol["swap_size_short"] = value
                    elif tag == "10126":
                        current_symbol["swap_size_long"] = value
                    elif tag == "10213":
                        current_symbol["triple_swap_day"] = value
                    elif tag == "10155":
                        current_symbol["default_slippage"] = value
                    elif tag == "10131":
                        current_symbol["sort_order"] = value
                    elif tag == "10132":
                        current_symbol["group_sort_order"] = value
                    elif tag == "10170":
                        current_symbol["status_group_id"] = value
                    elif tag == "10243":
                        current_symbol["close_only"] = value
                    else:
                        logger.debug(
                            f"Unmapped field for symbol {current_symbol.get('symbol', 'unknown')}: {tag}={value}"
                        )

            if current_symbol:
                symbols.append(current_symbol)

            result["symbols"] = symbols
            logger.info(f"Parsed {len(symbols)} symbols from Security List response")

            if symbols:
                logger.info(f"First symbol example: {symbols[0]}")
                non_null_fields = {k: v for k, v in symbols[0].items() if v is not None}
                logger.info(f"First symbol non-null fields count: {len(non_null_fields)}")
                if len(symbols) > 1:
                    logger.info(f"Second symbol example: {symbols[1]}")

            logger.info(f"Total fields parsed from message: {len(fields)}")
            symbol_fields = [f for f in fields if f[0] in ["55", "48", "231", "15", "561", "562"]]
            logger.info(f"Sample symbol-related fields: {symbol_fields[:10]}")

            return result

        except Exception as e:
            logger.error(f"Failed to parse security list response: {str(e)}")
            return {"error": f"Failed to parse security list response: {str(e)}"}
