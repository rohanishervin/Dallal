import asyncio
import json
import logging
import multiprocessing
import os
import signal
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FIXProcessManager:
    def __init__(self):
        self.processes: Dict[str, multiprocessing.Process] = {}
        self.request_queues: Dict[str, multiprocessing.Queue] = {}
        self.response_queues: Dict[str, multiprocessing.Queue] = {}
        self.process_metadata: Dict[str, dict] = {}

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

    def cleanup_all_processes(self):
        """Clean up all FIX processes"""
        for process_id in list(self.processes.keys()):
            self.stop_fix_process(process_id)


# Global instance
fix_process_manager = FIXProcessManager()
