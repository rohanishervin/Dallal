import logging
from typing import Optional

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
                cached_data = await nats_service.get_account_data(user_id)
                if cached_data:
                    logger.debug(f"Retrieved cached account info for user {user_id}")
                    # Ensure we return just the dict, not a tuple
                    if isinstance(cached_data, tuple):
                        logger.warning(f"Cached data is tuple, extracting dict part: {cached_data}")
                        success, data, error = cached_data
                        return data if success and isinstance(data, dict) else None
                    return cached_data

            # Get fresh data from FIX server
            account_info = await self._fetch_account_info_from_fix(user_id)

            if account_info:
                # Cache the account info
                await nats_service.store_account_data(user_id, account_info)
                logger.info(f"Fetched and cached account info for user {user_id}")
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
                return None

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


# Global instance
account_service = AccountService()
