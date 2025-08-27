from typing import Dict, Optional, Tuple
import asyncio
import time
import logging
from src.adapters.fix_adapter import FIXAdapter
from src.config.settings import config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        # Separate sessions for trade and feed operations
        self.trade_sessions: Dict[str, FIXAdapter] = {}
        self.feed_sessions: Dict[str, FIXAdapter] = {}
        self.session_metadata: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def get_or_create_session(self, user_id: str, username: str, password: str, device_id: Optional[str] = None, connection_type: str = "trade") -> FIXAdapter:
        """Get or create a session for specified connection type (trade or feed)"""
        async with self._lock:
            sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
            session_key = f"{user_id}_{connection_type}"
            
            existing_session = sessions_dict.get(user_id)
            
            if existing_session and self._is_session_healthy(session_key):
                self._update_last_activity(session_key)
                logger.info(f"Reusing existing {connection_type} session for user {user_id}")
                return existing_session
            
            if existing_session:
                logger.info(f"Cleaning up unhealthy {connection_type} session for user {user_id}")
                await self._cleanup_session(session_key, connection_type)
            
            logger.info(f"Creating new {connection_type} session for user {user_id}")
            session = await self._create_new_session(user_id, username, password, device_id, connection_type)
            
            # Start heartbeat monitoring
            self._start_heartbeat_monitoring(session_key, connection_type)
            
            return session

    async def _create_new_session(self, user_id: str, username: str, password: str, device_id: Optional[str] = None, connection_type: str = "trade") -> FIXAdapter:
        fix_adapter = FIXAdapter(connection_type=connection_type)
        
        success, error_message = fix_adapter.logon(
            username=username,
            password=password,
            device_id=device_id,
            timeout=10
        )
        
        if not success:
            raise Exception(f"Failed to create FIX {connection_type} session: {error_message}")
        
        # Store in appropriate sessions dictionary
        if connection_type == "trade":
            self.trade_sessions[user_id] = fix_adapter
        else:
            self.feed_sessions[user_id] = fix_adapter
            
        session_key = f"{user_id}_{connection_type}"
        self.session_metadata[session_key] = {
            "created_at": time.time(),
            "last_activity": time.time(),
            "last_heartbeat": None,
            "heartbeat_status": "pending",
            "username": username,
            "connection_type": connection_type
        }
        
        return fix_adapter

    def get_session(self, user_id: str, connection_type: str = "trade") -> Optional[FIXAdapter]:
        """Get existing session for specified connection type"""
        sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
        session_key = f"{user_id}_{connection_type}"
        
        if user_id in sessions_dict and self._is_session_healthy(session_key):
            self._update_last_activity(session_key)
            return sessions_dict[user_id]
        return None

    def get_feed_session(self, user_id: str) -> Optional[FIXAdapter]:
        """Convenience method to get feed session"""
        return self.get_session(user_id, "feed")

    def get_trade_session(self, user_id: str) -> Optional[FIXAdapter]:
        """Convenience method to get trade session"""
        return self.get_session(user_id, "trade")
    
    def get_session_details(self, user_id: str, connection_type: str) -> Optional[dict]:
        """Get detailed session information including heartbeat status"""
        sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
        session_key = f"{user_id}_{connection_type}"
        
        session = sessions_dict.get(user_id)
        metadata = self.session_metadata.get(session_key, {})
        
        if not session:
            return None
            
        current_time = time.time()
        created_at = metadata.get("created_at", current_time)
        last_activity = metadata.get("last_activity", created_at)
        last_heartbeat = metadata.get("last_heartbeat")
        heartbeat_status = metadata.get("heartbeat_status", "unknown")
        
        # Determine heartbeat status based on timing
        if last_heartbeat:
            heartbeat_age = current_time - last_heartbeat
            if heartbeat_age > 90:  # No heartbeat for more than 90 seconds (3 intervals)
                heartbeat_status = "warning"
            elif heartbeat_age > 150:  # No heartbeat for more than 150 seconds (5 intervals)
                heartbeat_status = "failed"
        elif heartbeat_status == "pending" and (current_time - created_at) > 60:
            # Session created more than 60 seconds ago but no heartbeat yet
            heartbeat_status = "warning"
            
        return {
            "connection_type": connection_type,
            "is_active": session.is_session_active(),
            "created_at": created_at,
            "last_activity": last_activity,
            "last_heartbeat": last_heartbeat,
            "session_age_seconds": int(current_time - created_at),
            "heartbeat_status": heartbeat_status
        }

    def _is_session_healthy(self, session_key: str) -> bool:
        if session_key not in self.session_metadata:
            return False
        
        # Extract user_id and connection_type from session_key
        parts = session_key.split("_")
        if len(parts) < 2:
            return False
            
        user_id = parts[0]
        connection_type = parts[1]
        
        # Get session from appropriate dictionary
        sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
        session = sessions_dict.get(user_id)
        
        if not session or not session.is_session_active():
            return False
        
        metadata = self.session_metadata[session_key]
        session_age = time.time() - metadata["last_activity"]
        
        # Session is healthy if less than 1 hour old and adapter reports active
        return session_age < 3600

    def _update_last_activity(self, session_key: str):
        if session_key in self.session_metadata:
            self.session_metadata[session_key]["last_activity"] = time.time()

    async def _cleanup_session(self, session_key: str, connection_type: str = "trade"):
        user_id = session_key.split("_")[0]  # Extract user_id from session_key
        
        # Stop heartbeat monitoring
        if session_key in self._heartbeat_tasks:
            self._heartbeat_tasks[session_key].cancel()
            del self._heartbeat_tasks[session_key]
        
        # Clean up session from appropriate dictionary
        sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
        
        if user_id in sessions_dict:
            try:
                session = sessions_dict[user_id]
                session.logout()  # Proper logout
            except Exception as e:
                logger.warning(f"Error during {connection_type} session cleanup for {user_id}: {e}")
            finally:
                del sessions_dict[user_id]
                
        if session_key in self.session_metadata:
            del self.session_metadata[session_key]
        
        logger.info(f"{connection_type.title()} session cleaned up for user {user_id}")

    def _start_heartbeat_monitoring(self, session_key: str, connection_type: str = "trade"):
        """Start background heartbeat monitoring for a session"""
        user_id = session_key.split("_")[0]  # Extract user_id from session_key
        sessions_dict = self.trade_sessions if connection_type == "trade" else self.feed_sessions
        
        async def heartbeat_monitor():
            while user_id in sessions_dict:
                try:
                    await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                    
                    session = sessions_dict.get(user_id)
                    if session and session.is_session_active():
                        success = session.send_heartbeat()
                        current_time = time.time()
                        
                        # Update heartbeat tracking in metadata
                        if session_key in self.session_metadata:
                            if success:
                                self.session_metadata[session_key]["last_heartbeat"] = current_time
                                self.session_metadata[session_key]["heartbeat_status"] = "healthy"
                                logger.debug(f"Heartbeat sent successfully for {connection_type} session of user {user_id}")
                            else:
                                self.session_metadata[session_key]["heartbeat_status"] = "failed"
                                logger.warning(f"Heartbeat failed for {connection_type} session of user {user_id}")
                                await self._cleanup_session(session_key, connection_type)
                                break
                        
                        if not success:
                            await self._cleanup_session(session_key, connection_type)
                            break
                    else:
                        logger.info(f"{connection_type.title()} session no longer active for user {user_id}")
                        break
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat monitor error for {connection_type} session of user {user_id}: {e}")
                    await self._cleanup_session(session_key, connection_type)
                    break
        
        # Cancel existing heartbeat task if any
        if session_key in self._heartbeat_tasks:
            self._heartbeat_tasks[session_key].cancel()
        
        # Start new heartbeat task
        self._heartbeat_tasks[session_key] = asyncio.create_task(heartbeat_monitor())

    async def cleanup_all_sessions(self):
        async with self._lock:
            # Cleanup all trade sessions
            for user_id in list(self.trade_sessions.keys()):
                session_key = f"{user_id}_trade"
                await self._cleanup_session(session_key, "trade")
            
            # Cleanup all feed sessions
            for user_id in list(self.feed_sessions.keys()):
                session_key = f"{user_id}_feed"
                await self._cleanup_session(session_key, "feed")

session_manager = SessionManager()
