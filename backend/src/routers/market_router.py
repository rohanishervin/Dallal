from fastapi import APIRouter, Depends, HTTPException

from src.middleware.auth_middleware import AuthUser, get_current_user
from src.schemas.market_schemas import HistoricalBarsRequest, HistoricalBarsResponse, SecurityListResponse
from src.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_current_user)])

market_service = MarketService()


@router.get("/instruments", response_model=SecurityListResponse)
async def get_trading_instruments(current_user: AuthUser = Depends(get_current_user)):
    """Get list of available trading instruments from FIX server"""
    try:
        response = await market_service.get_security_list(user_id=current_user.user_id)

        if not response.success:
            raise HTTPException(status_code=400, detail={"message": response.message, "error": response.error})

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


@router.post("/history", response_model=HistoricalBarsResponse)
async def get_historical_bars(request: HistoricalBarsRequest, current_user: AuthUser = Depends(get_current_user)):
    """Get historical price bars for a specified symbol and time period"""
    try:
        response = await market_service.get_historical_bars(user_id=current_user.user_id, request=request)

        if not response.success:
            raise HTTPException(status_code=400, detail={"message": response.message, "error": response.error})

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})
