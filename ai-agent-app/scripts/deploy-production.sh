#!/bin/bash
set -euo pipefail

echo "🚀 Production Deployment Script for AI Agent Application"
echo "========================================================"

# Check if required environment variables are set
required_vars=(
    "SECURITY_SECRET_KEY"
    "DATABASE_HOST"
    "DATABASE_PASSWORD"
    "REDIS_HOST"
    "CORS_ORIGINS"
    "FRONTEND_URL"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please set these variables before deploying:"
    echo "   export SECURITY_SECRET_KEY=your-secret-key"
    echo "   export DATABASE_HOST=your-db-host"
    echo "   export DATABASE_PASSWORD=your-db-password"
    echo "   export REDIS_HOST=your-redis-host"
    echo "   export CORS_ORIGINS=https://yourdomain.com"
    echo "   export FRONTEND_URL=https://yourdomain.com"
    exit 1
fi

echo "✅ All required environment variables are set"
echo ""

# Set production defaults
export ENVIRONMENT=${ENVIRONMENT:-production}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-10000}
export APP_NAME=${APP_NAME:-ai-agent-app}
export DEBUG=${DEBUG:-false}
export LOG_LEVEL=${LOG_LEVEL:-info}
export USE_DATABASE=${USE_DATABASE:-true}
export USE_REDIS=${USE_REDIS:-true}
export ENABLE_WEBSOCKETS=${ENABLE_WEBSOCKETS:-true}
export REDIS_DB=${REDIS_DB:-0}
export DATABASE_NAME=${DATABASE_NAME:-ai_agent}
export DATABASE_USER=${DATABASE_USER:-postgres}
export DATABASE_PORT=${DATABASE_PORT:-5432}
export REDIS_PORT=${REDIS_PORT:-6379}

echo "🔧 Production Configuration:"
echo "   Environment: $ENVIRONMENT"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Database: $DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo "   Redis: $REDIS_HOST:$REDIS_PORT"
echo "   CORS Origins: $CORS_ORIGINS"
echo "   Frontend URL: $FRONTEND_URL"
echo ""

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for application to be healthy
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f "http://localhost:${PORT}/health" >/dev/null 2>&1; then
        echo "✅ Application is ready!"
        break
    fi

    attempt=$((attempt + 1))
    echo "⏳ Waiting for application... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  Application may not be ready yet. Check logs with:"
    echo "   docker-compose logs -f ai-agent"
    exit 1
fi

echo ""
echo "🎉 Production deployment successful!"
echo "   📱 Application: http://localhost:${PORT}"
echo "   📚 API Docs: http://localhost:${PORT}/docs"
echo "   🔍 Health: http://localhost:${PORT}/health"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose logs -f ai-agent"
echo "   Check status: docker-compose ps"
echo "   Stop services: docker-compose down"
