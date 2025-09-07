from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Import centralized enums from the FIX translation system
from ..core.fix_translation_system import ModernOrderSide as OrderSide
from ..core.fix_translation_system import ModernOrderStatus as OrderStatus
from ..core.fix_translation_system import ModernOrderType as OrderType
from ..core.fix_translation_system import ModernRejectionReason as RejectionReason
from ..core.fix_translation_system import ModernTimeInForce as TimeInForce


class OpenOrder(BaseModel):
    """Single open order information"""

    order_id: str = Field(..., description="Unique order identifier", example="12345678")
    client_order_id: str = Field(..., description="Client-provided order ID", example="ORD_1757255704625008")
    symbol: str = Field(..., description="Trading symbol", example="EUR/USD")

    # Order type and direction - using centralized translation system
    order_type: OrderType = Field(
        ...,
        description="Type of order",
        example="limit",
        json_schema_extra={
            "enum": ["market", "limit", "stop", "stop_limit"],
            "enum_descriptions": {
                "market": "Immediate execution at current market price",
                "limit": "Execute at specified price or better",
                "stop": "Trigger at stop price, then market order",
                "stop_limit": "Trigger at stop price, then limit order",
            },
        },
    )
    side: OrderSide = Field(
        ...,
        description="Buy or sell",
        example="buy",
        json_schema_extra={"enum": ["buy", "sell"], "enum_descriptions": {"buy": "Buy order", "sell": "Sell order"}},
    )

    # Order status - using centralized translation system
    status: OrderStatus = Field(
        ...,
        description="Current order status",
        example="pending",
        json_schema_extra={
            "enum": ["pending", "partial", "filled", "cancelled", "rejected", "expired", "cancelling", "modifying"],
            "enum_descriptions": {
                "pending": "Order accepted, waiting for execution",
                "partial": "Order partially executed",
                "filled": "Order completely executed",
                "cancelled": "Order cancelled by user or system",
                "rejected": "Order rejected by broker/market",
                "expired": "Order expired (GTD orders)",
                "cancelling": "Cancel request in progress",
                "modifying": "Modification request in progress",
            },
        },
    )

    # Quantities
    original_quantity: float = Field(..., description="Original order quantity", example=0.01)
    remaining_quantity: float = Field(..., description="Quantity still pending", example=0.01)
    executed_quantity: float = Field(0.0, description="Quantity already executed", example=0.0)

    # Prices
    price: Optional[float] = Field(None, description="Order price (for limit orders)", example=1.0850)
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)", example=1.0800)
    average_price: Optional[float] = Field(None, description="Average execution price", example=1.0852)

    # Order management
    time_in_force: TimeInForce = Field(
        TimeInForce.GTC,
        description="Time in force",
        example="gtc",
        json_schema_extra={
            "enum": ["gtc", "ioc", "gtd"],
            "enum_descriptions": {
                "gtc": "Good Till Cancel - remains active until filled or cancelled",
                "ioc": "Immediate or Cancel - execute immediately or cancel",
                "gtd": "Good Till Date - active until specified expiration time",
            },
        },
    )
    expire_time: Optional[datetime] = Field(None, description="Expiration time for GTD orders")

    # Risk management
    stop_loss: Optional[float] = Field(None, description="Stop loss price", example=1.0500)
    take_profit: Optional[float] = Field(None, description="Take profit price", example=1.1000)

    # Order flags and features
    max_visible_quantity: Optional[float] = Field(
        None, description="Maximum visible quantity (iceberg orders)", example=0.005
    )
    immediate_or_cancel: Optional[bool] = Field(None, description="Immediate or Cancel flag", example=False)
    market_with_slippage: Optional[bool] = Field(None, description="Market with slippage flag", example=False)

    # Financial details
    commission: Optional[float] = Field(None, description="Commission paid", example=0.02)
    swap: Optional[float] = Field(None, description="Swap charges", example=-0.50)
    slippage: Optional[float] = Field(None, description="Slippage amount", example=0.0001)

    # Rejection information (if applicable)
    rejection_reason: Optional[RejectionReason] = Field(
        None,
        description="Reason for rejection if order was rejected",
        example="invalid_quantity",
        json_schema_extra={
            "enum": [
                "market_closed",
                "insufficient_funds",
                "invalid_symbol",
                "invalid_price",
                "invalid_quantity",
                "order_limits_exceeded",
                "duplicate_order",
                "rate_limit_exceeded",
                "timeout",
                "unsupported_order",
                "system_error",
                "other",
            ],
            "enum_descriptions": {
                "market_closed": "Market is currently closed for trading",
                "insufficient_funds": "Not enough balance or margin available",
                "invalid_symbol": "Invalid or unknown trading symbol",
                "invalid_price": "Price is outside acceptable range",
                "invalid_quantity": "Order quantity is invalid",
                "order_limits_exceeded": "Order exceeds position or risk limits",
                "duplicate_order": "Duplicate order detected",
                "rate_limit_exceeded": "Too many requests, please slow down",
                "timeout": "Order processing timed out",
                "unsupported_order": "This order type is not supported",
                "system_error": "Internal system error occurred",
                "other": "Order was rejected by the broker",
            },
        },
    )

    # Metadata
    comment: Optional[str] = Field(None, description="Order comment", example="Swing trade setup")
    tag: Optional[str] = Field(None, description="Order tag", example="STRATEGY_A")
    magic: Optional[int] = Field(None, description="Magic number", example=12345)
    parent_order_id: Optional[str] = Field(None, description="Parent order ID if applicable", example="PARENT_123")

    # Timestamps
    created_at: datetime = Field(..., description="When order was created")
    updated_at: Optional[datetime] = Field(None, description="When order was last updated")


class OpenOrdersResponse(BaseModel):
    """Response for GET /trading/orders/open endpoint"""

    success: bool = Field(..., description="Whether the request was successful", example=True)
    orders: List[OpenOrder] = Field(
        default_factory=list,
        description="List of currently open orders",
        example=[
            {
                "order_id": "12345678",
                "client_order_id": "ORD_1757255704625008",
                "symbol": "EUR/USD",
                "order_type": "limit",
                "side": "buy",
                "status": "pending",
                "original_quantity": 0.01,
                "remaining_quantity": 0.01,
                "executed_quantity": 0.0,
                "price": 1.0850,
                "time_in_force": "gtc",
                "created_at": "2023-12-01T10:30:00Z",
            }
        ],
    )

    # Summary information
    total_orders: int = Field(..., description="Total number of open orders", example=1)
    orders_by_status: dict = Field(
        default_factory=dict, description="Breakdown of orders by status", example={"pending": 1, "partial": 0}
    )
    orders_by_symbol: dict = Field(
        default_factory=dict, description="Breakdown of orders by trading symbol", example={"EUR/USD": 1}
    )

    # Status message
    message: str = Field(..., description="Human-readable summary", example="Retrieved 1 open orders")

    # Request metadata
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds", example=150)


class OpenOrdersRequest(BaseModel):
    """Optional request parameters for filtering open orders"""

    symbol: Optional[str] = Field(None, description="Filter by trading symbol", example="EUR/USD")
    order_type: Optional[OrderType] = Field(None, description="Filter by order type", example="limit")
    side: Optional[OrderSide] = Field(None, description="Filter by order side", example="buy")
    status: Optional[OrderStatus] = Field(None, description="Filter by order status", example="pending")

    # Pagination (for future use)
    limit: Optional[int] = Field(None, description="Maximum number of orders to return", example=100)
    offset: Optional[int] = Field(None, description="Number of orders to skip", example=0)
