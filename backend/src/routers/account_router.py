import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.middleware.auth_middleware import AuthUser, get_current_user
from src.schemas.account_schemas import AccountBalanceResponse, AccountSummaryResponse
from src.services.account_service import account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/info", response_model=AccountSummaryResponse)
async def get_account_info(current_user: AuthUser = Depends(get_current_user)):
    """
    Get complete account information.

    This endpoint retrieves comprehensive account information including:
    - Account ID, name, and type
    - Balance, equity, margin, and leverage
    - Account status flags (valid, blocked, readonly)
    - Risk management levels (margin call, stop out)
    - Contact information and timestamps
    - Throttling and commission settings

    **Authentication Required**: JWT token in Authorization header
    """
    try:
        user_id = current_user.user_id
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")

        logger.info(f"Getting complete account info for user: {user_id}")

        account_summary = await account_service.get_account_summary(user_id)

        if not account_summary:
            logger.warning(f"No account info found for user: {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account information not found")

        logger.info(f"Successfully retrieved complete account info for user: {user_id}")
        return account_summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve account information"
        )


@router.get("/balance", response_model=AccountBalanceResponse)
async def get_account_balance(current_user: AuthUser = Depends(get_current_user)):
    """
    Get account balance information (balance, equity, margin, leverage only).

    This endpoint retrieves essential financial information including:
    - Balance: Current account balance
    - Equity: Current account equity
    - Margin: Used margin for open positions
    - Leverage: Account leverage setting

    **Authentication Required**: JWT token in Authorization header
    """
    try:
        user_id = current_user.user_id
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")

        logger.info(f"Getting account balance for user: {user_id}")

        balance_info = await account_service.get_account_balance(user_id)

        if not balance_info:
            logger.warning(f"No account balance found for user: {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account balance information not found")

        logger.info(f"Successfully retrieved account balance for user: {user_id}")
        return balance_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account balance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve account balance"
        )
