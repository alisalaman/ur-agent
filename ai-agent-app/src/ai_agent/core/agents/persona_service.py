"""Service for managing synthetic representative agents."""

import asyncio
from typing import Any

import structlog

from ai_agent.core.agents.persona_factory import PersonaAgentFactory
from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    QueryResult,
)

# Removed PersonaType import to avoid circular dependency
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()


class PersonaAgentService:
    """Service for managing synthetic representative agents."""

    def __init__(self, tool_registry: ToolRegistry):
        self.factory = PersonaAgentFactory(tool_registry)
        self.agents: dict[str, SyntheticRepresentativeAgent] = {}
        self.initialized = False

    async def initialize(self, llm_provider_type: str | None = None) -> None:
        """Initialize the service and create all persona agents."""
        try:
            await self.factory.initialize(llm_provider_type)
            self.agents = await self.factory.create_all_personas()
            self.initialized = True
            logger.info(
                "Persona agent service initialized", agent_count=len(self.agents)
            )
        except Exception as e:
            logger.error("Failed to initialize persona agent service", error=str(e))
            raise

    async def process_query(
        self,
        persona_type: str,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Process a query with a specific persona agent."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        agent = self.agents.get(persona_type)
        if not agent:
            raise ValueError(f"No agent available for persona type: {persona_type}")

        try:
            response = await agent.process_query(query, context)
            logger.info(
                "Query processed",
                persona_type=persona_type,
                query_length=len(query),
            )
            return str(response)
        except Exception as e:
            logger.error(
                "Failed to process query", persona_type=persona_type, error=str(e)
            )
            raise

    async def process_query_all_personas(
        self, query: str, context: dict[str, Any] | None = None
    ) -> dict[str, QueryResult]:
        """Process a query with all persona agents."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        responses = {}

        # Process query with all agents concurrently
        tasks = []
        for persona_type, agent in self.agents.items():
            task = asyncio.create_task(
                self._process_query_with_agent(persona_type, agent, query, context)
            )
            tasks.append((persona_type, task))

        # Wait for all tasks to complete
        for persona_type, task in tasks:
            try:
                response = await task
                responses[persona_type] = QueryResult(
                    success=True, response=response, persona_type=persona_type
                )
            except Exception as e:
                logger.error(
                    "Failed to process query with agent",
                    persona_type=persona_type,
                    error=str(e),
                )
                responses[persona_type] = QueryResult(
                    success=False,
                    error=f"Error processing query: {str(e)}",
                    persona_type=persona_type,
                )

        return responses

    async def _process_query_with_agent(
        self,
        persona_type: str,
        agent: SyntheticRepresentativeAgent,
        query: str,
        context: dict[str, Any] | None,
    ) -> str:
        """Process query with a specific agent."""
        return str(await agent.process_query(query, context))

    async def get_agent_status(self, persona_type: str) -> dict[str, Any] | None:
        """Get status of a specific agent."""
        agent = self.agents.get(persona_type)
        if not agent:
            return None

        return {
            "persona_type": persona_type,
            "status": agent.get_status().value,
            "conversation_length": len(agent.conversation_history),
            "cache_size": len(agent.evidence_cache),
        }

    async def get_all_agent_status(self) -> dict[str, dict[str, Any] | None]:
        """Get status of all agents."""
        status = {}
        for persona_type, _agent in self.agents.items():
            status[persona_type] = await self.get_agent_status(persona_type)
        return status

    async def clear_agent_cache(self, persona_type: str | None = None) -> None:
        """Clear evidence cache for agents."""
        if persona_type:
            agent = self.agents.get(persona_type)
            if agent:
                agent.clear_cache()
                logger.info("Cache cleared", persona_type=persona_type)
        else:
            for agent in self.agents.values():
                agent.clear_cache()
            logger.info("All agent caches cleared")

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the service."""
        if not self.initialized:
            return {"status": "not_initialized", "healthy": False}

        try:
            # Check factory health
            factory_health = await self.factory.health_check()

            # Check individual agents
            agent_health = {}
            for persona_type, agent in self.agents.items():
                try:
                    # Simple health check
                    await agent.process_query("health check")
                    agent_health[persona_type] = True
                except Exception as e:
                    agent_health[persona_type] = False
                    logger.warning(
                        "Agent health check failed",
                        persona_type=persona_type,
                        error=str(e),
                    )

            overall_healthy = all(agent_health.values())

            return {
                "status": "initialized",
                "healthy": overall_healthy,
                "factory_health": factory_health,
                "agent_health": agent_health,
                "agent_count": len(self.agents),
            }

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"status": "error", "healthy": False, "error": str(e)}
