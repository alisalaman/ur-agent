"""Unit tests for synthetic agents validation utilities."""

import pytest
from pydantic import ValidationError

from ai_agent.api.validation.synthetic_agents import (
    SecureAgentQueryRequest,
    SecureMultiAgentQueryRequest,
    validate_persona_type_string,
    sanitize_error_message,
    validate_websocket_message_size,
    validate_websocket_message_content,
)


class TestSyntheticAgentsValidation:
    """Test synthetic agents validation utilities."""

    def test_secure_agent_query_request_valid(self):
        """Test valid secure agent query request."""
        request = SecureAgentQueryRequest(
            query="What are the key concerns about digital currency?",
            persona_type="BankRep",
            context={"topic": "digital_currency"},
        )
        assert request.query == "What are the key concerns about digital currency?"
        assert request.persona_type == "BankRep"
        assert request.context == {"topic": "digital_currency"}

    def test_secure_agent_query_request_empty_query(self):
        """Test secure agent query request with empty query."""
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(query="", persona_type="BankRep")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_secure_agent_query_request_whitespace_only(self):
        """Test secure agent query request with whitespace only query."""
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(query="   ", persona_type="BankRep")
        assert "Query cannot be empty" in str(exc_info.value)

    def test_secure_agent_query_request_unsafe_characters(self):
        """Test secure agent query request with unsafe characters."""
        unsafe_queries = [
            "Query with <script>alert('xss')</script>",
            "Query with & ampersand",
            "Query with > greater than",
            'Query with " quotes',
            "Query with ' single quotes",
            "Query with \\ backslash",
            "Query with / forward slash",
            "Query with ` backtick",
        ]

        for query in unsafe_queries:
            with pytest.raises(ValidationError) as exc_info:
                SecureAgentQueryRequest(query=query, persona_type="BankRep")
            assert "unsafe character" in str(exc_info.value) or "unsafe content" in str(
                exc_info.value
            )

    def test_secure_agent_query_request_unsafe_patterns(self):
        """Test secure agent query request with unsafe patterns."""
        unsafe_queries = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:alert('xss')",
            "onclick=alert('xss')",
        ]

        for query in unsafe_queries:
            with pytest.raises(ValidationError) as exc_info:
                SecureAgentQueryRequest(query=query, persona_type="BankRep")
            assert "unsafe character" in str(exc_info.value) or "unsafe content" in str(
                exc_info.value
            )

    def test_secure_agent_query_request_invalid_persona_type(self):
        """Test secure agent query request with invalid persona type."""
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(query="Test query", persona_type="InvalidPersona")
        assert "Invalid persona type" in str(exc_info.value)

    def test_secure_agent_query_request_query_too_long(self):
        """Test secure agent query request with query too long."""
        long_query = "a" * 10001  # Exceeds MAX_QUERY_LENGTH
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(query=long_query, persona_type="BankRep")
        assert "String should have at most 10000 characters" in str(exc_info.value)

    def test_secure_agent_query_request_context_too_large(self):
        """Test secure agent query request with context too large."""
        large_context = {"key": "x" * 1001}  # Exceeds MAX_CONTEXT_SIZE
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(
                query="Test query", persona_type="BankRep", context=large_context
            )
        assert "Context too large" in str(exc_info.value)

    def test_secure_agent_query_request_invalid_context_type(self):
        """Test secure agent query request with invalid context type."""
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(
                query="Test query",
                persona_type="BankRep",
                context="invalid_context",  # Should be dict
            )
        assert "Input should be a valid dictionary" in str(exc_info.value)

    def test_secure_agent_query_request_context_unsafe_values(self):
        """Test secure agent query request with unsafe context values."""
        with pytest.raises(ValidationError) as exc_info:
            SecureAgentQueryRequest(
                query="Test query",
                persona_type="BankRep",
                context={"key": "<script>alert('xss')</script>"},
            )
        assert "unsafe character" in str(exc_info.value)

    def test_secure_multi_agent_query_request_valid(self):
        """Test valid secure multi-agent query request."""
        request = SecureMultiAgentQueryRequest(
            query="How should cross-border payments be regulated?",
            include_personas=["BankRep", "TradeBodyRep"],
        )
        assert request.query == "How should cross-border payments be regulated?"
        assert request.include_personas == ["BankRep", "TradeBodyRep"]

    def test_secure_multi_agent_query_request_invalid_personas(self):
        """Test secure multi-agent query request with invalid personas."""
        with pytest.raises(ValidationError) as exc_info:
            SecureMultiAgentQueryRequest(
                query="Test query", include_personas=["InvalidPersona", "BankRep"]
            )
        assert "Invalid persona type" in str(exc_info.value)

    def test_secure_multi_agent_query_request_too_many_personas(self):
        """Test secure multi-agent query request with too many personas."""
        many_personas = ["BankRep"] * 11  # Exceeds MAX_PERSONAS_COUNT
        with pytest.raises(ValidationError) as exc_info:
            SecureMultiAgentQueryRequest(
                query="Test query", include_personas=many_personas
            )
        assert "List should have at most 10 items" in str(exc_info.value)

    def test_validate_persona_type_string_valid(self):
        """Test valid persona type string validation."""
        from ai_agent.core.agents.synthetic_representative import PersonaType

        result = validate_persona_type_string("BankRep")
        assert result == PersonaType.BANK_REP

    def test_validate_persona_type_string_invalid(self):
        """Test invalid persona type string validation."""
        with pytest.raises(ValueError) as exc_info:
            validate_persona_type_string("InvalidPersona")
        assert "Invalid persona type" in str(exc_info.value)

    def test_sanitize_error_message(self):
        """Test error message sanitization."""
        # Test different error types
        value_error = ValueError("Invalid input")
        runtime_error = RuntimeError("Service unavailable")
        generic_error = Exception("Internal error")

        assert sanitize_error_message(value_error) == "Invalid input provided"
        assert (
            sanitize_error_message(runtime_error) == "Service temporarily unavailable"
        )
        assert sanitize_error_message(generic_error) == "An unexpected error occurred"

    def test_validate_websocket_message_size_valid(self):
        """Test valid WebSocket message size validation."""
        small_message = "a" * 1000
        validate_websocket_message_size(small_message, 1024 * 1024)  # Should not raise

    def test_validate_websocket_message_size_too_large(self):
        """Test WebSocket message size validation with too large message."""
        large_message = "a" * (1024 * 1024 + 1)
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_size(large_message, 1024 * 1024)
        assert "Message too large" in str(exc_info.value)

    def test_validate_websocket_message_content_valid(self):
        """Test valid WebSocket message content validation."""
        valid_messages = [
            {"type": "query", "query": "Test query", "persona_type": "BankRep"},
            {"type": "query_all", "query": "Test query"},
            {"type": "status"},
            {"type": "ping"},
        ]

        for message in valid_messages:
            validate_websocket_message_content(message)  # Should not raise

    def test_validate_websocket_message_content_missing_type(self):
        """Test WebSocket message content validation with missing type."""
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_content({"query": "Test query"})
        assert "Message must contain 'type' field" in str(exc_info.value)

    def test_validate_websocket_message_content_invalid_type(self):
        """Test WebSocket message content validation with invalid type."""
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_content({"type": "invalid_type"})
        assert "Invalid message type" in str(exc_info.value)

    def test_validate_websocket_message_content_unsafe_query(self):
        """Test WebSocket message content validation with unsafe query."""
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_content(
                {
                    "type": "query",
                    "query": "<script>alert('xss')</script>",
                    "persona_type": "BankRep",
                }
            )
        assert "unsafe character" in str(exc_info.value)

    def test_validate_websocket_message_content_invalid_persona_type(self):
        """Test WebSocket message content validation with invalid persona type."""
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_content(
                {
                    "type": "query",
                    "query": "Test query",
                    "persona_type": "InvalidPersona",
                }
            )
        assert "Invalid persona type" in str(exc_info.value)

    def test_validate_websocket_message_content_query_too_long(self):
        """Test WebSocket message content validation with query too long."""
        long_query = "a" * 10001
        with pytest.raises(ValueError) as exc_info:
            validate_websocket_message_content(
                {"type": "query", "query": long_query, "persona_type": "BankRep"}
            )
        assert "Query too long" in str(exc_info.value)
