from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from src.schemas.auth_schemas import LoginRequest, LoginResponse
from src.services.auth_service import AuthService

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()

router.state.limiter = limiter
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    success, token, error = await auth_service.authenticate_user(
        username=login_request.username,
        password=login_request.password,
        device_id=login_request.device_id
    )
    
    if success:
        return LoginResponse(
            success=True,
            token=token,
            message="Login successful"
        )
    else:
        return LoginResponse(
            success=False,
            error=error,
            message="Login failed"
        )
