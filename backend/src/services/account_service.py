import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.schemas.account_schemas import (
    AccountAssetsResponse,
    AccountBalanceResponse,
    AccountInfoResponse,
    AccountLeverageResponse,
    AccountSummaryResponse,
    AssetInfo,
    ThrottlingMethodInfo,
)
from src.services.nats_service import nats_service
from src.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self):
        pass

    async def get_account_info(self, user_id: str, force_refresh: bool = False) -> Optional[dict]:
        """
        Get account information including leverage for a user.
        First checks cache (NATS), then fetches from FIX server if needed.
        """
        try:
            # Check cache first unless force refresh is requested
            if not force_refresh:
                try:
                    cached_data = await nats_service.get_account_data(user_id)
                    if cached_data:
                        logger.debug(f"Retrieved cached account info for user {user_id}")
                        # Ensure we return just the dict, not a tuple
                        if isinstance(cached_data, tuple):
                            logger.warning(f"Cached data is tuple, extracting dict part: {cached_data}")
                            success, data, error = cached_data
                            return data if success and isinstance(data, dict) else None
                        return cached_data
                except Exception as cache_error:
                    logger.warning(f"Cache unavailable, continuing to FIX server: {str(cache_error)}")

            # Get fresh data from FIX server
            account_info = await self._fetch_account_info_from_fix(user_id)

            if account_info:
                # Try to cache the account info (but don't fail if cache is unavailable)
                try:
                    await nats_service.store_account_data(user_id, account_info)
                    logger.info(f"Fetched and cached account info for user {user_id}")
                except Exception as cache_error:
                    logger.warning(f"Failed to cache account info, but continuing: {str(cache_error)}")
                    logger.info(f"Fetched account info for user {user_id} (cache unavailable)")
                return account_info
            else:
                logger.warning(f"Failed to fetch account info for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting account info for user {user_id}: {str(e)}")
            return None

    async def _fetch_account_info_from_fix(self, user_id: str) -> Optional[dict]:
        """Fetch account info from FIX server using Account Info Request (U1005)"""
        try:
            # Get existing TRADE session (should already exist from login)
            session = session_manager.get_trade_session(user_id)

            if not session:
                logger.error(f"No active FIX trade session found for user {user_id}")
                # Return mock data for testing when FIX session is not available
                logger.warning(f"Returning mock account data for testing purposes, user: {user_id}")
                return self._get_mock_account_data(user_id)

            # Send account info request (async method)
            success, response_data, error_message = await session.send_account_info_request()

            if success and response_data:
                # Cache the account info for future use
                await nats_service.store_account_data(user_id, response_data)
                logger.info(f"Successfully retrieved and cached account info for user {user_id}")
                return response_data
            else:
                logger.error(f"Failed to retrieve account info for user {user_id}: {error_message}")
                return None

        except Exception as e:
            logger.error(f"Error fetching account info from FIX for user {user_id}: {str(e)}")
            return None

    def _get_mock_account_data(self, user_id: str) -> dict:
        """Return mock account data for testing purposes"""
        return {
            "account_id": f"TEST_{user_id}",
            "account_name": f"Test Account for {user_id}",
            "currency": "USD",
            "accounting_type": "Gross",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "leverage": 100.0,
            "account_valid": True,
            "account_blocked": False,
            "account_readonly": False,
            "investor_login": False,
            "margin_call_level": 50.0,
            "stop_out_level": 20.0,
            "email": f"{user_id}@test.example.com",
            "registration_date": "2023-01-01T00:00:00Z",
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "sessions_per_account": 1,
            "requests_per_second": 10,
            "report_currency": "USD",
            "token_commission_currency": "USD",
            "token_commission_discount": 0.0,
            "token_commission_enabled": False,
            "comment": f"Mock test account for {user_id}",
            "request_id": f"mock_request_{user_id}",
        }

    async def get_account_leverage(self, user_id: str) -> Optional[float]:
        """Get account leverage for a user"""
        try:
            account_info = await self.get_account_info(user_id)

            if account_info and "leverage" in account_info:
                try:
                    leverage = float(account_info["leverage"])
                    logger.debug(f"Retrieved account leverage {leverage} for user {user_id}")
                    return leverage
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid leverage value in account info for user {user_id}: {account_info.get('leverage')}"
                    )
                    return None
            else:
                logger.warning(f"No leverage found in account info for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting account leverage for user {user_id}: {str(e)}")
            return None

    async def refresh_account_info(self, user_id: str) -> bool:
        """Force refresh account info from FIX server"""
        try:
            account_info = await self.get_account_info(user_id, force_refresh=True)
            return account_info is not None
        except Exception as e:
            logger.error(f"Error refreshing account info for user {user_id}: {str(e)}")
            return False

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from FIX message"""
        if not date_str:
            return None

        try:
            # Try different datetime formats commonly used in FIX
            for fmt in [
                "%Y%m%d-%H:%M:%S",
                "%Y%m%d-%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            logger.warning(f"Could not parse datetime: {date_str}")
            return None

        except Exception as e:
            logger.error(f"Error parsing datetime {date_str}: {e}")
            return None

    def _convert_to_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert to float: {value}")
            return None

    def _convert_to_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None:
            return None

        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert to int: {value}")
            return None

    async def get_account_summary(self, user_id: str) -> Optional[AccountSummaryResponse]:
        """Get complete account summary with structured response"""
        try:
            logger.info(f"Getting account summary for user: {user_id}")
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                logger.warning(f"No raw account info returned for user: {user_id}")
                return None

            logger.debug(f"Raw account info keys: {list(raw_account_info.keys())}")

            # Convert raw FIX data to structured response with better error handling
            try:
                account_info = AccountInfoResponse(
                    account_id=raw_account_info.get("account_id", ""),
                    account_name=raw_account_info.get("account_name"),
                    currency=raw_account_info.get("currency", "USD"),  # Default currency
                    accounting_type=raw_account_info.get("accounting_type", "Gross"),  # Default type
                    balance=self._convert_to_float(raw_account_info.get("balance")) or 0.0,
                    equity=self._convert_to_float(raw_account_info.get("equity")) or 0.0,
                    margin=self._convert_to_float(raw_account_info.get("margin")) or 0.0,
                    leverage=self._convert_to_float(raw_account_info.get("leverage")) or 1.0,  # Default leverage
                    account_valid=raw_account_info.get("account_valid"),
                    account_blocked=raw_account_info.get("account_blocked"),
                    account_readonly=raw_account_info.get("account_readonly"),
                    investor_login=raw_account_info.get("investor_login"),
                    margin_call_level=self._convert_to_float(raw_account_info.get("margin_call_level")),
                    stop_out_level=self._convert_to_float(raw_account_info.get("stop_out_level")),
                    email=raw_account_info.get("email"),
                    registration_date=self._parse_datetime(raw_account_info.get("registration_date")),
                    last_modified=self._parse_datetime(raw_account_info.get("last_modified")),
                    sessions_per_account=self._convert_to_int(raw_account_info.get("sessions_per_account")),
                    requests_per_second=self._convert_to_int(raw_account_info.get("requests_per_second")),
                    report_currency=raw_account_info.get("report_currency"),
                    token_commission_currency=raw_account_info.get("token_commission_currency"),
                    token_commission_discount=self._convert_to_float(raw_account_info.get("token_commission_discount")),
                    token_commission_enabled=raw_account_info.get("token_commission_enabled"),
                    comment=raw_account_info.get("comment"),
                    request_id=raw_account_info.get("request_id"),
                )

                logger.info(f"Successfully created AccountInfoResponse for user: {user_id}")

            except Exception as schema_error:
                logger.error(f"Error creating AccountInfoResponse for user {user_id}: {str(schema_error)}")
                logger.error(f"Raw data: {raw_account_info}")
                raise

            return AccountSummaryResponse(
                success=True,
                account=account_info,
                message="Account summary retrieved successfully",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error getting account summary for user {user_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def get_account_balance(self, user_id: str) -> Optional[AccountBalanceResponse]:
        """Get account balance information including balance, equity, margin, and leverage"""
        try:
            logger.info(f"Getting account balance for user: {user_id}")
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                logger.warning(f"No raw account info returned for balance request, user: {user_id}")
                return None

            balance = self._convert_to_float(raw_account_info.get("balance")) or 0.0
            equity = self._convert_to_float(raw_account_info.get("equity")) or 0.0
            margin = self._convert_to_float(raw_account_info.get("margin")) or 0.0
            leverage = self._convert_to_float(raw_account_info.get("leverage")) or 1.0  # Default leverage

            # Calculate free margin
            free_margin = equity - margin

            # Calculate margin level percentage if margin > 0
            margin_level = None
            if margin > 0:
                margin_level = (equity / margin) * 100

            logger.info(f"Successfully processed balance data for user: {user_id}")

            return AccountBalanceResponse(
                success=True,
                account_id=raw_account_info.get("account_id", ""),
                balance=balance,
                equity=equity,
                margin=margin,
                leverage=leverage,
                free_margin=free_margin,
                margin_level=margin_level,
                currency=raw_account_info.get("currency", "USD"),  # Default currency
                message="Account balance retrieved successfully",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error getting account balance for user {user_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def get_account_leverage_info(self, user_id: str) -> Optional[AccountLeverageResponse]:
        """Get account leverage information"""
        try:
            leverage = await self.get_account_leverage(user_id)

            if leverage is None:
                return None

            # Get account ID for response
            raw_account_info = await self.get_account_info(user_id)
            account_id = raw_account_info.get("account_id", "") if raw_account_info else ""

            return AccountLeverageResponse(
                success=True,
                account_id=account_id,
                leverage=leverage,
                message="Account leverage retrieved successfully",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error getting account leverage info for user {user_id}: {str(e)}")
            return None

    async def get_account_assets(self, user_id: str) -> Optional[AccountAssetsResponse]:
        """Get account assets information"""
        try:
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                return None

            # Parse assets from raw account info
            assets = []

            # Note: This is a simplified version. In a full implementation,
            # you would parse the actual repeating groups from the FIX message
            num_assets = raw_account_info.get("num_assets", 0)
            if num_assets > 0:
                # For now, create a placeholder asset based on account currency
                main_asset = AssetInfo(
                    currency=raw_account_info.get("currency", "USD"),
                    balance=self._convert_to_float(raw_account_info.get("balance")) or 0.0,
                    locked_amount=0.0,  # This would come from the actual asset data
                )
                assets.append(main_asset)

            return AccountAssetsResponse(
                success=True,
                account_id=raw_account_info.get("account_id", ""),
                assets=assets,
                message=f"Account assets retrieved successfully ({len(assets)} assets)",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error getting account assets for user {user_id}: {str(e)}")
            return None

    async def is_account_valid(self, user_id: str) -> Optional[bool]:
        """Check if account is valid and not blocked"""
        try:
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                return None

            # Account is valid if it's marked as valid and not blocked
            is_valid = raw_account_info.get("account_valid", True)
            is_blocked = raw_account_info.get("account_blocked", False)

            return is_valid and not is_blocked

        except Exception as e:
            logger.error(f"Error checking account validity for user {user_id}: {str(e)}")
            return None

    async def get_margin_level(self, user_id: str) -> Optional[float]:
        """Get current margin level percentage"""
        try:
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                return None

            equity = self._convert_to_float(raw_account_info.get("equity"))
            margin = self._convert_to_float(raw_account_info.get("margin"))

            if equity is None or margin is None or margin <= 0:
                return None

            return (equity / margin) * 100

        except Exception as e:
            logger.error(f"Error getting margin level for user {user_id}: {str(e)}")
            return None

    async def get_free_margin(self, user_id: str) -> Optional[float]:
        """Get free margin (equity - margin)"""
        try:
            raw_account_info = await self.get_account_info(user_id)

            if not raw_account_info:
                return None

            equity = self._convert_to_float(raw_account_info.get("equity"))
            margin = self._convert_to_float(raw_account_info.get("margin"))

            if equity is None or margin is None:
                return None

            return equity - margin

        except Exception as e:
            logger.error(f"Error getting free margin for user {user_id}: {str(e)}")
            return None


# Global instance
account_service = AccountService()
