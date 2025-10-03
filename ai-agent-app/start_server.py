#!/usr/bin/env python3
"""Simple server startup script for Render deployment."""

import os
import uvicorn


def main():
    """Start the FastAPI server."""
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print("🚀 Starting AI Agent Application...")
    print(f"🔍 Host: {host}")
    print(f"🔍 Port: {port}")
    print(f"🔍 Environment: {os.getenv('ENVIRONMENT', 'not set')}")

    # Start the server
    uvicorn.run(
        "ai_agent.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
