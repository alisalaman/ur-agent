"""Validation utilities for synthetic agents API."""

import re
from typing import Any
from pydantic import BaseModel, Field, validator
import structlog

# Removed circular import - using string literals instead

logger = structlog.get_logger()

# Security constants
MAX_QUERY_LENGTH = 10000
MIN_QUERY_LENGTH = 1
MAX_CONTEXT_SIZE = 1000
MAX_PERSONAS_COUNT = 10

# Unsafe characters that could be used for injection attacks
UNSAFE_CHARS = ["<", ">", "&", '"', "'", "\\", "/", "`"]
UNSAFE_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"data:",
    r"vbscript:",
    r"on\w+\s*=",
]


class SecureAgentQueryRequest(BaseModel):
    """Secure request model for agent queries with comprehensive validation."""

    query: str = Field(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="Query to process",
    )
    context: dict[str, Any] | None = Field(
        None, max_length=MAX_CONTEXT_SIZE, description="Additional context"
    )
    persona_type: str = Field(..., description="Persona type to use")

    @validator("query")
    def validate_query_content(cls, v: str) -> str:
        """Validate query content for security and quality."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        # Check for unsafe characters
        for char in UNSAFE_CHARS:
            if char in v:
                raise ValueError(f"Query contains potentially unsafe character: {char}")

        # Check for unsafe patterns
        for pattern in UNSAFE_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Query contains potentially unsafe content")

        # Check for excessive whitespace
        if len(v) != len(v.strip()):
            logger.warning(
                "Query contains leading/trailing whitespace", query_length=len(v)
            )

        return v.strip()

    @validator("persona_type")
    def validate_persona_type(cls, v: str) -> str:
        """Validate persona type."""
        valid_types = ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"]
        if v not in valid_types:
            raise ValueError(f"Invalid persona type: {v}. Valid types: {valid_types}")
        return v

    @validator("context")
    def validate_context(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate context data."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Context must be a dictionary")

        # Check context size
        if len(str(v)) > MAX_CONTEXT_SIZE:
            raise ValueError(
                f"Context too large. Maximum size: {MAX_CONTEXT_SIZE} characters"
            )

        # Validate context keys and values
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Context keys must be strings")

            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                raise ValueError(
                    f'Invalid context value type for key "{key}": {type(value)}'
                )

            # Check for unsafe content in string values
            if isinstance(value, str):
                for char in UNSAFE_CHARS:
                    if char in value:
                        raise ValueError(
                            f'Context value for key "{key}" contains unsafe character: {char}'
                        )

        return v


class SecureMultiAgentQueryRequest(BaseModel):
    """Secure request model for multi-agent queries with comprehensive validation."""

    query: str = Field(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="Query to process",
    )
    context: dict[str, Any] | None = Field(
        None, max_length=MAX_CONTEXT_SIZE, description="Additional context"
    )
    include_personas: list[str] | None = Field(
        None, max_length=MAX_PERSONAS_COUNT, description="Persona types to include"
    )

    @validator("query")
    def validate_query_content(cls, v: str) -> str:
        """Validate query content for security and quality."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        # Check for unsafe characters
        for char in UNSAFE_CHARS:
            if char in v:
                raise ValueError(f"Query contains potentially unsafe character: {char}")

        # Check for unsafe patterns
        for pattern in UNSAFE_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Query contains potentially unsafe content")

        return v.strip()

    @validator("include_personas")
    def validate_include_personas(cls, v: list[str] | None) -> list[str] | None:
        """Validate include_personas list."""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("include_personas must be a list")

        if len(v) > MAX_PERSONAS_COUNT:
            raise ValueError(
                f"Too many personas specified. Maximum: {MAX_PERSONAS_COUNT}"
            )

        # Validate each persona type
        valid_types = ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"]
        for persona in v:
            if not isinstance(persona, str):
                raise ValueError("Persona types must be strings")

            if persona not in valid_types:
                raise ValueError(
                    f"Invalid persona type: {persona}. Valid types: {valid_types}"
                )

        return v

    @validator("context")
    def validate_context(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate context data."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Context must be a dictionary")

        # Check context size
        if len(str(v)) > MAX_CONTEXT_SIZE:
            raise ValueError(
                f"Context too large. Maximum size: {MAX_CONTEXT_SIZE} characters"
            )

        # Validate context keys and values
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Context keys must be strings")

            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                raise ValueError(
                    f'Invalid context value type for key "{key}": {type(value)}'
                )

            # Check for unsafe content in string values
            if isinstance(value, str):
                for char in UNSAFE_CHARS:
                    if char in value:
                        raise ValueError(
                            f'Context value for key "{key}" contains unsafe character: {char}'
                        )

        return v


def validate_persona_type_string(persona_type_str: str) -> str:
    """Validate and return persona type string."""
    valid_types = ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"]
    if persona_type_str not in valid_types:
        raise ValueError(
            f"Invalid persona type: {persona_type_str}. Valid types: {valid_types}"
        )
    return persona_type_str


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error messages to prevent information leakage."""
    # Log the full error for debugging
    logger.error("Error occurred", error=str(error), error_type=type(error).__name__)

    # Return generic error message to client
    if isinstance(error, ValueError):
        return "Invalid input provided"
    elif isinstance(error, RuntimeError):
        return "Service temporarily unavailable"
    else:
        return "An unexpected error occurred"


def validate_websocket_message_size(message: str, max_size: int = 1024 * 1024) -> None:
    """Validate WebSocket message size."""
    if len(message) > max_size:
        raise ValueError(f"Message too large. Maximum size: {max_size} bytes")


def validate_websocket_message_content(message: dict[str, Any]) -> None:
    """Validate WebSocket message content for security."""
    # Check for required fields
    if "type" not in message:
        raise ValueError("Message must contain 'type' field")

    # Validate message type
    valid_types = ["query", "query_all", "status", "ping"]
    if message["type"] not in valid_types:
        raise ValueError(
            f"Invalid message type: {message['type']}. Valid types: {valid_types}"
        )

    # Validate query content if present
    if "query" in message and message["query"]:
        query = message["query"]
        if not isinstance(query, str):
            raise ValueError("Query must be a string")

        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query too long. Maximum length: {MAX_QUERY_LENGTH}")

        # Check for unsafe content
        for char in UNSAFE_CHARS:
            if char in query:
                raise ValueError(f"Query contains unsafe character: {char}")

    # Validate persona_type if present
    if "persona_type" in message and message["persona_type"]:
        validate_persona_type_string(message["persona_type"])
