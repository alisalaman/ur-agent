# Phase 6: Configuration and Deployment

## Overview

This phase implements comprehensive configuration management, database migrations, and deployment infrastructure for the synthetic representative agent system. It ensures the system can be deployed reliably across different environments with proper monitoring and observability.

## Objectives

- Create comprehensive configuration management
- Implement database migrations for new features
- Build Docker containerization and orchestration
- Set up monitoring and observability
- Create deployment automation and CI/CD pipelines

## Implementation Tasks

### 6.1 Configuration Management

**File**: `src/ai_agent/config/synthetic_agents.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from enum import Enum

class Environment(str, Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class TranscriptProcessingConfig:
    """Configuration for transcript processing."""
    transcript_directory: Path = Path("docs/transcripts")
    vector_db_path: Path = Path("data/vector_db")
    min_segment_length: int = 50
    max_segment_length: int = 2000
    embedding_model_name: str = "all-MiniLM-L6-v2"
    default_search_limit: int = 10
    max_search_limit: int = 100
    processing_batch_size: int = 10
    enable_parallel_processing: bool = True

@dataclass
class MCPConfig:
    """Configuration for MCP servers."""
    stakeholder_views_server_name: str = "stakeholder-views-server"
    stakeholder_views_server_description: str = "MCP server for querying stakeholder views from transcripts"
    server_startup_timeout: int = 30
    server_health_check_interval: int = 30
    max_retry_attempts: int = 3
    retry_delay: int = 5
    enable_auto_restart: bool = True

@dataclass
class AgentConfig:
    """Configuration for synthetic agents."""
    llm_provider: str = "anthropic"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    evidence_cache_size: int = 1000
    evidence_cache_ttl: int = 3600  # 1 hour
    max_conversation_history: int = 50
    enable_evidence_caching: bool = True
    persona_system_prompts: Dict[str, str] = None

@dataclass
class EvaluationConfig:
    """Configuration for governance evaluation."""
    evaluation_timeout: int = 300  # 5 minutes
    max_concurrent_evaluations: int = 5
    report_generation_timeout: int = 60
    enable_parallel_factor_evaluation: bool = True
    evidence_quality_threshold: float = 0.3
    min_evidence_count: int = 2
    max_evidence_count: int = 20

@dataclass
class APIConfig:
    """Configuration for API endpoints."""
    enable_websocket: bool = True
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10
    max_websocket_connections: int = 100
    api_rate_limit: int = 100  # requests per minute
    enable_cors: bool = True
    cors_origins: List[str] = None

@dataclass
class MonitoringConfig:
    """Configuration for monitoring and observability."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_tracing: bool = True
    tracing_endpoint: str = "http://jaeger:14268/api/traces"
    enable_health_checks: bool = True
    health_check_interval: int = 30
    log_level: str = "INFO"
    enable_structured_logging: bool = True

@dataclass
class DatabaseConfig:
    """Configuration for database connections."""
    host: str = "localhost"
    port: int = 5432
    database: str = "ai_agent"
    username: str = "ai_agent"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    enable_ssl: bool = False

@dataclass
class SyntheticAgentConfig:
    """Main configuration class for synthetic agent system."""
    environment: Environment = Environment.DEVELOPMENT
    transcript_processing: TranscriptProcessingConfig = None
    mcp: MCPConfig = None
    agents: AgentConfig = None
    evaluation: EvaluationConfig = None
    api: APIConfig = None
    monitoring: MonitoringConfig = None
    database: DatabaseConfig = None
    
    def __post_init__(self):
        if self.transcript_processing is None:
            self.transcript_processing = TranscriptProcessingConfig()
        if self.mcp is None:
            self.mcp = MCPConfig()
        if self.agents is None:
            self.agents = AgentConfig()
        if self.evaluation is None:
            self.evaluation = EvaluationConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.database is None:
            self.database = DatabaseConfig()

def load_config(environment: Optional[str] = None) -> SyntheticAgentConfig:
    """Load configuration based on environment."""
    env = environment or os.getenv("ENVIRONMENT", "development")
    
    config = SyntheticAgentConfig(environment=Environment(env))
    
    # Override with environment variables
    config.transcript_processing.transcript_directory = Path(
        os.getenv("TRANSCRIPT_DIRECTORY", config.transcript_processing.transcript_directory)
    )
    config.transcript_processing.vector_db_path = Path(
        os.getenv("VECTOR_DB_PATH", config.transcript_processing.vector_db_path)
    )
    config.transcript_processing.embedding_model_name = os.getenv(
        "EMBEDDING_MODEL_NAME", config.transcript_processing.embedding_model_name
    )
    
    config.agents.llm_provider = os.getenv("LLM_PROVIDER", config.agents.llm_provider)
    config.agents.llm_temperature = float(os.getenv("LLM_TEMPERATURE", config.agents.llm_temperature))
    config.agents.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", config.agents.llm_max_tokens))
    
    config.database.host = os.getenv("DATABASE_HOST", config.database.host)
    config.database.port = int(os.getenv("DATABASE_PORT", config.database.port))
    config.database.database = os.getenv("DATABASE_NAME", config.database.database)
    config.database.username = os.getenv("DATABASE_USERNAME", config.database.username)
    config.database.password = os.getenv("DATABASE_PASSWORD", config.database.password)
    
    config.monitoring.log_level = os.getenv("LOG_LEVEL", config.monitoring.log_level)
    config.monitoring.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    config.monitoring.enable_tracing = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    
    return config

def get_config() -> SyntheticAgentConfig:
    """Get the current configuration."""
    return load_config()
```

### 6.2 Database Migrations

**File**: `src/ai_agent/infrastructure/database/migrations/001_add_synthetic_agents.sql`

```sql
-- Migration: Add synthetic agent system tables
-- Version: 001
-- Description: Create tables for transcript data, agent management, and evaluation results

-- Transcript metadata table
CREATE TABLE IF NOT EXISTS transcript_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    stakeholder_group VARCHAR(50) NOT NULL,
    interview_date TIMESTAMP,
    participants TEXT[],
    total_segments INTEGER DEFAULT 0,
    file_size_bytes INTEGER DEFAULT 0,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transcript segments table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcript_metadata(id) ON DELETE CASCADE,
    speaker_name VARCHAR(255) NOT NULL,
    speaker_title VARCHAR(255),
    content TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    segment_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Topic tags table
CREATE TABLE IF NOT EXISTS topic_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Segment topic mappings
CREATE TABLE IF NOT EXISTS segment_topic_mappings (
    segment_id UUID NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topic_tags(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (segment_id, topic_id)
);

-- Governance models table
CREATE TABLE IF NOT EXISTS governance_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    key_features TEXT[],
    proposed_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evaluation results table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES governance_models(id) ON DELETE CASCADE,
    overall_score FLOAT NOT NULL,
    overall_assessment TEXT,
    evaluation_status VARCHAR(50) NOT NULL,
    key_risks TEXT[],
    key_benefits TEXT[],
    recommendations TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Factor scores table
CREATE TABLE IF NOT EXISTS factor_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES evaluation_results(id) ON DELETE CASCADE,
    factor_name VARCHAR(100) NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    rationale TEXT NOT NULL,
    evidence_citations TEXT[],
    confidence_level VARCHAR(20) NOT NULL,
    persona_perspective VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent sessions table
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    session_id UUID NOT NULL,
    user_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent conversations table
CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    evidence_count INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0,
    confidence_level VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content ON transcript_segments USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker_name);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_stakeholder ON transcript_segments(metadata->>'stakeholder_group');
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_source ON transcript_metadata(source);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_stakeholder_group ON transcript_metadata(stakeholder_group);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_processing_status ON transcript_metadata(processing_status);

CREATE INDEX IF NOT EXISTS idx_evaluation_results_model_id ON evaluation_results(model_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_status ON evaluation_results(evaluation_status);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_created_at ON evaluation_results(created_at);

CREATE INDEX IF NOT EXISTS idx_factor_scores_evaluation_id ON factor_scores(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_factor_scores_factor_name ON factor_scores(factor_name);
CREATE INDEX IF NOT EXISTS idx_factor_scores_score ON factor_scores(score);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent_type ON agent_sessions(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_session_id ON agent_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_session_id ON agent_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_agent_type ON agent_conversations(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_created_at ON agent_conversations(created_at);

-- Create views for common queries
CREATE OR REPLACE VIEW transcript_summary AS
SELECT 
    tm.id,
    tm.filename,
    tm.source,
    tm.stakeholder_group,
    tm.total_segments,
    tm.processing_status,
    COUNT(ts.id) as actual_segments,
    AVG(LENGTH(ts.content)) as avg_segment_length
FROM transcript_metadata tm
LEFT JOIN transcript_segments ts ON tm.id = ts.transcript_id
GROUP BY tm.id, tm.filename, tm.source, tm.stakeholder_group, tm.total_segments, tm.processing_status;

CREATE OR REPLACE VIEW evaluation_summary AS
SELECT 
    gm.name as model_name,
    gm.model_type,
    er.overall_score,
    er.evaluation_status,
    er.created_at as evaluation_date,
    COUNT(fs.id) as factor_count,
    AVG(fs.score) as avg_factor_score
FROM governance_models gm
JOIN evaluation_results er ON gm.id = er.model_id
LEFT JOIN factor_scores fs ON er.id = fs.evaluation_id
GROUP BY gm.id, gm.name, gm.model_type, er.overall_score, er.evaluation_status, er.created_at;

-- Insert default topic tags
INSERT INTO topic_tags (name, description, category, confidence_score) VALUES
('commercial sustainability', 'Commercial viability and sustainability aspects', 'business', 0.9),
('governance', 'Governance and regulatory aspects', 'policy', 0.9),
('cost considerations', 'Cost and financial considerations', 'financial', 0.9),
('interoperability', 'Interoperability and integration aspects', 'technical', 0.9),
('technical feasibility', 'Technical implementation feasibility', 'technical', 0.9)
ON CONFLICT (name) DO NOTHING;
```

### 6.3 Docker Configuration

**File**: `docker-compose.synthetic.yml`

```yaml
version: '3.8'

services:
  # Main AI Agent Application
  ai-agent-app:
    build:
      context: .
      dockerfile: Dockerfile.synthetic
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_HOST=postgres
      - DATABASE_NAME=ai_agent
      - DATABASE_USERNAME=ai_agent
      - DATABASE_PASSWORD=ai_agent_password
      - REDIS_HOST=redis
      - VECTOR_DB_PATH=/app/data/vector_db
      - TRANSCRIPT_DIRECTORY=/app/docs/transcripts
      - LLM_PROVIDER=anthropic
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
      - ENABLE_TRACING=true
    volumes:
      - ./data:/app/data
      - ./docs/transcripts:/app/docs/transcripts
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
      - chroma
    networks:
      - ai-agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=ai_agent
      - POSTGRES_USER=ai_agent
      - POSTGRES_PASSWORD=ai_agent_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./src/ai_agent/infrastructure/database/migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - ai-agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ai_agent -d ai_agent"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for Caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - ai-agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ChromaDB for Vector Storage
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_HTTP_PORT=8000
    networks:
      - ai-agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ai-agent-app
    networks:
      - ai-agent-network
    restart: unless-stopped

  # Prometheus for Metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - ai-agent-network
    restart: unless-stopped

  # Grafana for Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    networks:
      - ai-agent-network
    restart: unless-stopped

  # Jaeger for Tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - ai-agent-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  prometheus_data:
  grafana_data:

networks:
  ai-agent-network:
    driver: bridge
```

**File**: `Dockerfile.synthetic`

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install UV
RUN pip install uv

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY docs/ ./docs/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/data/vector_db /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uv", "run", "python", "-m", "ai_agent.main"]
```

### 6.4 Monitoring and Observability

**File**: `src/ai_agent/observability/synthetic_metrics.py`

```python
from typing import Dict, Any
import structlog
from prometheus_client import Counter, Histogram, Gauge, Info
import time

logger = structlog.get_logger()

# Metrics for transcript processing
transcript_processing_duration = Histogram(
    'transcript_processing_duration_seconds',
    'Time spent processing transcript files',
    ['filename', 'status']
)

transcript_segments_processed = Counter(
    'transcript_segments_processed_total',
    'Total number of transcript segments processed',
    ['stakeholder_group']
)

# Metrics for MCP server operations
mcp_tool_calls = Counter(
    'mcp_tool_calls_total',
    'Total number of MCP tool calls',
    ['tool_name', 'status']
)

mcp_tool_duration = Histogram(
    'mcp_tool_duration_seconds',
    'Time spent executing MCP tools',
    ['tool_name']
)

# Metrics for agent operations
agent_queries = Counter(
    'agent_queries_total',
    'Total number of agent queries',
    ['persona_type', 'status']
)

agent_query_duration = Histogram(
    'agent_query_duration_seconds',
    'Time spent processing agent queries',
    ['persona_type']
)

agent_evidence_cache_hits = Counter(
    'agent_evidence_cache_hits_total',
    'Total number of evidence cache hits',
    ['persona_type']
)

agent_evidence_cache_misses = Counter(
    'agent_evidence_cache_misses_total',
    'Total number of evidence cache misses',
    ['persona_type']
)

# Metrics for evaluation operations
evaluation_duration = Histogram(
    'evaluation_duration_seconds',
    'Time spent evaluating governance models',
    ['model_type', 'status']
)

evaluation_scores = Histogram(
    'evaluation_scores',
    'Distribution of evaluation scores',
    ['factor_name']
)

# Metrics for API operations
api_requests = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Time spent processing API requests',
    ['method', 'endpoint']
)

# Metrics for WebSocket operations
websocket_connections = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

websocket_messages = Counter(
    'websocket_messages_total',
    'Total number of WebSocket messages',
    ['message_type']
)

# System information
system_info = Info(
    'synthetic_agent_system_info',
    'Information about the synthetic agent system'
)

class SyntheticAgentMetrics:
    """Metrics collector for synthetic agent system."""
    
    def __init__(self):
        self.start_time = time.time()
        system_info.info({
            'version': '1.0.0',
            'start_time': str(self.start_time)
        })
    
    def record_transcript_processing(self, filename: str, duration: float, status: str) -> None:
        """Record transcript processing metrics."""
        transcript_processing_duration.labels(
            filename=filename, status=status
        ).observe(duration)
    
    def record_segments_processed(self, stakeholder_group: str, count: int) -> None:
        """Record segments processed metrics."""
        transcript_segments_processed.labels(
            stakeholder_group=stakeholder_group
        ).inc(count)
    
    def record_mcp_tool_call(self, tool_name: str, duration: float, status: str) -> None:
        """Record MCP tool call metrics."""
        mcp_tool_calls.labels(tool_name=tool_name, status=status).inc()
        mcp_tool_duration.labels(tool_name=tool_name).observe(duration)
    
    def record_agent_query(self, persona_type: str, duration: float, status: str) -> None:
        """Record agent query metrics."""
        agent_queries.labels(persona_type=persona_type, status=status).inc()
        agent_query_duration.labels(persona_type=persona_type).observe(duration)
    
    def record_evidence_cache_hit(self, persona_type: str) -> None:
        """Record evidence cache hit."""
        agent_evidence_cache_hits.labels(persona_type=persona_type).inc()
    
    def record_evidence_cache_miss(self, persona_type: str) -> None:
        """Record evidence cache miss."""
        agent_evidence_cache_misses.labels(persona_type=persona_type).inc()
    
    def record_evaluation(self, model_type: str, duration: float, status: str) -> None:
        """Record evaluation metrics."""
        evaluation_duration.labels(model_type=model_type, status=status).observe(duration)
    
    def record_evaluation_score(self, factor_name: str, score: float) -> None:
        """Record evaluation score."""
        evaluation_scores.labels(factor_name=factor_name).observe(score)
    
    def record_api_request(self, method: str, endpoint: str, duration: float, status_code: int) -> None:
        """Record API request metrics."""
        api_requests.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()
        api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_websocket_connection(self, count: int) -> None:
        """Record WebSocket connection count."""
        websocket_connections.set(count)
    
    def record_websocket_message(self, message_type: str) -> None:
        """Record WebSocket message."""
        websocket_messages.labels(message_type=message_type).inc()

# Global metrics instance
metrics = SyntheticAgentMetrics()
```

### 6.5 Deployment Scripts

**File**: `scripts/deploy.sh`

```bash
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
mkdir -p data/vector_db
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
```

**File**: `scripts/initialize_transcripts.py`

```python
#!/usr/bin/env python3
"""Initialize transcript data for the synthetic agent system."""

import asyncio
import sys
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_agent.infrastructure.knowledge.transcript_processor import TranscriptProcessor, ProcessingConfig
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import StakeholderGroup, TranscriptSource
from ai_agent.config.synthetic_agents import get_config

logger = structlog.get_logger()

async def initialize_transcripts():
    """Initialize transcript data."""
    try:
        config = get_config()
        
        # Create transcript processor
        processor_config = ProcessingConfig()
        processor = TranscriptProcessor(processor_config)
        
        # Create transcript store
        store = TranscriptStore(None, config.transcript_processing.vector_db_path)
        
        # Process all transcript files
        transcript_dir = config.transcript_processing.transcript_directory
        processed_count = 0
        
        for file_path in transcript_dir.glob("*.docx"):
            try:
                # Determine stakeholder group and source
                stakeholder_group = config.transcript_processing.stakeholder_group_mappings.get(
                    file_path.name, StakeholderGroup.BANK_REP
                )
                source = config.transcript_processing.source_mappings.get(
                    file_path.name, TranscriptSource.SANTANDER
                )
                
                logger.info("Processing transcript", file_path=file_path.name)
                
                # Process transcript
                metadata, segments = await processor.process_transcript_file(
                    file_path, stakeholder_group, source
                )
                
                # Store in database
                success = await store.store_transcript_data(metadata, segments)
                
                if success:
                    processed_count += 1
                    logger.info("Transcript processed successfully", 
                              file_path=file_path.name, 
                              segments=len(segments))
                else:
                    logger.error("Failed to store transcript data", file_path=file_path.name)
                    
            except Exception as e:
                logger.error("Failed to process transcript", 
                           file_path=file_path.name, 
                           error=str(e))
        
        logger.info("Transcript initialization completed", processed_count=processed_count)
        
    except Exception as e:
        logger.error("Transcript initialization failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(initialize_transcripts())
```

### 6.6 CI/CD Pipeline

**File**: `.github/workflows/deploy-synthetic-agents.yml`

```yaml
name: Deploy Synthetic Agent System

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/synthetic-agents

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install UV
        run: pip install uv
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run tests
        run: uv run pytest tests/ -v
      
      - name: Run linting
        run: uv run ruff check src/
      
      - name: Run type checking
        run: uv run mypy src/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.synthetic
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # Add deployment commands here
          # This would typically involve:
          # 1. SSH to production server
          # 2. Pull latest images
          # 3. Run deployment script
          # 4. Verify deployment
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_configuration.py`
- Test configuration loading and validation
- Test environment variable overrides
- Test configuration serialization

### Integration Tests
- **File**: `tests/integration/test_deployment.py`
- Test Docker containerization
- Test database migrations
- Test service health checks

### Performance Tests
- **File**: `tests/performance/test_deployment.py`
- Test deployment performance
- Test resource usage
- Test scalability

## Success Criteria

1. **Configuration Management**: All settings properly configurable via environment variables
2. **Database Migrations**: Clean migration system with rollback capability
3. **Docker Deployment**: Reliable containerized deployment
4. **Monitoring**: Comprehensive metrics and observability
5. **CI/CD**: Automated testing and deployment pipeline

## Dependencies

This phase depends on:
- All previous phases (1-5)
- Docker and Docker Compose
- PostgreSQL database
- Redis for caching
- ChromaDB for vector storage
- Prometheus and Grafana for monitoring

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 7: Testing and validation
- Production deployment
- Ongoing maintenance and monitoring

The configuration and deployment system must be fully functional and tested before proceeding to Phase 7.
