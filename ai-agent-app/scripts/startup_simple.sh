#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Simple Mode)..."

# Set environment variables
export PYTHONUNBUFFERED=1

# Get the port from Render's environment variable
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "🔍 Environment variables:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  PYTHONPATH: ${PYTHONPATH:-not set}"
echo "  ENVIRONMENT: ${ENVIRONMENT:-not set}"
echo "  Current directory: $(pwd)"

echo "🔍 Starting uvicorn server directly..."
echo "🔍 Command: uv run uvicorn ai_agent.main:app --host $HOST --port $PORT"

# Start uvicorn using uv run (since uvicorn is managed by uv)
exec uv run uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
