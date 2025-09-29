"""Factory for creating synthetic representative agents."""

from uuid import UUID, uuid4

import structlog

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaType,
)
from ai_agent.core.agents.personas.bank_rep import BankRepAgent
from ai_agent.core.agents.personas.trade_body_rep import TradeBodyRepAgent
from ai_agent.core.agents.personas.payments_ecosystem_rep import (
    PaymentsEcosystemRepAgent,
)
from ai_agent.domain.models import AgentStatus
from ai_agent.infrastructure.llm import BaseLLMProvider, get_llm_provider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()


class PersonaAgentFactory:
    """Factory for creating synthetic representative agents."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.agents: dict[UUID, SyntheticRepresentativeAgent] = {}
        self.agents_by_persona: dict[PersonaType, SyntheticRepresentativeAgent] = {}
        self.llm_provider: BaseLLMProvider | None = None

    async def initialize(self, llm_provider_type: str = "anthropic") -> None:
        """Initialize the factory with LLM provider."""
        try:
            self.llm_provider = await get_llm_provider(llm_provider_type)
            logger.info("Persona agent factory initialized", provider=llm_provider_type)
        except Exception as e:
            logger.error("Failed to initialize persona agent factory", error=str(e))
            raise

    async def create_agent(
        self, persona_type: PersonaType
    ) -> SyntheticRepresentativeAgent:
        """Create a synthetic representative agent."""
        if not self.llm_provider:
            raise RuntimeError("Factory not initialized. Call initialize() first.")

        agent_id = uuid4()

        try:
            if persona_type == PersonaType.BANK_REP:
                agent = BankRepAgent(agent_id, self.llm_provider, self.tool_registry)
            elif persona_type == PersonaType.TRADE_BODY_REP:
                agent = TradeBodyRepAgent(
                    agent_id, self.llm_provider, self.tool_registry
                )
            elif persona_type == PersonaType.PAYMENTS_ECOSYSTEM_REP:
                agent = PaymentsEcosystemRepAgent(
                    agent_id, self.llm_provider, self.tool_registry
                )
            else:
                raise ValueError(f"Unknown persona type: {persona_type}")

            self.agents[agent_id] = agent
            self.agents_by_persona[persona_type] = agent
            logger.info(
                "Agent created", agent_id=str(agent_id), persona_type=persona_type.value
            )

            return agent

        except Exception as e:
            logger.error(
                "Failed to create agent", persona_type=str(persona_type), error=str(e)
            )
            raise

    async def create_all_personas(
        self,
    ) -> dict[PersonaType, SyntheticRepresentativeAgent]:
        """Create all three persona agents."""
        agents = {}

        for persona_type in PersonaType:
            try:
                agent = await self.create_agent(persona_type)
                agents[persona_type] = agent
            except Exception as e:
                logger.error(
                    "Failed to create persona agent",
                    persona_type=persona_type.value,
                    error=str(e),
                )
                raise

        logger.info("All persona agents created", count=len(agents))
        return agents

    async def get_agent(self, agent_id: UUID) -> SyntheticRepresentativeAgent | None:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    async def get_agent_by_persona(
        self, persona_type: PersonaType
    ) -> SyntheticRepresentativeAgent | None:
        """Get agent by persona type."""
        return self.agents_by_persona.get(persona_type)

    async def list_agents(self) -> list[SyntheticRepresentativeAgent]:
        """List all created agents."""
        return list(self.agents.values())

    async def remove_agent(self, agent_id: UUID) -> bool:
        """Remove an agent."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            # Remove from both dictionaries
            del self.agents[agent_id]
            if agent.persona_config.persona_type in self.agents_by_persona:
                del self.agents_by_persona[agent.persona_config.persona_type]
            logger.info("Agent removed", agent_id=str(agent_id))
            return True
        return False

    async def clear_all_agents(self) -> None:
        """Clear all agents."""
        self.agents.clear()
        self.agents_by_persona.clear()
        logger.info("All agents cleared")

    async def health_check(self) -> dict[str, bool]:
        """Perform lightweight health check on all agents."""
        health_status = {}

        for agent_id, agent in self.agents.items():
            try:
                # Lightweight check - just verify agent is responsive
                health_status[str(agent_id)] = agent.get_status() != AgentStatus.ERROR
            except Exception as e:
                logger.warning(
                    "Agent health check failed", agent_id=str(agent_id), error=str(e)
                )
                health_status[str(agent_id)] = False

        return health_status
