"""MCP integration manager for new servers."""

import asyncio
import structlog

from .server_manager import MCPServerManager
from .tool_registry import ToolRegistry, ToolMetadata, ToolCategory
from ..knowledge.transcript_store import TranscriptStore
from .servers.registry import StakeholderViewsServerRegistry

logger = structlog.get_logger()


class MCPIntegrationManager:
    """Manages integration of new MCP servers with existing infrastructure."""

    def __init__(
        self,
        server_manager: MCPServerManager,
        tool_registry: ToolRegistry,
        transcript_store: TranscriptStore,
    ):
        self.server_manager = server_manager
        self.tool_registry = tool_registry
        self.transcript_store = transcript_store
        self.stakeholder_views_registry: StakeholderViewsServerRegistry | None = None

    async def initialize_stakeholder_views_server(self) -> bool:
        """Initialize and register the stakeholder views MCP server."""
        try:
            # Create registry
            self.stakeholder_views_registry = StakeholderViewsServerRegistry(
                self.server_manager, self.transcript_store
            )

            # Register server
            server_id = await self.stakeholder_views_registry.register_server()

            # Wait for server to be ready
            await asyncio.sleep(2)

            # Verify server is running
            if not await self.stakeholder_views_registry.health_check():
                raise RuntimeError("Stakeholder views server failed health check")

            # Register tools with tool registry
            await self._register_stakeholder_views_tools(server_id)

            logger.info("Stakeholder views MCP server initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize stakeholder views server", error=str(e))
            return False

    async def _register_stakeholder_views_tools(self, server_id: str) -> None:
        """Register stakeholder views tools with the tool registry."""
        try:
            # Get server instance
            if not self.stakeholder_views_registry:
                raise RuntimeError("Stakeholder views registry not initialized")

            server_instance = self.stakeholder_views_registry.get_server_instance()
            if not server_instance:
                raise RuntimeError("Server instance not available")

            # Get tool definition
            tool_definition = await server_instance.get_tool_definition()

            # Register with tool registry
            metadata = ToolMetadata(
                category=ToolCategory.GENERAL,
                version="1.0.0",
                description="Query stakeholder views from transcripts",
            )
            await self.tool_registry.register_tool(
                tool=tool_definition,
                server_id=server_id,
                metadata=metadata,
            )

            logger.info("Stakeholder views tools registered successfully")

        except Exception as e:
            logger.error("Failed to register stakeholder views tools", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Shutdown all registered servers."""
        try:
            if self.stakeholder_views_registry:
                await self.stakeholder_views_registry.unregister_server()

            logger.info("MCP integration manager shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
