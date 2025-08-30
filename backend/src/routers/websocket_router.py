import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from src.config.settings import config
from src.services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def get_token_from_query(token: str = Query(..., description="JWT authentication token")):
    return token


def get_required_token_from_header(authorization: str = Depends(HTTPBearer())):
    """Extract Bearer token from Authorization header (required)"""
    return authorization.credentials


async def get_token_from_websocket(websocket: WebSocket, token: Optional[str] = None):
    if not token:
        query_params = dict(websocket.query_params)
        token = query_params.get("token")

    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        raise HTTPException(status_code=401, detail="Authentication token required")

    try:
        payload = jwt.decode(token, config.jwt.secret, algorithms=[config.jwt.algorithm])
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=1008, reason="Invalid token - no user ID")
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id, token

    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


@router.websocket("/orderbook")
async def orderbook_websocket(websocket: WebSocket, token: str = Query(..., description="JWT authentication token")):
    user_id = None

    try:
        user_id = await websocket_manager.connect(websocket, token)

        if not user_id:
            return

        logger.info(f"WebSocket orderbook connection established for user: {user_id}")

        while True:
            try:
                data = await websocket.receive_text()

                try:
                    message_data = json.loads(data)
                    await websocket_manager.handle_message(user_id, message_data)

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"type": "error", "error": "Invalid JSON format"}))

            except WebSocketDisconnect:
                logger.info(f"WebSocket orderbook disconnected for user: {user_id}")
                break

            except Exception as e:
                logger.error(f"Error handling WebSocket message from {user_id}: {e}")
                try:
                    await websocket.send_text(
                        json.dumps({"type": "error", "error": f"Message processing error: {str(e)}"})
                    )
                except:
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket orderbook disconnected during handshake")

    except Exception as e:
        logger.error(f"WebSocket orderbook error: {e}")

    finally:
        if user_id:
            await websocket_manager.disconnect(user_id)


@router.get("/orderbook/status")
async def websocket_status(bearer_token: str = Depends(get_required_token_from_header)):
    try:
        # Validate the Bearer token
        payload = jwt.decode(bearer_token, config.jwt.secret, algorithms=[config.jwt.algorithm])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Return user-specific status
        is_connected = user_id in websocket_manager.connections
        subscriptions = list(websocket_manager.user_subscriptions.get(user_id, {}).keys())
        total_connections = len(websocket_manager.connections)
        total_subscriptions = sum(len(subs) for subs in websocket_manager.user_subscriptions.values())

        return {
            "success": True,
            "user_id": user_id,
            "websocket_connected": is_connected,
            "active_subscriptions": subscriptions,
            "total_connections": total_connections,
            "total_active_subscriptions": total_subscriptions,
            "message": f"WebSocket status for user {user_id}",
        }

    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
