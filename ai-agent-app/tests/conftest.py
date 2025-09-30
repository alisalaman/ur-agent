"""Test configuration and fixtures."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Set required environment variables for tests
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECURITY_SECRET_KEY"] = "test-secret-key-for-testing-only-32-chars-min"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["GOOGLE_API_KEY"] = "test-google-key"

from ai_agent.main import app


@pytest.fixture
def client():
    """Create test client with proper environment setup."""
    return TestClient(app)


@pytest.fixture
def mock_persona_service():
    """Create mock persona service."""
    service = AsyncMock()
    service.initialized = True
    service.process_query = AsyncMock()
    service.process_query_all_personas = AsyncMock()
    service.get_agent_status = AsyncMock()
    service.get_all_agent_status = AsyncMock()
    service.clear_agent_cache = AsyncMock()
    service.health_check = AsyncMock()
    return service


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    return MagicMock()


@pytest.fixture
def mock_dependency_container():
    """Create mock dependency container."""
    container = AsyncMock()
    container.get_persona_service = AsyncMock()
    return container


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = AsyncMock()
    provider.generate_response = AsyncMock(return_value="Test response")
    provider.generate_streaming_response = AsyncMock()
    provider.get_models = AsyncMock(return_value=[])
    provider.health_check = AsyncMock(return_value=True)
    return provider


@pytest.fixture(autouse=True)
def override_auth_dependency():
    """Override authentication dependency for all tests."""
    from ai_agent.api.dependencies import get_current_user

    def mock_get_current_user():
        return "test-user-id"

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_llm_initialization(mock_llm_provider, request):
    """Mock LLM provider initialization for all tests except integration tests."""
    # Skip mocking for integration tests
    if "integration" in request.node.fspath.strpath:
        yield None
        return
    with (
        patch(
            "ai_agent.infrastructure.llm.factory.get_llm_provider"
        ) as mock_get_provider,
        patch(
            "ai_agent.infrastructure.llm.factory.register_llm_provider"
        ) as mock_register_provider,
        patch(
            "ai_agent.core.agents.persona_factory.PersonaAgentFactory.initialize"
        ) as mock_factory_init,
        patch(
            "ai_agent.core.agents.persona_factory.PersonaAgentFactory.create_all_personas"
        ) as mock_create_personas,
    ):
        mock_get_provider.return_value = mock_llm_provider
        mock_register_provider.return_value = "test-provider-id"
        mock_factory_init.return_value = None  # Mock the factory initialization

        # Mock the create_all_personas method to return mock agents
        from ai_agent.core.agents.synthetic_representative import PersonaType

        mock_agents = {
            PersonaType.BANK_REP: AsyncMock(),
            PersonaType.TRADE_BODY_REP: AsyncMock(),
            PersonaType.PAYMENTS_ECOSYSTEM_REP: AsyncMock(),
        }
        mock_create_personas.return_value = mock_agents

        yield mock_get_provider
