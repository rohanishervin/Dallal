from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class IndividualSessionStatus(BaseModel):
    connection_type: str = Field(..., description="Connection type (trade or feed)")
    is_active: bool = Field(..., description="Whether this specific session is active")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat sent/received")
    session_age_seconds: Optional[int] = Field(None, description="Session age in seconds")
    heartbeat_status: str = Field(..., description="Heartbeat status (healthy, warning, failed)")

class SessionStatus(BaseModel):
    user_id: str = Field(..., description="User identifier")
    overall_active: bool = Field(..., description="Whether any session is active")
    trade_session: Optional[IndividualSessionStatus] = Field(None, description="Trade session details")
    feed_session: Optional[IndividualSessionStatus] = Field(None, description="Feed session details")
    
class SessionStatusResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    session: Optional[SessionStatus] = Field(None, description="Session status information")
    message: str = Field(..., description="Response message")
