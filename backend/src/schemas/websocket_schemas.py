from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ORDERBOOK = "orderbook"
    ERROR = "error"
    SUCCESS = "success"
    HEARTBEAT = "heartbeat"


class OrderBookLevel(BaseModel):
    price: float = Field(..., description="Price level")
    size: float = Field(..., description="Size at this level")
    level: int = Field(..., description="Depth level (1 = best)")


class OrderBookData(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol")
    timestamp: Optional[str] = Field(None, description="Market data timestamp")
    tick_id: Optional[str] = Field(None, description="Tick identifier")
    is_indicative: bool = Field(False, description="Whether the quote is indicative")

    best_bid: Optional[float] = Field(None, description="Best bid price")
    best_ask: Optional[float] = Field(None, description="Best ask price")
    mid_price: Optional[float] = Field(None, description="Mid price")
    spread: Optional[float] = Field(None, description="Bid-ask spread")
    spread_bps: Optional[float] = Field(None, description="Spread in basis points")

    bids: List[OrderBookLevel] = Field(default_factory=list, description="Bid levels")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Ask levels")

    latest_price: Optional[Dict[str, Union[float, str]]] = Field(None, description="Latest price info")
    levels: Optional[Dict[str, int]] = Field(None, description="Level counts")
    metadata: Optional[Dict[str, Union[int, bool]]] = Field(None, description="Additional metadata")


class WSSubscribeRequest(BaseModel):
    type: WSMessageType = Field(WSMessageType.SUBSCRIBE, description="Message type")
    symbol: str = Field(..., description="Currency pair to subscribe to")
    levels: int = Field(5, ge=1, le=5, description="Number of orderbook levels (1-5)")
    md_req_id: Optional[str] = Field(None, description="Market data request ID (auto-generated if not provided)")


class WSUnsubscribeRequest(BaseModel):
    type: WSMessageType = Field(WSMessageType.UNSUBSCRIBE, description="Message type")
    symbol: str = Field(..., description="Currency pair to unsubscribe from")
    md_req_id: Optional[str] = Field(None, description="Market data request ID to cancel")


class WSOrderBookMessage(BaseModel):
    type: WSMessageType = Field(WSMessageType.ORDERBOOK, description="Message type")
    symbol: str = Field(..., description="Currency pair symbol")
    request_id: str = Field(..., description="Market data request ID")
    data: OrderBookData = Field(..., description="Orderbook data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Server timestamp")


class WSErrorMessage(BaseModel):
    type: WSMessageType = Field(WSMessageType.ERROR, description="Message type")
    error: str = Field(..., description="Error message")
    symbol: Optional[str] = Field(None, description="Related symbol if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class WSSuccessMessage(BaseModel):
    type: WSMessageType = Field(WSMessageType.SUCCESS, description="Message type")
    message: str = Field(..., description="Success message")
    symbol: Optional[str] = Field(None, description="Related symbol if applicable")
    md_req_id: Optional[str] = Field(None, description="Market data request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Success timestamp")


class WSHeartbeatMessage(BaseModel):
    type: WSMessageType = Field(WSMessageType.HEARTBEAT, description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Heartbeat timestamp")


WSMessage = Union[
    WSSubscribeRequest, WSUnsubscribeRequest, WSOrderBookMessage, WSErrorMessage, WSSuccessMessage, WSHeartbeatMessage
]
