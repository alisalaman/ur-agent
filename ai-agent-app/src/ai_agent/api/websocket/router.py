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
        # Accept the WebSocket connection first
        await websocket.accept()
        logger.info("WebSocket connection accepted for synthetic agents")

        # For synthetic agents, allow anonymous access (demo mode)
        # Try to authenticate, but fall back to anonymous if it fails
        try:
            user_id, _ = await websocket_auth.authenticate_websocket(websocket)
            logger.info("WebSocket authenticated with user", user_id=user_id)
        except (WebSocketDisconnect, Exception) as e:
            # If authentication fails, use anonymous user for demo purposes
            logger.info(
                "WebSocket using anonymous user for synthetic agents demo", error=str(e)
            )
            user_id = "demo-user"

        await websocket_endpoint(websocket, user_id)
    except WebSocketDisconnect:
        # Connection was closed
        logger.info("WebSocket connection closed")
        pass
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        try:
            await websocket.close(code=1008, reason="Internal server error")
        except Exception:
            pass
