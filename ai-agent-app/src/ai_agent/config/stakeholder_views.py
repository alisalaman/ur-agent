"""Configuration for stakeholder views MCP server."""

import os
from dataclasses import dataclass


@dataclass
class StakeholderViewsConfig:
    """Configuration for stakeholder views functionality."""

    # Search parameters
    max_results: int = int(os.getenv("STAKEHOLDER_MAX_RESULTS", "50"))
    min_relevance_score: float = float(os.getenv("STAKEHOLDER_MIN_RELEVANCE", "0.3"))
    search_timeout: int = int(os.getenv("STAKEHOLDER_SEARCH_TIMEOUT", "30"))

    # Analysis parameters
    sentiment_boost_factor: float = float(
        os.getenv("STAKEHOLDER_SENTIMENT_BOOST", "0.1")
    )
    keyword_boost_factor: float = float(os.getenv("STAKEHOLDER_KEYWORD_BOOST", "0.1"))
    max_keyword_boost: float = float(os.getenv("STAKEHOLDER_MAX_KEYWORD_BOOST", "0.3"))

    # Server configuration
    server_name: str = os.getenv("MCP_SERVER_NAME", "stakeholder-views-server")
    server_command: str = os.getenv(
        "MCP_SERVER_COMMAND",
        "python -m ai_agent.infrastructure.mcp.servers.stakeholder_views_server",
    )
    working_directory: str = os.getenv("MCP_WORKING_DIR", ".")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Security parameters
    max_topic_length: int = int(os.getenv("STAKEHOLDER_MAX_TOPIC_LENGTH", "1000"))
    min_topic_length: int = int(os.getenv("STAKEHOLDER_MIN_TOPIC_LENGTH", "2"))

    # Performance parameters
    cache_ttl: int = int(os.getenv("STAKEHOLDER_CACHE_TTL", "300"))  # 5 minutes
    batch_size: int = int(os.getenv("STAKEHOLDER_BATCH_SIZE", "100"))

    def validate(self) -> None:
        """Validate configuration values."""
        if self.max_results < 1 or self.max_results > 100:
            raise ValueError("max_results must be between 1 and 100")

        if not 0.0 <= self.min_relevance_score <= 1.0:
            raise ValueError("min_relevance_score must be between 0.0 and 1.0")

        if self.search_timeout < 1:
            raise ValueError("search_timeout must be positive")

        if self.max_topic_length < self.min_topic_length:
            raise ValueError("max_topic_length must be >= min_topic_length")


# Global configuration instance
config = StakeholderViewsConfig()
