"""API v1 module for AI Agent application."""

# Import all the API modules
from . import agents
from . import health
from . import mcp_servers
from . import messages
from . import sessions
from . import tools
from . import synthetic_agents

# Temporarily commented out due to circular import issues
# from .governance_evaluation import router as governance_evaluation_router

__all__ = [
    "agents",
    "health",
    "mcp_servers",
    "messages",
    "sessions",
    "tools",
    "synthetic_agents",
]
