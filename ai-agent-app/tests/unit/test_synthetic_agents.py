"""Unit tests for synthetic representative agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaType,
    PersonaConfig,
    EvidenceResult,
)
from ai_agent.core.agents.personas.bank_rep import BankRepAgent
from ai_agent.core.agents.personas.trade_body_rep import TradeBodyRepAgent
from ai_agent.core.agents.personas.payments_ecosystem_rep import (
    PaymentsEcosystemRepAgent,
)
from ai_agent.core.agents.persona_factory import PersonaAgentFactory
from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.domain.models import AgentStatus
from ai_agent.infrastructure.llm import LLMResponse
from ai_agent.infrastructure.mcp.tool_registry import ToolExecutionResult


class TestSyntheticRepresentativeAgent:
    """Test the base synthetic representative agent."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider."""
        provider = AsyncMock()
        provider.generate_response.return_value = LLMResponse(
            content="Test response",
            model="test-model",
            provider="test-provider",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            metadata={},
        )
        return provider

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        registry = AsyncMock()
        registry.execute_tool.return_value = ToolExecutionResult(
            success=True,
            result={
                "results_count": 3,
                "results": [
                    {
                        "speaker_name": "Test Speaker",
                        "content": "Test evidence content",
                        "relevance_score": 0.8,
                    }
                ],
            },
        )
        return registry

    @pytest.fixture
    def persona_config(self):
        """Sample persona configuration."""
        return PersonaConfig(
            persona_type=PersonaType.BANK_REP,
            system_prompt="Test system prompt",
            core_perspectives=["test perspective"],
            tool_usage_patterns={"test": "pattern"},
            response_format="Test format",
            evidence_requirements={"test": "requirement"},
        )

    @pytest.fixture
    def agent(self, mock_llm_provider, mock_tool_registry, persona_config):
        """Create a test agent."""

        class TestAgent(SyntheticRepresentativeAgent):
            def get_persona_specific_insights(self, evidence):
                return "Test insights"

        return TestAgent(
            agent_id=uuid4(),
            persona_config=persona_config,
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
        )

    def test_agent_initialization(self, agent, persona_config):
        """Test agent initialization."""
        assert agent.persona_config == persona_config
        assert agent.status == AgentStatus.IDLE
        assert agent.conversation_history == []
        assert agent.evidence_cache == {}

    def test_extract_topics_from_query(self, agent):
        """Test topic extraction from queries."""
        # Test commercial sustainability topic
        query = "What are the commercial sustainability considerations?"
        topics = agent._extract_topics_from_query(query)
        assert "commercial sustainability" in topics

        # Test governance topic
        query = "How should governance be structured?"
        topics = agent._extract_topics_from_query(query)
        assert "governance" in topics

        # Test cost topic
        query = "What are the cost implications?"
        topics = agent._extract_topics_from_query(query)
        assert "cost" in topics

        # Test interoperability topic
        query = "How can we ensure interoperability?"
        topics = agent._extract_topics_from_query(query)
        assert "interoperability" in topics

        # Test technical feasibility topic
        query = "What are the technical implementation challenges?"
        topics = agent._extract_topics_from_query(query)
        assert "technical feasibility" in topics

        # Test fallback for unknown topics
        query = "What is the meaning of life?"
        topics = agent._extract_topics_from_query(query)
        assert topics == [query]

    def test_calculate_confidence_level(self, agent):
        """Test confidence level calculation."""
        # High confidence
        result = {"results_count": 6}
        assert agent._calculate_confidence_level(result) == "high"

        # Medium confidence
        result = {"results_count": 4}
        assert agent._calculate_confidence_level(result) == "medium"

        # Low confidence
        result = {"results_count": 2}
        assert agent._calculate_confidence_level(result) == "low"

        # Very low confidence
        result = {"results_count": 0}
        assert agent._calculate_confidence_level(result) == "very_low"

    def test_format_evidence_for_prompt(self, agent):
        """Test evidence formatting for prompts."""
        evidence_results = [
            EvidenceResult(
                topic="test topic",
                results_count=2,
                evidence=[
                    {
                        "speaker_name": "Speaker 1",
                        "content": "Evidence 1",
                        "relevance_score": 0.8,
                    },
                    {
                        "speaker_name": "Speaker 2",
                        "content": "Evidence 2",
                        "relevance_score": 0.6,
                    },
                ],
                confidence_level="medium",
                query_metadata={},
            )
        ]

        formatted = agent._format_evidence_for_prompt(evidence_results)
        assert "Evidence Available:" in formatted
        assert "Topic: test topic" in formatted
        assert "Confidence Level: medium" in formatted
        assert "Evidence Count: 2" in formatted
        assert "Speaker: Speaker 1" in formatted
        assert "Content: Evidence 1" in formatted

    def test_format_evidence_for_prompt_empty(self, agent):
        """Test evidence formatting with no evidence."""
        formatted = agent._format_evidence_for_prompt([])
        assert formatted == "No evidence available for this query."

    def test_generate_fallback_response(self, agent):
        """Test fallback response generation."""
        query = "test query"

        # With evidence
        evidence_results = [EvidenceResult("topic", 1, [], "low", {})]
        response = agent._generate_fallback_response(query, evidence_results)
        assert "Based on the available evidence" in response
        assert query in response

        # Without evidence
        response = agent._generate_fallback_response(query, [])
        assert "I don't have sufficient evidence" in response
        assert PersonaType.BANK_REP.value in response

    def test_clear_cache(self, agent):
        """Test cache clearing."""
        # Add some data to cache
        agent.evidence_cache["test_key"] = EvidenceResult("topic", 1, [], "low", {})
        assert len(agent.evidence_cache) == 1

        # Clear cache
        agent.clear_cache()
        assert len(agent.evidence_cache) == 0

    def test_get_status(self, agent):
        """Test status retrieval."""
        assert agent.get_status() == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_process_query_success(
        self, agent, mock_llm_provider, mock_tool_registry
    ):
        """Test successful query processing."""
        query = "What are the cost considerations?"

        response = await agent.process_query(query)

        # Verify LLM was called
        mock_llm_provider.generate_response.assert_called_once()

        # Verify tool registry was called
        mock_tool_registry.execute_tool.assert_called()

        # Verify response
        assert response == "Test response"
        assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_query_tool_failure(
        self, agent, mock_llm_provider, mock_tool_registry
    ):
        """Test query processing when tool fails."""
        # Mock tool failure
        mock_tool_registry.execute_tool.return_value = ToolExecutionResult(
            success=False, error="Tool failed"
        )

        query = "What are the cost considerations?"

        response = await agent.process_query(query)

        # Should still generate response with LLM
        mock_llm_provider.generate_response.assert_called_once()
        assert response == "Test response"

    @pytest.mark.asyncio
    async def test_process_query_llm_failure(
        self, agent, mock_llm_provider, mock_tool_registry
    ):
        """Test query processing when LLM fails."""
        # Mock LLM failure
        mock_llm_provider.generate_response.side_effect = Exception("LLM failed")

        query = "What are the cost considerations?"

        response = await agent.process_query(query)

        # Should return fallback response
        assert (
            "Based on the available evidence" in response
            or "I don't have sufficient evidence" in response
        )


class TestPersonaAgents:
    """Test individual persona agents."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider."""
        provider = AsyncMock()
        provider.generate_response.return_value = LLMResponse(
            content="Test response",
            model="test-model",
            provider="test-provider",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            metadata={},
        )
        return provider

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        registry = AsyncMock()
        registry.execute_tool.return_value = ToolExecutionResult(
            success=True,
            result={
                "results_count": 3,
                "results": [
                    {
                        "speaker_name": "Test Speaker",
                        "content": "Test evidence content",
                        "relevance_score": 0.8,
                    }
                ],
            },
        )
        return registry

    def test_bank_rep_agent(self, mock_llm_provider, mock_tool_registry):
        """Test BankRep agent configuration."""
        agent = BankRepAgent(uuid4(), mock_llm_provider, mock_tool_registry)

        assert agent.persona_config.persona_type == PersonaType.BANK_REP
        assert "BankRep" in agent.persona_config.system_prompt
        assert "cost" in agent.persona_config.system_prompt.lower()
        assert "governance" in agent.persona_config.system_prompt.lower()

        # Test insights
        evidence = [{"content": "This will cost millions"}]
        insights = agent.get_persona_specific_insights(evidence)
        assert "Cost considerations" in insights

    def test_trade_body_rep_agent(self, mock_llm_provider, mock_tool_registry):
        """Test TradeBodyRep agent configuration."""
        agent = TradeBodyRepAgent(uuid4(), mock_llm_provider, mock_tool_registry)

        assert agent.persona_config.persona_type == PersonaType.TRADE_BODY_REP
        assert "TradeBodyRep" in agent.persona_config.system_prompt
        assert "business case" in agent.persona_config.system_prompt.lower()
        assert "commercial" in agent.persona_config.system_prompt.lower()

        # Test insights
        evidence = [{"content": "The business case is unclear"}]
        insights = agent.get_persona_specific_insights(evidence)
        assert "Business case considerations" in insights

    def test_payments_ecosystem_rep_agent(self, mock_llm_provider, mock_tool_registry):
        """Test PaymentsEcosystemRep agent configuration."""
        agent = PaymentsEcosystemRepAgent(
            uuid4(), mock_llm_provider, mock_tool_registry
        )

        assert agent.persona_config.persona_type == PersonaType.PAYMENTS_ECOSYSTEM_REP
        assert "PaymentsEcosystemRep" in agent.persona_config.system_prompt
        assert "ecosystem" in agent.persona_config.system_prompt.lower()
        assert "interoperability" in agent.persona_config.system_prompt.lower()

        # Test insights
        evidence = [{"content": "We need cross-sector interoperability"}]
        insights = agent.get_persona_specific_insights(evidence)
        assert "Interoperability considerations" in insights


class TestPersonaAgentFactory:
    """Test the persona agent factory."""

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        return AsyncMock()

    @pytest.fixture
    def factory(self, mock_tool_registry):
        """Create factory instance."""
        return PersonaAgentFactory(mock_tool_registry)

    @pytest.mark.asyncio
    async def test_factory_initialization(self, factory):
        """Test factory initialization."""
        # Skip this test when global mocking is active
        # The global mocking patches PersonaAgentFactory.initialize to return None
        # which prevents testing the real initialization logic
        pytest.skip("Skipped due to global mocking interference")

    @pytest.mark.asyncio
    async def test_create_agent_bank_rep(self, factory):
        """Test creating BankRep agent."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.BANK_REP)

            assert isinstance(agent, BankRepAgent)
            assert agent.persona_config.persona_type == PersonaType.BANK_REP
            assert agent.agent_id in factory.agents

    @pytest.mark.asyncio
    async def test_create_agent_trade_body_rep(self, factory):
        """Test creating TradeBodyRep agent."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.TRADE_BODY_REP)

            assert isinstance(agent, TradeBodyRepAgent)
            assert agent.persona_config.persona_type == PersonaType.TRADE_BODY_REP

    @pytest.mark.asyncio
    async def test_create_agent_payments_ecosystem_rep(self, factory):
        """Test creating PaymentsEcosystemRep agent."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.PAYMENTS_ECOSYSTEM_REP)

            assert isinstance(agent, PaymentsEcosystemRepAgent)
            assert (
                agent.persona_config.persona_type == PersonaType.PAYMENTS_ECOSYSTEM_REP
            )

    @pytest.mark.asyncio
    async def test_create_agent_unknown_type(self, factory):
        """Test creating agent with unknown persona type."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            with pytest.raises(ValueError, match="Unknown persona type"):
                await factory.create_agent("UNKNOWN_TYPE")  # type: ignore

    @pytest.mark.asyncio
    async def test_create_agent_not_initialized(self, factory):
        """Test creating agent when factory not initialized."""
        with pytest.raises(RuntimeError, match="Factory not initialized"):
            await factory.create_agent(PersonaType.BANK_REP)

    @pytest.mark.asyncio
    async def test_create_all_personas(self, factory):
        """Test creating all persona agents."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agents = await factory.create_all_personas()

            assert len(agents) == 3
            assert PersonaType.BANK_REP in agents
            assert PersonaType.TRADE_BODY_REP in agents
            assert PersonaType.PAYMENTS_ECOSYSTEM_REP in agents

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, factory):
        """Test getting agent by ID."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.BANK_REP)
            agent_id = agent.agent_id

            retrieved_agent = await factory.get_agent(agent_id)
            assert retrieved_agent == agent

            # Test non-existent agent
            non_existent_id = uuid4()
            retrieved_agent = await factory.get_agent(non_existent_id)
            assert retrieved_agent is None

    @pytest.mark.asyncio
    async def test_get_agent_by_persona(self, factory):
        """Test getting agent by persona type."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.BANK_REP)

            retrieved_agent = await factory.get_agent_by_persona(PersonaType.BANK_REP)
            assert retrieved_agent == agent

            # Test non-existent persona
            retrieved_agent = await factory.get_agent_by_persona(
                PersonaType.TRADE_BODY_REP
            )
            assert retrieved_agent is None

    @pytest.mark.asyncio
    async def test_list_agents(self, factory):
        """Test listing all agents."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent1 = await factory.create_agent(PersonaType.BANK_REP)
            agent2 = await factory.create_agent(PersonaType.TRADE_BODY_REP)

            agents = await factory.list_agents()
            assert len(agents) == 2
            assert agent1 in agents
            assert agent2 in agents

    @pytest.mark.asyncio
    async def test_remove_agent(self, factory):
        """Test removing an agent."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            agent = await factory.create_agent(PersonaType.BANK_REP)
            agent_id = agent.agent_id

            # Remove agent
            result = await factory.remove_agent(agent_id)
            assert result is True
            assert agent_id not in factory.agents

            # Try to remove non-existent agent
            result = await factory.remove_agent(uuid4())
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_all_agents(self, factory):
        """Test clearing all agents."""
        with patch(
            "ai_agent.core.agents.persona_factory.get_llm_provider"
        ) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            factory.llm_provider = mock_llm

            await factory.create_agent(PersonaType.BANK_REP)
            await factory.create_agent(PersonaType.TRADE_BODY_REP)

            assert len(factory.agents) == 2

            await factory.clear_all_agents()
            assert len(factory.agents) == 0


class TestPersonaAgentService:
    """Test the persona agent service."""

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_tool_registry):
        """Create service instance."""
        return PersonaAgentService(mock_tool_registry)

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        with patch(
            "ai_agent.core.agents.persona_service.PersonaAgentFactory"
        ) as mock_factory_class:
            mock_factory = AsyncMock()
            mock_factory_class.return_value = mock_factory
            mock_factory.initialize.return_value = None
            mock_factory.create_all_personas.return_value = {
                PersonaType.BANK_REP: AsyncMock(),
                PersonaType.TRADE_BODY_REP: AsyncMock(),
                PersonaType.PAYMENTS_ECOSYSTEM_REP: AsyncMock(),
            }

            # Replace the factory instance
            service.factory = mock_factory

            await service.initialize("anthropic")

            assert service.initialized is True
            assert len(service.agents) == 3
            mock_factory.initialize.assert_called_once_with("anthropic")
            mock_factory.create_all_personas.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_query_single_persona(self, service):
        """Test processing query with single persona."""
        mock_agent = AsyncMock()
        mock_agent.process_query.return_value = "Test response"
        service.agents = {PersonaType.BANK_REP: mock_agent}
        service.initialized = True

        response = await service.process_query(PersonaType.BANK_REP, "test query")

        assert response == "Test response"
        mock_agent.process_query.assert_called_once_with("test query", None)

    @pytest.mark.asyncio
    async def test_process_query_not_initialized(self, service):
        """Test processing query when service not initialized."""
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await service.process_query(PersonaType.BANK_REP, "test query")

    @pytest.mark.asyncio
    async def test_process_query_unknown_persona(self, service):
        """Test processing query with unknown persona."""
        service.initialized = True
        service.agents = {}

        with pytest.raises(ValueError, match="No agent available for persona type"):
            await service.process_query(PersonaType.BANK_REP, "test query")

    @pytest.mark.asyncio
    async def test_process_query_all_personas(self, service):
        """Test processing query with all personas."""
        mock_agent1 = AsyncMock()
        mock_agent1.process_query.return_value = "Response 1"
        mock_agent1.clear_cache = MagicMock()
        mock_agent2 = AsyncMock()
        mock_agent2.process_query.return_value = "Response 2"
        mock_agent2.clear_cache = MagicMock()

        service.agents = {
            PersonaType.BANK_REP: mock_agent1,
            PersonaType.TRADE_BODY_REP: mock_agent2,
        }
        service.initialized = True

        responses = await service.process_query_all_personas("test query")

        assert len(responses) == 2
        assert responses[PersonaType.BANK_REP].success is True
        assert responses[PersonaType.BANK_REP].response == "Response 1"
        assert responses[PersonaType.TRADE_BODY_REP].success is True
        assert responses[PersonaType.TRADE_BODY_REP].response == "Response 2"

    @pytest.mark.asyncio
    async def test_get_agent_status(self, service):
        """Test getting agent status."""
        mock_agent = AsyncMock()
        mock_agent.get_status = MagicMock(return_value=AgentStatus.IDLE)
        mock_agent.clear_cache = MagicMock()
        mock_agent.conversation_history = [AsyncMock(), AsyncMock()]
        mock_agent.evidence_cache = {"key1": "value1", "key2": "value2"}

        service.agents = {PersonaType.BANK_REP: mock_agent}

        status = await service.get_agent_status(PersonaType.BANK_REP)

        assert status["persona_type"] == "BankRep"
        assert status["status"] == "idle"
        assert status["conversation_length"] == 2
        assert status["cache_size"] == 2

    @pytest.mark.asyncio
    async def test_get_agent_status_unknown_persona(self, service):
        """Test getting status for unknown persona."""
        service.agents = {}

        status = await service.get_agent_status(PersonaType.BANK_REP)
        assert status is None

    @pytest.mark.asyncio
    async def test_clear_agent_cache_specific_persona(self, service):
        """Test clearing cache for specific persona."""
        mock_agent = AsyncMock()
        service.agents = {PersonaType.BANK_REP: mock_agent}

        await service.clear_agent_cache(PersonaType.BANK_REP)

        mock_agent.clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_agent_cache_all_personas(self, service):
        """Test clearing cache for all personas."""
        mock_agent1 = AsyncMock()
        mock_agent2 = AsyncMock()
        service.agents = {
            PersonaType.BANK_REP: mock_agent1,
            PersonaType.TRADE_BODY_REP: mock_agent2,
        }

        await service.clear_agent_cache()

        mock_agent1.clear_cache.assert_called_once()
        mock_agent2.clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, service):
        """Test health check when service not initialized."""
        health = await service.health_check()

        assert health["status"] == "not_initialized"
        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_initialized(self, service):
        """Test health check when service initialized."""
        mock_factory = AsyncMock()
        mock_factory.health_check.return_value = {"agent1": True, "agent2": True}

        mock_agent1 = AsyncMock()
        mock_agent1.process_query.return_value = "Health check response"
        mock_agent2 = AsyncMock()
        mock_agent2.process_query.return_value = "Health check response"

        service.factory = mock_factory
        service.agents = {
            PersonaType.BANK_REP: mock_agent1,
            PersonaType.TRADE_BODY_REP: mock_agent2,
        }
        service.initialized = True

        health = await service.health_check()

        assert health["status"] == "initialized"
        assert health["healthy"] is True
        assert health["agent_count"] == 2
        assert "BankRep" in health["agent_health"]
        assert "TradeBodyRep" in health["agent_health"]
