import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.auth_router import router as auth_router
from src.config.settings import config

app = FastAPI(
    title="FIX API Adapter",
    description="Modern REST and WebSocket API layer for FIX protocol",
    version="1.0.0",
    debug=config.debug
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "FIX API Adapter is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
