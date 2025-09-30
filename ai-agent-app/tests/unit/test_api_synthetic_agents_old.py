"""Unit tests for synthetic agents API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch

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

        # Request without context
        request = SecureAgentQueryRequest(query="Test query", persona_type="BankRep")
        assert request.context is None

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

    def test_multi_agent_query_request_validation(self):
        """Test multi-agent query request model validation."""
        # Valid request with include_personas
        request = SecureMultiAgentQueryRequest(
            query="Test query", include_personas=["BankRep", "TradeBodyRep"]
        )
        assert request.query == "Test query"
        assert request.include_personas == ["BankRep", "TradeBodyRep"]

        # Request without include_personas
        request = SecureMultiAgentQueryRequest(query="Test query")
        assert request.include_personas is None

    def test_multi_agent_query_response_creation(self):
        """Test multi-agent query response model creation."""
        responses = {"BankRep": "Bank response", "TradeBodyRep": "Trade response"}
        response = MultiAgentQueryResponse(
            responses=responses, processing_time_ms=200, total_evidence_count=10
        )
        assert response.responses == responses
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
    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    async def test_get_persona_service_initialization(
        self, mock_get_container, mock_dependency_container, mock_persona_service
    ):
        """Test persona service initialization."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        service = await get_persona_service()

        # The service should be the mock service
        assert service == mock_persona_service
        mock_dependency_container.get_persona_service.assert_called_once()

    @pytest.mark.asyncio
    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    async def test_get_persona_service_existing(
        self, mock_get_container, mock_dependency_container, mock_persona_service
    ):
        """Test getting existing persona service."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        service = await get_persona_service()
        assert service == mock_persona_service

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_query_agent_success(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test successful agent query."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        # Ensure the mocks are properly configured
        mock_persona_service.process_query = AsyncMock(return_value="Test response")
        mock_persona_service.get_agent_status = AsyncMock(
            return_value={"cache_size": 5}
        )

        response = client.post(
            "/api/v1/synthetic-agents/query",
            json={
                "query": "Test query",
                "persona_type": "BankRep",
                "context": {"key": "value"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert data["persona_type"] == "BankRep"
        assert data["evidence_count"] == 5
        assert "processing_time_ms" in data

    def test_query_agent_invalid_persona_type(self, client):
        """Test agent query with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/query",
            json={"query": "Test query", "persona_type": "InvalidPersona"},
        )

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

        # Ensure the mocks are properly configured
        mock_persona_service.process_query = AsyncMock(
            side_effect=Exception("Service error")
        )
        mock_persona_service.get_agent_status = AsyncMock(
            return_value={"cache_size": 0}
        )

        response = client.post(
            "/api/v1/synthetic-agents/query",
            json={"query": "Test query", "persona_type": "BankRep"},
        )

        assert response.status_code == 500
        assert "An unexpected error occurred" in response.json()["detail"]

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_query_all_agents_success(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test successful multi-agent query."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        # Ensure the mocks are properly configured
        mock_persona_service.process_query_all_personas = AsyncMock(
            return_value={
                PersonaType.BANK_REP: QueryResult(
                    success=True, response="Bank response", persona_type="BankRep"
                ),
                PersonaType.TRADE_BODY_REP: QueryResult(
                    success=True, response="Trade response", persona_type="TradeBodyRep"
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

        assert response.status_code == 200
        data = response.json()
        assert "BankRep" in data["responses"]
        assert "TradeBodyRep" in data["responses"]
        assert data["responses"]["BankRep"] == "Bank response"
        assert data["responses"]["TradeBodyRep"] == "Trade response"
        assert "processing_time_ms" in data

    def test_query_all_agents_invalid_persona_type(self, client):
        """Test multi-agent query with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/query-all",
            json={"query": "Test query", "include_personas": ["InvalidPersona"]},
        )

        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_get_agent_status_success(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test successful agent status retrieval."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        # Ensure the mocks are properly configured
        mock_persona_service.get_all_agent_status = AsyncMock(
            return_value={
                PersonaType.BANK_REP: {
                    "persona_type": "BankRep",
                    "status": "idle",
                    "conversation_length": 5,
                    "cache_size": 10,
                },
                PersonaType.TRADE_BODY_REP: {
                    "persona_type": "TradeBodyRep",
                    "status": "processing",
                    "conversation_length": 3,
                    "cache_size": 7,
                },
            }
        )

        response = client.get("/api/v1/synthetic-agents/status")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(agent["persona_type"] == "BankRep" for agent in data)
        assert any(agent["persona_type"] == "TradeBodyRep" for agent in data)

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

        # Ensure the mocks are properly configured
        mock_persona_service.clear_agent_cache = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/synthetic-agents/clear-cache?persona_type=BankRep"
        )

        assert response.status_code == 200
        data = response.json()
        assert "Cache cleared for BankRep" in data["message"]
        mock_persona_service.clear_agent_cache.assert_called_once_with(
            PersonaType.BANK_REP
        )

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

        # Ensure the mocks are properly configured
        mock_persona_service.clear_agent_cache = AsyncMock(return_value=None)

        response = client.post("/api/v1/synthetic-agents/clear-cache")

        assert response.status_code == 200
        data = response.json()
        assert "Cache cleared for all agents" in data["message"]
        mock_persona_service.clear_agent_cache.assert_called_once_with()

    def test_clear_agent_cache_invalid_persona_type(self, client):
        """Test clearing cache with invalid persona type."""
        response = client.post(
            "/api/v1/synthetic-agents/clear-cache?persona_type=InvalidPersona"
        )

        assert response.status_code == 400
        assert "Invalid persona type" in response.json()["detail"]

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

        # Ensure the mocks are properly configured
        mock_persona_service.health_check = AsyncMock(
            return_value={
                "status": "initialized",
                "healthy": True,
                "agent_count": 3,
            }
        )

        response = client.get("/api/v1/synthetic-agents/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"
        assert data["healthy"] is True
        assert data["agent_count"] == 3

    @patch("ai_agent.api.v1.synthetic_agents.get_container")
    def test_health_check_error(
        self,
        mock_get_container,
        client,
        mock_dependency_container,
        mock_persona_service,
    ):
        """Test health check with error."""
        mock_dependency_container.get_persona_service.return_value = (
            mock_persona_service
        )
        mock_get_container.return_value = mock_dependency_container

        # Ensure the mocks are properly configured
        mock_persona_service.health_check = AsyncMock(
            side_effect=Exception("Health check failed")
        )

        response = client.get("/api/v1/synthetic-agents/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["healthy"] is False
        assert "error" in data

    def test_get_available_personas(self, client):
        """Test getting available personas."""
        response = client.get("/api/v1/synthetic-agents/personas")

        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
        assert "descriptions" in data
        assert "BankRep" in data["personas"]
        assert "TradeBodyRep" in data["personas"]
        assert "PaymentsEcosystemRep" in data["personas"]
