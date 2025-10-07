#!/bin/bash
set -euo pipefail

echo "🐳 Starting AI Agent Application with Docker..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.docker .env
    echo "⚠️  Please edit .env file with your configuration before running again."
    echo "   At minimum, set SECURITY_SECRET_KEY to a secure value."
    exit 1
fi

# Parse command line arguments
MODE="production"
CLEAN=false
HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev|--development)
            MODE="development"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            HELP=true
            shift
            ;;
    esac
done

if [ "$HELP" = true ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev, --development    Start in development mode with hot reloading"
    echo "  --clean                 Clean up existing containers before starting"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Start in production mode"
    echo "  $0 --dev              # Start in development mode"
    echo "  $0 --clean --dev      # Clean and start in development mode"
    exit 0
fi

# Clean up if requested
if [ "$CLEAN" = true ]; then
    echo "🧹 Cleaning up existing containers..."
    docker-compose down -v
    docker system prune -f
fi

# Start services based on mode
if [ "$MODE" = "development" ]; then
    echo "🚀 Starting in DEVELOPMENT mode..."
    echo "   - Hot reloading enabled"
    echo "   - Source code mounted"
    echo "   - Debug logging enabled"

    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

    echo ""
    echo "✅ Development environment started!"
    echo "   📱 Application: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    echo "   🔍 Health: http://localhost:8000/health"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker-compose logs -f ai-agent"
    echo "   Run tests: make -f Makefile.docker test"
    echo "   Format code: make -f Makefile.docker format"
    echo "   Stop services: docker-compose down"

else
    echo "🚀 Starting in PRODUCTION mode..."
    echo "   - Optimized for performance"
    echo "   - Health checks enabled"
    echo "   - Restart policies configured"

    docker-compose up -d

    echo ""
    echo "✅ Production environment started!"
    echo "   📱 Application: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    echo "   🔍 Health: http://localhost:8000/health"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker-compose logs -f ai-agent"
    echo "   Check status: docker-compose ps"
    echo "   Stop services: docker-compose down"
fi

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."

# Check if application is responding
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Application is ready!"
        break
    fi

    attempt=$((attempt + 1))
    echo "⏳ Waiting for application... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  Application may not be ready yet. Check logs with: docker-compose logs -f ai-agent"
fi

echo ""
echo "🎉 Setup complete! Your AI Agent application is running."
