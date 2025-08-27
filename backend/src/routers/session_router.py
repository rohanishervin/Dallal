import time
from datetime import datetime

from fastapi import APIRouter, Depends

from src.middleware.auth_middleware import AuthUser, get_current_user
from src.schemas.session_schemas import IndividualSessionStatus, SessionStatus, SessionStatusResponse
from src.services.session_manager import session_manager

router = APIRouter(prefix="/session", tags=["session"], dependencies=[Depends(get_current_user)])


@router.get("/status", response_model=SessionStatusResponse)
async def get_session_status(current_user: AuthUser = Depends(get_current_user)):
    # Get detailed information for both Trade and Feed sessions
    trade_details = session_manager.get_session_details(current_user.user_id, "trade")
    feed_details = session_manager.get_session_details(current_user.user_id, "feed")

    trade_session_status = None
    feed_session_status = None

    # Build Trade session status
    if trade_details:
        trade_session_status = IndividualSessionStatus(
            connection_type="trade",
            is_active=trade_details["is_active"],
            created_at=datetime.fromtimestamp(trade_details["created_at"]),
            last_activity=datetime.fromtimestamp(trade_details["last_activity"]),
            last_heartbeat=datetime.fromtimestamp(trade_details["last_heartbeat"])
            if trade_details["last_heartbeat"]
            else None,
            session_age_seconds=trade_details["session_age_seconds"],
            heartbeat_status=trade_details["heartbeat_status"],
        )

    # Build Feed session status
    if feed_details:
        feed_session_status = IndividualSessionStatus(
            connection_type="feed",
            is_active=feed_details["is_active"],
            created_at=datetime.fromtimestamp(feed_details["created_at"]),
            last_activity=datetime.fromtimestamp(feed_details["last_activity"]),
            last_heartbeat=datetime.fromtimestamp(feed_details["last_heartbeat"])
            if feed_details["last_heartbeat"]
            else None,
            session_age_seconds=feed_details["session_age_seconds"],
            heartbeat_status=feed_details["heartbeat_status"],
        )

    # Determine overall status
    overall_active = bool(
        (trade_details and trade_details["is_active"]) or (feed_details and feed_details["is_active"])
    )

    # Build comprehensive session status
    session_status = SessionStatus(
        user_id=current_user.user_id,
        overall_active=overall_active,
        trade_session=trade_session_status,
        feed_session=feed_session_status,
    )

    # Build status message
    status_parts = []
    if trade_session_status and trade_session_status.is_active:
        heartbeat_info = f"(heartbeat: {trade_session_status.heartbeat_status})"
        status_parts.append(f"Trade session active {heartbeat_info}")
    elif trade_session_status:
        status_parts.append("Trade session inactive")

    if feed_session_status and feed_session_status.is_active:
        heartbeat_info = f"(heartbeat: {feed_session_status.heartbeat_status})"
        status_parts.append(f"Feed session active {heartbeat_info}")
    elif feed_session_status:
        status_parts.append("Feed session inactive")

    if not status_parts:
        message = "No sessions found"
    else:
        message = ", ".join(status_parts)

    return SessionStatusResponse(success=True, session=session_status, message=message)


@router.post("/logout")
async def logout_session(current_user: AuthUser = Depends(get_current_user)):
    # Cleanup both Trade and Feed sessions
    trade_session = session_manager.get_trade_session(current_user.user_id)
    feed_session = session_manager.get_feed_session(current_user.user_id)

    cleanup_results = []

    if trade_session:
        trade_key = f"{current_user.user_id}_trade"
        await session_manager._cleanup_session(trade_key, "trade")
        cleanup_results.append("Trade session")

    if feed_session:
        feed_key = f"{current_user.user_id}_feed"
        await session_manager._cleanup_session(feed_key, "feed")
        cleanup_results.append("Feed session")

    if cleanup_results:
        return {"success": True, "message": f"{', '.join(cleanup_results)} logged out successfully"}
    else:
        return {"success": True, "message": "No active sessions to logout"}
