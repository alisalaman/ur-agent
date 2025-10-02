#!/bin/bash
set -e

echo "🚀 Starting AI Agent Application..."

# Set default values for optional environment variables (only for local dev)
export PORT=${PORT:-8000}
export HOST=${HOST:-0.0.0.0}
export ENVIRONMENT=${ENVIRONMENT:-production}
export APP_NAME=${APP_NAME:-ai-agent-app}
export REDIS_DB=${REDIS_DB:-0}

# Validate required environment variables
required_vars=(
    "DATABASE_HOST"
    "DATABASE_PORT"
    "DATABASE_NAME"
    "DATABASE_USER"
    "DATABASE_PASSWORD"
    "REDIS_HOST"
    "REDIS_PORT"
    "USE_DATABASE"
    "USE_REDIS"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "❌ Missing required environment variables:"
    printf '  - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please set these environment variables before running the application."
    exit 1
fi

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
uv run python -c "
import asyncio
import asyncpg
import os
import sys
import time

async def wait_for_db():
    max_retries = 30
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

    print('❌ Database connection failed after maximum retries')
    sys.exit(1)

asyncio.run(wait_for_db())
"

# Run database migrations
echo "🔄 Running database migrations..."
echo "📋 Database connection details:"
echo "  DATABASE_HOST: $DATABASE_HOST"
echo "  DATABASE_PORT: $DATABASE_PORT"
echo "  DATABASE_NAME: $DATABASE_NAME"
echo "  DATABASE_USER: $DATABASE_USER"
echo "📋 Redis connection details:"
echo "  REDIS_HOST: $REDIS_HOST"
echo "  REDIS_PORT: $REDIS_PORT"
echo "  REDIS_DB: $REDIS_DB"
echo "  REDIS_PASSWORD: ${REDIS_PASSWORD:-'(not set)'}"
uv run python scripts/migrate_database.py
if [ $? -ne 0 ]; then
    echo "❌ Database migrations failed"
    exit 1
else
    echo "✅ Database migrations completed successfully"
fi

# Start the application
echo "🎯 Starting FastAPI application..."
echo "🔍 Environment variables:"
echo "  ENVIRONMENT: ${ENVIRONMENT:-'(not set)'}"
echo "  PORT: ${PORT:-'(not set)'}"
echo "  HOST: ${HOST:-'(not set)'}"
echo "  SECURITY_SECRET_KEY: ${SECURITY_SECRET_KEY:-'(not set)'}"
if [[ -n "${SECURITY_SECRET_KEY:-}" ]]; then
    echo "  SECURITY_SECRET_KEY length: ${#SECURITY_SECRET_KEY}"
else
    echo "  SECURITY_SECRET_KEY length: 0"
fi
echo "🔍 Current working directory: $(pwd)"
echo "🔍 Python path: $PYTHONPATH"
echo "🔍 About to execute: $*"

# Test if we can import the module before running
echo "🔍 Testing module import..."
python -c "
import sys
sys.path.insert(0, '/app/src')
try:
    import ai_agent.main
    print('✅ Module import successful')
except Exception as e:
    print(f'❌ Module import failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Module import test failed"
    exit 1
fi

echo "🔍 Module import test passed, starting application..."

# Get the port from Render's environment variable
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "🔍 Starting uvicorn server directly..."
echo "🔍 Host: $HOST"
echo "🔍 Port: $PORT"

# Start uvicorn directly in the foreground
exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
