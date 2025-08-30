import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from src.config.settings import config
from src.schemas.websocket_schemas import (
    OrderBookData,
    OrderBookLevel,
    WSErrorMessage,
    WSHeartbeatMessage,
    WSMessageType,
    WSOrderBookMessage,
    WSSubscribeRequest,
    WSSuccessMessage,
    WSUnsubscribeRequest,
)
from src.services.nats_service import nats_service
from src.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class WebSocketConnection:
    def __init__(self, websocket: WebSocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.subscriptions: Dict[str, str] = {}
        self.last_heartbeat = time.time()
        self.is_active = True

    async def send_message(self, message: dict):
        if self.is_active:
            try:
                await self.websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Failed to send message to {self.user_id}: {e}")
                self.is_active = False

    async def send_error(self, error: str, symbol: Optional[str] = None):
        error_msg = WSErrorMessage(error=error, symbol=symbol)
        await self.send_message(error_msg.dict())

    async def send_success(self, message: str, symbol: Optional[str] = None, md_req_id: Optional[str] = None):
        success_msg = WSSuccessMessage(message=message, symbol=symbol, md_req_id=md_req_id)
        await self.send_message(success_msg.dict())

    async def send_heartbeat(self):
        heartbeat_msg = WSHeartbeatMessage()
        await self.send_message(heartbeat_msg.dict())

    async def send_orderbook(self, symbol: str, request_id: str, orderbook_data: dict):
        try:
            bids = []
            asks = []

            if "order_book" in orderbook_data and orderbook_data["order_book"]:
                ob = orderbook_data["order_book"]

                for bid in ob.get("bids", []):
                    if bid.get("price") is not None and bid.get("size") is not None:
                        bids.append(OrderBookLevel(price=bid["price"], size=bid["size"], level=bid.get("level", 1)))

                for ask in ob.get("asks", []):
                    if ask.get("price") is not None and ask.get("size") is not None:
                        asks.append(OrderBookLevel(price=ask["price"], size=ask["size"], level=ask.get("level", 1)))

            market_data = orderbook_data.get("market_data", {})
            latest_price = orderbook_data.get("latest_price")
            levels = orderbook_data.get("levels")
            metadata = orderbook_data.get("metadata")

            ob_data = OrderBookData(
                symbol=symbol,
                timestamp=orderbook_data.get("timestamp"),
                tick_id=orderbook_data.get("tick_id"),
                is_indicative=orderbook_data.get("is_indicative", False),
                best_bid=market_data.get("best_bid"),
                best_ask=market_data.get("best_ask"),
                mid_price=market_data.get("mid_price"),
                spread=market_data.get("spread"),
                spread_bps=market_data.get("spread_bps"),
                bids=bids,
                asks=asks,
                latest_price=latest_price,
                levels=levels,
                metadata=metadata,
            )

            orderbook_msg = WSOrderBookMessage(symbol=symbol, request_id=request_id, data=ob_data)

            await self.send_message(orderbook_msg.dict())

        except Exception as e:
            logger.error(f"Error sending orderbook data: {e}")
            await self.send_error(f"Failed to process orderbook data: {str(e)}", symbol)


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.symbol_subscriptions: Dict[str, Set[str]] = {}
        self.user_subscriptions: Dict[str, Dict[str, str]] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.nats_subscriptions: Dict[str, any] = {}

    async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, config.jwt.secret, algorithms=[config.jwt.algorithm])
            user_id = payload.get("sub")

            if not user_id:
                await websocket.close(code=1008, reason="Invalid token - no user ID")
                return None

            await websocket.accept()

            if user_id in self.connections:
                old_connection = self.connections[user_id]
                old_connection.is_active = False
                await self._cleanup_user_subscriptions(user_id)

            connection = WebSocketConnection(websocket, user_id)
            self.connections[user_id] = connection
            self.user_subscriptions[user_id] = {}

            logger.info(f"WebSocket connected for user: {user_id}")

            if not self.heartbeat_task or self.heartbeat_task.done():
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return user_id

        except JWTError as e:
            logger.error(f"JWT validation failed: {e}")
            await websocket.close(code=1008, reason="Invalid token")
            return None
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await websocket.close(code=1011, reason="Internal server error")
            return None

    async def disconnect(self, user_id: str):
        if user_id in self.connections:
            connection = self.connections[user_id]
            connection.is_active = False

            await self._cleanup_user_subscriptions(user_id)

            del self.connections[user_id]
            if user_id in self.user_subscriptions:
                del self.user_subscriptions[user_id]

            logger.info(f"WebSocket disconnected for user: {user_id}")

    async def _cleanup_user_subscriptions(self, user_id: str):
        user_subs = self.user_subscriptions.get(user_id, {})

        for symbol, md_req_id in user_subs.items():
            try:
                session = session_manager.get_feed_session(user_id)
                if session:
                    await session.send_market_data_unsubscribe(symbol, md_req_id)
                    logger.info(f"Unsubscribed from {symbol} (req_id: {md_req_id}) for user {user_id}")

                if symbol in self.symbol_subscriptions:
                    self.symbol_subscriptions[symbol].discard(user_id)
                    if not self.symbol_subscriptions[symbol]:
                        del self.symbol_subscriptions[symbol]

            except Exception as e:
                logger.error(f"Error cleaning up subscription for {symbol}: {e}")

    async def subscribe_to_orderbook(
        self, user_id: str, symbol: str, levels: int = 5, md_req_id: Optional[str] = None
    ) -> bool:
        if user_id not in self.connections:
            return False

        connection = self.connections[user_id]

        try:
            session = session_manager.get_feed_session(user_id)
            if not session:
                await connection.send_error("No active FIX feed session found. Please login first.", symbol)
                return False

            if not md_req_id:
                md_req_id = f"OB_{symbol}_{int(time.time() * 1000)}"

            success, error_message = await session.send_market_data_subscribe(symbol, levels, md_req_id)

            if success:
                # Subscribe to NATS if this is the first subscription for this symbol
                if symbol not in self.symbol_subscriptions:
                    self.symbol_subscriptions[symbol] = set()
                    await self._subscribe_to_nats_orderbook(symbol)

                self.symbol_subscriptions[symbol].add(user_id)
                self.user_subscriptions[user_id][symbol] = md_req_id

                await connection.send_success(f"Subscribed to orderbook for {symbol}", symbol, md_req_id)
                logger.info(f"User {user_id} subscribed to {symbol} orderbook (req_id: {md_req_id})")
                return True
            else:
                await connection.send_error(f"Failed to subscribe to {symbol}: {error_message}", symbol)
                return False

        except Exception as e:
            logger.error(f"Error subscribing to orderbook for {symbol}: {e}")
            await connection.send_error(f"Subscription failed: {str(e)}", symbol)
            return False

    async def unsubscribe_from_orderbook(self, user_id: str, symbol: str) -> bool:
        if user_id not in self.connections:
            return False

        connection = self.connections[user_id]

        try:
            user_subs = self.user_subscriptions.get(user_id, {})
            md_req_id = user_subs.get(symbol)

            if not md_req_id:
                await connection.send_error(f"Not subscribed to {symbol}", symbol)
                return False

            session = session_manager.get_feed_session(user_id)
            if session:
                success, error_message = await session.send_market_data_unsubscribe(symbol, md_req_id)

                if success:
                    if symbol in self.symbol_subscriptions:
                        self.symbol_subscriptions[symbol].discard(user_id)
                        # Unsubscribe from NATS if no more users are subscribed to this symbol
                        if not self.symbol_subscriptions[symbol]:
                            await self._unsubscribe_from_nats_orderbook(symbol)
                            del self.symbol_subscriptions[symbol]

                    del self.user_subscriptions[user_id][symbol]

                    await connection.send_success(f"Unsubscribed from orderbook for {symbol}", symbol)
                    logger.info(f"User {user_id} unsubscribed from {symbol} orderbook")
                    return True
                else:
                    await connection.send_error(f"Failed to unsubscribe from {symbol}: {error_message}", symbol)
                    return False
            else:
                await connection.send_error("No active FIX feed session found", symbol)
                return False

        except Exception as e:
            logger.error(f"Error unsubscribing from orderbook for {symbol}: {e}")
            await connection.send_error(f"Unsubscription failed: {str(e)}", symbol)
            return False

    async def broadcast_orderbook_update(self, symbol: str, request_id: str, orderbook_data: dict):
        if symbol not in self.symbol_subscriptions:
            return

        subscribers = list(self.symbol_subscriptions[symbol])

        for user_id in subscribers:
            if user_id in self.connections:
                connection = self.connections[user_id]
                if connection.is_active:
                    await connection.send_orderbook(symbol, request_id, orderbook_data)

    async def handle_message(self, user_id: str, message_data: dict):
        if user_id not in self.connections:
            return

        connection = self.connections[user_id]

        try:
            msg_type = message_data.get("type")

            if msg_type == WSMessageType.SUBSCRIBE:
                subscribe_req = WSSubscribeRequest(**message_data)
                await self.subscribe_to_orderbook(
                    user_id, subscribe_req.symbol, subscribe_req.levels, subscribe_req.md_req_id
                )

            elif msg_type == WSMessageType.UNSUBSCRIBE:
                unsubscribe_req = WSUnsubscribeRequest(**message_data)
                await self.unsubscribe_from_orderbook(user_id, unsubscribe_req.symbol)

            else:
                await connection.send_error(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await connection.send_error(f"Message processing failed: {str(e)}")

    async def _heartbeat_loop(self):
        while self.connections:
            try:
                await asyncio.sleep(30)

                current_time = time.time()
                disconnected_users = []

                for user_id, connection in self.connections.items():
                    if connection.is_active:
                        try:
                            await connection.send_heartbeat()
                            connection.last_heartbeat = current_time
                        except:
                            connection.is_active = False
                            disconnected_users.append(user_id)
                    else:
                        disconnected_users.append(user_id)

                for user_id in disconnected_users:
                    await self.disconnect(user_id)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _subscribe_to_nats_orderbook(self, symbol: str):
        """Subscribe to NATS orderbook stream for a symbol"""
        try:
            # Ensure NATS is connected
            if not nats_service.is_connected:
                await nats_service.connect()

            # Subscribe to orderbook updates for this symbol
            success = await nats_service.subscribe_to_orderbook(
                symbol,
                self._handle_nats_orderbook_update,
                queue="websocket_group",  # Load balancing across multiple WebSocket services
            )

            if success:
                logger.info(f"Subscribed to NATS orderbook stream for {symbol}")
            else:
                logger.error(f"Failed to subscribe to NATS orderbook stream for {symbol}")

        except Exception as e:
            logger.error(f"Error subscribing to NATS for {symbol}: {e}")

    async def _unsubscribe_from_nats_orderbook(self, symbol: str):
        """Unsubscribe from NATS orderbook stream for a symbol"""
        try:
            success = await nats_service.unsubscribe_from_orderbook(symbol)
            if success:
                logger.info(f"Unsubscribed from NATS orderbook stream for {symbol}")
            else:
                logger.warning(f"Failed to unsubscribe from NATS orderbook stream for {symbol}")
        except Exception as e:
            logger.error(f"Error unsubscribing from NATS for {symbol}: {e}")

    async def _handle_nats_orderbook_update(self, orderbook_data: dict):
        """Handle orderbook updates received from NATS"""
        try:
            symbol = orderbook_data.get("symbol")
            request_id = orderbook_data.get("request_id", "")

            if symbol and symbol in self.symbol_subscriptions:
                # Broadcast to all WebSocket clients subscribed to this symbol
                await self.broadcast_orderbook_update(symbol, request_id, orderbook_data)
                logger.debug(f"Broadcasted orderbook update for {symbol} to WebSocket clients")
            else:
                logger.debug(f"No WebSocket subscriptions for symbol {symbol}")

        except Exception as e:
            logger.error(f"Error handling NATS orderbook update: {e}")


websocket_manager = WebSocketManager()
