from typing import Optional
import os

class FIXConfig:
    def __init__(self):
        self.protocol_spec = os.getenv("FIX_PROTOCOL_SPEC", "FIX44")
        self.use_ssl = os.getenv("FIX_USE_SSL", "True").lower() == "true"
        self.sender_comp_id = os.getenv("FIX_SENDER_COMP_ID")
        self.target_comp_id = os.getenv("FIX_TARGET_COMP_ID")
        self.ssl_host = os.getenv("FIX_SSL_HOST")
        self.ssl_port = int(os.getenv("FIX_SSL_PORT", "0")) if os.getenv("FIX_SSL_PORT") else None
        self.nonssl_host = os.getenv("FIX_NONSSL_HOST")
        self.nonssl_port = int(os.getenv("FIX_NONSSL_PORT", "0")) if os.getenv("FIX_NONSSL_PORT") else None
        
        if not self.sender_comp_id or not self.target_comp_id:
            raise ValueError("FIX_SENDER_COMP_ID and FIX_TARGET_COMP_ID must be set in environment variables")
        
        if self.use_ssl and (not self.ssl_host or not self.ssl_port):
            raise ValueError("FIX_SSL_HOST and FIX_SSL_PORT must be set when SSL is enabled")
        
        if not self.use_ssl and (not self.nonssl_host or not self.nonssl_port):
            raise ValueError("FIX_NONSSL_HOST and FIX_NONSSL_PORT must be set when SSL is disabled")

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
