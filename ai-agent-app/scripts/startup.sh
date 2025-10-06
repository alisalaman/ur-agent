#!/bin/bash
set -e

echo "🚀 Starting AI Agent Application..."

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
python -c "
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
python scripts/migrate_database.py

# Start the application
echo "🎯 Starting FastAPI application..."

# Get port and host from environment
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

# If no arguments provided, use default uvicorn command
if [ $# -eq 0 ]; then
    echo "🔍 No arguments provided, using default uvicorn command"
    exec uvicorn ai_agent.main:app --host "$HOST" --port "$PORT"
else
    echo "🔍 Using provided arguments: $@"
    exec "$@"
fi
