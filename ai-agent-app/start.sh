#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application..."

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app/src

# Get the port from Render's environment variable
PORT=${PORT:?PORT not set}
HOST=${HOST:-0.0.0.0}

echo "🔍 Environment:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  Current directory: $(pwd)"

# Try different approaches to start the server
echo "🔍 Attempting to start server..."

# Method 1: Try uvicorn directly
if command -v uvicorn >/dev/null 2>&1; then
    echo "✅ uvicorn found in PATH"
    exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
fi

# Method 2: Try with uv run
echo "⚠️  uvicorn not in PATH, trying uv run..."
exec uv run uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
