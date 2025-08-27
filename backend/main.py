import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config.settings import config
from src.routers.auth_router import router as auth_router
from src.routers.market_router import router as market_router
from src.routers.session_router import router as session_router

logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FIX API Adapter",
    description="Modern REST and WebSocket API layer for FIX protocol",
    version="1.0.0",
    debug=config.debug,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(session_router)
app.include_router(market_router)


@app.get("/")
async def root():
    return {"message": "FIX API Adapter is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
