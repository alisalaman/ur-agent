"""Integration tests for stakeholder views MCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import (
    StakeholderViewsServer,
)
from ai_agent.infrastructure.mcp.servers.registry import StakeholderViewsServerRegistry
from ai_agent.infrastructure.mcp.integration import MCPIntegrationManager
from ai_agent.infrastructure.mcp.server_manager import MCPServerManager
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import StakeholderGroup, TranscriptSegment


class TestStakeholderViewsIntegration:
    """Integration tests for stakeholder views system."""

    @pytest.fixture
    def mock_transcript_store(self):
        """Create a mock transcript store."""
        store = AsyncMock(spec=TranscriptStore)
        return store

    @pytest.fixture
    def mock_server_manager(self):
        """Create a mock server manager."""
        manager = AsyncMock(spec=MCPServerManager)
        manager.register_server.return_value = "test-server-id"
        manager.start_server.return_value = True
        manager.unregister_server.return_value = True
        manager.get_server_status.return_value = "running"
        manager.health_check_server.return_value = True
        return manager

    @pytest.fixture
    def mock_tool_registry(self):
        """Create a mock tool registry."""
        registry = AsyncMock(spec=ToolRegistry)
        return registry

    @pytest.fixture
    def integration_manager(
        self, mock_server_manager, mock_tool_registry, mock_transcript_store
    ):
        """Create an integration manager."""
        return MCPIntegrationManager(
            mock_server_manager, mock_tool_registry, mock_transcript_store
        )

    @pytest.mark.asyncio
    async def test_server_registry_lifecycle(
        self, mock_server_manager, mock_transcript_store
    ):
        """Test server registry registration and unregistration."""
        registry = StakeholderViewsServerRegistry(
            mock_server_manager, mock_transcript_store
        )

        # Test registration
        server_id = await registry.register_server()
        assert server_id == "test-server-id"
        assert registry.server_id == "test-server-id"
        assert registry.server_instance is not None

        # Test server instance
        server_instance = registry.get_server_instance()
        assert isinstance(server_instance, StakeholderViewsServer)

        # Test status check
        status = await registry.get_server_status()
        assert status == "running"

        # Test health check
        health = await registry.health_check()
        assert health is True

        # Test unregistration
        success = await registry.unregister_server()
        assert success is True
        assert registry.server_id is None
        assert registry.server_instance is None

    @pytest.mark.asyncio
    async def test_integration_manager_initialization(self, integration_manager):
        """Test integration manager initialization."""
        # Mock the transcript store to return some data
        mock_segment = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Test Speaker",
            content="Test content about governance",
            metadata={"stakeholder_group": "BankRep"},
        )
        integration_manager.transcript_store.search_segments.return_value = [
            (mock_segment, 0.8)
        ]

        # Initialize the stakeholder views server
        success = await integration_manager.initialize_stakeholder_views_server()

        assert success is True
        assert integration_manager.stakeholder_views_registry is not None

        # Verify server was registered
        integration_manager.server_manager.register_server.assert_called_once()
        integration_manager.server_manager.start_server.assert_called_once()

        # Verify tools were registered
        integration_manager.tool_registry.register_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_to_end_search_workflow(self, mock_transcript_store):
        """Test end-to-end search workflow."""
        # Create test data
        segment1 = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Bank Rep A",
            speaker_title="Senior Manager",
            content="We believe the cost of open banking implementation is reasonable and will provide good ROI",
            metadata={"stakeholder_group": "BankRep"},
        )
        segment2 = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Trade Body Rep B",
            speaker_title="Policy Director",
            content="The governance framework needs to be more robust to ensure proper oversight",
            metadata={"stakeholder_group": "TradeBodyRep"},
        )

        # Mock search results
        mock_transcript_store.search_segments.return_value = [
            (segment1, 0.85),
            (segment2, 0.75),
        ]

        # Create server and perform search
        server = StakeholderViewsServer(mock_transcript_store)

        from ai_agent.infrastructure.mcp.protocol import MCPRequest

        request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {
                    "topic": "cost and governance",
                    "limit": 10,
                    "min_relevance_score": 0.7,
                },
            },
        )

        response = await server.handle_tool_call(request)

        # Verify response
        assert response.result is not None
        assert response.result["topic"] == "cost and governance"
        assert response.result["results_count"] == 2
        assert len(response.result["results"]) == 2

        # Verify results are sorted by relevance
        results = response.result["results"]
        assert results[0]["relevance_score"] >= results[1]["relevance_score"]

        # Verify result structure
        for result in results:
            assert "segment_id" in result
            assert "speaker_name" in result
            assert "content" in result
            assert "relevance_score" in result
            assert "stakeholder_group" in result
            assert "metadata" in result

    @pytest.mark.asyncio
    async def test_stakeholder_group_filtering(self, mock_transcript_store):
        """Test filtering by stakeholder group."""
        # Create segments from different stakeholder groups
        bank_segment = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Bank Rep",
            content="Bank perspective on cost",
            metadata={"stakeholder_group": "BankRep"},
        )
        trade_segment = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Trade Rep",
            content="Trade body perspective on governance",
            metadata={"stakeholder_group": "TradeBodyRep"},
        )

        # Mock search to return both segments
        mock_transcript_store.search_segments.return_value = [
            (bank_segment, 0.8),
            (trade_segment, 0.7),
        ]

        server = StakeholderViewsServer(mock_transcript_store)

        # Test search with BankRep filter
        from ai_agent.infrastructure.mcp.protocol import MCPRequest

        request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {
                    "topic": "perspectives",
                    "stakeholder_group": "BankRep",
                    "limit": 10,
                },
            },
        )

        await server.handle_tool_call(request)

        # Verify that the search was called with the correct stakeholder group
        mock_transcript_store.search_segments.assert_called_once()
        call_args = mock_transcript_store.search_segments.call_args
        assert call_args[1]["stakeholder_group"] == StakeholderGroup.BANK_REP

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_transcript_store):
        """Test error handling in integration scenarios."""
        # Mock search to raise an exception
        mock_transcript_store.search_segments.side_effect = Exception("Database error")

        server = StakeholderViewsServer(mock_transcript_store)

        from ai_agent.infrastructure.mcp.protocol import MCPRequest

        request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {"topic": "test topic", "limit": 10},
            },
        )

        # Should raise an MCPError, not return an error response
        from ai_agent.infrastructure.mcp.protocol import MCPError, MCPErrorCode

        with pytest.raises(MCPError) as exc_info:
            await server.handle_tool_call(request)

        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Search failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_shutdown_integration(self, integration_manager):
        """Test integration manager shutdown."""
        # Initialize first
        integration_manager.stakeholder_views_registry = MagicMock()
        integration_manager.stakeholder_views_registry.unregister_server.return_value = (
            True
        )

        # Test shutdown
        await integration_manager.shutdown()

        # Verify unregister was called
        integration_manager.stakeholder_views_registry.unregister_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_definition_consistency(self, mock_transcript_store):
        """Test that tool definition is consistent across calls."""
        server = StakeholderViewsServer(mock_transcript_store)

        # Get tool definition multiple times
        tool_def1 = await server.get_tool_definition()
        tool_def2 = await server.get_tool_definition()

        # Should be the same
        assert tool_def1.name == tool_def2.name
        assert tool_def1.description == tool_def2.description
        assert tool_def1.input_schema == tool_def2.input_schema
        assert tool_def1.metadata == tool_def2.metadata
