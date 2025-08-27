import re
from typing import Optional

from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    username: str = Field(..., description="FIX account username", min_length=1, max_length=50)
    password: str = Field(..., description="FIX account password", min_length=1, max_length=100)
    device_id: Optional[str] = Field(None, description="Optional device identifier", max_length=50)

    @validator("username")
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username must contain only alphanumeric characters, hyphens, and underscores")
        return v

    @validator("device_id")
    def validate_device_id(cls, v):
        if v is not None and not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Device ID must contain only alphanumeric characters, hyphens, and underscores")
        return v


class LoginResponse(BaseModel):
    success: bool = Field(..., description="Login success status")
    token: Optional[str] = Field(None, description="JWT token if login successful")
    error: Optional[str] = Field(None, description="Error message if login failed")
    message: str = Field(..., description="Response message")
