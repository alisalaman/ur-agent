#!/bin/bash
set -euo pipefail

echo "🚀 Starting AI Agent Application (Production Simple Mode)..."
echo "🔍 This is the NEW production startup script - NOT the minimal one!"

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH=/opt/render/project/src

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

echo "🔍 CORS Configuration:"
echo "  CORS_ORIGINS: ${CORS_ORIGINS:-not set}"
echo "  FRONTEND_URL: ${FRONTEND_URL:-not set}"

echo "🔍 Database Configuration:"
echo "  DATABASE_HOST: ${DATABASE_HOST:-not set}"
echo "  DATABASE_PORT: ${DATABASE_PORT:-not set}"
echo "  DATABASE_NAME: ${DATABASE_NAME:-not set}"
echo "  DATABASE_USER: ${DATABASE_USER:-not set}"
echo "  DATABASE_PASSWORD: ${DATABASE_PASSWORD:-not set}"

echo "🔍 Security Configuration:"
echo "  SECURITY_SECRET_KEY: ${SECURITY_SECRET_KEY:-not set}"
if [ -n "${SECURITY_SECRET_KEY:-}" ]; then
    echo "  SECURITY_SECRET_KEY length: ${#SECURITY_SECRET_KEY}"
else
    echo "  SECURITY_SECRET_KEY length: 0"
fi
echo "🔍 LLM Configuration:"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:-not set}"
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-not set}"
echo "  GOOGLE_API_KEY: ${GOOGLE_API_KEY:-not set}"
echo "  LM_STUDIO_BASE_URL: ${LM_STUDIO_BASE_URL:-not set}"
echo "  LM_STUDIO_API_KEY: ${LM_STUDIO_API_KEY:-not set}"
echo "  LM_STUDIO_MODEL: ${LM_STUDIO_MODEL:-not set}"

echo "🔍 Feature Flags:"
echo "  USE_DATABASE: ${USE_DATABASE:-not set}"
echo "  USE_REDIS: ${USE_REDIS:-not set}"
echo "  ENABLE_WEBSOCKETS: ${ENABLE_WEBSOCKETS:-not set}"

echo "🔍 Python Environment:"
echo "  Python version: $(python --version 2>&1 || echo 'not found')"
echo "  uv version: $(uv --version 2>&1 || echo 'not found')"
echo "  Available Python modules:"
python -c "import sys; print('  Python path:', sys.path[:3])" 2>/dev/null || echo "  Python not available"

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
echo "🔍 About to execute: uv run uvicorn ai_agent.main:app --host $HOST --port $PORT --log-level info"
echo "🔍 Current directory: $(pwd)"
echo "🔍 Python path: $PYTHONPATH"

# Try to start the server
echo "🔍 Executing server startup command..."
echo "🔍 Starting FastAPI application with Uvicorn..."
uv run uvicorn ai_agent.main:app --host $HOST --port $PORT --log-level info
