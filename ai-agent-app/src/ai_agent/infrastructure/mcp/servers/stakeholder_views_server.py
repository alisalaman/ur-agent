"""MCP server for stakeholder views tool."""

from typing import Any
import structlog

from ..protocol import (
    MCPTool,
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPErrorCode,
)
from ..exceptions import (
    SearchError,
    ValidationError,
)
from ...knowledge.transcript_store import TranscriptStore
from ...knowledge.stakeholder_utils import (
    StakeholderGroupInference,
    InputValidator,
    SearchResultFormatter,
)
from ....domain.knowledge_models import StakeholderGroup
from ....config.stakeholder_views import config

logger = structlog.get_logger()


class StakeholderViewsServer:
    """MCP server for stakeholder views tool."""

    def __init__(self, transcript_store: TranscriptStore):
        self.transcript_store = transcript_store
        self.tool_definition = self._create_tool_definition()

    def _create_tool_definition(self) -> MCPTool:
        """Create the stakeholder views tool definition."""
        return MCPTool(
            name="get_stakeholder_views",
            description="Retrieves relevant opinions, statements, and data points from transcripts of stakeholder groups. Use this tool to gather evidence before answering any question about stakeholder perspectives. All content is automatically sanitized and returned in clean markdown format.",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic to search for within the transcripts. For example: 'cost of open banking', 'governance models', 'commercial viability of Project Perseus', 'cross-sector interoperability'. Content will be returned in markdown format.",
                    },
                    "stakeholder_group": {
                        "type": "string",
                        "enum": ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"],
                        "description": "Optional filter by stakeholder group. If not provided, searches across all groups.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": config.max_results,
                        "default": 10,
                        "description": f"Maximum number of results to return (1-{config.max_results}).",
                    },
                    "min_relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": config.min_relevance_score,
                        "description": "Minimum relevance score for results (0.0-1.0).",
                    },
                },
                "required": ["topic"],
            },
            metadata={
                "category": "research",
                "version": "1.0.0",
                "author": "AI Agent System",
                "output_format": "markdown",
                "content_sanitization": "enabled",
            },
        )

    async def handle_tool_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tool call requests."""
        try:
            if request.method != "tools/call":
                raise MCPError(
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Invalid method for tool call",
                )

            params = request.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name != "get_stakeholder_views":
                raise MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Tool '{tool_name}' not found",
                )

            # Validate required parameters
            if "topic" not in arguments:
                raise MCPError(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message="Parameter 'topic' is required",
                )

            # Extract and validate parameters
            try:
                topic = InputValidator.validate_topic(arguments["topic"])
                limit = InputValidator.validate_limit(arguments.get("limit", 10))
                min_relevance_score = InputValidator.validate_relevance_score(
                    arguments.get("min_relevance_score", config.min_relevance_score)
                )
            except ValidationError as e:
                raise MCPError(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message=f"Invalid parameter: {e.message}",
                )

            # Convert stakeholder group string to enum
            stakeholder_group = arguments.get("stakeholder_group")
            stakeholder_group_enum = None
            if stakeholder_group:
                stakeholder_group_enum = StakeholderGroupInference.validate_group(
                    stakeholder_group
                )
                if not stakeholder_group_enum:
                    raise MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message=f"Invalid stakeholder group: {stakeholder_group}. "
                        f"Available groups: {StakeholderGroupInference.get_available_groups()}",
                    )

            # Execute search
            results = await self._search_stakeholder_views(
                topic=topic,
                stakeholder_group=stakeholder_group_enum,
                limit=limit,
                min_relevance_score=min_relevance_score,
            )

            # Format response
            response_data = {
                "topic": topic,
                "stakeholder_group": stakeholder_group,
                "results_count": len(results),
                "results": results,
            }

            return MCPResponse(id=request.id, result=response_data)

        except MCPError:
            raise
        except SearchError as e:
            logger.error("Search error in tool call", error=str(e), topic=e.topic)
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR, message=f"Search failed: {e.message}"
            )
        except ValidationError as e:
            logger.error("Validation error in tool call", error=str(e), field=e.field)
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS, message=f"Invalid input: {e.message}"
            )
        except Exception as e:
            logger.error("Unexpected error in tool call", error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR, message="An unexpected error occurred"
            )

    async def _search_stakeholder_views(
        self,
        topic: str,
        stakeholder_group: StakeholderGroup | None = None,
        limit: int = 10,
        min_relevance_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search for stakeholder views on a topic."""
        try:
            # Perform semantic search with optimized parameters
            segments_with_scores = await self.transcript_store.search_segments(
                query=topic,
                stakeholder_group=stakeholder_group,
                limit=limit,  # Use exact limit instead of 2x
            )

            # Format results using shared utility
            results = []
            for segment, score in segments_with_scores:
                if score >= min_relevance_score:
                    result = SearchResultFormatter.format_segment_result(segment, score)
                    results.append(result)

                    if len(results) >= limit:
                        break

            # Sort by relevance score using shared utility
            results = SearchResultFormatter.sort_by_relevance(results)

            logger.info(
                "Stakeholder views search completed",
                topic=topic,
                stakeholder_group=stakeholder_group,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("Error searching stakeholder views", error=str(e), topic=topic)
            raise SearchError(f"Search operation failed: {str(e)}", topic=topic)

    async def get_tool_definition(self) -> MCPTool:
        """Get the tool definition."""
        return self.tool_definition
