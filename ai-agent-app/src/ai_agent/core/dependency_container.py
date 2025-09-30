"""Dependency injection container for managing service instances."""

import asyncio
from typing import Any
import structlog

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()


class DependencyContainer:
    """Thread-safe dependency injection container."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the container and all services."""
        async with self._lock:
            if self._initialized:
                return

            try:
                # Initialize tool registry
                tool_registry = ToolRegistry()
                self._services["tool_registry"] = tool_registry

                # Initialize persona service
                persona_service = PersonaAgentService(tool_registry)
                await persona_service.initialize()
                self._services["persona_service"] = persona_service

                self._initialized = True
                logger.info("Dependency container initialized successfully")

            except Exception as e:
                logger.error("Failed to initialize dependency container", error=str(e))
                raise

    async def get_persona_service(self) -> PersonaAgentService:
        """Get persona service instance."""
        if not self._initialized:
            await self.initialize()

        service = self._services.get("persona_service")
        if not service:
            raise RuntimeError("Persona service not available")

        return service

    async def get_tool_registry(self) -> ToolRegistry:
        """Get tool registry instance."""
        if not self._initialized:
            await self.initialize()

        service = self._services.get("tool_registry")
        if not service:
            raise RuntimeError("Tool registry not available")

        return service

    async def shutdown(self) -> None:
        """Shutdown all services."""
        async with self._lock:
            # Add cleanup logic here if needed
            self._services.clear()
            self._initialized = False
            logger.info("Dependency container shutdown")


# Global container instance
_container: DependencyContainer | None = None


async def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container
    if _container is None:
        _container = DependencyContainer()
        await _container.initialize()
    return _container


async def shutdown_container() -> None:
    """Shutdown the global dependency container."""
    global _container
    if _container:
        await _container.shutdown()
        _container = None
