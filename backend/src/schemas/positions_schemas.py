from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Import centralized enums from the FIX translation system
from ..core.fix_translation_system import ModernPositionStatus as PositionStatus
from ..core.fix_translation_system import ModernPositionType as PositionType


class OpenPosition(BaseModel):
    """Single open position information"""

    position_id: str = Field(..., description="Unique position identifier", example="POS_12345")
    symbol: str = Field(..., description="Trading symbol", example="EUR/USD")
    currency: str = Field(..., description="Position currency", example="EUR")

    # Position type and status - using centralized translation system
    position_type: PositionType = Field(
        ...,
        description="Type of position",
        example="long",
        json_schema_extra={
            "enum": ["long", "short", "net"],
            "enum_descriptions": {
                "long": "Long position (buy)",
                "short": "Short position (sell)",
                "net": "Net position (combined long/short)",
            },
        },
    )
    status: PositionStatus = Field(
        ...,
        description="Position status",
        example="open",
        json_schema_extra={
            "enum": ["open", "closed", "closing"],
            "enum_descriptions": {
                "open": "Position is currently open",
                "closed": "Position has been closed",
                "closing": "Position is being closed",
            },
        },
    )

    # Position quantities
    net_quantity: float = Field(..., description="Net position quantity", example=0.01)
    long_quantity: float = Field(0.0, description="Long position quantity", example=0.01)
    short_quantity: float = Field(0.0, description="Short position quantity", example=0.0)

    # Position prices
    average_price: float = Field(..., description="Average weighted price of the position", example=1.08950)
    long_average_price: Optional[float] = Field(None, description="Average price of long quantity", example=1.08950)
    short_average_price: Optional[float] = Field(None, description="Average price of short quantity", example=None)
    current_price: Optional[float] = Field(None, description="Current market price", example=1.09150)

    # Financial information
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized profit/loss", example=20.0)
    realized_pnl: Optional[float] = Field(None, description="Realized profit/loss", example=0.0)
    commission: Optional[float] = Field(None, description="Total commission paid", example=0.02)
    commission_currency: Optional[str] = Field(None, description="Commission currency", example="USD")
    agent_commission: Optional[float] = Field(None, description="Agent commission", example=0.01)
    agent_commission_currency: Optional[str] = Field(None, description="Agent commission currency", example="USD")
    swap: Optional[float] = Field(None, description="Swap amount charged for holding position", example=-0.50)

    # Account information
    account_balance: Optional[float] = Field(None, description="Account balance", example=10000.50)
    transaction_amount: Optional[float] = Field(None, description="Transaction amount", example=1089.50)
    transaction_currency: Optional[str] = Field(None, description="Transaction currency", example="USD")

    # Metadata
    report_type: str = Field(
        "response",
        description="Type of position report",
        example="response",
        json_schema_extra={
            "enum": ["login", "response", "rollover", "create", "modify", "cancel", "close"],
            "enum_descriptions": {
                "login": "Position report generated on login",
                "response": "Position report generated as response to request",
                "rollover": "Position report generated after rollover",
                "create": "Position was created",
                "modify": "Position was modified",
                "cancel": "Position was cancelled",
                "close": "Position was closed",
            },
        },
    )

    # Timestamps
    created_at: datetime = Field(..., description="When position was opened")
    updated_at: Optional[datetime] = Field(None, description="When position was last updated")
    clearing_date: Optional[datetime] = Field(None, description="Clearing business date")


class OpenPositionsResponse(BaseModel):
    """Response for GET /trading/positions/open endpoint"""

    success: bool = Field(..., description="Whether the request was successful", example=True)
    positions: List[OpenPosition] = Field(
        default_factory=list,
        description="List of currently open positions",
        example=[
            {
                "position_id": "POS_12345",
                "symbol": "EUR/USD",
                "currency": "EUR",
                "position_type": "long",
                "status": "open",
                "net_quantity": 0.01,
                "long_quantity": 0.01,
                "short_quantity": 0.0,
                "average_price": 1.08950,
                "unrealized_pnl": 20.0,
                "created_at": "2023-12-01T10:30:00Z",
            }
        ],
    )

    # Summary information
    total_positions: int = Field(..., description="Total number of open positions", example=1)
    positions_by_type: dict = Field(
        default_factory=dict, description="Breakdown of positions by type", example={"long": 1, "short": 0, "net": 0}
    )
    positions_by_symbol: dict = Field(
        default_factory=dict, description="Breakdown of positions by trading symbol", example={"EUR/USD": 1}
    )

    # Financial summary
    total_unrealized_pnl: Optional[float] = Field(
        None, description="Total unrealized P&L across all positions", example=20.0
    )
    total_realized_pnl: Optional[float] = Field(None, description="Total realized P&L", example=0.0)
    total_commission: Optional[float] = Field(None, description="Total commission paid", example=0.02)
    total_swap: Optional[float] = Field(None, description="Total swap charges", example=-0.50)

    # Status message
    message: str = Field(..., description="Human-readable summary", example="Retrieved 1 open positions")

    # Request metadata
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    request_result: str = Field(
        "valid_request",
        description="Result of the position request",
        example="valid_request",
        json_schema_extra={
            "enum": ["valid_request", "no_positions", "not_supported", "not_authorized", "unknown"],
            "enum_descriptions": {
                "valid_request": "Request was valid and processed",
                "no_positions": "No positions found matching criteria",
                "not_supported": "Position requests not supported for this account type",
                "not_authorized": "Not authorized to access position data",
                "unknown": "Unknown error occurred",
            },
        },
    )
    request_status: str = Field(
        "completed",
        description="Status of the position request",
        example="completed",
        json_schema_extra={
            "enum": ["completed", "rejected"],
            "enum_descriptions": {"completed": "Request completed successfully", "rejected": "Request was rejected"},
        },
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds", example=200)


class OpenPositionsRequest(BaseModel):
    """Optional request parameters for filtering open positions"""

    symbol: Optional[str] = Field(None, description="Filter by trading symbol", example="EUR/USD")
    position_type: Optional[PositionType] = Field(None, description="Filter by position type", example="long")
    status: Optional[PositionStatus] = Field(None, description="Filter by position status", example="open")

    # Minimum thresholds
    min_quantity: Optional[float] = Field(None, description="Minimum position quantity to include", example=0.001)
    min_pnl: Optional[float] = Field(None, description="Minimum P&L to include", example=-100.0)

    # Pagination (for future use)
    limit: Optional[int] = Field(None, description="Maximum number of positions to return", example=100)
    offset: Optional[int] = Field(None, description="Number of positions to skip", example=0)
