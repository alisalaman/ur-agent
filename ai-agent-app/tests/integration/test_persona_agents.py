"""Integration tests for persona agents with MCP server."""

import pytest
import pytest_asyncio
from unittest.mock import patch

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType
from ai_agent.infrastructure.mcp.tool_registry import ToolExecutionResult


class TestPersonaAgentMCPIntegration:
    """Test integration between persona agents and MCP server."""

    @pytest_asyncio.fixture
    async def persona_service(self, mock_tool_registry):
        """Create persona service with mocked LLM provider."""
        service = PersonaAgentService(mock_tool_registry)

        # Mock LLM provider only - let the factory work normally
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            # Create a proper mock LLM provider
            from ai_agent.infrastructure.llm.mock_client import MockLLMProvider

            mock_llm = MockLLMProvider({"default_model": "mock-model"})

            # Mock the generate method to return the expected response
            async def mock_generate(request):
                from ai_agent.infrastructure.llm.base import LLMResponse

                return LLMResponse(
                    content="Test response based on evidence",
                    model=request.model,
                    provider="mock",
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    },
                    metadata={},
                )

            mock_llm.generate = mock_generate
            mock_get_llm.return_value = mock_llm

            await service.initialize("anthropic")

        return service

    @pytest.mark.asyncio
    async def test_bank_rep_evidence_gathering(
        self, persona_service, mock_tool_registry
    ):
        """Test BankRep agent evidence gathering from MCP server."""
        query = "What are the cost considerations for new Smart Data schemes?"

        # Debug: Check what topics are extracted
        agent = persona_service.agents[PersonaType.BANK_REP]
        topics = agent._extract_topics_from_query(query)
        print(f"Extracted topics: {topics}")

        # Debug: Check evidence queries
        evidence_queries = await agent._identify_evidence_queries(query)
        print(f"Evidence queries: {evidence_queries}")

        response = await persona_service.process_query(PersonaType.BANK_REP, query)

        # Debug: Check call status
        print(f"Tool registry called: {agent.tool_registry.execute_tool.called}")
        print(f"Call count: {agent.tool_registry.execute_tool.call_count}")

        # Verify tool was called with correct arguments
        # Use the actual tool registry that the agent is using
        agent_tool_registry = agent.tool_registry
        agent_tool_registry.execute_tool.assert_called()
        call_args = agent_tool_registry.execute_tool.call_args

        assert call_args[1]["tool_name"] == "get_stakeholder_views"
        assert (
            "commercial sustainability" in call_args[1]["arguments"]["topic"]
            or "cost" in call_args[1]["arguments"]["topic"]
        )
        assert call_args[1]["arguments"]["stakeholder_group"] == "BankRep"
        assert call_args[1]["arguments"]["limit"] == 10
        assert call_args[1]["arguments"]["min_relevance_score"] == 0.3

        # Verify response was generated
        assert response == "Test response based on evidence"

    @pytest.mark.asyncio
    async def test_trade_body_rep_evidence_gathering(
        self, persona_service, mock_tool_registry
    ):
        """Test TradeBodyRep agent evidence gathering from MCP server."""
        query = "Is there a viable business case for this scheme?"

        response = await persona_service.process_query(
            PersonaType.TRADE_BODY_REP, query
        )

        # Verify tool was called
        mock_tool_registry.execute_tool.assert_called()
        call_args = mock_tool_registry.execute_tool.call_args

        assert call_args[1]["tool_name"] == "get_stakeholder_views"
        assert call_args[1]["arguments"]["stakeholder_group"] == "TradeBodyRep"

        # Verify response was generated
        assert response == "Test response based on evidence"

    @pytest.mark.asyncio
    async def test_payments_ecosystem_rep_evidence_gathering(
        self, persona_service, mock_tool_registry
    ):
        """Test PaymentsEcosystemRep agent evidence gathering from MCP server."""
        query = "How can we ensure cross-sector interoperability?"

        response = await persona_service.process_query(
            PersonaType.PAYMENTS_ECOSYSTEM_REP, query
        )

        # Verify tool was called
        mock_tool_registry.execute_tool.assert_called()
        call_args = mock_tool_registry.execute_tool.call_args

        assert call_args[1]["tool_name"] == "get_stakeholder_views"
        assert call_args[1]["arguments"]["stakeholder_group"] == "PaymentsEcosystemRep"

        # Verify response was generated
        assert response == "Test response based on evidence"

    @pytest.mark.asyncio
    async def test_evidence_caching(self, persona_service, mock_tool_registry):
        """Test that evidence is cached between queries."""
        query = "What are the governance requirements?"

        # First query
        response1 = await persona_service.process_query(PersonaType.BANK_REP, query)

        # Second query with same topic
        response2 = await persona_service.process_query(PersonaType.BANK_REP, query)

        # Tool should be called once (cached on second call)
        assert mock_tool_registry.execute_tool.call_count == 1

        # Verify responses are generated
        assert response1 == "Test response based on evidence"
        assert response2 == "Test response based on evidence"

    @pytest.mark.asyncio
    async def test_multi_persona_query_processing(
        self, persona_service, mock_tool_registry
    ):
        """Test processing query with all personas concurrently."""
        query = "What are the key considerations for implementing this scheme?"

        responses = await persona_service.process_query_all_personas(query)

        # Verify all personas responded
        assert len(responses) == 3
        assert PersonaType.BANK_REP in responses
        assert PersonaType.TRADE_BODY_REP in responses
        assert PersonaType.PAYMENTS_ECOSYSTEM_REP in responses

        # Verify all responses are generated
        for response in responses.values():
            assert response.success is True
            assert response.response == "Test response based on evidence"

        # Verify tool was called for each persona
        assert mock_tool_registry.execute_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_execution_failure_handling(self, mock_tool_registry):
        """Test handling of tool execution failures."""
        # Mock tool failure
        mock_tool_registry.execute_tool.return_value = ToolExecutionResult(
            success=False, error="MCP server unavailable"
        )

        service = PersonaAgentService(mock_tool_registry)

        # Mock LLM provider
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            # Create a proper mock LLM provider
            from ai_agent.infrastructure.llm.mock_client import MockLLMProvider

            mock_llm = MockLLMProvider({"default_model": "mock-model"})

            # Mock the generate method to return the expected response
            async def mock_generate(request):
                from ai_agent.infrastructure.llm.base import LLMResponse

                return LLMResponse(
                    content="Fallback response due to tool failure",
                    model=request.model,
                    provider="mock",
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    },
                    metadata={},
                )

            mock_llm.generate = mock_generate
            mock_get_llm.return_value = mock_llm

            await service.initialize("anthropic")

        query = "What are the cost considerations?"
        response = await service.process_query(PersonaType.BANK_REP, query)

        # Should still generate response despite tool failure
        assert "Fallback response due to tool failure" in response

    @pytest.mark.asyncio
    async def test_evidence_quality_filtering(self, mock_tool_registry):
        """Test that evidence is filtered by relevance score."""
        # Mock tool with mixed quality results
        mock_tool_registry.execute_tool.return_value = ToolExecutionResult(
            success=True,
            result={
                "results_count": 5,
                "results": [
                    {
                        "speaker_name": "BankRep",
                        "content": "High relevance evidence",
                        "relevance_score": 0.9,
                        "stakeholder_group": "BankRep",
                    },
                    {
                        "speaker_name": "BankRep",
                        "content": "Medium relevance evidence",
                        "relevance_score": 0.6,
                        "stakeholder_group": "BankRep",
                    },
                    {
                        "speaker_name": "BankRep",
                        "content": "Low relevance evidence",
                        "relevance_score": 0.2,
                        "stakeholder_group": "BankRep",
                    },
                ],
            },
        )

        service = PersonaAgentService(mock_tool_registry)

        # Mock LLM provider
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            # Create a proper mock LLM provider
            from ai_agent.infrastructure.llm.mock_client import MockLLMProvider

            mock_llm = MockLLMProvider({"default_model": "mock-model"})

            # Mock the generate method to return the expected response
            async def mock_generate(request):
                from ai_agent.infrastructure.llm.base import LLMResponse

                return LLMResponse(
                    content="Response with filtered evidence",
                    model=request.model,
                    provider="mock",
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    },
                    metadata={},
                )

            mock_llm.generate = mock_generate
            mock_get_llm.return_value = mock_llm

            await service.initialize("anthropic")

        query = "What are the cost considerations?"
        response = await service.process_query(PersonaType.BANK_REP, query)

        # Verify tool was called with minimum relevance score
        call_args = mock_tool_registry.execute_tool.call_args
        assert call_args[1]["arguments"]["min_relevance_score"] == 0.3

        # Verify response was generated
        assert response == "Response with filtered evidence"

    @pytest.mark.asyncio
    async def test_agent_status_tracking(self, persona_service):
        """Test that agent status is properly tracked during processing."""
        # Get agent status before processing
        status_before = await persona_service.get_agent_status(PersonaType.BANK_REP)
        assert status_before["status"] == "idle"

        # Process a query
        query = "What are the governance requirements?"
        response = await persona_service.process_query(PersonaType.BANK_REP, query)

        # Get agent status after processing
        status_after = await persona_service.get_agent_status(PersonaType.BANK_REP)
        assert status_after["status"] == "completed"
        assert status_after["conversation_length"] > 0

        # Verify response was generated
        assert response == "Test response based on evidence"

    @pytest.mark.asyncio
    async def test_cache_clearing(self, persona_service):
        """Test that evidence cache can be cleared."""
        # Process a query to populate cache
        query = "What are the cost considerations?"
        await persona_service.process_query(PersonaType.BANK_REP, query)

        # Get cache size before clearing
        status_before = await persona_service.get_agent_status(PersonaType.BANK_REP)
        cache_size_before = status_before["cache_size"]

        # Clear cache
        await persona_service.clear_agent_cache(PersonaType.BANK_REP)

        # Get cache size after clearing
        status_after = await persona_service.get_agent_status(PersonaType.BANK_REP)
        cache_size_after = status_after["cache_size"]

        # Cache should be empty
        assert cache_size_after == 0
        assert cache_size_before > 0

    @pytest.mark.asyncio
    async def test_health_check_integration(self, persona_service):
        """Test health check with MCP integration."""
        health = await persona_service.health_check()

        assert health["status"] == "initialized"
        assert health["healthy"] is True
        assert health["agent_count"] == 3
        assert "BankRep" in health["agent_health"]
        assert "TradeBodyRep" in health["agent_health"]
        assert "PaymentsEcosystemRep" in health["agent_health"]

        # All agents should be healthy
        for agent_health in health["agent_health"].values():
            assert agent_health is True

    @pytest.mark.asyncio
    async def test_concurrent_query_processing(
        self, persona_service, mock_tool_registry
    ):
        """Test concurrent processing of multiple queries."""
        import asyncio

        queries = [
            "What are the cost considerations?",
            "Is there a business case?",
            "How can we ensure interoperability?",
        ]

        # Process queries concurrently
        tasks = [
            persona_service.process_query(PersonaType.BANK_REP, queries[0]),
            persona_service.process_query(PersonaType.TRADE_BODY_REP, queries[1]),
            persona_service.process_query(
                PersonaType.PAYMENTS_ECOSYSTEM_REP, queries[2]
            ),
        ]

        responses = await asyncio.gather(*tasks)

        # Verify all responses were generated
        assert len(responses) == 3
        for response in responses:
            assert response == "Test response based on evidence"

        # Verify tool was called for each query
        assert mock_tool_registry.execute_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_evidence_metadata_preservation(
        self, persona_service, mock_tool_registry
    ):
        """Test that evidence metadata is preserved and used correctly."""
        query = "What are the stakeholder perspectives on governance?"

        response = await persona_service.process_query(PersonaType.BANK_REP, query)

        # Verify tool was called with correct metadata
        call_args = mock_tool_registry.execute_tool.call_args
        arguments = call_args[1]["arguments"]

        assert arguments["stakeholder_group"] == "BankRep"
        assert arguments["limit"] == 10
        assert arguments["min_relevance_score"] == 0.3
        assert "governance" in arguments["topic"] or "stakeholder" in arguments["topic"]

        # Verify response was generated
        assert response == "Test response based on evidence"
