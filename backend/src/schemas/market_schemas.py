from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class SecurityInfo(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol (e.g., EUR/USD)")
    security_id: Optional[str] = Field(None, description="Security identifier")
    security_id_source: Optional[str] = Field(None, description="Security ID source")
    security_desc: Optional[str] = Field(None, description="Security description")
    currency: Optional[str] = Field(None, description="Base currency")
    settle_currency: Optional[str] = Field(None, description="Settlement currency")
    trade_enabled: Optional[bool] = Field(None, description="Whether trading is enabled")
    description: Optional[str] = Field(None, description="Human readable description")

    # Trading parameters
    contract_multiplier: Optional[str] = Field(None, description="Contract multiplier")
    round_lot: Optional[str] = Field(None, description="Trading lot size")
    min_trade_vol: Optional[str] = Field(None, description="Minimum trading volume")
    max_trade_volume: Optional[str] = Field(None, description="Maximum trading volume")
    trade_vol_step: Optional[str] = Field(None, description="Trading volume step")
    px_precision: Optional[str] = Field(None, description="Price precision (decimal places)")

    # Currency information
    currency_precision: Optional[str] = Field(None, description="Base currency precision")
    currency_sort_order: Optional[str] = Field(None, description="Currency sort order")
    settl_currency_precision: Optional[str] = Field(None, description="Settlement currency precision")
    settl_currency_sort_order: Optional[str] = Field(None, description="Settlement currency sort order")

    # Commission and fees
    commission: Optional[str] = Field(None, description="Commission value")
    limits_commission: Optional[str] = Field(None, description="Limits commission value")
    comm_type: Optional[str] = Field(None, description="Commission type")
    comm_charge_type: Optional[str] = Field(None, description="Commission charge type")
    comm_charge_method: Optional[str] = Field(None, description="Commission charge method")
    min_commission: Optional[str] = Field(None, description="Minimum commission")
    min_commission_currency: Optional[str] = Field(None, description="Minimum commission currency")

    # Swap information
    swap_type: Optional[str] = Field(None, description="Swap type")
    swap_size_short: Optional[str] = Field(None, description="Swap size for short positions")
    swap_size_long: Optional[str] = Field(None, description="Swap size for long positions")
    triple_swap_day: Optional[str] = Field(None, description="Day of week for triple swap")

    # Margin and risk
    profit_calc_mode: Optional[str] = Field(
        None, description="Mode of profit calculation (FOREX, CFD, FUTURES, CFD_INDEX, CFD_LEVERAGE)"
    )
    margin_factor_fractional: Optional[str] = Field(None, description="Margin factor (fractional)")
    margin_calc_mode: Optional[str] = Field(
        None, description="Mode of margin calculation (FOREX, CFD, FUTURES, CFD_INDEX, CFD_LEVERAGE)"
    )
    margin_hedge: Optional[str] = Field(None, description="Factor for calculating margin for hedged orders/positions")
    margin_factor: Optional[str] = Field(None, description="Integer margin factor")
    stop_order_margin_reduction: Optional[str] = Field(None, description="Stop order margin reduction")
    hidden_limit_order_margin_reduction: Optional[str] = Field(None, description="Hidden limit order margin reduction")

    # Display and grouping
    description_len: Optional[str] = Field(None, description="Description length")
    encoded_security_desc_len: Optional[str] = Field(None, description="Encoded security description length")
    encoded_security_desc: Optional[str] = Field(None, description="Encoded security description")
    color_ref: Optional[str] = Field(None, description="Symbol color reference (Win32 COLORREF format)")
    default_slippage: Optional[str] = Field(None, description="Default slippage")
    sort_order: Optional[str] = Field(None, description="Sort order")
    group_sort_order: Optional[str] = Field(None, description="Group sort order")
    status_group_id: Optional[str] = Field(None, description="Status group ID")
    close_only: Optional[bool] = Field(None, description="Close only flag")


class SecurityListResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    request_id: Optional[str] = Field(None, description="Request identifier")
    response_id: Optional[str] = Field(None, description="Server response identifier")
    symbols: List[SecurityInfo] = Field(default_factory=list, description="List of available trading instruments")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if request failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PeriodID(str, Enum):
    S1 = "S1"
    S10 = "S10"
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class PriceType(str, Enum):
    ASK = "A"
    BID = "B"


class GraphType(str, Enum):
    BARS = "B"
    TICKS_BEST = "T"
    TICKS_FULL = "L"


class HistoricalBarsRequest(BaseModel):
    symbol: str = Field(..., description="Currency pair symbol (e.g., EUR/USD)")
    timeframe: PeriodID = Field(..., description="Time period for bars (M1, M5, M15, M30, H1, H4, D1, etc.)")
    count: int = Field(..., ge=1, le=10000, description="Number of bars to retrieve (1-10000)")
    to_time: Optional[datetime] = Field(None, description="End time for data (defaults to now)")
    price_type: PriceType = Field(PriceType.BID, description="Price type (Ask or Bid)")

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip()

    @validator("to_time", pre=True, always=True)
    def set_default_to_time(cls, v):
        if v is None:
            return datetime.utcnow()
        return v


class HistoricalBar(BaseModel):
    timestamp: datetime = Field(..., description="Bar timestamp")
    open_price: float = Field(..., description="Opening price")
    high_price: float = Field(..., description="Highest price")
    low_price: float = Field(..., description="Lowest price")
    close_price: float = Field(..., description="Closing price")
    volume: Optional[int] = Field(None, description="Volume (integer representation)")
    volume_ex: Optional[float] = Field(None, description="Volume (float representation)")


class HistoricalBarsResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    request_id: Optional[str] = Field(None, description="Request identifier")
    symbol: str = Field(..., description="Currency pair symbol")
    timeframe: PeriodID = Field(..., description="Time period for bars")
    price_type: PriceType = Field(..., description="Price type (Ask or Bid)")
    from_time: Optional[datetime] = Field(None, description="Start time of returned data")
    to_time: Optional[datetime] = Field(None, description="End time of returned data")
    bars: List[HistoricalBar] = Field(default_factory=list, description="Historical price bars")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if request failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
