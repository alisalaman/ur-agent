"""Integration test configuration."""

import pytest
from unittest.mock import AsyncMock

from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry
from ai_agent.infrastructure.mcp.tool_executor import ToolExecutionResult


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry for integration tests."""
    registry = AsyncMock(spec=ToolRegistry)
    registry.execute_tool = AsyncMock(
        return_value=ToolExecutionResult(
            success=True,
            result={
                "results": [
                    {
                        "id": "test-1",
                        "content": "Test evidence content",
                        "relevance_score": 0.8,
                        "stakeholder_group": "BankRep",
                    }
                ],
                "results_count": 1,
            },
        )
    )
    return registry


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider for integration tests."""
    provider = AsyncMock()
    provider.generate_response = AsyncMock(return_value="Test response")
    provider.generate_streaming_response = AsyncMock()
    provider.get_models = AsyncMock(return_value=[])
    provider.health_check = AsyncMock(return_value=True)
    return provider
