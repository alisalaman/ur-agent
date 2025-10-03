#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Minimal Mode)..."

# Set environment variables
export PYTHONUNBUFFERED=1

# Get the port from Render's environment variable
PORT=${PORT:?PORT not set}
HOST=${HOST:-0.0.0.0}

echo "🔍 Starting uvicorn server..."
echo "🔍 Host: $HOST"
echo "🔍 Port: $PORT"

# Start uvicorn directly in the foreground
exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
