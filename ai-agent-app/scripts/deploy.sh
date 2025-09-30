#!/bin/bash

# Deployment script for synthetic agent system
set -e

# Configuration
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
DOCKER_COMPOSE_FILE="docker-compose.synthetic.yml"

echo "Deploying synthetic agent system..."
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p ssl

# Set environment variables
export ENVIRONMENT=$ENVIRONMENT
export VERSION=$VERSION

# Pull latest images
echo "Pulling latest images..."
docker-compose -f $DOCKER_COMPOSE_FILE pull

# Build application image
echo "Building application image..."
docker-compose -f $DOCKER_COMPOSE_FILE build ai-agent-app

# Stop existing services
echo "Stopping existing services..."
docker-compose -f $DOCKER_COMPOSE_FILE down

# Start services
echo "Starting services..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 30

# Check service health
echo "Checking service health..."
if ! docker-compose -f $DOCKER_COMPOSE_FILE ps | grep -q "Up (healthy)"; then
    echo "Error: Some services are not healthy"
    docker-compose -f $DOCKER_COMPOSE_FILE logs
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
docker-compose -f $DOCKER_COMPOSE_FILE exec ai-agent-app python -m ai_agent.scripts.migrate_database

# Initialize transcript data
echo "Initializing transcript data..."
docker-compose -f $DOCKER_COMPOSE_FILE exec ai-agent-app python -m ai_agent.scripts.initialize_transcripts

echo "Deployment completed successfully!"
echo "Application is available at: http://localhost:8000"
echo "Grafana is available at: http://localhost:3000"
echo "Prometheus is available at: http://localhost:9090"
