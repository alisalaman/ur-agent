"""Main module for stakeholder views MCP server."""

import asyncio
import sys
from pathlib import Path
from typing import Any
import structlog

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import after path manipulation
from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import (  # noqa: E402
    StakeholderViewsServer,
)
from ai_agent.infrastructure.knowledge.transcript_store import (  # noqa: E402
    TranscriptStore,
)
from ai_agent.infrastructure.mcp.protocol import (  # noqa: E402
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPErrorCode,
)

logger = structlog.get_logger()


class StakeholderViewsServerHandler:
    """Handler for stakeholder views MCP server."""

    def __init__(self) -> None:
        # Initialize transcript store (mock for now)
        self.transcript_store = TranscriptStore()
        self.server = StakeholderViewsServer(self.transcript_store)

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP requests."""
        try:
            if request.method == "tools/call":
                return await self.server.handle_tool_call(request)
            elif request.method == "tools/list":
                tool_def = await self.server.get_tool_definition()
                return MCPResponse(id=request.id, result={"tools": [tool_def.__dict__]})
            else:
                raise MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method '{request.method}' not supported",
                )
        except MCPError:
            raise
        except Exception as e:
            logger.error("Error handling request", error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR, message=f"Internal error: {str(e)}"
            )

    async def handle_notification(self, notification: Any) -> None:
        """Handle MCP notifications."""
        # Notifications are not used in this server
        pass


async def main() -> None:
    """Main entry point for the stakeholder views server."""
    handler = StakeholderViewsServerHandler()

    # Simple stdio-based MCP server
    while True:
        try:
            # Read JSON-RPC message from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Parse and handle the message
            from ai_agent.infrastructure.mcp.protocol import MCPMessage

            message = MCPMessage.from_json(line)

            if hasattr(message, "method") and message.method:
                # This is a request
                from ai_agent.infrastructure.mcp.protocol import MCPRequest

                request = MCPRequest(
                    id=message.id, method=message.method, params=message.params
                )
                response = await handler.handle_request(request)

                # Send response to stdout
                print(response.to_json(), flush=True)
            else:
                # This is a response or notification
                logger.warning("Received unexpected message type", message=message)

        except Exception as e:
            logger.error("Error in main loop", error=str(e))
            # Send error response
            error_response = MCPResponse(
                id=getattr(message, "id", None),
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR.value,
                    "message": f"Server error: {str(e)}",
                },
            )
            print(error_response.to_json(), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
