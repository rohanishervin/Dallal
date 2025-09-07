import logging
from datetime import datetime
from typing import Optional, Tuple

from .fix_process_manager import fix_process_manager

logger = logging.getLogger(__name__)


class ProcessFIXAdapter:
    """Process-isolated FIX adapter that communicates with QuickFIX via separate processes"""

    def __init__(self, connection_type: str = "trade"):
        self.connection_type = connection_type
        self.process_id = None
        self.user_id = None

    def logon(
        self, username: str, password: str, device_id: Optional[str] = None, timeout: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """Start FIX session in separate process"""
        try:
            self.user_id = username
            self.process_id = f"{username}_{self.connection_type}"

            success, error_msg = fix_process_manager.start_fix_process(
                user_id=username,
                connection_type=self.connection_type,
                username=username,
                password=password,
                device_id=device_id,
            )

            if success:
                logger.info(f"FIX {self.connection_type} process started for user {username}")
                return True, None
            else:
                logger.error(f"Failed to start FIX {self.connection_type} process: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error starting FIX {self.connection_type} process: {e}")
            return False, f"Process start error: {e}"

    def is_session_active(self) -> bool:
        """Check if the FIX session process is active and healthy"""
        if not self.process_id:
            return False
        return fix_process_manager.is_process_healthy(self.process_id)

    def is_connected(self) -> bool:
        """Alias for is_session_active for compatibility"""
        return self.is_session_active()

    async def send_security_list_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send security list request via process communication"""
        if not self.process_id:
            return False, None, "No active FIX process"

        try:
            request_data = {"request_id": request_id}

            success, data, error = await fix_process_manager.send_request(
                self.process_id, "security_list", request_data, timeout=15
            )

            return success, data, error

        except Exception as e:
            logger.error(f"Security list request error: {e}")
            return False, None, f"Request error: {e}"

    async def send_market_history_request(
        self,
        symbol: str,
        period_id: str,
        max_bars: int,
        end_time: datetime,
        price_type: str = "B",
        graph_type: str = "B",
        request_id: str = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send market history request via process communication"""
        if not self.process_id:
            return False, None, "No active FIX process"

        try:
            request_data = {
                "symbol": symbol,
                "period_id": period_id,
                "max_bars": max_bars,
                "end_time": end_time.isoformat(),
                "price_type": price_type,
                "graph_type": graph_type,
                "request_id": request_id,
            }

            success, data, error = await fix_process_manager.send_request(
                self.process_id, "market_history", request_data, timeout=30
            )

            return success, data, error

        except Exception as e:
            logger.error(f"Market history request error: {e}")
            return False, None, f"Request error: {e}"

    async def send_account_info_request(self, request_id: str = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send account info request via process communication"""
        if not self.process_id:
            return False, None, "No active FIX process"

        try:
            request_data = {"request_id": request_id}

            success, data, error = await fix_process_manager.send_request(
                self.process_id, "account_info", request_data, timeout=15
            )

            return success, data, error

        except Exception as e:
            logger.error(f"Account info request error: {e}")
            return False, None, f"Request error: {e}"

    async def send_market_data_request(self, symbol: str, md_req_id: str = None) -> Tuple[bool, Optional[str]]:
        """Send market data request via process communication (feed only)"""
        if not self.process_id:
            return False, "No active FIX process"

        if self.connection_type != "feed":
            return False, "Market data requests only available on feed connection"

        try:
            request_data = {"symbol": symbol, "md_req_id": md_req_id}

            success, data, error = await fix_process_manager.send_request(
                self.process_id, "market_data", request_data, timeout=10
            )

            return success, error

        except Exception as e:
            logger.error(f"Market data request error: {e}")
            return False, f"Request error: {e}"

    def send_heartbeat(self) -> bool:
        """Send heartbeat via process communication (synchronous for compatibility)"""
        if not self.process_id:
            return False

        try:
            # Use asyncio to run the async request
            import asyncio

            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async request
            if loop.is_running():
                # If loop is running, create a task
                task = loop.create_task(self._send_heartbeat_async())
                # Don't wait for completion to avoid blocking
                return True
            else:
                # If loop is not running, run until complete
                success, _, _ = loop.run_until_complete(self._send_heartbeat_async())
                return success

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False

    async def _send_heartbeat_async(self) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Async helper for heartbeat"""
        return await fix_process_manager.send_request(self.process_id, "heartbeat", {}, timeout=5)

    def send_test_request(self) -> bool:
        """Send test request via process communication"""
        if not self.process_id:
            return False

        try:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                task = loop.create_task(self._send_test_request_async())
                return True
            else:
                success, _, _ = loop.run_until_complete(self._send_test_request_async())
                return success

        except Exception as e:
            logger.error(f"Test request error: {e}")
            return False

    async def _send_test_request_async(self) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Async helper for test request"""
        return await fix_process_manager.send_request(self.process_id, "test_request", {}, timeout=5)

    def send_new_order_single(
        self,
        user_id: str,
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
        """Send new order single request via process communication (trade only)"""
        if not self.process_id:
            return False, None, "No active FIX process"

        if self.connection_type != "trade":
            return False, None, "Order requests only available on trade connection"

        try:
            request_data = {
                "client_order_id": client_order_id,
                "symbol": symbol,
                "order_type": order_type,
                "side": side,
                "quantity": quantity,
                "price": price,
                "stop_price": stop_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "time_in_force": time_in_force,
                "expire_time": expire_time.isoformat() if expire_time else None,
                "max_visible_qty": max_visible_qty,
                "comment": comment,
                "tag": tag,
                "magic": magic,
                "immediate_or_cancel": immediate_or_cancel,
                "market_with_slippage": market_with_slippage,
                "slippage": slippage,
            }

            # Use asyncio to run the async request
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Create a future and run in thread pool
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            fix_process_manager.send_request(
                                self.process_id, "new_order_single", request_data, timeout=15
                            )
                        )
                    )
                    success, data, error = future.result(timeout=20)
            else:
                success, data, error = loop.run_until_complete(
                    fix_process_manager.send_request(self.process_id, "new_order_single", request_data, timeout=15)
                )

            return success, data, error

        except Exception as e:
            logger.error(f"New order single request error: {e}")
            return False, None, f"Request error: {e}"

    def send_order_cancel_request(
        self,
        user_id: str,
        client_order_id: str,
        original_client_order_id: str,
        symbol: str,
        side: str,
        order_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send order cancel request via process communication (trade only)"""
        if not self.process_id:
            return False, None, "No active FIX process"

        if self.connection_type != "trade":
            return False, None, "Order cancel requests only available on trade connection"

        try:
            request_data = {
                "client_order_id": client_order_id,
                "original_client_order_id": original_client_order_id,
                "symbol": symbol,
                "side": side,
                "order_id": order_id,
            }

            # Use asyncio to run the async request
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Create a future and run in thread pool
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            fix_process_manager.send_request(self.process_id, "order_cancel", request_data, timeout=15)
                        )
                    )
                    success, data, error = future.result(timeout=20)
            else:
                success, data, error = loop.run_until_complete(
                    fix_process_manager.send_request(self.process_id, "order_cancel", request_data, timeout=15)
                )

            return success, data, error

        except Exception as e:
            logger.error(f"Order cancel request error: {e}")
            return False, None, f"Request error: {e}"

    def send_order_cancel_replace_request(
        self,
        user_id: str,
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
        """Send order cancel/replace request via process communication (trade only)"""
        if not self.process_id:
            return False, None, "No active FIX process"

        if self.connection_type != "trade":
            return False, None, "Order modify requests only available on trade connection"

        try:
            request_data = {
                "client_order_id": client_order_id,
                "original_client_order_id": original_client_order_id,
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "quantity": quantity,
                "price": price,
                "stop_price": stop_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "time_in_force": time_in_force,
                "expire_time": expire_time.isoformat() if expire_time else None,
                "comment": comment,
                "tag": tag,
                "leaves_qty": leaves_qty,
                "order_id": order_id,
            }

            # Use asyncio to run the async request
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Create a future and run in thread pool
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            fix_process_manager.send_request(self.process_id, "order_modify", request_data, timeout=15)
                        )
                    )
                    success, data, error = future.result(timeout=20)
            else:
                success, data, error = loop.run_until_complete(
                    fix_process_manager.send_request(self.process_id, "order_modify", request_data, timeout=15)
                )

            return success, data, error

        except Exception as e:
            logger.error(f"Order modify request error: {e}")
            return False, None, f"Request error: {e}"

    def logout(self) -> bool:
        """Disconnect FIX session by stopping the process"""
        if not self.process_id:
            return True

        try:
            success = fix_process_manager.stop_fix_process(self.process_id)
            self.process_id = None
            self.user_id = None
            return success
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def disconnect(self) -> bool:
        """Alias for logout for compatibility"""
        return self.logout()

    def get_process_status(self) -> Optional[dict]:
        """Get detailed process status"""
        if not self.process_id:
            return None
        return fix_process_manager.get_process_status(self.process_id)

    def cleanup_sessions(self):
        """Cleanup all sessions (for compatibility)"""
        self.logout()

    def parse_security_list_response(self, response_fields: dict) -> dict:
        """Parse security list response fields (for compatibility with old adapter)"""
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
        """Parse security list from raw FIX message (for compatibility)"""
        logger.warning("parse_security_list_from_raw_message called on process adapter - not implemented")
        return {"error": "Raw message parsing not supported in process adapter"}

    def create_fix_message(self, msg_type: str, fields: list) -> str:
        """Create FIX message (for compatibility - not functional in process adapter)"""
        logger.warning("create_fix_message called on process adapter - not implemented")
        return ""

    def parse_fix_response(self, response: str) -> dict:
        """Parse FIX response (for compatibility - not functional in process adapter)"""
        logger.warning("parse_fix_response called on process adapter - not implemented")
        return {}

    def get_connection_params(self) -> Tuple[str, int]:
        """Get connection parameters (for compatibility)"""
        from src.config.settings import config

        if self.connection_type == "feed":
            return config.fix.host, config.fix.feed_port
        else:
            return config.fix.host, config.fix.trade_port

    def create_ssl_socket(self, host: str, port: int, timeout: int):
        """Create SSL socket (for compatibility - not functional in process adapter)"""
        logger.warning("create_ssl_socket called on process adapter - not implemented")
        return None

    def send_logout(self, sock, username: str) -> bool:
        """Send logout (for compatibility - use disconnect() instead)"""
        logger.warning("send_logout called on process adapter - use disconnect() instead")
        return self.disconnect()

    def recv_complete_fix_message(self, timeout: int = 15) -> Optional[str]:
        """Receive complete FIX message (for compatibility - not functional in process adapter)"""
        logger.warning("recv_complete_fix_message called on process adapter - not implemented")
        return None

    @property
    def active_sessions(self):
        """Active sessions property (for compatibility)"""
        return {self.user_id: self} if self.is_connected() else {}

    @active_sessions.setter
    def active_sessions(self, value):
        """Active sessions setter (for compatibility - ignored in process adapter)"""
        pass

    @property
    def session_socket(self):
        """Session socket property (for compatibility - not applicable in process adapter)"""
        return None

    @session_socket.setter
    def session_socket(self, value):
        """Session socket setter (for compatibility - ignored in process adapter)"""
        pass

    @property
    def next_seq_num(self):
        """Next sequence number (for compatibility - managed by QuickFIX internally)"""
        return 1

    @next_seq_num.setter
    def next_seq_num(self, value):
        """Next sequence number setter (for compatibility - ignored in process adapter)"""
        pass

    @property
    def is_logged_in(self):
        """Is logged in property (for compatibility)"""
        return self.is_connected()

    @is_logged_in.setter
    def is_logged_in(self, value):
        """Is logged in setter (for compatibility - ignored in process adapter)"""
        pass

    def set_orderbook_callback(self, callback):
        """Set orderbook callback for real-time market data (feed sessions only)"""
        if self.connection_type == "feed":
            fix_process_manager.set_orderbook_callback(self.process_id, callback)
        else:
            logger.warning("Orderbook callback can only be set on feed sessions")

    async def send_market_data_subscribe(
        self, symbol: str, levels: int = 5, md_req_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Subscribe to market data for a symbol (feed sessions only)"""
        if self.connection_type != "feed":
            return False, "Market data subscription only available on feed sessions"

        if not self.is_connected():
            return False, "Session not connected"

        try:
            return fix_process_manager.send_market_data_subscribe(self.process_id, symbol, levels, md_req_id)
        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
            return False, f"Subscription error: {e}"

    async def send_market_data_unsubscribe(self, symbol: str, md_req_id: str = None) -> Tuple[bool, Optional[str]]:
        """Unsubscribe from market data for a symbol (feed sessions only)"""
        if self.connection_type != "feed":
            return False, "Market data unsubscription only available on feed sessions"

        if not self.is_connected():
            return False, "Session not connected"

        try:
            return fix_process_manager.send_market_data_unsubscribe(self.process_id, symbol, md_req_id)
        except Exception as e:
            logger.error(f"Error unsubscribing from market data: {e}")
            return False, f"Unsubscription error: {e}"
