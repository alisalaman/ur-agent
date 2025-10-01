"""Shared API dependencies."""

from fastapi import HTTPException
import structlog

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.service import AgentService
from ai_agent.core.mcp.service import MCPService
from ai_agent.core.messages.service import MessageService
from ai_agent.core.sessions.service import SessionService
from ai_agent.core.tools.service import ToolService
from ai_agent.core.dependency_container import get_container
from ai_agent.config.settings import get_settings, ApplicationSettings

logger = structlog.get_logger()


async def get_persona_service() -> PersonaAgentService:
    """Get persona service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_persona_service()
    except Exception as e:
        logger.error("Failed to get persona service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_agent_service() -> AgentService:
    """Get agent service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_agent_service()
    except Exception as e:
        logger.error("Failed to get agent service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_mcp_service() -> MCPService:
    """Get MCP service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_mcp_service()
    except Exception as e:
        logger.error("Failed to get MCP service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_message_service() -> MessageService:
    """Get message service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_message_service()
    except Exception as e:
        logger.error("Failed to get message service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_session_service() -> SessionService:
    """Get session service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_session_service()
    except Exception as e:
        logger.error("Failed to get session service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_tool_service() -> ToolService:
    """Get tool service instance from dependency container."""
    try:
        container = await get_container()
        return await container.get_tool_service()
    except Exception as e:
        logger.error("Failed to get tool service", error=str(e))
        raise HTTPException(status_code=500, detail="Service unavailable")


async def get_current_user() -> str:
    """Get current user for development purposes."""
    # In development, return a default user
    # In production, this would extract user from JWT token or session
    return "anonymous_user"


def get_settings_dependency() -> ApplicationSettings:
    """Get settings dependency for FastAPI."""
    return get_settings()
