from fastapi import APIRouter, Depends, HTTPException
from src.schemas.market_schemas import SecurityListResponse
from src.services.market_service import MarketService
from src.middleware.auth_middleware import get_current_user, AuthUser

router = APIRouter(
    prefix="/market", 
    tags=["market"],
    dependencies=[Depends(get_current_user)]
)

market_service = MarketService()

@router.get("/instruments", response_model=SecurityListResponse)
async def get_trading_instruments(
    current_user: AuthUser = Depends(get_current_user)
):
    """Get list of available trading instruments from FIX server"""
    try:
        response = await market_service.get_security_list(
            user_id=current_user.user_id
        )
        
        if not response.success:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": response.message,
                    "error": response.error
                }
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error",
                "error": str(e)
            }
        )
