import asyncio
import json
import logging
import multiprocessing
import os
import queue
import signal
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..services.nats_service import nats_service

logger = logging.getLogger(__name__)


class FIXProcessManager:
    def __init__(self):
        self.processes: Dict[str, multiprocessing.Process] = {}
        self.request_queues: Dict[str, multiprocessing.Queue] = {}
        self.response_queues: Dict[str, multiprocessing.Queue] = {}
        self.process_metadata: Dict[str, dict] = {}
        # Thread-safe queue for NATS publishing
        self.nats_publish_queue = queue.Queue()
        self.nats_publisher_task = None

    async def start_nats_publisher(self):
        """Start the NATS publisher task"""
        if self.nats_publisher_task is None:
            self.nats_publisher_task = asyncio.create_task(self._nats_publisher_loop())
            logger.info("Started NATS publisher task")
        else:
            logger.info("NATS publisher task already running")

    async def stop_nats_publisher(self):
        """Stop the NATS publisher task"""
        if self.nats_publisher_task:
            self.nats_publisher_task.cancel()
            try:
                await self.nats_publisher_task
            except asyncio.CancelledError:
                pass
            self.nats_publisher_task = None
            logger.info("Stopped NATS publisher task")

    async def _nats_publisher_loop(self):
        """Main loop for publishing messages to NATS"""
        logger.info("NATS publisher loop starting...")
        message_count = 0
        while True:
            try:
                # Check for messages to publish (non-blocking)
                try:
                    publish_data = self.nats_publish_queue.get_nowait()
                    symbol = publish_data.get("symbol")
                    orderbook_data = publish_data.get("orderbook_data")
                    message_count += 1

                    if symbol and orderbook_data:
                        await nats_service.publish_orderbook(symbol, orderbook_data)
                        logger.info(f"Published orderbook for {symbol} to NATS (message #{message_count})")
                    else:
                        logger.warning(
                            f"Invalid publish data: symbol={symbol}, has_orderbook_data={bool(orderbook_data)}"
                        )
                except queue.Empty:
                    # No messages to publish, sleep briefly
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error publishing to NATS: {e}")

            except asyncio.CancelledError:
                logger.info("NATS publisher loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in NATS publisher loop: {e}")
                await asyncio.sleep(1)

    def start_fix_process(
        self, user_id: str, connection_type: str, username: str, password: str, device_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Start a separate FIX process for the given user and connection type"""
        try:
            process_id = f"{user_id}_{connection_type}"

            # Clean up existing process if any
            if process_id in self.processes:
                self.stop_fix_process(process_id)

            # Create communication queues
            request_queue = multiprocessing.Queue()
            response_queue = multiprocessing.Queue()

            # Start FIX service process
            from .fix_service_runner import run_fix_service

            process = multiprocessing.Process(
                target=run_fix_service,
                args=(connection_type, username, password, device_id, request_queue, response_queue),
                daemon=True,
            )

            process.start()

            # Store process information
            self.processes[process_id] = process
            self.request_queues[process_id] = request_queue
            self.response_queues[process_id] = response_queue
            self.process_metadata[process_id] = {
                "user_id": user_id,
                "connection_type": connection_type,
                "username": username,
                "started_at": time.time(),
                "last_activity": time.time(),
            }

            # Wait for connection confirmation
            try:
                response = response_queue.get(timeout=30)
                if response.get("type") == "connection_status" and response.get("success"):
                    logger.info(f"FIX {connection_type} process started successfully for user {user_id}")
                    return True, None
                else:
                    error_msg = response.get("error", "Connection failed")
                    logger.error(f"FIX {connection_type} process connection failed: {error_msg}")
                    self.stop_fix_process(process_id)
                    return False, error_msg
            except Exception as e:
                logger.error(f"Timeout waiting for FIX {connection_type} process connection: {e}")
                self.stop_fix_process(process_id)
                return False, "Connection timeout"

        except Exception as e:
            logger.error(f"Failed to start FIX {connection_type} process: {e}")
            return False, f"Process start failed: {e}"

    def stop_fix_process(self, process_id: str) -> bool:
        """Stop a FIX process"""
        try:
            if process_id in self.processes:
                process = self.processes[process_id]

                # Send shutdown signal via queue if possible
                if process_id in self.request_queues:
                    try:
                        self.request_queues[process_id].put(
                            {"type": "shutdown", "request_id": str(uuid.uuid4())}, timeout=1
                        )
                    except Exception:
                        pass

                # Wait for graceful shutdown
                process.join(timeout=5)

                # Force terminate if still running
                if process.is_alive():
                    logger.warning(f"Force terminating FIX process {process_id}")
                    process.terminate()
                    process.join(timeout=2)

                    if process.is_alive():
                        logger.error(f"Killing FIX process {process_id}")
                        process.kill()
                        process.join()

                # Cleanup
                del self.processes[process_id]

                if process_id in self.request_queues:
                    self.request_queues[process_id].close()
                    del self.request_queues[process_id]

                if process_id in self.response_queues:
                    self.response_queues[process_id].close()
                    del self.response_queues[process_id]

                if process_id in self.process_metadata:
                    del self.process_metadata[process_id]

                logger.info(f"FIX process {process_id} stopped")
                return True

        except Exception as e:
            logger.error(f"Error stopping FIX process {process_id}: {e}")
            return False

    async def send_request(
        self, process_id: str, request_type: str, request_data: dict, timeout: int = 30
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send a request to a FIX process and wait for response"""
        try:
            if process_id not in self.processes:
                return False, None, "FIX process not found"

            if not self.processes[process_id].is_alive():
                return False, None, "FIX process not running"

            request_id = str(uuid.uuid4())
            request = {"type": request_type, "request_id": request_id, "data": request_data, "timestamp": time.time()}

            # Send request
            self.request_queues[process_id].put(request, timeout=5)

            # Update last activity
            if process_id in self.process_metadata:
                self.process_metadata[process_id]["last_activity"] = time.time()

            # Wait for response with async polling
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self.response_queues[process_id].get(timeout=1)
                    if response.get("request_id") == request_id:
                        success = response.get("success", False)
                        data = response.get("data")
                        error = response.get("error")
                        return success, data, error
                    else:
                        # Put back response for other requests
                        self.response_queues[process_id].put(response)
                        await asyncio.sleep(0.1)
                except:
                    await asyncio.sleep(0.1)

            return False, None, "Request timeout"

        except Exception as e:
            logger.error(f"Error sending request to FIX process {process_id}: {e}")
            return False, None, f"Request failed: {e}"

    def is_process_healthy(self, process_id: str) -> bool:
        """Check if a FIX process is healthy"""
        if process_id not in self.processes:
            return False

        process = self.processes[process_id]
        if not process.is_alive():
            return False

        # Check if process is responsive (last activity within reasonable time)
        metadata = self.process_metadata.get(process_id, {})
        last_activity = metadata.get("last_activity", 0)
        return time.time() - last_activity < 300  # 5 minutes

    def get_process_status(self, process_id: str) -> Optional[dict]:
        """Get status information for a FIX process"""
        if process_id not in self.processes:
            return None

        process = self.processes[process_id]
        metadata = self.process_metadata.get(process_id, {})

        return {
            "process_id": process_id,
            "is_alive": process.is_alive(),
            "pid": process.pid if process.is_alive() else None,
            "user_id": metadata.get("user_id"),
            "connection_type": metadata.get("connection_type"),
            "started_at": metadata.get("started_at"),
            "last_activity": metadata.get("last_activity"),
            "uptime_seconds": int(time.time() - metadata.get("started_at", time.time())),
        }

    def start_orderbook_monitoring(self, process_id: str):
        """Start monitoring for orderbook updates from a FIX process and publish to NATS"""
        if process_id not in self.process_metadata:
            logger.error(f"Process {process_id} not found for orderbook monitoring")
            return

        logger.info(f"Starting orderbook monitoring for process {process_id}")
        # Start monitoring for orderbook updates from this process
        self._start_orderbook_monitoring(process_id)

    def send_market_data_subscribe(
        self, process_id: str, symbol: str, levels: int = 5, md_req_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Send market data subscription request to FIX process"""
        if process_id not in self.request_queues:
            return False, f"Process {process_id} not found"

        try:
            request = {
                "action": "market_data_subscribe",
                "symbol": symbol,
                "levels": levels,
                "md_req_id": md_req_id,
                "request_id": str(uuid.uuid4()),
            }

            self.request_queues[process_id].put(request)

            # Wait for response with timeout
            try:
                response = self.response_queues[process_id].get(timeout=10)
                if response.get("success"):
                    return True, None
                else:
                    return False, response.get("error", "Subscription failed")
            except:
                return False, "Request timeout"

        except Exception as e:
            logger.error(f"Error sending market data subscribe request: {e}")
            return False, f"Request error: {e}"

    def send_market_data_unsubscribe(
        self, process_id: str, symbol: str, md_req_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Send market data unsubscription request to FIX process"""
        if process_id not in self.request_queues:
            return False, f"Process {process_id} not found"

        try:
            request = {
                "action": "market_data_unsubscribe",
                "symbol": symbol,
                "md_req_id": md_req_id,
                "request_id": str(uuid.uuid4()),
            }

            self.request_queues[process_id].put(request)

            # Wait for response with timeout
            try:
                response = self.response_queues[process_id].get(timeout=5)
                if response.get("success"):
                    return True, None
                else:
                    return False, response.get("error", "Unsubscription failed")
            except:
                return False, "Request timeout"

        except Exception as e:
            logger.error(f"Error sending market data unsubscribe request: {e}")
            return False, f"Request error: {e}"

    def _start_orderbook_monitoring(self, process_id: str):
        """Start monitoring for orderbook updates from a FIX process"""
        import threading

        def monitor_orderbook_updates():
            logger.info(f"Orderbook monitoring thread started for process {process_id}")
            while process_id in self.processes and self.processes[process_id].is_alive():
                try:
                    if process_id not in self.response_queues:
                        logger.warning(f"No response queue for process {process_id}")
                        break

                    # Process all available messages in the queue
                    messages_processed = 0
                    while True:
                        try:
                            # Use a short timeout to check for multiple messages
                            # Give more time for the second message (orderbook data) to arrive
                            timeout = 1.0 if messages_processed == 0 else 0.5
                            response = self.response_queues[process_id].get(timeout=timeout)
                            messages_processed += 1

                            response_type = response.get("type", "unknown")
                            logger.info(
                                f"MONITORING: Received response #{messages_processed} from process {process_id}: type='{response_type}', keys={list(response.keys()) if isinstance(response, dict) else 'not_dict'}"
                            )

                            if response.get("type") == "orderbook_update":
                                # Queue orderbook data for NATS publishing
                                orderbook_data = response.get("data")
                                if orderbook_data:
                                    symbol = orderbook_data.get("symbol")
                                    if symbol:
                                        # Put the data in the queue for the NATS publisher task
                                        try:
                                            self.nats_publish_queue.put(
                                                {"symbol": symbol, "orderbook_data": orderbook_data}, block=False
                                            )
                                            logger.info(f"Queued orderbook data for {symbol} for NATS publishing")
                                        except Exception as e:
                                            logger.error(f"Failed to queue orderbook data for NATS: {e}")
                                    else:
                                        logger.warning("No symbol found in orderbook data")
                                else:
                                    logger.warning("No orderbook data in response")
                            else:
                                # Log other response types for debugging
                                if response_type not in ["unknown"]:
                                    logger.debug(f"Ignoring non-orderbook response: {response_type}")
                                elif isinstance(response, dict) and len(response) > 0:
                                    logger.debug(f"Received response with unknown type. Full response: {response}")

                        except:
                            # No more messages available, break inner loop
                            break

                    # If no messages were processed, continue outer loop
                    if messages_processed == 0:
                        continue

                except Exception as e:
                    logger.error(f"Error in orderbook monitoring for {process_id}: {e}")
                    time.sleep(1)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_orderbook_updates, daemon=True)
        monitor_thread.start()

    def cleanup_all_processes(self):
        """Clean up all FIX processes"""
        for process_id in list(self.processes.keys()):
            self.stop_fix_process(process_id)

    async def send_order_mass_status_request_async(
        self, process_id: str, user_id: str, request_id: str
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send Order Mass Status Request to FIX process (async version)"""
        request_data = {"user_id": user_id, "request_id": request_id}

        return await self.send_request(process_id, "order_mass_status_request", request_data, timeout=30)

    async def send_request_for_positions_async(
        self, process_id: str, user_id: str, request_id: str, account_id: str
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Send Request for Positions to FIX process (async version)"""
        request_data = {"user_id": user_id, "request_id": request_id, "account_id": account_id}

        return await self.send_request(process_id, "request_for_positions", request_data, timeout=30)


# Global instance
fix_process_manager = FIXProcessManager()
