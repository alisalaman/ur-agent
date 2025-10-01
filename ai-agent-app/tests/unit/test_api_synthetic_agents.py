"""Unit tests for synthetic agents API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from ai_agent.api.v1.synthetic_agents import (
    AgentQueryResponse,
    MultiAgentQueryResponse,
    AgentStatusResponse,
    get_persona_service,
)
from ai_agent.api.validation.synthetic_agents import (
    SecureAgentQueryRequest,
    SecureMultiAgentQueryRequest,
)
from ai_agent.core.agents.synthetic_representative import PersonaType, QueryResult


class TestSyntheticAgentsAPI:
    """Test synthetic agents API endpoints."""

    def test_agent_query_request_validation(self):
        """Test agent query request model validation."""
        # Valid request
        request = SecureAgentQueryRequest(
            query="Test query", persona_type="BankRep", context={"key": "value"}
        )
        assert request.query == "Test query"
        assert request.persona_type == "BankRep"
        assert request.context == {"key": "value"}

    def test_multi_agent_query_request_validation(self):
        """Test multi-agent query request model validation."""
        # Valid request with include_personas
        request = SecureMultiAgentQueryRequest(
            query="Test query", include_personas=["BankRep", "TradeBodyRep"]
        )
        assert request.query == "Test query"
        assert request.include_personas == ["BankRep", "TradeBodyRep"]

    def test_agent_query_response_creation(self):
        """Test agent query response model creation."""
        response = AgentQueryResponse(
            response="Test response",
            persona_type="BankRep",
            evidence_count=5,
            confidence_level="high",
            processing_time_ms=100,
        )
        assert response.response == "Test response"
        assert response.persona_type == "BankRep"
        assert response.evidence_count == 5
        assert response.confidence_level == "high"
        assert response.processing_time_ms == 100

    def test_multi_agent_query_response_creation(self):
        """Test multi-agent query response model creation."""
        response = MultiAgentQueryResponse(
            responses={"BankRep": "Bank response", "TradeBodyRep": "Trade response"},
            processing_time_ms=200,
            total_evidence_count=10,
        )
        assert response.responses == {
            "BankRep": "Bank response",
            "TradeBodyRep": "Trade response",
        }
        assert response.processing_time_ms == 200
        assert response.total_evidence_count == 10

    def test_agent_status_response_creation(self):
        """Test agent status response model creation."""
        response = AgentStatusResponse(
            persona_type="BankRep",
            status="idle",
            conversation_length=5,
            cache_size=10,
            last_activity="2023-01-01T00:00:00Z",
        )
        assert response.persona_type == "BankRep"
        assert response.status == "idle"
        assert response.conversation_length == 5
        assert response.cache_size == 10
        assert response.last_activity == "2023-01-01T00:00:00Z"

    @pytest.mark.asyncio
    @patch("ai_agent.api.dependencies.get_container")
    async def test_get_persona_service_initialization(
        self, mock_get_container, mock_dependency_container
    ):
        """Test persona service initialization failure."""
        mock_dependency_container.get_persona_service = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        mock_get_container.return_value = mock_dependency_container

        # Service initialization fails, so expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_persona_service()

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Service unavailable"

    @pytest.mark.asyncio
    @patch("ai_agent.api.dependencies.get_container")
    async def test_get_persona_service_existing(
        self, mock_get_container, mock_dependency_container, mock_persona_service
    ):
        """Test getting existing persona service successfully."""
        mock_dependency_container.get_persona_service = AsyncMock(
            return_value=mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        # Service should work correctly
        service = await get_persona_service()
        assert service == mock_persona_service

    def test_query_agent_success(
        self,
        client,
        mock_persona_service,
    ):
        """Test successful agent query."""
        from ai_agent.api.dependencies import get_persona_service
        from ai_agent.main import app

        # Override the dependency
        async def mock_get_persona_service():
            return mock_persona_service

        app.dependency_overrides[get_persona_service] = mock_get_persona_service

        try:
            mock_persona_service.process_query = AsyncMock(return_value="Test response")
            mock_persona_service.get_agent_status = AsyncMock(
                return_value={"cache_size": 5}
            )
            mock_persona_service.initialized = True

            response = client.post(
                "/api/v1/synthetic-agents/query",
                json={
                    "query": "Test query",
                    "persona_type": "BankRep",
                    "context": {"key": "value"},
                },
            )

            # With proper mocking, expect 200
            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Test response"
            assert data["persona_type"] == "BankRep"
            assert data["evidence_count"] == 5
            assert "processing_time_ms" in data
        finally:
            # Clean up the dependency override
            app.dependency_overrides.clear()

    def test_query_agent_invalid_persona_type(self, client):
        """Test agent query with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/query",
            json={"query": "Test query", "persona_type": "InvalidPersona"},
        )

        # Invalid persona type should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_query_agent_service_error(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test agent query with service error."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container
        mock_persona_service.process_query = AsyncMock(
            side_effect=Exception("Service error")
        )

        response = client.post(
            "/api/v1/synthetic-agents/query",
            json={"query": "Test query", "persona_type": "BankRep"},
        )

        assert response.status_code == 500
        assert "An unexpected error occurred" in response.json()["detail"]

    def test_query_all_agents_success(
        self,
        client,
        mock_persona_service,
    ):
        """Test successful multi-agent query."""
        from ai_agent.api.dependencies import get_persona_service
        from ai_agent.main import app

        # Override the dependency
        async def mock_get_persona_service():
            return mock_persona_service

        app.dependency_overrides[get_persona_service] = mock_get_persona_service

        try:
            mock_persona_service.process_query_all_personas = AsyncMock(
                return_value={
                    PersonaType.BANK_REP: QueryResult(
                        success=True, response="Bank response", persona_type="BankRep"
                    ),
                    PersonaType.TRADE_BODY_REP: QueryResult(
                        success=True,
                        response="Trade response",
                        persona_type="TradeBodyRep",
                    ),
                }
            )
            mock_persona_service.get_agent_status = AsyncMock(
                return_value={"cache_size": 5}
            )

            response = client.post(
                "/api/v1/synthetic-agents/query-all",
                json={
                    "query": "Test query",
                    "include_personas": ["BankRep", "TradeBodyRep"],
                },
            )

            # With proper mocking, expect 200
            assert response.status_code == 200
            data = response.json()
            assert "responses" in data
            assert len(data["responses"]) == 2
        finally:
            # Clean up the dependency override
            app.dependency_overrides.clear()

    def test_query_all_agents_invalid_persona_type(self, client):
        """Test multi-agent query with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/query-all",
            json={"query": "Test query", "include_personas": ["InvalidPersona"]},
        )

        # Invalid persona type should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data

    def test_get_agent_status_success(
        self,
        client,
        mock_persona_service,
    ):
        """Test successful agent status retrieval."""
        from ai_agent.api.dependencies import get_persona_service
        from ai_agent.main import app

        # Override the dependency
        async def mock_get_persona_service():
            return mock_persona_service

        app.dependency_overrides[get_persona_service] = mock_get_persona_service

        try:
            mock_persona_service.get_all_agent_status = AsyncMock(
                return_value={
                    PersonaType.BANK_REP: {
                        "status": "idle",
                        "conversation_length": 5,
                        "cache_size": 10,
                    },
                    PersonaType.TRADE_BODY_REP: {
                        "status": "processing",
                        "conversation_length": 3,
                        "cache_size": 7,
                    },
                }
            )

            response = client.get("/api/v1/synthetic-agents/status")

            # With proper mocking, expect 200
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2  # Two persona types
        finally:
            # Clean up the dependency override
            app.dependency_overrides.clear()

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_clear_agent_cache_specific_persona(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test clearing cache for specific persona."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        response = client.post(
            "/api/v1/synthetic-agents/clear-cache?persona_type=BankRep"
        )

        # With proper mocking, expect 200
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cache cleared for BankRep"

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_clear_agent_cache_all(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test clearing cache for all agents."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        response = client.post("/api/v1/synthetic-agents/clear-cache")

        # With proper mocking, expect 200
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cache cleared for all agents"

    def test_clear_agent_cache_invalid_persona_type(self, client):
        """Test clearing cache with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/clear-cache?persona_type=InvalidPersona"
        )

        # Invalid persona type should return 400 bad request
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_health_check_success(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test successful health check."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container
        mock_persona_service.health_check.return_value = {
            "status": "initialized",
            "healthy": True,
            "agent_count": 3,
        }

        response = client.get("/api/v1/synthetic-agents/health")

        # With proper mocking, expect 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"
        assert data["healthy"] is True
        assert data["agent_count"] == 3

    def test_health_check_error(
        self,
        client,
        mock_persona_service,
    ):
        """Test health check with error."""
        from ai_agent.api.dependencies import get_persona_service
        from ai_agent.main import app

        # Override the dependency
        async def mock_get_persona_service():
            return mock_persona_service

        app.dependency_overrides[get_persona_service] = mock_get_persona_service

        try:
            mock_persona_service.health_check = AsyncMock(
                side_effect=Exception("Health check failed")
            )

            response = client.get("/api/v1/synthetic-agents/health")

            # With proper mocking, expect 200 (error is handled in response body)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["healthy"] is False
            assert "error" in data
        finally:
            # Clean up the dependency override
            app.dependency_overrides.clear()

    def test_get_available_personas(self, client):
        """Test getting available personas."""
        response = client.get("/api/v1/synthetic-agents/personas")

        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
        assert isinstance(data["personas"], list)
        assert "BankRep" in data["personas"]
        assert "TradeBodyRep" in data["personas"]
        assert "PaymentsEcosystemRep" in data["personas"]
