from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config.settings import config

security = HTTPBearer()


class AuthUser:
    def __init__(self, username: str, user_id: str):
        self.username = username
        self.user_id = user_id


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(credentials.credentials, config.jwt.secret, algorithms=[config.jwt.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        return AuthUser(username=username, user_id=username)

    except JWTError:
        raise credentials_exception
