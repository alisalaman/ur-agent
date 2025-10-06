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

# Run debug script to check environment
echo "🔍 Running production debug script..."
uv run python scripts/debug_production.py || echo "⚠️  Debug script failed, continuing..."

# Start the application with error handling
echo "🎯 Starting FastAPI application..."

# Start the application using uv run
echo "✅ Starting server with uv run..."
echo "🔍 About to execute: uv run python -c \"from ai_agent.main import main; main()\""
echo "🔍 Current directory: $(pwd)"
echo "🔍 Python path: $PYTHONPATH"

# Try to start the server
echo "🔍 Executing server startup command..."
uv run python -c "from ai_agent.main import main; main()"
