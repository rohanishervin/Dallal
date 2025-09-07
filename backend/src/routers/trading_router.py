import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ..middleware.auth_middleware import AuthUser, get_current_user
from ..schemas.modern_trading_schemas import ModernOrderResponse, OrderManagementResponse, PossibleOrderOutcomes
from ..schemas.orders_schemas import OpenOrdersRequest, OpenOrdersResponse
from ..schemas.positions_schemas import OpenPositionsRequest, OpenPositionsResponse
from ..schemas.trading_schemas import (
    LimitOrderRequest,
    MarketOrderRequest,
    NewOrderRequest,
    OrderCancelRequest,
    OrderModifyRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
)
from ..services.orders_service import OrdersService
from ..services.positions_service import PositionsService
from ..services.session_manager import session_manager
from ..services.trading_service import TradingService

logger = logging.getLogger(__name__)
security = HTTPBearer()
router = APIRouter(prefix="/trading", tags=["trading"])


def get_trading_service(current_user: AuthUser = Depends(get_current_user)) -> TradingService:
    user_id = current_user.user_id

    trade_adapter = session_manager.get_trade_session(user_id)
    if not trade_adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Trade session not available. Please login first."
        )

    return TradingService(trade_adapter)


def get_orders_service(current_user: AuthUser = Depends(get_current_user)) -> OrdersService:
    user_id = current_user.user_id

    trade_adapter = session_manager.get_trade_session(user_id)
    if not trade_adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Trade session not available. Please login first."
        )

    return OrdersService(trade_adapter)


def get_positions_service(current_user: AuthUser = Depends(get_current_user)) -> PositionsService:
    user_id = current_user.user_id

    trade_adapter = session_manager.get_trade_session(user_id)
    if not trade_adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Trade session not available. Please login first."
        )

    return PositionsService(trade_adapter)


@router.post("/orders/market", response_model=ModernOrderResponse, summary="Place Market Order")
async def place_market_order(
    request: MarketOrderRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Place a market order for immediate execution at the current market price.

    **Market orders:**
    - Execute immediately at the best available price
    - No price specification required
    - Suitable for quick entry/exit when price is less important than execution speed

    **Parameters:**
    - **symbol**: Currency pair (e.g., "EUR/USD", "GBP/JPY")
    - **side**: "1" for Buy, "2" for Sell
    - **quantity**: Order size (must be positive)
    - **stop_loss**: Optional stop loss price
    - **take_profit**: Optional take profit price
    - **comment**: Optional order comment (max 512 characters)
    - **tag**: Optional order tag (max 128 characters)
    - **magic**: Optional magic number for order identification
    - **slippage**: Optional slippage tolerance
    """
    try:
        user_id = current_user.user_id
        logger.info(f"Market order request from user {user_id}: {request.symbol} {request.side} {request.quantity}")

        response = trading_service.place_market_order(request, user_id)

        if response.success:
            logger.info(f"Market order placed successfully: {response.client_order_id}")
        else:
            logger.warning(f"Market order failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Market order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process market order: {str(e)}"
        )


@router.post("/orders/limit", response_model=ModernOrderResponse, summary="Place Limit Order")
async def place_limit_order(
    request: LimitOrderRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Place a limit order to execute at a specified price or better.

    **Limit orders:**
    - Execute only at the specified price or better
    - Remain pending until price is reached or order expires
    - Suitable for precise entry/exit prices

    **Parameters:**
    - **symbol**: Currency pair (e.g., "EUR/USD", "GBP/JPY")
    - **side**: "1" for Buy, "2" for Sell
    - **quantity**: Order size (must be positive)
    - **price**: Limit price (required)
    - **stop_loss**: Optional stop loss price
    - **take_profit**: Optional take profit price
    - **time_in_force**: "1" = GTC (default), "3" = IOC, "6" = GTD
    - **expire_time**: Required for GTD orders
    - **max_visible_qty**: Optional iceberg order size
    - **immediate_or_cancel**: IOC flag for limit orders
    - **market_with_slippage**: Market with slippage flag
    """
    try:
        user_id = current_user.user_id
        logger.info(
            f"Limit order request from user {user_id}: {request.symbol} {request.side} {request.quantity} @ {request.price}"
        )

        response = trading_service.place_limit_order(request, user_id)

        if response.success:
            logger.info(f"Limit order placed successfully: {response.client_order_id}")
        else:
            logger.warning(f"Limit order failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Limit order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process limit order: {str(e)}"
        )


@router.post("/orders/stop", response_model=ModernOrderResponse, summary="Place Stop Order")
async def place_stop_order(
    request: StopOrderRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Place a stop order that becomes a market order when the stop price is reached.

    **Stop orders:**
    - Trigger when market reaches the stop price
    - Become market orders after trigger
    - Used for stop losses or breakout strategies

    **Parameters:**
    - **symbol**: Currency pair (e.g., "EUR/USD", "GBP/JPY")
    - **side**: "1" for Buy, "2" for Sell
    - **quantity**: Order size (must be positive)
    - **stop_price**: Stop trigger price (required)
    - **stop_loss**: Optional stop loss price
    - **take_profit**: Optional take profit price
    - **time_in_force**: "1" = GTC (default), "6" = GTD
    - **expire_time**: Required for GTD orders
    """
    try:
        user_id = current_user.user_id
        logger.info(
            f"Stop order request from user {user_id}: {request.symbol} {request.side} {request.quantity} stop @ {request.stop_price}"
        )

        response = trading_service.place_stop_order(request, user_id)

        if response.success:
            logger.info(f"Stop order placed successfully: {response.client_order_id}")
        else:
            logger.warning(f"Stop order failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Stop order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process stop order: {str(e)}"
        )


@router.post("/orders/stop-limit", response_model=ModernOrderResponse, summary="Place Stop-Limit Order")
async def place_stop_limit_order(
    request: StopLimitOrderRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Place a stop-limit order that becomes a limit order when the stop price is reached.

    **Stop-limit orders:**
    - Trigger when market reaches the stop price
    - Become limit orders at the specified limit price after trigger
    - Provide price protection after stop trigger

    **Parameters:**
    - **symbol**: Currency pair (e.g., "EUR/USD", "GBP/JPY")
    - **side**: "1" for Buy, "2" for Sell
    - **quantity**: Order size (must be positive)
    - **stop_price**: Stop trigger price (required)
    - **price**: Limit price after trigger (required)
    - **stop_loss**: Optional stop loss price
    - **take_profit**: Optional take profit price
    - **time_in_force**: "1" = GTC (default), "3" = IOC, "6" = GTD
    - **expire_time**: Required for GTD orders
    - **max_visible_qty**: Optional iceberg order size
    - **immediate_or_cancel**: IOC flag for stop-limit orders
    """
    try:
        user_id = current_user.user_id
        logger.info(
            f"Stop-limit order request from user {user_id}: {request.symbol} {request.side} {request.quantity} stop @ {request.stop_price}, limit @ {request.price}"
        )

        response = trading_service.place_stop_limit_order(request, user_id)

        if response.success:
            logger.info(f"Stop-limit order placed successfully: {response.client_order_id}")
        else:
            logger.warning(f"Stop-limit order failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Stop-limit order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process stop-limit order: {str(e)}"
        )


@router.post("/orders", response_model=ModernOrderResponse, summary="Place Order (Generic)")
async def place_order(
    request: NewOrderRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Generic endpoint to place any type of order based on the order_type field.

    **Order Types:**
    - **"1"**: Market Order - immediate execution
    - **"2"**: Limit Order - execute at specified price or better
    - **"3"**: Stop Order - trigger at stop price, then market order
    - **"4"**: Stop-Limit Order - trigger at stop price, then limit order

    **Common Parameters:**
    - **symbol**: Currency pair (e.g., "EUR/USD", "GBP/JPY")
    - **order_type**: "1", "2", "3", or "4"
    - **side**: "1" for Buy, "2" for Sell
    - **quantity**: Order size (must be positive)
    - **price**: Required for Limit and Stop-Limit orders
    - **stop_price**: Required for Stop and Stop-Limit orders

    Use specific endpoints (/market, /limit, /stop, /stop-limit) for better validation.
    """
    try:
        user_id = current_user.user_id
        logger.info(
            f"Generic order request from user {user_id}: {request.order_type} {request.symbol} {request.side} {request.quantity}"
        )

        response = trading_service.place_order(request, user_id)

        if response.success:
            logger.info(f"Order placed successfully: {response.client_order_id}")
        else:
            logger.warning(f"Order failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Generic order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process order: {str(e)}"
        )


@router.delete("/orders/{order_id}", response_model=OrderManagementResponse, summary="Cancel Order")
async def cancel_order(
    order_id: str,
    symbol: str,
    side: str,
    original_client_order_id: str = None,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Cancel a pending order.

    **Parameters:**
    - **order_id**: Server-assigned order ID to cancel
    - **symbol**: Currency pair of the original order
    - **side**: Side of the original order ("1" for Buy, "2" for Sell)
    - **original_client_order_id**: Optional original client order ID

    **Note:** Only pending orders can be cancelled. Filled or rejected orders cannot be cancelled.
    """
    try:
        user_id = current_user.user_id
        logger.info(f"Cancel order request from user {user_id}: {order_id}")

        request = OrderCancelRequest(
            order_id=order_id, symbol=symbol, side=side, original_client_order_id=original_client_order_id
        )

        response = trading_service.cancel_order(request, user_id)

        if response.success:
            logger.info(f"Order cancel request sent: {order_id}")
        else:
            logger.warning(f"Order cancel failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Cancel order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to cancel order: {str(e)}"
        )


@router.put("/orders/{order_id}", response_model=OrderManagementResponse, summary="Modify Order")
async def modify_order(
    order_id: str,
    request: OrderModifyRequest,
    current_user: AuthUser = Depends(get_current_user),
    trading_service: TradingService = Depends(get_trading_service),
):
    """
    Modify a pending order.

    **Modifiable Fields:**
    - **new_quantity**: New order quantity
    - **new_price**: New order price (for limit orders)
    - **new_stop_price**: New stop price (for stop orders)
    - **new_stop_loss**: New stop loss price
    - **new_take_profit**: New take profit price
    - **new_time_in_force**: New time in force
    - **new_expire_time**: New expiration time (for GTD orders)
    - **new_comment**: New order comment
    - **new_tag**: New order tag
    - **leaves_qty**: Expected remaining quantity for validation

    **Note:**
    - At least one field must be modified
    - Only pending orders can be modified
    - Some modifications may be rejected by the server
    """
    try:
        user_id = current_user.user_id
        logger.info(f"Modify order request from user {user_id}: {order_id}")

        # Set the order_id in the request
        request.order_id = order_id

        response = trading_service.modify_order(request, user_id)

        if response.success:
            logger.info(f"Order modify request sent: {order_id}")
        else:
            logger.warning(f"Order modify failed: {response.error}")

        return response

    except Exception as e:
        logger.error(f"Modify order endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to modify order: {str(e)}"
        )


@router.get("/possible-outcomes", response_model=PossibleOrderOutcomes, summary="Get Possible Order Outcomes")
async def get_possible_outcomes():
    """
    Get documentation of possible order outcomes and statuses.

    This endpoint helps API users understand what to expect when placing orders:
    - Immediate outcomes when order is first placed
    - Eventual outcomes as order lifecycle progresses
    - Possible rejection reasons and their meanings

    **No authentication required** - this is documentation only.
    """
    return TradingService.get_possible_order_outcomes()


@router.get("/health", summary="Trading Service Health Check")
async def health_check():
    """
    Check if the trading service is operational.
    """
    return {"status": "healthy", "service": "trading", "message": "Trading service is operational"}


@router.get("/orders/open", response_model=OpenOrdersResponse, summary="Get Open Orders")
async def get_open_orders(
    current_user: AuthUser = Depends(get_current_user),
    orders_service: OrdersService = Depends(get_orders_service),
):
    """
    Get all currently open/pending orders.

    This endpoint retrieves all orders that are currently active in the trading system.
    Orders are retrieved using the FIX Order Mass Status Request (AF) and translated
    into modern, user-friendly format using the centralized translation system.

    **Order Statuses:**
    - **pending**: Order accepted, waiting for execution
    - **partial**: Order partially executed
    - **filled**: Order completely executed
    - **cancelled**: Order cancelled by user or system
    - **rejected**: Order rejected by broker/market
    - **expired**: Order expired (GTD orders)
    - **cancelling**: Cancel request in progress
    - **modifying**: Modification request in progress

    **Response includes:**
    - Complete list of open orders with modern field names
    - Summary statistics (orders by status, by symbol)
    - Human-readable status messages
    - Processing time and request metadata

    **Authentication required**: JWT token in Authorization header.
    """
    try:
        user_id = current_user.user_id
        logger.info(f"Open orders request from user {user_id}")

        response = await orders_service.get_open_orders(user_id)

        if response.success:
            logger.info(f"Retrieved {response.total_orders} open orders for user {user_id}")
        else:
            logger.warning(f"Failed to retrieve open orders for user {user_id}: {response.message}")

        return response

    except Exception as e:
        logger.error(f"Open orders endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve open orders: {str(e)}"
        )


@router.get("/positions/open", response_model=OpenPositionsResponse, summary="Get Open Positions")
async def get_open_positions(
    current_user: AuthUser = Depends(get_current_user),
    positions_service: PositionsService = Depends(get_positions_service),
):
    """
    Get all currently open trading positions.

    This endpoint retrieves all positions that are currently open in the trading account.
    Positions are retrieved using the FIX Request for Positions (AN) and translated
    into modern, user-friendly format using the centralized translation system.

    **Position Types:**
    - **long**: Long position (buy)
    - **short**: Short position (sell)
    - **net**: Net position (combined long/short)

    **Position Status:**
    - **open**: Position is currently open
    - **closed**: Position has been closed
    - **closing**: Position is being closed

    **Response includes:**
    - Complete list of open positions with modern field names
    - Summary statistics (positions by type, by symbol)
    - Financial summary (total P&L, commission, swap)
    - Position quantities and average prices
    - Human-readable status messages
    - Processing time and request metadata

    **Financial Information:**
    Each position includes detailed financial data:
    - Net quantity and long/short breakdown
    - Average prices for long and short positions
    - Unrealized and realized profit/loss
    - Commission and swap charges
    - Account balance and transaction details

    **Authentication required**: JWT token in Authorization header.
    """
    try:
        user_id = current_user.user_id
        account_id = current_user.user_id  # Using user_id as account_id for now
        logger.info(f"Open positions request from user {user_id}")

        response = await positions_service.get_open_positions(user_id, account_id)

        if response.success:
            logger.info(f"Retrieved {response.total_positions} open positions for user {user_id}")
        else:
            logger.warning(f"Failed to retrieve open positions for user {user_id}: {response.message}")

        return response

    except Exception as e:
        logger.error(f"Open positions endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve open positions: {str(e)}"
        )
