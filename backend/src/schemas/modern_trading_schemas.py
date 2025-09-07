from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Import centralized enums from the FIX translation system
from ..core.fix_translation_system import ModernOrderSide as OrderSide
from ..core.fix_translation_system import ModernOrderStatus as OrderStatus
from ..core.fix_translation_system import ModernOrderType as OrderType
from ..core.fix_translation_system import ModernRejectionReason as RejectionReason
from ..core.fix_translation_system import ModernTimeInForce as TimeInForce


class ExecutionDetails(BaseModel):
    """Details about order execution"""

    executed_quantity: float = Field(..., description="Quantity that was executed")
    remaining_quantity: float = Field(..., description="Quantity still pending")
    average_price: Optional[float] = Field(None, description="Average execution price")
    last_execution_price: Optional[float] = Field(None, description="Price of last execution")
    last_execution_quantity: Optional[float] = Field(None, description="Quantity of last execution")
    total_executions: int = Field(0, description="Number of separate executions")


class OrderInfo(BaseModel):
    """Complete order information in modern format"""

    order_id: str = Field(..., description="Unique order identifier", example="12345678")
    client_order_id: str = Field(..., description="Client-provided order ID", example="ORD_1757255704625008")
    symbol: str = Field(..., description="Trading symbol", example="EUR/USD")
    order_type: OrderType = Field(
        ...,
        description="Type of order",
        example="market",
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

    # Quantities and prices
    original_quantity: float = Field(..., description="Original order quantity", example=0.01)
    price: Optional[float] = Field(None, description="Order price (for limit orders)", example=1.0850)
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)", example=1.0800)

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

    # Metadata
    comment: Optional[str] = Field(None, description="Order comment", example="Test market order")
    tag: Optional[str] = Field(None, description="Order tag", example="STRATEGY_A")
    magic: Optional[int] = Field(None, description="Magic number", example=12345)

    # Timestamps
    created_at: datetime = Field(..., description="When order was created")
    updated_at: Optional[datetime] = Field(None, description="When order was last updated")


class ModernOrderResponse(BaseModel):
    """Modern order response - no FIX codes visible"""

    success: bool = Field(..., description="Whether the request was successful")
    order_id: Optional[str] = Field(None, description="Unique order identifier")
    client_order_id: str = Field(..., description="Client-provided order ID")

    # Order status and lifecycle
    status: OrderStatus = Field(
        ...,
        description="Current order status",
        example="filled",
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
    status_message: str = Field(
        ...,
        description="Human-readable status explanation",
        example="Market buy order for 0.01 EUR/USD executed at average price 1.08950",
    )

    # Backward compatibility fields for tests
    message: str = Field(..., description="Alias for status_message for backward compatibility")
    execution_report: Optional[Dict[str, Any]] = Field(
        None, description="Backward compatibility execution report structure"
    )

    # Order details
    order_info: Optional[OrderInfo] = Field(None, description="Complete order information")
    execution_details: Optional[ExecutionDetails] = Field(None, description="Execution details if applicable")

    # Error handling
    rejection_reason: Optional[RejectionReason] = Field(
        None,
        description="Reason for rejection if applicable",
        example="market_closed",
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
                "market_closed": "Trading session is closed",
                "insufficient_funds": "Not enough balance/margin",
                "invalid_symbol": "Unknown trading symbol",
                "invalid_price": "Price outside allowed range",
                "invalid_quantity": "Quantity outside allowed range",
                "order_limits_exceeded": "Too many orders or position limits",
                "duplicate_order": "Duplicate order detected",
                "rate_limit_exceeded": "Too many requests",
                "timeout": "Order processing timeout",
                "unsupported_order": "Order type not supported",
                "system_error": "Internal system error",
                "other": "Other broker-specific reason",
            },
        },
    )
    error_message: Optional[str] = Field(None, description="Detailed error message if failed")

    # Financial information
    account_balance: Optional[float] = Field(None, description="Account balance after transaction", example=10000.50)
    commission: Optional[float] = Field(None, description="Commission charged", example=0.02)
    swap: Optional[float] = Field(None, description="Swap amount")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds", example=245)


class OrderManagementResponse(BaseModel):
    """Response for order cancellation/modification"""

    success: bool = Field(..., description="Whether the request was successful", example=True)
    order_id: str = Field(..., description="Order ID that was modified/cancelled", example="12345679")
    client_order_id: str = Field(
        ..., description="Client order ID for the operation", example="CANCEL_1757255704625011"
    )

    operation: str = Field(
        ...,
        description="Type of operation (cancel/modify)",
        example="cancel",
        json_schema_extra={
            "enum": ["cancel", "modify"],
            "enum_descriptions": {"cancel": "Order cancellation request", "modify": "Order modification request"},
        },
    )
    status: OrderStatus = Field(
        ...,
        description="Current order status after operation",
        example="cancelling",
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
    status_message: str = Field(
        ..., description="Human-readable status explanation", example="Order 12345679 cancellation request sent"
    )

    error_message: Optional[str] = Field(None, description="Error message if operation failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PossibleOrderOutcomes(BaseModel):
    """Documentation of possible order outcomes for API users"""

    immediate_outcomes: List[str] = Field(
        default=[
            "pending - Order accepted and waiting for execution",
            "filled - Order executed immediately (market orders)",
            "partial - Order partially executed",
            "rejected - Order rejected by broker/market",
        ]
    )

    eventual_outcomes: List[str] = Field(
        default=[
            "filled - Order eventually executed completely",
            "partial - Order partially executed and expired/cancelled",
            "cancelled - Order cancelled by user or system",
            "expired - Order expired (for GTD orders)",
            "rejected - Order rejected after initial acceptance",
        ]
    )

    rejection_reasons: List[str] = Field(
        default=[
            "market_closed - Trading session is closed",
            "insufficient_funds - Not enough balance/margin",
            "invalid_symbol - Unknown trading symbol",
            "invalid_price - Price outside allowed range",
            "invalid_quantity - Quantity outside allowed range",
            "order_limits_exceeded - Too many orders or position limits",
            "rate_limit_exceeded - Too many requests",
            "timeout - Order processing timeout",
            "system_error - Internal system error",
        ]
    )


# All FIX mappings are now centralized in src.core.fix_translation_system
