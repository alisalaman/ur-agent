# Multi-stage build for production-ready AI Agent service
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Make startup scripts executable
RUN chmod +x scripts/*.sh

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Create non-root user for security with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser
RUN chown -R appuser:appuser /app /home/appuser
USER appuser

# Set home directory and ensure UV can create cache
ENV HOME=/home/appuser
RUN mkdir -p /home/appuser/.cache

# Set Python path
ENV PYTHONPATH=/app/src

# Expose ports
EXPOSE 8000 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command (can be overridden)
CMD ["uv", "run", "uvicorn", "ai_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Switch back to root for development dependencies
USER root

# Install development dependencies
RUN uv sync --frozen

# Install additional development tools
RUN uv add --dev pytest pytest-asyncio pytest-cov black ruff mypy

# Switch back to app user and ensure proper permissions
USER appuser
RUN mkdir -p /home/appuser/.cache

# Development command
CMD ["uv", "run", "uvicorn", "ai_agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy production-specific configurations if any
# (Add any production-specific files here)

# Production command - use single worker for containerized deployment
CMD ["sh", "-c", "uv run uvicorn ai_agent.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
