"""FastAPI application entry point."""

import os
from datetime import datetime, UTC
from dotenv import load_dotenv

# Load .env file before importing settings
load_dotenv()

print("🔍 Starting FastAPI application import...")
print(f"🔍 ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"🔍 PORT: {os.getenv('PORT', 'not set')}")
print(f"🔍 SECURITY_SECRET_KEY length: {len(os.getenv('SECURITY_SECRET_KEY', ''))}")

from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from .api.rate_limiting import rate_limit_exceeded_handler  # noqa: E402
from . import __description__, __version__  # noqa: E402
from .api.v1.router import router as v1_router  # noqa: E402
from .api.websocket.endpoints import router as websocket_router  # noqa: E402
from .api.websocket.router import (  # noqa: E402
    router as synthetic_agents_websocket_router,
)
from .core.dependency_container import shutdown_container  # noqa: E402
from .api.error_handlers import (  # noqa: E402
    authentication_exception_handler,
    authorization_exception_handler,
    circuit_breaker_exception_handler,
    external_service_exception_handler,
    general_exception_handler,
    rate_limit_exception_handler,
    timeout_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
    validation_exception_handler_custom,
)
from .api.middleware import (  # noqa: E402
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from .api.openapi import custom_openapi  # noqa: E402
from .api.rate_limiting import limiter  # noqa: E402

print("🔍 About to import settings...")
from .config.settings import get_settings  # noqa: E402

print("🔍 Settings imported successfully!")
from .infrastructure.llm.factory import LLMProviderFactory  # noqa: E402
from .domain.exceptions import (  # noqa: E402
    AIAgentException,
    AuthenticationException,
    AuthorizationException,
    CircuitBreakerOpenException,
    ExternalServiceException,
    RateLimitException,
    TimeoutException,
    ValidationException,
)

# Get settings
settings = get_settings()

# Rate limiter is imported from api.rate_limiting module

# Create FastAPI application
app = FastAPI(
    title="AI Agent Application",
    description=__description__,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add middleware
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler_custom)
app.add_exception_handler(AuthenticationException, authentication_exception_handler)
app.add_exception_handler(AuthorizationException, authorization_exception_handler)
app.add_exception_handler(RateLimitException, rate_limit_exception_handler)
app.add_exception_handler(ExternalServiceException, external_service_exception_handler)
app.add_exception_handler(
    CircuitBreakerOpenException, circuit_breaker_exception_handler
)
app.add_exception_handler(TimeoutException, timeout_exception_handler)
app.add_exception_handler(AIAgentException, general_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)

# Include API routers
app.include_router(v1_router)
app.include_router(websocket_router)
app.include_router(synthetic_agents_websocket_router)

# Mount static files

static_dir = os.path.join(os.path.dirname(__file__), "api", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Set custom OpenAPI schema
app.openapi_schema = custom_openapi(app)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize services on startup."""
    try:
        # Initialize database and run migrations
        from .infrastructure.database.factory import setup_repository
        from .scripts.migrate_database import DatabaseMigrator

        # Setup repository (database connection)
        await setup_repository(settings)

        # Run database migrations
        migrator = DatabaseMigrator()
        migration_success = await migrator.run_migrations()
        if not migration_success:
            print("⚠️  Database migrations failed, but continuing...")
        else:
            print("✅ Database migrations completed successfully")

        # Try to register real LLM providers based on environment variables
        providers_registered = 0

        # Check for OpenAI API key
        openai_key = settings.openai_api_key

        # Also check environment variable directly as fallback
        if not openai_key:
            openai_key = os.getenv("OPENAI_API_KEY") or ""

        if openai_key and openai_key not in ["sk-your-openai-key", ""]:
            try:
                await LLMProviderFactory.create_openai_provider(
                    api_key=openai_key,
                    name="OpenAI Provider",
                    default_model="gpt-4o",
                )
                print("✅ OpenAI provider registered")
                providers_registered += 1
            except Exception as e:
                print(f"⚠️  Failed to register OpenAI provider: {e}")

        # Check for Anthropic API key
        anthropic_key = settings.anthropic_api_key
        if anthropic_key and anthropic_key not in ["sk-ant-your-anthropic-key", ""]:
            try:
                await LLMProviderFactory.create_anthropic_provider(
                    api_key=anthropic_key,
                    name="Anthropic Provider",
                    default_model="claude-3-5-sonnet-20241022",
                )
                print("✅ Anthropic provider registered")
                providers_registered += 1
            except Exception as e:
                print(f"⚠️  Failed to register Anthropic provider: {e}")

        # Check for Google API key
        google_key = settings.google_api_key
        if google_key and google_key not in ["your-google-api-key", ""]:
            try:
                await LLMProviderFactory.create_google_provider(
                    api_key=google_key,
                    name="Google Provider",
                    default_model="gemini-1.5-pro",
                )
                print("✅ Google provider registered")
                providers_registered += 1
            except Exception as e:
                print(f"⚠️  Failed to register Google provider: {e}")

        # Check for LM Studio configuration
        lm_studio_url = settings.lm_studio_base_url
        lm_studio_key = settings.lm_studio_api_key
        lm_studio_model = settings.lm_studio_model

        if lm_studio_url and lm_studio_key and lm_studio_model:
            try:
                await LLMProviderFactory.create_openai_provider(
                    api_key=lm_studio_key,
                    name="LM Studio Provider",
                    base_url=lm_studio_url,
                    default_model=lm_studio_model,
                )
                print("✅ LM Studio provider registered")
                providers_registered += 1
            except Exception as e:
                print(f"⚠️  Failed to register LM Studio provider: {e}")

        # If no real providers were registered, fall back to mock provider
        if providers_registered == 0:
            await LLMProviderFactory.create_anthropic_provider(
                api_key="demo-key",  # Mock key for demo
                name="Demo Anthropic Provider",
                default_model="claude-3-5-sonnet-20241022",
            )
            print("⚠️  No real LLM providers configured, using mock provider")
            print(
                "💡 To use real LLM providers, set OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or LM_STUDIO_* environment variables"
            )
        else:
            print(f"✅ {providers_registered} real LLM provider(s) registered")

    except Exception as e:
        print(f"⚠️  Failed to register LLM providers: {e}")
        # Continue anyway - the service will work with mock responses


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "AI Agent Application",
        "version": __version__,
        "status": "running",
        "docs_url": "/docs",
        "synthetic_agents_ui": "/static/index.html",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    """Main entry point for production deployment."""
    import uvicorn
    import atexit
    import asyncio

    # Register cleanup function
    atexit.register(lambda: asyncio.run(shutdown_container()))

    # Get port from environment variable, default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 Starting FastAPI server on host={host} port={port}")
    print(f"🔍 Environment: {os.getenv('ENVIRONMENT', 'not set')}")
    print(f"🔍 PORT environment variable: {os.getenv('PORT', 'not set')}")
    print(f"🔍 PYTHONPATH: {os.getenv('PYTHONPATH', 'not set')}")
    print(f"🔍 Current working directory: {os.getcwd()}")
    print("🔍 About to start uvicorn with app='ai_agent.main:app'")

    try:
        # Create uvicorn config explicitly
        config = uvicorn.Config(
            "ai_agent.main:app",
            host=host,
            port=port,
            workers=1,
            log_level="info",
            access_log=True,
        )

        # Create and run the server
        server = uvicorn.Server(config)
        print(f"🔍 Server config created: host={host}, port={port}")
        print("🔍 Starting server...")

        server.run()

    except Exception as e:
        print(f"❌ Failed to start uvicorn: {e}")
        import traceback

        traceback.print_exc()
        raise


def dev_main() -> None:
    """Development entry point with hot reload."""
    import uvicorn
    import atexit
    import asyncio

    # Register cleanup function
    atexit.register(lambda: asyncio.run(shutdown_container()))

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 Starting FastAPI server (dev mode) on host={host} port={port}")
    uvicorn.run(
        "ai_agent.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug",
        access_log=True,
    )


if __name__ == "__main__":
    dev_main()
