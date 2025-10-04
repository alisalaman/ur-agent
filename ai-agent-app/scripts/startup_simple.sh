#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Simple Mode)..."

# Set environment variables
export PYTHONUNBUFFERED=1

# Activate the virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "🔍 Activating virtual environment..."
    source .venv/bin/activate
elif [ -f "/app/.venv/bin/activate" ]; then
    echo "🔍 Activating virtual environment from /app..."
    source /app/.venv/bin/activate
fi

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
echo "🔍 Command: uvicorn ai_agent.main:app --host $HOST --port $PORT"

# Try to start uvicorn directly first
if command -v uvicorn >/dev/null 2>&1; then
    echo "✅ uvicorn found in PATH, starting directly..."
    exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
else
    echo "⚠️  uvicorn not found in PATH, trying with uv run..."
    exec uv run uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
fi
