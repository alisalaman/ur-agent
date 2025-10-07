#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Production Simple Mode)..."

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app/src

# Get the port from Render's environment variable
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "🔍 Environment:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  ENVIRONMENT: ${ENVIRONMENT:-not set}"
echo "  Current directory: $(pwd)"

echo "🔍 CORS Configuration:"
echo "  CORS_ORIGINS: ${CORS_ORIGINS:-not set}"
echo "  FRONTEND_URL: ${FRONTEND_URL:-not set}"

echo "🔍 Database Configuration:"
echo "  DATABASE_HOST: ${DATABASE_HOST:-not set}"
echo "  DATABASE_PORT: ${DATABASE_PORT:-not set}"
echo "  DATABASE_NAME: ${DATABASE_NAME:-not set}"
echo "  DATABASE_USER: ${DATABASE_USER:-not set}"

echo "🔍 Security Configuration:"
if [ -n "${SECURITY_SECRET_KEY:-}" ]; then
    echo "  SECURITY_SECRET_KEY length: ${#SECURITY_SECRET_KEY}"
else
    echo "  SECURITY_SECRET_KEY length: 0"
fi

echo "🔍 Feature Flags:"
echo "  USE_DATABASE: ${USE_DATABASE:-not set}"
echo "  USE_REDIS: ${USE_REDIS:-not set}"
echo "  ENABLE_WEBSOCKETS: ${ENABLE_WEBSOCKETS:-not set}"

# Wait for database to be ready (with timeout)
echo "⏳ Waiting for database to be ready..."
uv run python -c "
import asyncio
import asyncpg
import os
import sys
import time

async def wait_for_db():
    max_retries = 10
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn = await asyncpg.connect(
                host=os.getenv('DATABASE_HOST'),
                port=int(os.getenv('DATABASE_PORT', 5432)),
                database=os.getenv('DATABASE_NAME'),
                user=os.getenv('DATABASE_USER'),
                password=os.getenv('DATABASE_PASSWORD')
            )
            await conn.close()
            print('✅ Database connection successful')
            return
        except Exception as e:
            retry_count += 1
            print(f'⏳ Database not ready yet (attempt {retry_count}/{max_retries}): {e}')
            time.sleep(2)

    print('⚠️  Database connection failed, continuing without database...')

asyncio.run(wait_for_db())
"

# Run database migrations (with error handling)
echo "🔄 Running database migrations..."
uv run python scripts/migrate_database.py || echo "⚠️  Database migrations failed, continuing..."

# Start the application directly (removed debug script that was causing conflicts)
echo "🎯 Starting FastAPI application..."
echo "✅ Starting server with uv run..."
echo "🔍 About to execute: uv run uvicorn ai_agent.main:app --host $HOST --port $PORT --log-level info"
echo "🔍 Current directory: $(pwd)"
echo "🔍 Python path: $PYTHONPATH"

# Start the server and keep it running (use exec to replace shell process)
echo "🔍 Starting FastAPI application with Uvicorn..."
exec uv run uvicorn ai_agent.main:app --host $HOST --port $PORT --log-level info
