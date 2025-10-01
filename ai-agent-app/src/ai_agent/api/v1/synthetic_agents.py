"""Synthetic agents API endpoints for governance model evaluation."""

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import structlog

from ai_agent.api.dependencies import get_current_user, get_persona_service
from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.dependency_container import get_container
from ai_agent.api.validation.synthetic_agents import (
    SecureAgentQueryRequest,
    SecureMultiAgentQueryRequest,
    validate_persona_type_string,
    sanitize_error_message,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/synthetic-agents", tags=["synthetic-agents"])

# Constants
MILLISECONDS_PER_SECOND = 1000


class AgentQueryResponse(BaseModel):
    """Response model for agent queries."""

    response: str
    persona_type: str
    evidence_count: int
    confidence_level: str
    processing_time_ms: int


class MultiAgentQueryResponse(BaseModel):
    """Response model for multi-agent queries."""

    responses: dict[str, str]
    processing_time_ms: int
    total_evidence_count: int


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""

    persona_type: str
    status: str
    conversation_length: int
    cache_size: int
    last_activity: str | None = None


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    request: SecureAgentQueryRequest,
    persona_service: Annotated[PersonaAgentService, Depends(get_persona_service)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> AgentQueryResponse:
    """Query a specific persona agent."""
    try:
        # Validate persona type (already validated by SecureAgentQueryRequest)
        persona_type = validate_persona_type_string(request.persona_type)

        # Process query
        start_time = time.time()

        response = await persona_service.process_query(
            persona_type=persona_type, query=request.query, context=request.context
        )

        processing_time = int((time.time() - start_time) * MILLISECONDS_PER_SECOND)

        # Get agent status for additional metadata
        agent_status = await persona_service.get_agent_status(persona_type)

        return AgentQueryResponse(
            response=response,
            persona_type=persona_type,
            evidence_count=agent_status.get("cache_size", 0) if agent_status else 0,
            confidence_level="medium",  # This would be calculated from response analysis
            processing_time_ms=processing_time,
        )

    except ValueError as e:
        # Input validation errors - return 400 with sanitized message
        logger.warning(
            "Invalid input for agent query", error=str(e), user_id=current_user
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors - sanitize and return 500
        logger.error("Agent query failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/query-all", response_model=MultiAgentQueryResponse)
async def query_all_agents(
    request: SecureMultiAgentQueryRequest,
    persona_service: Annotated[PersonaAgentService, Depends(get_persona_service)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> MultiAgentQueryResponse:
    """Query all persona agents."""
    try:
        # Process query with all agents
        start_time = time.time()

        responses = await persona_service.process_query_all_personas(
            query=request.query, context=request.context
        )

        processing_time = int((time.time() - start_time) * MILLISECONDS_PER_SECOND)

        # Calculate total evidence count and format responses concurrently
        import asyncio

        async def get_agent_status_concurrently() -> dict[str, Any]:
            """Get agent statuses concurrently for better performance."""
            tasks = []
            persona_types = []

            for persona_type, query_result in responses.items():
                if query_result.success:
                    tasks.append(persona_service.get_agent_status(persona_type))
                    persona_types.append(persona_type)

            if tasks:
                statuses = await asyncio.gather(*tasks, return_exceptions=True)
                return dict(zip(persona_types, statuses, strict=True))
            return {}

        # Get agent statuses concurrently
        agent_statuses = await get_agent_status_concurrently()

        # Format responses
        formatted_responses = {}
        total_evidence_count = 0

        for persona_type, query_result in responses.items():
            if query_result.success:
                formatted_responses[persona_type] = query_result.response
                # Get evidence count for this agent
                agent_status = agent_statuses.get(persona_type)
                if agent_status and not isinstance(agent_status, Exception):
                    total_evidence_count += agent_status.get("cache_size", 0)
            else:
                formatted_responses[persona_type] = f"Error: {query_result.error}"

        return MultiAgentQueryResponse(
            responses=formatted_responses,
            processing_time_ms=processing_time,
            total_evidence_count=total_evidence_count,
        )

    except ValueError as e:
        # Input validation errors - return 400 with sanitized message
        logger.warning(
            "Invalid input for multi-agent query", error=str(e), user_id=current_user
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors - sanitize and return 500
        logger.error("Multi-agent query failed", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.get("/status", response_model=list[AgentStatusResponse])
async def get_agent_status(
    persona_service: Annotated[PersonaAgentService, Depends(get_persona_service)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> list[AgentStatusResponse]:
    """Get status of all agents."""
    try:
        status_data = await persona_service.get_all_agent_status()

        responses = []
        for persona_type, status in status_data.items():
            if status:
                responses.append(
                    AgentStatusResponse(
                        persona_type=persona_type,
                        status=status.get("status", "unknown"),
                        conversation_length=status.get("conversation_length", 0),
                        cache_size=status.get("cache_size", 0),
                        last_activity=None,  # This would be tracked in practice
                    )
                )

        return responses

    except Exception as e:
        logger.error("Failed to get agent status", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/clear-cache")
async def clear_agent_cache(
    persona_service: Annotated[PersonaAgentService, Depends(get_persona_service)],
    current_user: Annotated[str, Depends(get_current_user)],
    persona_type: str | None = Query(
        None, description="Persona type to clear cache for"
    ),
) -> dict[str, str]:
    """Clear evidence cache for agents."""
    try:
        if persona_type:
            try:
                persona_enum = validate_persona_type_string(persona_type)
                await persona_service.clear_agent_cache(persona_enum)
                return {"message": f"Cache cleared for {persona_type}"}
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            await persona_service.clear_agent_cache()
            return {"message": "Cache cleared for all agents"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Failed to clear agent cache", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.get("/health")
async def health_check(
    persona_service: Annotated[PersonaAgentService, Depends(get_persona_service)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> dict[str, Any]:
    """Health check for synthetic agents service."""
    try:
        health_data = await persona_service.health_check()
        return dict(health_data)
    except Exception as e:
        logger.error("Health check failed", error=str(e), user_id=current_user)
        return {"status": "error", "healthy": False, "error": sanitize_error_message(e)}


@router.get("/personas")
async def get_available_personas(
    current_user: Annotated[str, Depends(get_current_user)],
) -> dict[str, list[str]]:
    """Get list of available persona types."""
    return {
        "personas": ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"],
        "descriptions": [
            "Bank Representative - Financial institution perspective",
            "Trade Body Representative - Trade association perspective",
            "Payments Ecosystem Representative - Payment system perspective",
        ],
    }


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get status without authentication for demo purposes."""
    try:
        container = await get_container()
        persona_service = await container.get_persona_service()

        # Get basic status information
        status = {
            "service": "synthetic-agents",
            "status": "running",
            "personas": ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"],
            "agents_initialized": (
                len(persona_service.agents) if hasattr(persona_service, "agents") else 0
            ),
            "initialized": (
                persona_service.initialized
                if hasattr(persona_service, "initialized")
                else False
            ),
        }

        return status
    except Exception as e:
        logger.error("Status check failed", error=str(e))
        return {
            "service": "synthetic-agents",
            "status": "error",
            "error": str(e),
            "personas": ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"],
        }
