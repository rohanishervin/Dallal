from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class FIXConfig:
    def __init__(self):
        self.protocol_spec = os.getenv("FIX_PROTOCOL_SPEC", "FIX44")
        self.sender_comp_id = os.getenv("FIX_SENDER_COMP_ID")
        self.target_comp_id = os.getenv("FIX_TARGET_COMP_ID")
        self.host = os.getenv("FIX_HOST")
        self.port = int(os.getenv("FIX_PORT", "0")) if os.getenv("FIX_PORT") else None
        
        if not self.sender_comp_id or not self.target_comp_id:
            raise ValueError("FIX_SENDER_COMP_ID and FIX_TARGET_COMP_ID must be set in environment variables")
        
        if not self.host or not self.port:
            raise ValueError("FIX_HOST and FIX_PORT must be set in environment variables")

class JWTConfig:
    def __init__(self):
        self.secret = os.getenv("JWT_SECRET")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.expiry = int(os.getenv("JWT_EXPIRY", "3600"))
        
        if not self.secret:
            raise ValueError("JWT_SECRET must be set in environment variables")
        
        if len(self.secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")

class AppConfig:
    def __init__(self):
        self.fix = FIXConfig()
        self.jwt = JWTConfig()
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

config = AppConfig()
