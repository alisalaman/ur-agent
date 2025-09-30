"""WebSocket router for real-time communication."""

from fastapi import APIRouter, WebSocket
from ai_agent.api.websocket.synthetic_agents import websocket_endpoint
from ai_agent.api.websocket.auth import websocket_auth

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/synthetic-agents")
async def synthetic_agents_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for synthetic agents."""
    # Authenticate the WebSocket connection
    user_id, session_id = await websocket_auth.authenticate_websocket(websocket)
    await websocket_endpoint(websocket, user_id)
