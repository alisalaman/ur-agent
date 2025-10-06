#!/usr/bin/env python3
"""Debug script to test production environment setup."""

import os
import sys
import asyncio
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

print("🔍 Production Environment Debug Script")
print("=" * 50)

# Check environment variables
print("🔍 Environment Variables:")
print(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"  PORT: {os.getenv('PORT', 'not set')}")
print(f"  HOST: {os.getenv('HOST', 'not set')}")
print(f"  PYTHONPATH: {os.getenv('PYTHONPATH', 'not set')}")
print(f"  OPENAI_API_KEY: {'set' if os.getenv('OPENAI_API_KEY') else 'not set'}")
print(f"  ANTHROPIC_API_KEY: {'set' if os.getenv('ANTHROPIC_API_KEY') else 'not set'}")
print(f"  GOOGLE_API_KEY: {'set' if os.getenv('GOOGLE_API_KEY') else 'not set'}")
print(f"  DATABASE_HOST: {os.getenv('DATABASE_HOST', 'not set')}")
print(f"  DATABASE_NAME: {os.getenv('DATABASE_NAME', 'not set')}")
print(f"  DATABASE_USER: {os.getenv('DATABASE_USER', 'not set')}")
print(f"  DATABASE_PORT: {os.getenv('DATABASE_PORT', 'not set')}")
print(f"  REDIS_HOST: {os.getenv('REDIS_HOST', 'not set')}")
print(f"  REDIS_PORT: {os.getenv('REDIS_PORT', 'not set')}")
print(f"  USE_DATABASE: {os.getenv('USE_DATABASE', 'not set')}")
print(f"  USE_REDIS: {os.getenv('USE_REDIS', 'not set')}")

# Test imports
print("\n🔍 Testing Imports:")
try:

    print("✅ Main app imported successfully")
except Exception as e:
    print(f"❌ Failed to import main app: {e}")
    import traceback

    traceback.print_exc()

try:

    print("✅ LLM factory imported successfully")
except Exception as e:
    print(f"❌ Failed to import LLM factory: {e}")

try:

    print("✅ Persona service imported successfully")
except Exception as e:
    print(f"❌ Failed to import persona service: {e}")

# Test LLM provider registration
print("\n🔍 Testing LLM Provider Registration:")


async def test_llm_registration():
    try:
        from ai_agent.infrastructure.llm.factory import register_llm_provider
        from ai_agent.infrastructure.llm.base import LLMProviderType

        # Test OpenAI registration
        openai_key = os.getenv("OPENAI_API_KEY")
        print(f"🔍 OpenAI API Key found: {bool(openai_key)}")
        print(f"🔍 OpenAI API Key length: {len(openai_key) if openai_key else 0}")
        print(
            f"🔍 OpenAI API Key starts with: {openai_key[:10] if openai_key else 'None'}..."
        )

        if openai_key and openai_key not in ["sk-your-openai-key", ""]:
            print(f"🔍 Testing OpenAI registration with key: {openai_key[:10]}...")
            provider_id = await register_llm_provider(
                provider_type=LLMProviderType.OPENAI,
                name="Test OpenAI Provider",
                config={
                    "api_key": openai_key,
                    "default_model": "gpt-4o",
                },
                priority=1,
            )
            print(f"✅ OpenAI provider registered with ID: {provider_id}")

            # Test getting the provider manager and listing providers
            from ai_agent.infrastructure.llm.factory import LLMProviderManager

            manager = LLMProviderManager()
            print(f"🔍 Provider manager: {manager}")
            print(f"🔍 Registered providers: {list(manager._providers.keys())}")
            print(f"🔍 Provider configs: {list(manager._configs.keys())}")

        else:
            print("⚠️  No valid OpenAI API key found")
            print(f"   Key value: {repr(openai_key)}")

    except Exception as e:
        print(f"❌ LLM registration failed: {e}")
        import traceback

        traceback.print_exc()


# Test persona service initialization
print("\n🔍 Testing Persona Service Initialization:")


async def test_persona_service():
    try:
        from ai_agent.core.agents.persona_service import PersonaAgentService
        from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

        tool_registry = ToolRegistry()
        persona_service = PersonaAgentService(tool_registry)

        print("🔍 Initializing persona service...")
        await persona_service.initialize()

        print(f"✅ Persona service initialized: {persona_service.initialized}")
        print(f"✅ Available agents: {list(persona_service.agents.keys())}")

    except Exception as e:
        print(f"❌ Persona service initialization failed: {e}")
        import traceback

        traceback.print_exc()


# Test application configuration
print("\n🔍 Testing Application Configuration:")
try:
    from ai_agent.config.settings import get_settings

    settings = get_settings()
    print(f"✅ Settings loaded: {type(settings).__name__}")
    print(f"🔍 Database host: {settings.database.host}")
    print(f"🔍 Database name: {settings.database.name}")
    print(f"🔍 Redis host: {settings.redis.host}")
    print(f"🔍 OpenAI API key configured: {bool(settings.openai_api_key)}")
    print(f"🔍 Anthropic API key configured: {bool(settings.anthropic_api_key)}")
    print(f"🔍 Google API key configured: {bool(settings.google_api_key)}")
    print(
        f"🔍 Default LLM model: {getattr(settings, 'llm', {}).get('default_model', 'not configured')}"
    )
    print(
        f"🔍 LLM temperature: {getattr(settings, 'llm', {}).get('temperature', 'not configured')}"
    )
    print(
        f"🔍 LLM max tokens: {getattr(settings, 'llm', {}).get('max_tokens', 'not configured')}"
    )

except Exception as e:
    print(f"❌ Settings loading failed: {e}")
    import traceback

    traceback.print_exc()

# Test WebSocket functionality
print("\n🔍 Testing WebSocket Setup:")
try:
    from ai_agent.api.websocket.router import (
        router as synthetic_agents_websocket_router,
    )

    print("✅ WebSocket router imported successfully")

    # Check if the router has the expected routes
    routes = [route.path for route in synthetic_agents_websocket_router.routes]
    print(f"✅ WebSocket routes: {routes}")

except Exception as e:
    print(f"❌ WebSocket setup failed: {e}")

# Test main application startup simulation
print("\n🔍 Testing Main Application Startup Simulation:")


async def test_main_app_startup():
    try:
        from ai_agent.main import startup_async

        print("🔍 Running main application startup logic...")
        await startup_async()
        print("✅ Main application startup completed successfully")

        # Check what providers are registered after startup
        from ai_agent.infrastructure.llm.factory import LLMProviderManager

        manager = LLMProviderManager()
        print(f"🔍 Final provider count: {len(manager._providers)}")
        print(f"🔍 Final provider IDs: {list(manager._providers.keys())}")
        for provider_id, provider in manager._providers.items():
            config = manager._configs.get(provider_id)
            print(
                f"  - {provider_id}: {type(provider).__name__} (priority: {config.priority if config else 'unknown'})"
            )

    except Exception as e:
        print(f"❌ Main application startup failed: {e}")
        import traceback

        traceback.print_exc()


# Run async tests
async def main():
    await test_llm_registration()
    await test_persona_service()
    await test_main_app_startup()


if __name__ == "__main__":
    asyncio.run(main())
    print("\n🎉 Debug script completed!")
