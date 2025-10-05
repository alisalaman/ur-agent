"""Simple FastAPI application for Render deployment."""

import os
from datetime import datetime, UTC
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

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


@app.websocket("/ws/synthetic-agents")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for synthetic agents."""
    print(f"🔌 WebSocket connection attempt from: {websocket.client}")
    await websocket.accept()
    print("🔌 WebSocket connection established successfully")

    try:
        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection",
                    "message": "Connected to AI Agent WebSocket",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        )

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                print(f"📨 Received message: {data}")

                # Echo back the message
                response = {
                    "type": "echo",
                    "message": f"Echo: {data}",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await websocket.send_text(json.dumps(response))

            except WebSocketDisconnect:
                print("🔌 WebSocket disconnected")
                break
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                    )
                )

    except WebSocketDisconnect:
        print("🔌 WebSocket connection closed")
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")


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
