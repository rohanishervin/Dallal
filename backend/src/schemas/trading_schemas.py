from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class OrderType(str, Enum):
    MARKET = "1"
    LIMIT = "2"
    STOP = "3"
    STOP_LIMIT = "4"


class OrderSide(str, Enum):
    BUY = "1"
    SELL = "2"


class TimeInForce(str, Enum):
    GOOD_TILL_CANCEL = "1"
    IMMEDIATE_OR_CANCEL = "3"
    GOOD_TILL_DATE = "6"


class OrderStatus(str, Enum):
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    DONE = "3"
    CANCELLED = "4"
    PENDING_CANCEL = "6"
    REJECTED = "8"
    CALCULATED = "B"
    EXPIRED = "C"
    PENDING_REPLACEMENT = "E"
    PENDING_CLOSE = "F"


class ExecType(str, Enum):
    NEW = "0"
    CANCELLED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    REJECTED = "8"
    CALCULATED = "B"
    EXPIRED = "C"
    PENDING_REPLACEMENT = "E"
    TRADE = "F"
    ORDER_STATUS = "I"
    PENDING_CLOSE = "J"


class NewOrderRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol (e.g., 'EUR/USD')")
    order_type: OrderType = Field(..., description="Order type: 1=Market, 2=Limit, 3=Stop, 4=StopLimit")
    side: OrderSide = Field(..., description="Order side: 1=Buy, 2=Sell")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Limit price (required for Limit and StopLimit orders)")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price (required for Stop and StopLimit orders)")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    time_in_force: TimeInForce = Field(TimeInForce.GOOD_TILL_CANCEL, description="Time in force")
    expire_time: Optional[datetime] = Field(None, description="Order expiration time (for GTD orders)")
    max_visible_qty: Optional[float] = Field(None, gt=0, description="Maximum visible quantity for iceberg orders")
    comment: Optional[str] = Field(None, max_length=512, description="Order comment")
    tag: Optional[str] = Field(None, max_length=128, description="Order tag")
    magic: Optional[int] = Field(None, description="Magic number")
    immediate_or_cancel: bool = Field(False, description="Immediate or Cancel flag (Limit orders only)")
    market_with_slippage: bool = Field(False, description="Market with slippage flag (Limit orders only)")
    slippage: Optional[float] = Field(None, ge=0, description="Slippage tolerance")

    @validator("price")
    def validate_price(cls, v, values):
        order_type = values.get("order_type")
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError(f"Price is required for {order_type.name} orders")
        return v

    @validator("stop_price")
    def validate_stop_price(cls, v, values):
        order_type = values.get("order_type")
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and v is None:
            raise ValueError(f"Stop price is required for {order_type.name} orders")
        return v

    @validator("expire_time")
    def validate_expire_time(cls, v, values):
        time_in_force = values.get("time_in_force")
        if time_in_force == TimeInForce.GOOD_TILL_DATE and v is None:
            raise ValueError("Expire time is required for Good Till Date orders")
        return v

    @validator("immediate_or_cancel")
    def validate_immediate_or_cancel(cls, v, values):
        if v:
            order_type = values.get("order_type")
            if order_type not in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                raise ValueError("Immediate or Cancel flag is only valid for Limit and StopLimit orders")
        return v


class ExecutionReport(BaseModel):
    order_id: str = Field(..., description="Server-assigned order ID")
    client_order_id: str = Field(..., description="Client-assigned order ID")
    exec_id: str = Field(..., description="Execution ID")
    order_status: OrderStatus = Field(..., description="Current order status")
    exec_type: ExecType = Field(..., description="Execution type")
    symbol: str = Field(..., description="Currency pair symbol")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    cum_qty: float = Field(..., description="Cumulative executed quantity")
    order_qty: float = Field(..., description="Original order quantity")
    leaves_qty: float = Field(..., description="Remaining quantity")
    avg_price: Optional[float] = Field(None, description="Average execution price")
    price: Optional[float] = Field(None, description="Order price")
    stop_price: Optional[float] = Field(None, description="Stop price")
    last_qty: Optional[float] = Field(None, description="Last execution quantity")
    last_price: Optional[float] = Field(None, description="Last execution price")
    transact_time: Optional[datetime] = Field(None, description="Transaction time")
    order_created: Optional[datetime] = Field(None, description="Order creation time")
    order_modified: Optional[datetime] = Field(None, description="Last modification time")
    time_in_force: Optional[TimeInForce] = Field(None, description="Time in force")
    expire_time: Optional[datetime] = Field(None, description="Order expiration time")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    commission: Optional[float] = Field(None, description="Commission amount")
    swap: Optional[float] = Field(None, description="Swap amount")
    account_balance: Optional[float] = Field(None, description="Account balance after execution")
    text: Optional[str] = Field(None, description="Descriptive text/error message")
    reject_reason: Optional[str] = Field(None, description="Rejection reason code")
    comment: Optional[str] = Field(None, description="Order comment")
    tag: Optional[str] = Field(None, description="Order tag")
    magic: Optional[int] = Field(None, description="Magic number")

    order_status_description: Optional[str] = Field(None, description="Human-readable order status")
    exec_type_description: Optional[str] = Field(None, description="Human-readable execution type")
    order_type_description: Optional[str] = Field(None, description="Human-readable order type")
    side_description: Optional[str] = Field(None, description="Human-readable order side")
    reject_reason_description: Optional[str] = Field(None, description="Human-readable rejection reason")
    time_in_force_description: Optional[str] = Field(None, description="Human-readable time in force")
    human_readable_summary: Optional[str] = Field(None, description="Human-readable summary of the execution report")


class OrderResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    client_order_id: str = Field(..., description="Client-assigned order ID")
    order_id: Optional[str] = Field(None, description="Server-assigned order ID (if successful)")
    execution_report: Optional[ExecutionReport] = Field(None, description="Initial execution report")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class MarketOrderRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol", example="EUR/USD")
    side: OrderSide = Field(
        ...,
        description="Order side: 1=Buy, 2=Sell",
        example="1",
        json_schema_extra={"enum": ["1", "2"], "enum_descriptions": {"1": "Buy order", "2": "Sell order"}},
    )
    quantity: float = Field(..., gt=0, description="Order quantity", example=0.01)
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price", example=1.0500)
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price", example=1.1000)
    comment: Optional[str] = Field(None, max_length=512, description="Order comment", example="Test market order")
    tag: Optional[str] = Field(None, max_length=128, description="Order tag", example="STRATEGY_A")
    magic: Optional[int] = Field(None, description="Magic number for order identification", example=12345)
    slippage: Optional[float] = Field(None, ge=0, description="Slippage tolerance in pips", example=2.0)


class LimitOrderRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol", example="EUR/USD")
    side: OrderSide = Field(
        ...,
        description="Order side: 1=Buy, 2=Sell",
        example="1",
        json_schema_extra={"enum": ["1", "2"], "enum_descriptions": {"1": "Buy order", "2": "Sell order"}},
    )
    quantity: float = Field(..., gt=0, description="Order quantity", example=0.01)
    price: float = Field(..., gt=0, description="Limit price", example=1.0850)
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price", example=1.0500)
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price", example=1.1000)
    time_in_force: TimeInForce = Field(
        TimeInForce.GOOD_TILL_CANCEL,
        description="Time in force",
        example="1",
        json_schema_extra={
            "enum": ["1", "3", "6"],
            "enum_descriptions": {
                "1": "Good Till Cancel (GTC) - remains active until filled or cancelled",
                "3": "Immediate or Cancel (IOC) - execute immediately or cancel",
                "6": "Good Till Date (GTD) - active until specified expiration time",
            },
        },
    )
    expire_time: Optional[datetime] = Field(None, description="Order expiration time (for GTD orders)")
    max_visible_qty: Optional[float] = Field(
        None, gt=0, description="Maximum visible quantity for iceberg orders", example=0.005
    )
    comment: Optional[str] = Field(
        None, max_length=512, description="Order comment", example="Limit buy at support level"
    )
    tag: Optional[str] = Field(None, max_length=128, description="Order tag", example="SUPPORT_BUY")
    magic: Optional[int] = Field(None, description="Magic number for order identification", example=12345)
    immediate_or_cancel: bool = Field(False, description="Immediate or Cancel flag (for limit orders)")
    market_with_slippage: bool = Field(False, description="Market with slippage flag (for limit orders)")

    @validator("expire_time")
    def validate_expire_time(cls, v, values):
        time_in_force = values.get("time_in_force")
        if time_in_force == TimeInForce.GOOD_TILL_DATE and v is None:
            raise ValueError("Expire time is required for Good Till Date orders")
        return v


class StopOrderRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol")
    side: OrderSide = Field(..., description="Order side: 1=Buy, 2=Sell")
    quantity: float = Field(..., gt=0, description="Order quantity")
    stop_price: float = Field(..., gt=0, description="Stop trigger price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    time_in_force: TimeInForce = Field(TimeInForce.GOOD_TILL_CANCEL, description="Time in force")
    expire_time: Optional[datetime] = Field(None, description="Order expiration time (for GTD orders)")
    comment: Optional[str] = Field(None, max_length=512, description="Order comment")
    tag: Optional[str] = Field(None, max_length=128, description="Order tag")
    magic: Optional[int] = Field(None, description="Magic number")

    @validator("expire_time")
    def validate_expire_time(cls, v, values):
        time_in_force = values.get("time_in_force")
        if time_in_force == TimeInForce.GOOD_TILL_DATE and v is None:
            raise ValueError("Expire time is required for Good Till Date orders")
        return v


class StopLimitOrderRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol")
    side: OrderSide = Field(..., description="Order side: 1=Buy, 2=Sell")
    quantity: float = Field(..., gt=0, description="Order quantity")
    stop_price: float = Field(..., gt=0, description="Stop trigger price")
    price: float = Field(..., gt=0, description="Limit price after trigger")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    time_in_force: TimeInForce = Field(TimeInForce.GOOD_TILL_CANCEL, description="Time in force")
    expire_time: Optional[datetime] = Field(None, description="Order expiration time (for GTD orders)")
    max_visible_qty: Optional[float] = Field(None, gt=0, description="Maximum visible quantity")
    comment: Optional[str] = Field(None, max_length=512, description="Order comment")
    tag: Optional[str] = Field(None, max_length=128, description="Order tag")
    magic: Optional[int] = Field(None, description="Magic number")
    immediate_or_cancel: bool = Field(False, description="Immediate or Cancel flag")

    @validator("expire_time")
    def validate_expire_time(cls, v, values):
        time_in_force = values.get("time_in_force")
        if time_in_force == TimeInForce.GOOD_TILL_DATE and v is None:
            raise ValueError("Expire time is required for Good Till Date orders")
        return v


class OrderCancelRequest(BaseModel):
    order_id: str = Field(..., description="Server-assigned order ID to cancel")
    symbol: str = Field(..., description="Currency pair symbol")
    side: OrderSide = Field(..., description="Original order side")
    original_client_order_id: Optional[str] = Field(None, description="Original client order ID")


class OrderModifyRequest(BaseModel):
    order_id: str = Field(..., description="Server-assigned order ID to modify")
    symbol: str = Field(..., description="Currency pair symbol")
    side: OrderSide = Field(..., description="Original order side")
    original_client_order_id: Optional[str] = Field(None, description="Original client order ID")
    new_quantity: Optional[float] = Field(None, gt=0, description="New order quantity")
    new_price: Optional[float] = Field(None, gt=0, description="New order price")
    new_stop_price: Optional[float] = Field(None, gt=0, description="New stop price")
    new_stop_loss: Optional[float] = Field(None, gt=0, description="New stop loss price")
    new_take_profit: Optional[float] = Field(None, gt=0, description="New take profit price")
    new_time_in_force: Optional[TimeInForce] = Field(None, description="New time in force")
    new_expire_time: Optional[datetime] = Field(None, description="New expiration time")
    new_comment: Optional[str] = Field(None, max_length=512, description="New order comment")
    new_tag: Optional[str] = Field(None, max_length=128, description="New order tag")
    leaves_qty: Optional[float] = Field(None, description="Expected remaining quantity for validation")


class OrderManagementResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    client_order_id: str = Field(..., description="Client-assigned order ID")
    order_id: Optional[str] = Field(None, description="Server-assigned order ID")
    execution_report: Optional[ExecutionReport] = Field(None, description="Execution report")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
