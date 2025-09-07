from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AccountInfoRequest(BaseModel):
    """Request schema for Account Info Request (U1005)"""

    request_id: Optional[str] = Field(
        None, description="Optional unique ID for the request. If not provided, will be auto-generated."
    )


class AssetInfo(BaseModel):
    """Asset information within account"""

    currency: str = Field(..., description="Currency name of the asset")
    balance: float = Field(..., description="Current balance of the asset")
    locked_amount: Optional[float] = Field(None, description="Locked balance amount of the asset")


class ThrottlingMethodInfo(BaseModel):
    """Throttling method information"""

    method: str = Field(..., description="Throttling method name")
    requests_per_second: int = Field(..., description="Allowed requests per second for this method")


class AccountInfoResponse(BaseModel):
    """Response schema for Account Info (U1006)"""

    # Core account information
    account_id: str = Field(..., description="Account ID")
    account_name: Optional[str] = Field(None, description="Account name")
    currency: str = Field(..., description="Balance currency")
    accounting_type: str = Field(..., description="Account type: 'N' (Net), 'G' (Gross), 'C' (Cash)")

    # Financial information
    balance: float = Field(..., description="Account balance")
    equity: float = Field(..., description="Current account equity")
    margin: float = Field(..., description="Account margin")
    leverage: float = Field(..., description="Account leverage")

    # Account status
    account_valid: Optional[bool] = Field(None, description="Account valid flag")
    account_blocked: Optional[bool] = Field(None, description="Account blocked flag")
    account_readonly: Optional[bool] = Field(None, description="Account read-only flag")
    investor_login: Optional[bool] = Field(None, description="Investor account flag")

    # Risk management
    margin_call_level: Optional[float] = Field(None, description="Margin call level")
    stop_out_level: Optional[float] = Field(None, description="Stop out level")

    # Contact information
    email: Optional[str] = Field(None, description="Registered email address")

    # Timestamps
    registration_date: Optional[datetime] = Field(None, description="Account registration date (UTC)")
    last_modified: Optional[datetime] = Field(None, description="Account last modification time (UTC)")

    # Assets
    assets: Optional[List[AssetInfo]] = Field(None, description="List of account assets")

    # Throttling information
    sessions_per_account: Optional[int] = Field(None, description="Allowed sessions per account")
    requests_per_second: Optional[int] = Field(None, description="Allowed requests per second")
    throttling_methods: Optional[List[ThrottlingMethodInfo]] = Field(None, description="Throttling methods info")

    # Commission and reporting
    report_currency: Optional[str] = Field(None, description="Report currency")
    token_commission_currency: Optional[str] = Field(None, description="Token commission currency")
    token_commission_discount: Optional[float] = Field(None, description="Token commission discount")
    token_commission_enabled: Optional[bool] = Field(None, description="Token commission enabled flag")

    # Comments
    comment: Optional[str] = Field(None, description="Account comment")

    # Request tracking
    request_id: Optional[str] = Field(None, description="Request ID that generated this response")


class AccountSummaryResponse(BaseModel):
    """Simplified account summary response"""

    success: bool = Field(..., description="Request success status")
    account: AccountInfoResponse = Field(..., description="Account information")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")


class AccountBalanceResponse(BaseModel):
    """Account balance information response"""

    success: bool = Field(..., description="Request success status")
    account_id: str = Field(..., description="Account ID")
    balance: float = Field(..., description="Account balance")
    equity: float = Field(..., description="Current account equity")
    margin: float = Field(..., description="Account margin")
    leverage: float = Field(..., description="Account leverage")
    free_margin: float = Field(..., description="Free margin (equity - margin)")
    margin_level: Optional[float] = Field(None, description="Margin level percentage")
    currency: str = Field(..., description="Balance currency")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")


class AccountLeverageResponse(BaseModel):
    """Account leverage information response"""

    success: bool = Field(..., description="Request success status")
    account_id: str = Field(..., description="Account ID")
    leverage: float = Field(..., description="Account leverage")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")


class AccountAssetsResponse(BaseModel):
    """Account assets information response"""

    success: bool = Field(..., description="Request success status")
    account_id: str = Field(..., description="Account ID")
    assets: List[AssetInfo] = Field(..., description="List of account assets")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")


class AccountHealthResponse(BaseModel):
    """Account service health check response"""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Status message")
