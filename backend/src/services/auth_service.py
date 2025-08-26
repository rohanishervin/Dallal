from datetime import datetime, timedelta
from typing import Optional, Tuple
import jwt
import uuid
from src.config.settings import config
from src.adapters.fix_adapter import FIXAdapter

class AuthService:
    def __init__(self):
        self.fix_adapter = FIXAdapter()

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
            success, error_message = self.fix_adapter.logon(
                username=username,
                password=password,
                device_id=device_id,
                timeout=10
            )

            if success:
                token = self.generate_token(username)
                return True, token, None
            else:
                return False, None, error_message

        except Exception as e:
            return False, None, "Authentication failed"
