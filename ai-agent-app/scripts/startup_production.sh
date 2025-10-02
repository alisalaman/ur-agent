#!/bin/bash
set -e

echo "🚀 Starting AI Agent Application..."

# Validate required environment variables
required_vars=(
    "DATABASE_HOST"
    "DATABASE_PORT"
    "DATABASE_NAME"
    "DATABASE_USER"
    "DATABASE_PASSWORD"
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
uv run python scripts/migrate_database.py

# Start the application
echo "🎯 Starting FastAPI application..."
exec "$@"
