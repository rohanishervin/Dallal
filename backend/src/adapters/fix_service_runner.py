import json
import logging
import multiprocessing
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.adapters.quickfix_feed_adapter import QuickFIXFeedAdapter
from src.adapters.quickfix_trade_adapter import QuickFIXTradeAdapter

# Configure logging for the FIX process
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FIXServiceProcess:
    def __init__(
        self,
        connection_type: str,
        username: str,
        password: str,
        device_id: Optional[str],
        request_queue: multiprocessing.Queue,
        response_queue: multiprocessing.Queue,
    ):
        self.connection_type = connection_type
        self.username = username
        self.password = password
        self.device_id = device_id
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.adapter = None
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down FIX service...")
        self.running = False

    def start(self):
        """Start the FIX service process"""
        try:
            logger.info(f"Starting FIX {self.connection_type} service for user {self.username}")

            # Create appropriate adapter
            if self.connection_type == "trade":
                self.adapter = QuickFIXTradeAdapter()
            else:
                self.adapter = QuickFIXFeedAdapter()

            # Connect to FIX server
            success, error_msg = self.adapter.connect(self.username, self.password, self.device_id, timeout=30)

            # Send connection status back to main process
            self.response_queue.put(
                {"type": "connection_status", "success": success, "error": error_msg, "timestamp": time.time()}
            )

            if not success:
                logger.error(f"Failed to connect FIX {self.connection_type} session: {error_msg}")
                return

            logger.info(f"FIX {self.connection_type} service connected successfully")

            # Start request processing loop
            self._process_requests()

        except Exception as e:
            logger.error(f"FIX service startup error: {e}")
            self.response_queue.put(
                {
                    "type": "connection_status",
                    "success": False,
                    "error": f"Startup error: {e}",
                    "timestamp": time.time(),
                }
            )
        finally:
            self._cleanup()

    def _process_requests(self):
        """Main request processing loop"""
        logger.info(f"FIX {self.connection_type} service ready to process requests")

        while self.running:
            try:
                # Check for requests with timeout
                try:
                    request = self.request_queue.get(timeout=1)
                except:
                    continue

                request_id = request.get("request_id")
                request_type = request.get("type")
                request_data = request.get("data", {})

                logger.info(f"Processing {request_type} request: {request_id}")

                if request_type == "shutdown":
                    logger.info("Received shutdown request")
                    self.running = False
                    break
                elif request_type == "security_list":
                    self._handle_security_list_request(request_id, request_data)
                elif request_type == "market_history":
                    self._handle_market_history_request(request_id, request_data)
                elif request_type == "heartbeat":
                    self._handle_heartbeat_request(request_id)
                elif request_type == "test_request":
                    self._handle_test_request(request_id)
                elif request_type == "market_data":
                    self._handle_market_data_request(request_id, request_data)
                else:
                    self._send_error_response(request_id, f"Unknown request type: {request_type}")

            except Exception as e:
                logger.error(f"Error processing request: {e}")
                if "request_id" in locals():
                    self._send_error_response(request_id, f"Processing error: {e}")

    def _handle_security_list_request(self, request_id: str, request_data: dict):
        """Handle security list request"""
        try:
            if not self.adapter or not self.adapter.is_connected():
                self._send_error_response(request_id, "FIX session not connected")
                return

            req_id = request_data.get("request_id")
            success, data, error = self.adapter.send_security_list_request(req_id)

            self.response_queue.put(
                {
                    "request_id": request_id,
                    "type": "security_list_response",
                    "success": success,
                    "data": data,
                    "error": error,
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            self._send_error_response(request_id, f"Security list error: {e}")

    def _handle_market_history_request(self, request_id: str, request_data: dict):
        """Handle market history request"""
        try:
            if not self.adapter or not self.adapter.is_connected():
                self._send_error_response(request_id, "FIX session not connected")
                return

            symbol = request_data.get("symbol")
            period_id = request_data.get("period_id")
            max_bars = request_data.get("max_bars")
            end_time_str = request_data.get("end_time")
            price_type = request_data.get("price_type", "B")
            graph_type = request_data.get("graph_type", "B")
            req_id = request_data.get("request_id")

            # Parse end_time
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

            success, data, error = self.adapter.send_market_history_request(
                symbol, period_id, max_bars, end_time, price_type, graph_type, req_id
            )

            self.response_queue.put(
                {
                    "request_id": request_id,
                    "type": "market_history_response",
                    "success": success,
                    "data": data,
                    "error": error,
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            self._send_error_response(request_id, f"Market history error: {e}")

    def _handle_heartbeat_request(self, request_id: str):
        """Handle heartbeat request"""
        try:
            if not self.adapter or not self.adapter.is_connected():
                self._send_error_response(request_id, "FIX session not connected")
                return

            success = self.adapter.send_heartbeat()

            self.response_queue.put(
                {"request_id": request_id, "type": "heartbeat_response", "success": success, "timestamp": time.time()}
            )

        except Exception as e:
            self._send_error_response(request_id, f"Heartbeat error: {e}")

    def _handle_test_request(self, request_id: str):
        """Handle test request"""
        try:
            if not self.adapter or not self.adapter.is_connected():
                self._send_error_response(request_id, "FIX session not connected")
                return

            success = self.adapter.send_test_request()

            self.response_queue.put(
                {
                    "request_id": request_id,
                    "type": "test_request_response",
                    "success": success,
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            self._send_error_response(request_id, f"Test request error: {e}")

    def _handle_market_data_request(self, request_id: str, request_data: dict):
        """Handle market data request (feed adapter only)"""
        try:
            if self.connection_type != "feed":
                self._send_error_response(request_id, "Market data requests only available on feed connection")
                return

            if not self.adapter or not self.adapter.is_connected():
                self._send_error_response(request_id, "FIX session not connected")
                return

            symbol = request_data.get("symbol")
            md_req_id = request_data.get("md_req_id")

            success, error = self.adapter.send_market_data_request(symbol, md_req_id)

            self.response_queue.put(
                {
                    "request_id": request_id,
                    "type": "market_data_response",
                    "success": success,
                    "error": error,
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            self._send_error_response(request_id, f"Market data error: {e}")

    def _send_error_response(self, request_id: str, error_msg: str):
        """Send error response"""
        self.response_queue.put(
            {"request_id": request_id, "success": False, "error": error_msg, "timestamp": time.time()}
        )

    def _cleanup(self):
        """Cleanup resources"""
        try:
            if self.adapter:
                logger.info(f"Disconnecting FIX {self.connection_type} adapter...")
                self.adapter.disconnect()
                self.adapter = None
            logger.info(f"FIX {self.connection_type} service cleanup completed")
        except Exception as e:
            logger.error(f"Error during FIX service cleanup: {e}")


def run_fix_service(
    connection_type: str,
    username: str,
    password: str,
    device_id: Optional[str],
    request_queue: multiprocessing.Queue,
    response_queue: multiprocessing.Queue,
):
    """Entry point for FIX service process"""
    try:
        service = FIXServiceProcess(connection_type, username, password, device_id, request_queue, response_queue)
        service.start()
    except Exception as e:
        logger.error(f"FIX service process failed: {e}")
        try:
            response_queue.put(
                {
                    "type": "connection_status",
                    "success": False,
                    "error": f"Process failed: {e}",
                    "timestamp": time.time(),
                }
            )
        except:
            pass
