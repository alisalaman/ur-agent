"""Simple FastAPI application for Render deployment."""

import os
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create a simple FastAPI app
app = FastAPI(
    title="AI Agent API",
    description="Simple AI Agent API for Render deployment",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Agent API is running",
        "version": "0.1.0",
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/ws/test")
async def websocket_test():
    """Test endpoint to verify WebSocket availability."""
    return {
        "message": "WebSocket endpoint is available",
        "websocket_url": "wss://ur-agent.onrender.com/ws/synthetic-agents",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Removed conflicting WebSocket endpoint - use main.py instead
# This prevents route conflicts with the proper synthetic agents WebSocket handler


if __name__ == "__main__":
    import uvicorn
    import signal
    import sys

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 Starting simple server on {host}:{port}")
    print("🔌 WebSocket endpoint available at: /ws/synthetic-agents")
    print("🔍 Health check available at: /health")
    print("🔍 Root endpoint available at: /")
    print("🔍 WebSocket test endpoint available at: /ws/test")
    print("🔍 Full WebSocket URL: wss://ur-agent.onrender.com/ws/synthetic-agents")

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("🛑 Received shutdown signal, stopping server...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)
    except KeyboardInterrupt:
        print("🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)
