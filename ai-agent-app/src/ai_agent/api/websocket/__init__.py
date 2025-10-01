"""WebSocket module for real-time communication."""

from .router import router as synthetic_agents_websocket_router
from .endpoints import router as websocket_router

__all__ = ["synthetic_agents_websocket_router", "websocket_router"]
