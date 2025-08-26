from typing import Dict, Optional, Tuple
import asyncio
import time
import logging
from src.adapters.fix_adapter import FIXAdapter
from src.config.settings import config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, FIXAdapter] = {}
        self.session_metadata: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def get_or_create_session(self, user_id: str, username: str, password: str, device_id: Optional[str] = None) -> FIXAdapter:
        async with self._lock:
            existing_session = self.active_sessions.get(user_id)
            
            if existing_session and self._is_session_healthy(user_id):
                self._update_last_activity(user_id)
                logger.info(f"Reusing existing session for user {user_id}")
                return existing_session
            
            if existing_session:
                logger.info(f"Cleaning up unhealthy session for user {user_id}")
                await self._cleanup_session(user_id)
            
            logger.info(f"Creating new session for user {user_id}")
            session = await self._create_new_session(user_id, username, password, device_id)
            
            # Start heartbeat monitoring
            self._start_heartbeat_monitoring(user_id)
            
            return session

    async def _create_new_session(self, user_id: str, username: str, password: str, device_id: Optional[str] = None) -> FIXAdapter:
        fix_adapter = FIXAdapter()
        
        success, error_message = fix_adapter.logon(
            username=username,
            password=password,
            device_id=device_id,
            timeout=10
        )
        
        if not success:
            raise Exception(f"Failed to create FIX session: {error_message}")
        
        self.active_sessions[user_id] = fix_adapter
        self.session_metadata[user_id] = {
            "created_at": time.time(),
            "last_activity": time.time(),
            "username": username
        }
        
        return fix_adapter

    def get_session(self, user_id: str) -> Optional[FIXAdapter]:
        if user_id in self.active_sessions and self._is_session_healthy(user_id):
            self._update_last_activity(user_id)
            return self.active_sessions[user_id]
        return None

    def _is_session_healthy(self, user_id: str) -> bool:
        if user_id not in self.session_metadata:
            return False
        
        session = self.active_sessions.get(user_id)
        if not session or not session.is_session_active():
            return False
        
        metadata = self.session_metadata[user_id]
        session_age = time.time() - metadata["last_activity"]
        
        # Session is healthy if less than 1 hour old and adapter reports active
        return session_age < 3600

    def _update_last_activity(self, user_id: str):
        if user_id in self.session_metadata:
            self.session_metadata[user_id]["last_activity"] = time.time()

    async def _cleanup_session(self, user_id: str):
        # Stop heartbeat monitoring
        if user_id in self._heartbeat_tasks:
            self._heartbeat_tasks[user_id].cancel()
            del self._heartbeat_tasks[user_id]
        
        # Clean up session
        if user_id in self.active_sessions:
            try:
                session = self.active_sessions[user_id]
                session.logout()  # Proper logout
            except Exception as e:
                logger.warning(f"Error during session cleanup for {user_id}: {e}")
            finally:
                del self.active_sessions[user_id]
                
        if user_id in self.session_metadata:
            del self.session_metadata[user_id]
        
        logger.info(f"Session cleaned up for user {user_id}")

    def _start_heartbeat_monitoring(self, user_id: str):
        """Start background heartbeat monitoring for a session"""
        async def heartbeat_monitor():
            while user_id in self.active_sessions:
                try:
                    await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                    
                    session = self.active_sessions.get(user_id)
                    if session and session.is_session_active():
                        success = session.send_heartbeat()
                        if not success:
                            logger.warning(f"Heartbeat failed for user {user_id}")
                            await self._cleanup_session(user_id)
                            break
                    else:
                        logger.info(f"Session no longer active for user {user_id}")
                        break
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat monitor error for user {user_id}: {e}")
                    await self._cleanup_session(user_id)
                    break
        
        # Cancel existing heartbeat task if any
        if user_id in self._heartbeat_tasks:
            self._heartbeat_tasks[user_id].cancel()
        
        # Start new heartbeat task
        self._heartbeat_tasks[user_id] = asyncio.create_task(heartbeat_monitor())

    async def cleanup_all_sessions(self):
        async with self._lock:
            for user_id in list(self.active_sessions.keys()):
                await self._cleanup_session(user_id)

session_manager = SessionManager()
