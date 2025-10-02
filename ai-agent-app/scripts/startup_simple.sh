#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Simple Mode)..."

# Set environment variables
export PYTHONPATH=${PYTHONPATH:-/app/src}
export PYTHONUNBUFFERED=1

# Change to the correct working directory
cd /app

# Get the port from Render's environment variable
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "🔍 Environment variables:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  ENVIRONMENT: ${ENVIRONMENT:-not set}"

echo "🔍 Starting uvicorn server directly..."
echo "🔍 Command: uvicorn ai_agent.main:app --host $HOST --port $PORT"

# Start uvicorn directly in the foreground
exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
