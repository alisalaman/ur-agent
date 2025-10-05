#!/usr/bin/env python3
"""Minimal server startup script for Render deployment."""

import os
import sys
import uvicorn
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

print("🚀 Starting minimal AI Agent server...")
print(f"🔍 Python path: {sys.path[:3]}")
print(f"🔍 Working directory: {os.getcwd()}")
print(f"🔍 Environment: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"🔍 Port: {os.getenv('PORT', 'not set')}")

# Get port and host from environment
port = int(os.getenv("PORT", 8000))
host = os.getenv("HOST", "0.0.0.0")

print(f"🔍 Starting server on {host}:{port}")

try:
    # Start the server immediately with simple app
    uvicorn.run(
        "ai_agent.simple_main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        reload=False,
    )
except Exception as e:
    print(f"❌ Failed to start server: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
