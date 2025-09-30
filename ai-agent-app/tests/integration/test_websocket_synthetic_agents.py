"""Integration tests for synthetic agents WebSocket functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from ai_agent.main import app
from ai_agent.core.agents.synthetic_representative import PersonaType, QueryResult


class TestSyntheticAgentsWebSocket:
    """Test synthetic agents WebSocket functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        """Mock authentication for all tests."""
        with patch(
            "ai_agent.api.websocket.router.websocket_auth.authenticate_websocket"
        ) as mock_auth:
            mock_auth.return_value = ("test-user-id", None)
            yield mock_auth

    @pytest.fixture(autouse=True)
    def mock_dependency_container(self, mock_persona_service):
        """Mock dependency container for all tests."""
        with patch(
            "ai_agent.api.websocket.synthetic_agents.get_persona_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_persona_service
            yield mock_get_service

    @pytest.fixture
    def mock_persona_service(self):
        """Create mock persona service."""
        service = AsyncMock()
        service.initialized = True
        service.process_query = AsyncMock()
        service.process_query_all_personas = AsyncMock()
        service.get_agent_status = AsyncMock()
        service.get_all_agent_status = AsyncMock()
        return service

    @pytest.fixture
    def mock_tool_registry(self):
        """Create mock tool registry."""
        return MagicMock()

    def test_websocket_connection_establishment(self, client):
        """Test WebSocket connection establishment."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "welcome"
            assert "Connected to synthetic agent service" in data["message"]
            assert "connection_id" in data
            assert "available_personas" in data
            assert "BankRep" in data["available_personas"]

    def test_websocket_query_message(self, client, mock_persona_service):
        """Test WebSocket query message handling."""
        mock_persona_service.process_query.return_value = "Test response"
        mock_persona_service.get_agent_status.return_value = {"cache_size": 5}

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query message
            query_message = {
                "type": "query",
                "query": "Test query",
                "persona_type": "BankRep",
                "context": {"key": "value"},
            }
            websocket.send_text(json.dumps(query_message))

            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "query_response"
            assert response["persona_type"] == "BankRep"
            assert response["response"] == "Test response"
            assert response["evidence_count"] == 5
            assert "processing_time_ms" in response

    def test_websocket_query_all_message(self, client, mock_persona_service):
        """Test WebSocket query all message handling."""
        mock_persona_service.process_query_all_personas.return_value = {
            PersonaType.BANK_REP: QueryResult(
                success=True, response="Bank response", persona_type="BankRep"
            ),
            PersonaType.TRADE_BODY_REP: QueryResult(
                success=True, response="Trade response", persona_type="TradeBodyRep"
            ),
        }
        mock_persona_service.get_agent_status.return_value = {"cache_size": 5}

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query all message
            query_all_message = {
                "type": "query_all",
                "query": "Test query",
                "include_personas": ["BankRep", "TradeBodyRep"],
            }
            websocket.send_text(json.dumps(query_all_message))

            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "query_all_response"
            assert "BankRep" in response["responses"]
            assert "TradeBodyRep" in response["responses"]
            assert response["responses"]["BankRep"] == "Bank response"
            assert response["responses"]["TradeBodyRep"] == "Trade response"
            assert "processing_time_ms" in response

    def test_websocket_status_message(self, client, mock_persona_service):
        """Test WebSocket status message handling."""
        mock_persona_service.get_all_agent_status.return_value = {
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

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send status message
            status_message = {"type": "status"}
            websocket.send_text(json.dumps(status_message))

            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "status_response"
            assert "agents" in response
            assert "BankRep" in response["agents"]
            assert "TradeBodyRep" in response["agents"]

    def test_websocket_ping_message(self, client):
        """Test WebSocket ping message handling."""
        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send ping message
            ping_message = {"type": "ping"}
            websocket.send_text(json.dumps(ping_message))

            # Receive pong response
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response

    def test_websocket_invalid_json(self, client):
        """Test WebSocket with invalid JSON message."""
        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("invalid json")

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid message" in response["message"]

    def test_websocket_unknown_message_type(self, client):
        """Test WebSocket with unknown message type."""
        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send unknown message type
            unknown_message = {"type": "unknown_type", "data": "test"}
            websocket.send_text(json.dumps(unknown_message))

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid message" in response["message"]

    def test_websocket_query_missing_parameters(self, client):
        """Test WebSocket query with missing parameters."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query without persona_type
            query_message = {"type": "query", "query": "Test query"}
            websocket.send_text(json.dumps(query_message))

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Query and persona_type are required" in response["message"]

    def test_websocket_query_invalid_persona_type(self, client):
        """Test WebSocket query with invalid persona type."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query with invalid persona type
            query_message = {
                "type": "query",
                "query": "Test query",
                "persona_type": "InvalidPersona",
            }
            websocket.send_text(json.dumps(query_message))

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid persona type" in response["message"]

    def test_websocket_query_all_missing_query(self, client):
        """Test WebSocket query all with missing query."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query all without query
            query_all_message = {"type": "query_all"}
            websocket.send_text(json.dumps(query_all_message))

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Query is required" in response["message"]

    def test_websocket_query_all_invalid_persona_type(self, client):
        """Test WebSocket query all with invalid persona type."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Receive welcome message
            websocket.receive_json()

            # Send query all with invalid persona type
            query_all_message = {
                "type": "query_all",
                "query": "Test query",
                "include_personas": ["InvalidPersona"],
            }
            websocket.send_text(json.dumps(query_all_message))

            # Receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid persona type" in response["message"]

    def test_websocket_connection_manager(self, client):
        """Test WebSocket connection manager functionality."""

        with client.websocket_connect(
            "/ws/synthetic-agents?token=test-token"
        ) as websocket:
            # Test connection establishment
            from ai_agent.api.websocket.synthetic_agents import connection_manager

            assert connection_manager.get_connection_count() > 0

            # Receive welcome message
            websocket.receive_json()

            # Test ping functionality
            ping_message = {"type": "ping"}
            websocket.send_text(json.dumps(ping_message))
            response = websocket.receive_json()
            assert response["type"] == "pong"

        # Connection should be cleaned up after context exit
        # Note: In a real test, we'd need to wait for cleanup
