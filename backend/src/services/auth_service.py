from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt
import uuid
from src.config.settings import config
from src.services.session_manager import session_manager

class AuthService:
    def generate_token(self, username: str) -> str:
        payload = {
            "sub": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=config.jwt.expiry),
            "jti": str(uuid.uuid4()),
        }
        
        token = jwt.encode(payload, config.jwt.secret, algorithm=config.jwt.algorithm)
        return token

    async def authenticate_user(self, username: str, password: str, device_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            user_id = username
            fix_session = await session_manager.get_or_create_session(
                user_id=user_id,
                username=username,
                password=password,
                device_id=device_id
            )

            if fix_session:
                token = self.generate_token(username)
                return True, token, None
            else:
                return False, None, "Authentication failed"

        except Exception as e:
            return False, None, "Authentication failed"
