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


@app.get("/ws/synthetic-agents")
async def websocket_endpoint():
    """WebSocket endpoint placeholder."""
    return {"message": "WebSocket endpoint available"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 Starting simple server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
