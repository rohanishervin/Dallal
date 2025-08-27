from typing import Tuple, Optional
import logging
from src.schemas.market_schemas import SecurityListResponse, SecurityInfo
from src.services.session_manager import session_manager

logger = logging.getLogger(__name__)

class MarketService:
    def __init__(self):
        pass

    async def get_security_list(self, user_id: str, request_id: Optional[str] = None) -> SecurityListResponse:
        try:
            # Get existing FEED session (should already exist from login)
            session = session_manager.get_feed_session(user_id)
            
            if not session:
                return SecurityListResponse(
                    success=False,
                    message="No active FIX feed session found. Please login first.",
                    error="Feed session not available",
                    symbols=[]
                )

            success, response_data, error_message = session.send_security_list_request(request_id)
            
            if success and response_data:
                symbols = []
                
                for symbol_data in response_data.get("symbols", []):
                    symbols.append(SecurityInfo(
                        symbol=symbol_data.get("symbol", ""),
                        security_id=symbol_data.get("security_id"),
                        security_id_source=symbol_data.get("security_id_source"),
                        security_desc=symbol_data.get("security_desc"),
                        currency=symbol_data.get("currency"),
                        settle_currency=symbol_data.get("settle_currency"),
                        trade_enabled=symbol_data.get("trade_enabled"),
                        description=symbol_data.get("description")
                    ))
                
                return SecurityListResponse(
                    success=True,
                    request_id=response_data.get("request_id"),
                    response_id=response_data.get("response_id"),
                    symbols=symbols,
                    message=f"Retrieved {len(symbols)} trading instruments"
                )
            else:
                return SecurityListResponse(
                    success=False,
                    message="Failed to retrieve security list",
                    error=error_message or "Unknown error",
                    symbols=[]
                )

        except Exception as e:
            logger.error(f"Error in get_security_list for user {user_id}: {str(e)}")
            return SecurityListResponse(
                success=False,
                message="Internal error occurred",
                error="Service error",
                symbols=[]
            )
