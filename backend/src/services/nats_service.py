import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

import nats
from nats.aio.client import Client as NATS

from ..config.settings import config

logger = logging.getLogger(__name__)


class NATSService:
    def __init__(self):
        self.nc: Optional[NATS] = None
        self.connected = False
        self.subscriptions: Dict[str, Any] = {}

    async def connect(self) -> bool:
        try:
            self.nc = await nats.connect(
                servers=config.nats.servers,
                max_reconnect_attempts=config.nats.max_reconnect_attempts,
                reconnect_time_wait=config.nats.reconnect_time_wait,
                ping_interval=config.nats.ping_interval,
                max_outstanding_pings=config.nats.max_outstanding_pings,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
                closed_cb=self._closed_callback,
            )
            self.connected = True
            logger.info(f"Connected to NATS servers: {config.nats.servers}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        if self.nc and self.connected:
            try:
                for sub in self.subscriptions.values():
                    await sub.unsubscribe()
                self.subscriptions.clear()
                await self.nc.close()
                self.connected = False
                logger.info("Disconnected from NATS")
            except Exception as e:
                logger.error(f"Error disconnecting from NATS: {e}")

    async def publish_orderbook(self, symbol: str, orderbook_data: dict):
        if not self.nc or not self.connected:
            logger.error("NATS not connected, cannot publish orderbook")
            return False

        try:
            subject = config.nats.orderbook_subject.format(symbol=symbol)
            payload = json.dumps(orderbook_data, default=str)
            await self.nc.publish(subject, payload.encode())
            logger.debug(f"Published orderbook for {symbol} to {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish orderbook for {symbol}: {e}")
            return False

    async def subscribe_to_orderbook(
        self, symbol: str, callback: Callable[[dict], None], queue: Optional[str] = None
    ) -> bool:
        if not self.nc or not self.connected:
            logger.error("NATS not connected, cannot subscribe to orderbook")
            return False

        try:
            subject = config.nats.orderbook_subject.format(symbol=symbol)

            async def message_handler(msg):
                try:
                    data = json.loads(msg.data.decode())
                    await asyncio.create_task(callback(data))
                except Exception as e:
                    logger.error(f"Error processing orderbook message for {symbol}: {e}")

            subscription = await self.nc.subscribe(subject, cb=message_handler, queue=queue)
            self.subscriptions[f"orderbook_{symbol}"] = subscription
            logger.info(f"Subscribed to orderbook for {symbol} on {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook for {symbol}: {e}")
            return False

    async def unsubscribe_from_orderbook(self, symbol: str) -> bool:
        sub_key = f"orderbook_{symbol}"
        if sub_key in self.subscriptions:
            try:
                await self.subscriptions[sub_key].unsubscribe()
                del self.subscriptions[sub_key]
                logger.info(f"Unsubscribed from orderbook for {symbol}")
                return True
            except Exception as e:
                logger.error(f"Failed to unsubscribe from orderbook for {symbol}: {e}")
                return False
        return True

    async def publish_session_event(self, user_id: str, event_data: dict):
        if not self.nc or not self.connected:
            logger.error("NATS not connected, cannot publish session event")
            return False

        try:
            subject = config.nats.session_subject.format(user_id=user_id)
            payload = json.dumps(event_data, default=str)
            await self.nc.publish(subject, payload.encode())
            logger.debug(f"Published session event for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish session event for user {user_id}: {e}")
            return False

    async def publish_heartbeat(self, process_id: str, heartbeat_data: dict):
        if not self.nc or not self.connected:
            return False

        try:
            subject = config.nats.heartbeat_subject.format(process_id=process_id)
            payload = json.dumps(heartbeat_data, default=str)
            await self.nc.publish(subject, payload.encode())
            return True
        except Exception as e:
            logger.error(f"Failed to publish heartbeat for process {process_id}: {e}")
            return False

    async def store_account_data(self, user_id: str, account_data: dict) -> bool:
        """Store account data for a user"""
        if not self.nc or not self.connected:
            logger.error("NATS not connected, cannot store account data")
            return False

        try:
            subject = config.nats.account_subject.format(user_id=user_id)
            payload = json.dumps(account_data, default=str)
            await self.nc.publish(subject, payload.encode())
            logger.debug(f"Stored account data for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store account data for user {user_id}: {e}")
            return False

    async def get_account_data(self, user_id: str) -> Optional[dict]:
        """Retrieve account data for a user from in-memory cache"""
        # For now, we'll use a simple in-memory approach since NATS KV might not be available
        # In a production environment, you might want to use NATS KV or Redis
        if not hasattr(self, "_account_cache"):
            self._account_cache = {}

        return self._account_cache.get(user_id)

    async def store_account_data(self, user_id: str, account_data: dict) -> bool:
        """Store account data for a user in in-memory cache"""
        if not hasattr(self, "_account_cache"):
            self._account_cache = {}

        try:
            self._account_cache[user_id] = account_data
            logger.debug(f"Stored account data for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store account data for user {user_id}: {e}")
            return False

    async def _error_callback(self, e):
        logger.error(f"NATS error: {e}")

    async def _disconnected_callback(self):
        logger.warning("NATS disconnected")
        self.connected = False

    async def _reconnected_callback(self):
        logger.info("NATS reconnected")
        self.connected = True

    async def _closed_callback(self):
        logger.info("NATS connection closed")
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected and self.nc is not None


nats_service = NATSService()
