from fastapi import APIRouter, Depends
from datetime import datetime
import time
from src.schemas.session_schemas import SessionStatusResponse, SessionStatus
from src.services.session_manager import session_manager
from src.middleware.auth_middleware import get_current_user, AuthUser

router = APIRouter(
    prefix="/session", 
    tags=["session"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/status", response_model=SessionStatusResponse)
async def get_session_status(
    current_user: AuthUser = Depends(get_current_user)
):
    session = session_manager.get_session(current_user.user_id)
    
    if session and session.is_session_active():
        metadata = session_manager.session_metadata.get(current_user.user_id, {})
        created_at = metadata.get("created_at", time.time())
        last_activity = metadata.get("last_activity", time.time())
        
        session_status = SessionStatus(
            user_id=current_user.user_id,
            is_active=True,
            created_at=datetime.fromtimestamp(created_at),
            last_activity=datetime.fromtimestamp(last_activity),
            session_age_seconds=int(time.time() - created_at)
        )
        
        return SessionStatusResponse(
            success=True,
            session=session_status,
            message="Session is active"
        )
    else:
        return SessionStatusResponse(
            success=True,
            session=SessionStatus(
                user_id=current_user.user_id,
                is_active=False
            ),
            message="No active session found"
        )

@router.post("/logout")
async def logout_session(
    current_user: AuthUser = Depends(get_current_user)
):
    session = session_manager.get_session(current_user.user_id)
    
    if session:
        await session_manager._cleanup_session(current_user.user_id)
        return {"success": True, "message": "Session logged out successfully"}
    else:
        return {"success": True, "message": "No active session to logout"}
