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



class SecurityListResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    request_id: Optional[str] = Field(None, description="Request identifier")
    response_id: Optional[str] = Field(None, description="Server response identifier")
    symbols: List[SecurityInfo] = Field(default_factory=list, description="List of available trading instruments")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if request failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
