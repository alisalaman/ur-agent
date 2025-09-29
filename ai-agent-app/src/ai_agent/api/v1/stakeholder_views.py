"""API endpoints for stakeholder views."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import structlog

from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import (
    StakeholderViewsServer,
)
from ai_agent.infrastructure.mcp.exceptions import ValidationError, SearchError
from ai_agent.infrastructure.knowledge.stakeholder_utils import InputValidator
from ai_agent.domain.knowledge_models import StakeholderGroup
from ai_agent.config.stakeholder_views import config

logger = structlog.get_logger()
router = APIRouter(prefix="/stakeholder-views", tags=["stakeholder-views"])


def get_stakeholder_views_server() -> StakeholderViewsServer:
    """Dependency to get stakeholder views server instance."""
    # This would be injected from the application context
    # For now, create a mock instance for demonstration
    from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore

    transcript_store = TranscriptStore()
    return StakeholderViewsServer(transcript_store)


class StakeholderViewsRequest(BaseModel):
    """Request model for stakeholder views search."""

    topic: str = Field(..., description="Topic to search for")
    stakeholder_group: StakeholderGroup | None = Field(
        None, description="Filter by stakeholder group"
    )
    limit: int = Field(
        10,
        ge=1,
        le=config.max_results,
        description=f"Maximum number of results (1-{config.max_results})",
    )
    min_relevance_score: float = Field(
        config.min_relevance_score,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score",
    )


class StakeholderViewsResponse(BaseModel):
    """Response model for stakeholder views search."""

    topic: str
    stakeholder_group: str | None
    results_count: int
    results: list[dict[str, Any]]


@router.post("/search", response_model=StakeholderViewsResponse)
async def search_stakeholder_views(
    request: StakeholderViewsRequest,
    server: StakeholderViewsServer = Depends(get_stakeholder_views_server),
) -> StakeholderViewsResponse:
    """Search for stakeholder views on a specific topic."""
    try:
        # Validate input parameters
        try:
            validated_topic = InputValidator.validate_topic(request.topic)
            validated_limit = InputValidator.validate_limit(request.limit)
            validated_score = InputValidator.validate_relevance_score(
                request.min_relevance_score
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {e.message}")

        # Create mock MCP request
        from ai_agent.infrastructure.mcp.protocol import MCPRequest

        mcp_request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {
                    "topic": validated_topic,
                    "stakeholder_group": (
                        request.stakeholder_group.value
                        if request.stakeholder_group
                        else None
                    ),
                    "limit": validated_limit,
                    "min_relevance_score": validated_score,
                },
            },
        )

        # Handle tool call
        response = await server.handle_tool_call(mcp_request)

        if response.error:
            raise HTTPException(
                status_code=400,
                detail=f"Search failed: {response.error.get('message', 'Unknown error')}",
            )

        return StakeholderViewsResponse(**response.result)

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error("Validation error in API", error=str(e), field=e.field)
        raise HTTPException(status_code=400, detail=f"Invalid input: {e.message}")
    except SearchError as e:
        logger.error("Search error in API", error=str(e), topic=e.topic)
        raise HTTPException(status_code=500, detail=f"Search failed: {e.message}")
    except Exception as e:
        logger.error("Unexpected error in API", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check(
    server: StakeholderViewsServer = Depends(get_stakeholder_views_server),
) -> dict[str, str]:
    """Health check for stakeholder views service."""
    return {"status": "healthy", "service": "stakeholder-views"}
