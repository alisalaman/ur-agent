#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Production Simple Mode)..."
echo "🔍 This is the NEW production startup script - NOT the minimal one!"

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
echo "  Script location: $(realpath $0)"
echo "  Script name: $(basename $0)"

# Wait for database to be ready (with timeout)
echo "⏳ Waiting for database to be ready..."
python -c "
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
python scripts/migrate_database.py || echo "⚠️  Database migrations failed, continuing..."

# Run debug script to check environment
echo "🔍 Running production debug script..."
python scripts/debug_production.py || echo "⚠️  Debug script failed, continuing..."

# Start the application with error handling
echo "🎯 Starting FastAPI application..."

# Try to start with uvicorn directly
if command -v uvicorn >/dev/null 2>&1; then
    echo "✅ uvicorn found in PATH, starting server..."
    exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT" --log-level info
else
    echo "⚠️  uvicorn not in PATH, trying uv run..."
    exec uv run uvicorn ai_agent.main:app --host "$HOST" --port "$PORT" --log-level info
fi
