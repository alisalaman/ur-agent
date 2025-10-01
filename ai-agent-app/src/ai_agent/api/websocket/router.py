"""WebSocket router for real-time communication."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ai_agent.api.websocket.synthetic_agents import websocket_endpoint
from ai_agent.api.websocket.auth import websocket_auth
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/synthetic-agents")
async def synthetic_agents_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for synthetic agents."""
    try:
        # Authenticate the WebSocket connection
        user_id, session_id = await websocket_auth.authenticate_websocket(websocket)
        await websocket_endpoint(websocket, user_id)
    except WebSocketDisconnect:
        # Connection was closed during authentication
        logger.info("WebSocket connection closed during authentication")
        pass
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        try:
            await websocket.close(code=1008, reason="Internal server error")
        except Exception:
            pass
