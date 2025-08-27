from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

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
    margin_factor_fractional: Optional[str] = Field(None, description="Margin factor")
    stop_order_margin_reduction: Optional[str] = Field(None, description="Stop order margin reduction")
    hidden_limit_order_margin_reduction: Optional[str] = Field(None, description="Hidden limit order margin reduction")
    
    # Display and grouping
    description_len: Optional[str] = Field(None, description="Description length")
    encoded_security_desc_len: Optional[str] = Field(None, description="Encoded security description length")
    encoded_security_desc: Optional[str] = Field(None, description="Encoded security description")
    default_slippage: Optional[str] = Field(None, description="Default slippage")
    sort_order: Optional[str] = Field(None, description="Sort order")
    group_sort_order: Optional[str] = Field(None, description="Group sort order")
    status_group_id: Optional[str] = Field(None, description="Status group ID")
    close_only: Optional[str] = Field(None, description="Close only flag")



class SecurityListResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    request_id: Optional[str] = Field(None, description="Request identifier")
    response_id: Optional[str] = Field(None, description="Server response identifier")
    symbols: List[SecurityInfo] = Field(default_factory=list, description="List of available trading instruments")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if request failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
