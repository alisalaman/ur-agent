"""Registry for stakeholder views MCP server."""

import structlog
from dataclasses import dataclass

from ..server_manager import MCPServerManager, MCPServerType
from ..exceptions import ServerRegistrationError, ConfigurationError
from .stakeholder_views_server import StakeholderViewsServer
from ...knowledge.transcript_store import TranscriptStore
from ....config.stakeholder_views import config

logger = structlog.get_logger()


@dataclass
class ServerConfig:
    """Configuration for MCP server registration."""

    name: str
    description: str
    command: list[str]
    env: dict[str, str]
    working_directory: str | None = None


class StakeholderViewsServerRegistry:
    """Registry for stakeholder views MCP server."""

    def __init__(
        self, server_manager: MCPServerManager, transcript_store: TranscriptStore
    ):
        self.server_manager = server_manager
        self.transcript_store = transcript_store
        self.server_id: str | None = None
        self.server_instance: StakeholderViewsServer | None = None

    async def register_server(self) -> str:
        """Register the stakeholder views MCP server."""
        try:
            # Validate configuration
            config.validate()

            # Create server configuration using environment-based values
            server_config = ServerConfig(
                name=config.server_name,
                description="MCP server for querying stakeholder views from transcripts",
                command=config.server_command.split(),
                env={
                    "PYTHONPATH": config.working_directory,
                    "LOG_LEVEL": config.log_level,
                },
                working_directory=config.working_directory,
            )

            # Register with server manager
            self.server_id = await self.server_manager.register_server(
                name=server_config.name,
                server_type=MCPServerType.PROCESS,
                endpoint="",  # Not used for process servers
                command=server_config.command,
                env=server_config.env,
                working_directory=server_config.working_directory,
                description=server_config.description,
            )

            # Start the server
            success = await self.server_manager.start_server(self.server_id)
            if not success:
                raise ServerRegistrationError(
                    "Failed to start stakeholder views server",
                    server_name=server_config.name,
                )

            # Create server instance for direct access
            self.server_instance = StakeholderViewsServer(self.transcript_store)

            logger.info(
                "Stakeholder views server registered and started",
                server_id=self.server_id,
                server_name=server_config.name,
            )

            return self.server_id

        except ConfigurationError as e:
            logger.error("Configuration error during server registration", error=str(e))
            raise
        except ServerRegistrationError:
            raise
        except Exception as e:
            logger.error("Failed to register stakeholder views server", error=str(e))
            raise ServerRegistrationError(
                f"Server registration failed: {str(e)}", server_name=config.server_name
            )

    async def unregister_server(self) -> bool:
        """Unregister the stakeholder views MCP server."""
        if not self.server_id:
            return False

        try:
            success = await self.server_manager.unregister_server(self.server_id)
            if success:
                self.server_id = None
                self.server_instance = None
                logger.info("Stakeholder views server unregistered")

            return success

        except Exception as e:
            logger.error("Failed to unregister stakeholder views server", error=str(e))
            return False

    async def get_server_status(self) -> str | None:
        """Get server status."""
        if not self.server_id:
            return None

        return await self.server_manager.get_server_status(self.server_id)

    async def health_check(self) -> bool:
        """Perform health check on server."""
        if not self.server_id:
            return False

        return await self.server_manager.health_check_server(self.server_id)

    def get_server_instance(self) -> StakeholderViewsServer | None:
        """Get direct access to server instance."""
        return self.server_instance
