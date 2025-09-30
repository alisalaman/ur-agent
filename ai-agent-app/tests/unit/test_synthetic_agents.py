"""Test synthetic agent functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from ai_agent.core.agents.synthetic_representative import (
    PersonaType,
)
from ai_agent.core.agents.personas import BankRepAgent
from ai_agent.core.agents.persona_factory import PersonaAgentFactory


class TestSyntheticAgents:
    """Test synthetic agent functionality."""

    @pytest.fixture
    def mock_llm_provider(self):
        provider = Mock()
        provider.generate_response = AsyncMock(
            return_value=Mock(content="Test response")
        )
        return provider

    @pytest.fixture
    def mock_tool_registry(self):
        registry = Mock()
        registry.execute_tool = AsyncMock(
            return_value=Mock(
                success=True,
                result={
                    "results": [{"content": "Test evidence", "relevance_score": 0.8}]
                },
            )
        )
        return registry

    @pytest.fixture
    def bank_rep_agent(self, mock_llm_provider, mock_tool_registry):
        return BankRepAgent(uuid4(), mock_llm_provider, mock_tool_registry)

    def test_agent_creation(self, bank_rep_agent):
        """Test agent creation and configuration."""
        assert bank_rep_agent.persona_config.persona_type == PersonaType.BANK_REP
        assert "BankRep" in bank_rep_agent.persona_config.system_prompt
        assert (
            "Cost-consciousness and ROI requirements"
            in bank_rep_agent.persona_config.core_perspectives
        )

    def test_evidence_query_identification(self, bank_rep_agent):
        """Test evidence query identification."""
        query = "What are the commercial sustainability concerns?"
        evidence_queries = asyncio.run(bank_rep_agent._identify_evidence_queries(query))

        assert len(evidence_queries) > 0
        assert any("commercial" in eq.topic for eq in evidence_queries)

    @pytest.mark.asyncio
    async def test_query_processing(self, bank_rep_agent):
        """Test query processing with evidence gathering."""
        query = "What are the cost concerns with Digital Financial Services?"

        response = await bank_rep_agent.process_query(query)

        assert response is not None
        assert len(response) > 0
        # Verify tool was called for evidence gathering
        bank_rep_agent.tool_registry.execute_tool.assert_called()

    def test_persona_specific_insights(self, bank_rep_agent):
        """Test persona-specific insight generation."""
        evidence = [
            {"content": "The costs have been enormous - over £1.5 billion"},
            {"content": "We need sustainable commercial models"},
        ]

        insights = bank_rep_agent.get_persona_specific_insights(evidence)

        assert "cost" in insights.lower()
        assert "considerations" in insights.lower()

    @pytest.mark.asyncio
    async def test_agent_factory(self, mock_tool_registry):
        """Test agent factory functionality."""
        factory = PersonaAgentFactory(mock_tool_registry)
        await factory.initialize("anthropic")

        # Create all personas
        agents = await factory.create_all_personas()

        assert len(agents) == 3
        assert PersonaType.BANK_REP in agents
        assert PersonaType.TRADE_BODY_REP in agents
        assert PersonaType.PAYMENTS_ECOSYSTEM_REP in agents
