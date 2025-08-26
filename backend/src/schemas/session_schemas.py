from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SessionStatus(BaseModel):
    user_id: str = Field(..., description="User identifier")
    is_active: bool = Field(..., description="Whether session is active")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    session_age_seconds: Optional[int] = Field(None, description="Session age in seconds")
    
class SessionStatusResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    session: Optional[SessionStatus] = Field(None, description="Session status information")
    message: str = Field(..., description="Response message")
