import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Dict, Optional, Tuple

import quickfix as fix

from ..services.nats_service import nats_service
from .quickfix_base_adapter import FIXMessageParser, QuickFIXBaseAdapter

logger = logging.getLogger(__name__)


class QuickFIXFeedAdapter(QuickFIXBaseAdapter):
    def __init__(self):
        super().__init__("feed")
        self.active_subscriptions: Dict[str, str] = {}
        self.nats_connected = False

    def fromAdmin(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_Reject:
            logger.error("✗ Feed session logon rejected!")
            if message.isSetField(fix.Text()):
                text = fix.Text()
                message.getField(text)
                logger.error(f"Reason: {text.getValue()}")

    def toApp(self, message, sessionID):
        logger.debug(f"→ Feed: {message}")

    def fromApp(self, message, sessionID):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)
        msg_type_str = msg_type.getValue()

        logger.debug(f"← Feed message type: {msg_type_str}")

        if msg_type_str == "W":
            self._handle_market_data_snapshot(message)
        elif msg_type_str == "X":
            self._handle_market_data_incremental_refresh(message)
        elif msg_type_str == "Y":
            self._handle_market_data_request_reject(message)
        elif msg_type_str == "U1011":
            self._handle_market_data_ack(message)
        elif msg_type_str == "y":
            self._handle_security_list_response(message)
        elif msg_type_str == "U1002":
            self._handle_market_history_response(message)
        elif msg_type_str == "j":
            self._handle_business_message_reject(message)
        elif msg_type_str == "U1001":
            self._handle_market_history_reject(message)

    def _handle_market_data_snapshot(self, message):
        logger.info("Received Market Data Snapshot (W)")
        try:
            md_req_id = ""
            if message.isSetField(262):
                md_req_id_field = fix.MDReqID()
                message.getField(md_req_id_field)
                md_req_id = md_req_id_field.getValue()

            orderbook_data = self._parse_orderbook_message(message)
            logger.info(
                f"Parsed orderbook data: {bool(orderbook_data)}, has_error: {orderbook_data.get('error') if orderbook_data else 'N/A'}"
            )

            if orderbook_data and not orderbook_data.get("error"):
                logger.info(f"Sending orderbook data to main process for NATS publishing")
                self._send_orderbook_to_main_process(orderbook_data)
            else:
                if orderbook_data and orderbook_data.get("error"):
                    logger.error(f"Orderbook parsing error: {orderbook_data.get('error')}")
                else:
                    logger.warning("No orderbook data parsed from message")

        except Exception as e:
            logger.error(f"Error handling market data snapshot: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")

    def _handle_market_data_incremental_refresh(self, message):
        logger.info("Received Market Data Incremental Refresh (X)")
        try:
            md_req_id = ""
            if message.isSetField(262):
                md_req_id_field = fix.MDReqID()
                message.getField(md_req_id_field)
                md_req_id = md_req_id_field.getValue()

            orderbook_data = self._parse_orderbook_message(message)

            if orderbook_data:
                logger.debug(f"Sending incremental orderbook data to main process for NATS publishing")
                self._send_orderbook_to_main_process(orderbook_data)

        except Exception as e:
            logger.error(f"Error handling market data incremental refresh: {e}")

    def _handle_market_data_ack(self, message):
        logger.info("Received Market Data Request Ack (U1011)")
        try:
            md_req_id = ""
            if message.isSetField(262):
                md_req_id_field = fix.MDReqID()
                message.getField(md_req_id_field)
                md_req_id = md_req_id_field.getValue()

            total_snaps = None
            if message.isSetField(10049):
                total_snaps_field = fix.IntField(10049)
                message.getField(total_snaps_field)
                total_snaps = total_snaps_field.getValue()

            logger.info(f"Market Data Request Acknowledged - ID: {md_req_id}, Total Snapshots: {total_snaps}")
            logger.debug(f"Available response events: {list(self.response_events.keys())}")

            if md_req_id in self.response_events:
                logger.debug(f"Setting response for request {md_req_id}")
                self.request_responses[md_req_id] = (True, {"acknowledged": True, "total_snaps": total_snaps}, None)
                self.response_events[md_req_id].set()
            else:
                logger.warning(f"No event found for request ID: {md_req_id}")

        except Exception as e:
            logger.error(f"Error handling market data ack: {e}")

    def _handle_market_data_request_reject(self, message):
        logger.warning("Received Market Data Request Reject (Y)")
        try:
            md_req_id = ""
            if message.isSetField(262):
                md_req_id_field = fix.MDReqID()
                message.getField(md_req_id_field)
                md_req_id = md_req_id_field.getValue()

            reject_reason = None
            if message.isSetField(281):
                rej_reason_field = fix.MDReqRejReason()
                message.getField(rej_reason_field)
                reject_reason = rej_reason_field.getValue()

            text = None
            if message.isSetField(58):
                text_field = fix.Text()
                message.getField(text_field)
                text = text_field.getValue()

            error_msg = f"Market Data Request Rejected - ID: {md_req_id}"
            if reject_reason:
                reason_map = {"0": "Unknown symbol", "5": "Unsupported MarketDepth", "D": "THROTTLING"}
                reason_text = reason_map.get(reject_reason, f"Unknown reason: {reject_reason}")
                error_msg += f", Reason: {reason_text}"
            if text:
                error_msg += f", Description: {text}"

            logger.warning(error_msg)

            if md_req_id in self.response_events:
                self.request_responses[md_req_id] = (False, None, error_msg)
                self.response_events[md_req_id].set()

        except Exception as e:
            logger.error(f"Error handling market data request reject: {e}")

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

    def set_response_queue(self, response_queue):
        self.response_queue = response_queue

    def _send_orderbook_to_main_process(self, orderbook_data: dict):
        try:
            # Direct NATS publishing from QuickFIX process
            symbol = orderbook_data.get("symbol")
            if symbol:
                self._publish_to_nats_sync(symbol, orderbook_data)
                logger.info(f"Successfully published orderbook data to NATS (symbol: {symbol})")
            else:
                logger.error("No symbol in orderbook data")
        except Exception as e:
            logger.error(f"Failed to publish orderbook data to NATS: {e}")

    def _publish_to_nats_sync(self, symbol: str, orderbook_data: dict):
        """Synchronously publish to NATS from QuickFIX process"""
        # Use Python NATS client directly instead of CLI
        self._publish_to_nats_python_sync(symbol, orderbook_data)

    def _publish_to_nats_python_sync(self, symbol: str, orderbook_data: dict):
        """Fallback: Use Python NATS client synchronously"""
        import asyncio
        import json
        import os

        import nats

        async def publish():
            try:
                # Use environment variable for NATS URL, fallback to Docker service name
                nats_url = os.getenv("NATS_URL", "nats://nats:4222")
                nc = await nats.connect(nats_url)
                subject = f"orderbook.{symbol}"
                payload = json.dumps(orderbook_data, default=str)
                await nc.publish(subject, payload.encode())
                await nc.close()
                logger.debug(f"Published to NATS via Python client")
            except Exception as e:
                logger.error(f"Python NATS publish failed: {e}")

        try:
            asyncio.run(publish())
        except Exception as e:
            logger.error(f"Failed to run async NATS publish: {e}")

    def send_market_data_subscribe(
        self, symbol: str, levels: int = 5, md_req_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        if not self.is_connected():
            return False, "Feed session not connected"

        try:
            if not md_req_id:
                md_req_id = f"OB_{symbol}_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_MarketDataRequest))

            message.setField(fix.MDReqID(md_req_id))
            message.setField(fix.SubscriptionRequestType("1"))
            message.setField(fix.MarketDepth(levels))

            message.setField(fix.MDUpdateType(0))

            message.setField(fix.NoMDEntryTypes(1))
            entry_types_group = fix.Group(267, 269)
            entry_types_group.setField(fix.MDEntryType("2"))
            message.addGroup(entry_types_group)

            message.setField(fix.NoRelatedSym(1))
            symbols_group = fix.Group(146, 55)
            symbols_group.setField(fix.Symbol(symbol))
            message.addGroup(symbols_group)

            event = threading.Event()
            self.response_events[md_req_id] = event

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Market Data Subscribe for {symbol} (levels: {levels}, req_id: {md_req_id})")

            logger.debug(f"Waiting for response for request ID: {md_req_id}")
            if event.wait(10):
                result = self.request_responses.pop(md_req_id, (False, None, "No response"))
                self.response_events.pop(md_req_id, None)

                logger.debug(f"Received response for {md_req_id}: {result}")
                if result[0]:
                    self.active_subscriptions[symbol] = md_req_id
                    logger.info(f"Successfully subscribed to {symbol} with req_id {md_req_id}")
                    return True, None
                else:
                    logger.warning(f"Subscription failed for {symbol}: {result[2]}")
                    return False, result[2] or "Subscription failed"
            else:
                self.response_events.pop(md_req_id, None)
                logger.warning(f"Subscription request timed out for {symbol} (req_id: {md_req_id})")
                return False, "Subscription request timed out"

        except Exception as e:
            logger.error(f"Market data subscription failed: {e}")
            return False, f"Subscription failed: {e}"

    def send_market_data_unsubscribe(self, symbol: str, md_req_id: str = None) -> Tuple[bool, Optional[str]]:
        if not self.is_connected():
            return False, "Feed session not connected"

        try:
            if not md_req_id and symbol in self.active_subscriptions:
                md_req_id = self.active_subscriptions[symbol]
            elif not md_req_id:
                return False, f"No active subscription found for {symbol}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_MarketDataRequest))

            message.setField(fix.MDReqID(md_req_id))
            message.setField(fix.SubscriptionRequestType("2"))
            message.setField(fix.MarketDepth(0))

            message.setField(fix.NoMDEntryTypes(1))
            entry_types_group = fix.Group(267, 269)
            entry_types_group.setField(fix.MDEntryType("2"))
            message.addGroup(entry_types_group)

            message.setField(fix.NoRelatedSym(1))
            symbols_group = fix.Group(146, 55)
            symbols_group.setField(fix.Symbol(symbol))
            message.addGroup(symbols_group)

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Market Data Unsubscribe for {symbol} (req_id: {md_req_id})")

            if symbol in self.active_subscriptions:
                del self.active_subscriptions[symbol]

            return True, None

        except Exception as e:
            logger.error(f"Market data unsubscription failed: {e}")
            return False, f"Unsubscription failed: {e}"

    def send_market_data_request(self, symbol: str, md_req_id: str = None) -> Tuple[bool, Optional[str]]:
        if not self.is_connected():
            return False, "Feed session not connected"

        try:
            if not md_req_id:
                md_req_id = f"MDR_{int(time.time() * 1000)}"

            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_MarketDataRequest))

            message.setField(fix.MDReqID(md_req_id))
            message.setField(fix.SubscriptionRequestType("1"))
            message.setField(fix.MarketDepth(1))

            entry_types_group = fix.Group(fix.NoMDEntryTypes())
            entry_types_group.setField(fix.MDEntryType("0"))
            message.addGroup(entry_types_group)

            entry_types_group = fix.Group(fix.NoMDEntryTypes())
            entry_types_group.setField(fix.MDEntryType("1"))
            message.addGroup(entry_types_group)

            message.setField(fix.NoMDEntryTypes(2))

            symbols_group = fix.Group(fix.NoRelatedSym())
            symbols_group.setField(fix.Symbol(symbol))
            message.addGroup(symbols_group)

            message.setField(fix.NoRelatedSym(1))

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Market Data Request for {symbol}: {md_req_id}")
            return True, None

        except Exception as e:
            logger.error(f"Market data request failed: {e}")
            return False, f"Request failed: {e}"

    def send_test_request(self) -> bool:
        if not self.is_connected():
            return False

        try:
            test_req_id = f"TEST_{int(time.time() * 1000)}"
            message = fix.Message()
            header = message.getHeader()
            header.setField(fix.MsgType(fix.MsgType_TestRequest))
            message.setField(fix.TestReqID(test_req_id))

            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"Sent Test Request: {test_req_id}")
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
            return False, None, "Feed session not connected"

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
            return False, None, "Feed session not connected"

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

    def _parse_orderbook_message(self, message) -> dict:
        try:
            logger.debug("Starting orderbook message parsing")
            symbol = fix.Symbol()
            message.getField(symbol)
            symbol_val = symbol.getValue()

            md_req_id = ""
            if message.isSetField(262):
                md_req_id_field = fix.MDReqID()
                message.getField(md_req_id_field)
                md_req_id = md_req_id_field.getValue()

            orig_time = None
            try:
                if message.isSetField(42):
                    orig_time_field = fix.StringField(42)
                    message.getField(orig_time_field)
                    orig_time = orig_time_field.getValue()
            except Exception:
                pass

            tick_id = None
            try:
                if message.isSetField(10094):
                    tick_id_field = fix.StringField(10094)
                    message.getField(tick_id_field)
                    tick_id = tick_id_field.getValue()
            except Exception:
                pass

            # Check for indicative tick flag - use StringField to handle 'N' values
            is_indicative = False
            try:
                if message.isSetField(10230):
                    indicative_field = fix.StringField(10230)
                    message.getField(indicative_field)
                    indicative_value = indicative_field.getValue()
                    # Only set to True if the value is explicitly '1', treat 'N' or other values as False
                    is_indicative = indicative_value == "1"
            except Exception as e:
                logger.debug(f"Error getting indicative flag: {e}")
                is_indicative = False

            no_md_entries = fix.NoMDEntries()
            message.getField(no_md_entries)
            num_entries = no_md_entries.getValue()

            bids = []
            asks = []
            trades = []

            # Define safe_float function BEFORE using it
            def safe_float(value):
                if not value or str(value).upper() in ["N", "NULL", ""]:
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None

            for i in range(1, num_entries + 1):
                try:
                    group = fix.Group(268, 269)
                    message.getGroup(i, group)

                    entry_type = fix.MDEntryType()
                    group.getField(entry_type)
                    entry_type_val = entry_type.getValue()

                    # Get price using StringField to handle 'N' values safely
                    price = None
                    if group.isSetField(270):  # MDEntryPx tag
                        try:
                            price_field = fix.StringField(270)
                            group.getField(price_field)
                            price_str = price_field.getValue()
                            price = safe_float(price_str)
                        except Exception as e:
                            logger.debug(f"Error getting price value: {e}")
                            price = None

                    # Get size using StringField to handle 'N' values safely
                    size = None
                    if group.isSetField(271):  # MDEntrySize tag
                        try:
                            size_field = fix.StringField(271)
                            group.getField(size_field)
                            size_str = size_field.getValue()
                            size = safe_float(size_str)
                        except Exception as e:
                            logger.debug(f"Error getting size value: {e}")
                            size = None

                    # Store entry data - only add entries with valid prices
                    if price is not None:
                        entry_data = {
                            "price": price,
                            "size": size,
                            "level": len(bids) + 1
                            if entry_type_val == "0"
                            else (len(asks) + 1 if entry_type_val == "1" else len(trades) + 1),
                        }

                        if entry_type_val == "0":  # Bid
                            bids.append(entry_data)
                        elif entry_type_val == "1":  # Ask/Offer
                            asks.append(entry_data)
                        elif entry_type_val == "2":  # Trade
                            trades.append(entry_data)
                    else:
                        logger.debug(f"Skipping entry {i} with invalid price: {price}")

                except Exception as entry_error:
                    logger.warning(f"Error parsing market data entry {i}: {entry_error}")
                    continue

            # Filter out None prices before sorting
            bids = [bid for bid in bids if bid["price"] is not None]
            asks = [ask for ask in asks if ask["price"] is not None]
            trades = [trade for trade in trades if trade["price"] is not None]

            bids = sorted(bids, key=lambda x: x["price"], reverse=True)
            asks = sorted(asks, key=lambda x: x["price"])

            for i, bid in enumerate(bids, 1):
                bid["level"] = i
            for i, ask in enumerate(asks, 1):
                ask["level"] = i

            best_bid = bids[0]["price"] if bids else None
            best_ask = asks[0]["price"] if asks else None
            mid_price = None
            spread = None
            spread_bps = None

            if best_bid and best_ask:
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
                spread_bps = (spread / mid_price) * 10000 if mid_price else None

            latest_price = None
            price_source = None

            if trades:
                latest_price = trades[-1]["price"]
                price_source = "trade"
            elif mid_price:
                latest_price = mid_price
                price_source = "mid"

            order_book_json = {
                "symbol": symbol_val,
                "request_id": md_req_id,
                "timestamp": orig_time,
                "tick_id": tick_id,
                "is_indicative": is_indicative,
                "latest_price": {"price": latest_price, "source": price_source},
                "market_data": {
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "mid_price": mid_price,
                    "spread": spread,
                    "spread_bps": spread_bps,
                },
                "order_book": {"bids": bids, "asks": asks, "trades": trades if trades else None},
                "levels": {"bid_levels": len(bids), "ask_levels": len(asks), "trade_count": len(trades)},
                "metadata": {
                    "total_entries": num_entries,
                    "has_trades": len(trades) > 0,
                    "book_depth": max(len(bids), len(asks)) if bids or asks else 0,
                },
            }

            return order_book_json

        except Exception as e:
            error_json = {
                "error": True,
                "message": f"Error parsing order book: {str(e)}",
                "symbol": None,
                "timestamp": None,
            }
            logger.error(f"Error creating order book JSON: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full exception details: {str(e)}")
            return error_json

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
