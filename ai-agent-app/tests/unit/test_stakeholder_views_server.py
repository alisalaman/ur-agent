"""Unit tests for stakeholder views MCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import (
    StakeholderViewsServer,
)
from ai_agent.infrastructure.mcp.servers.stakeholder_search import (
    StakeholderSearchEngine,
    SearchResult,
)
from ai_agent.infrastructure.mcp.protocol import MCPRequest, MCPError, MCPErrorCode
from ai_agent.domain.knowledge_models import TranscriptSegment
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore


class TestStakeholderViewsServer:
    """Test cases for StakeholderViewsServer."""

    @pytest.fixture
    def mock_transcript_store(self):
        """Create a mock transcript store."""
        store = AsyncMock(spec=TranscriptStore)
        return store

    @pytest.fixture
    def server(self, mock_transcript_store):
        """Create a stakeholder views server instance."""
        return StakeholderViewsServer(mock_transcript_store)

    def test_create_tool_definition(self, server):
        """Test tool definition creation."""
        tool_def = server._create_tool_definition()

        assert tool_def.name == "get_stakeholder_views"
        assert "stakeholder" in tool_def.description.lower()
        assert tool_def.input_schema["type"] == "object"
        assert "topic" in tool_def.input_schema["properties"]
        assert "stakeholder_group" in tool_def.input_schema["properties"]
        assert "limit" in tool_def.input_schema["properties"]
        assert "min_relevance_score" in tool_def.input_schema["properties"]
        assert tool_def.input_schema["required"] == ["topic"]

    @pytest.mark.asyncio
    async def test_handle_tool_call_success(self, server, mock_transcript_store):
        """Test successful tool call handling."""
        # Mock search results
        mock_segment = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="John Doe",
            speaker_title="Bank Representative",
            content="We believe the cost of implementation is reasonable",
            metadata={"stakeholder_group": "BankRep"},
        )
        mock_transcript_store.search_segments.return_value = [(mock_segment, 0.85)]

        # Create request
        request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {
                    "topic": "cost of implementation",
                    "stakeholder_group": "BankRep",
                    "limit": 10,
                    "min_relevance_score": 0.3,
                },
            },
        )

        # Execute
        response = await server.handle_tool_call(request)

        # Verify
        assert response.id == request.id
        assert response.result is not None
        assert response.result["topic"] == "cost of implementation"
        assert response.result["stakeholder_group"] == "BankRep"
        assert response.result["results_count"] == 1
        assert len(response.result["results"]) == 1

        result = response.result["results"][0]
        assert result["speaker_name"] == "John Doe"
        assert (
            result["content"] == "We believe the cost of implementation is reasonable"
        )
        assert result["relevance_score"] == 0.85
        assert result["stakeholder_group"] == "BankRep"

    @pytest.mark.asyncio
    async def test_handle_tool_call_invalid_method(self, server):
        """Test handling of invalid method."""
        request = MCPRequest(
            method="invalid_method",
            params={"name": "get_stakeholder_views", "arguments": {"topic": "test"}},
        )

        with pytest.raises(MCPError) as exc_info:
            await server.handle_tool_call(request)

        assert exc_info.value.code == MCPErrorCode.INVALID_REQUEST

    @pytest.mark.asyncio
    async def test_handle_tool_call_missing_topic(self, server):
        """Test handling of missing required topic parameter."""
        request = MCPRequest(
            method="tools/call",
            params={"name": "get_stakeholder_views", "arguments": {}},
        )

        with pytest.raises(MCPError) as exc_info:
            await server.handle_tool_call(request)

        assert exc_info.value.code == MCPErrorCode.INVALID_PARAMS
        assert "topic" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_handle_tool_call_invalid_stakeholder_group(self, server):
        """Test handling of invalid stakeholder group."""
        request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {"topic": "test", "stakeholder_group": "InvalidGroup"},
            },
        )

        with pytest.raises(MCPError) as exc_info:
            await server.handle_tool_call(request)

        assert exc_info.value.code == MCPErrorCode.INVALID_PARAMS
        assert "InvalidGroup" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_handle_tool_call_wrong_tool_name(self, server):
        """Test handling of wrong tool name."""
        request = MCPRequest(
            method="tools/call",
            params={"name": "wrong_tool", "arguments": {"topic": "test"}},
        )

        with pytest.raises(MCPError) as exc_info:
            await server.handle_tool_call(request)

        assert exc_info.value.code == MCPErrorCode.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_search_stakeholder_views_with_filtering(
        self, server, mock_transcript_store
    ):
        """Test search with relevance score filtering."""
        # Create mock segments with different scores
        segment1 = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Speaker 1",
            content="High relevance content",
            metadata={"stakeholder_group": "BankRep"},
        )
        segment2 = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Speaker 2",
            content="Low relevance content",
            metadata={"stakeholder_group": "BankRep"},
        )

        mock_transcript_store.search_segments.return_value = [
            (segment1, 0.8),  # High score
            (segment2, 0.2),  # Low score
        ]

        results = await server._search_stakeholder_views(
            topic="test topic", min_relevance_score=0.5
        )

        # Should only return high relevance result
        assert len(results) == 1
        assert results[0]["relevance_score"] == 0.8
        assert results[0]["speaker_name"] == "Speaker 1"

    @pytest.mark.asyncio
    async def test_search_stakeholder_views_limit_enforcement(
        self, server, mock_transcript_store
    ):
        """Test that search respects the limit parameter."""
        # Create multiple mock segments
        segments = []
        for i in range(10):
            segment = TranscriptSegment(
                id=uuid4(),
                transcript_id=uuid4(),
                speaker_name=f"Speaker {i}",
                content=f"Content {i}",
                metadata={"stakeholder_group": "BankRep"},
            )
            segments.append((segment, 0.7))

        mock_transcript_store.search_segments.return_value = segments

        results = await server._search_stakeholder_views(topic="test topic", limit=5)

        assert len(results) == 5

    def test_infer_stakeholder_group(self, server):
        """Test stakeholder group inference."""
        from ai_agent.infrastructure.knowledge.stakeholder_utils import (
            StakeholderGroupInference,
        )

        segment = MagicMock()
        segment.metadata = {"stakeholder_group": "BankRep"}

        result = StakeholderGroupInference.infer_from_segment(segment)
        assert result == "BankRep"

        # Test with missing metadata
        segment.metadata = {}
        result = StakeholderGroupInference.infer_from_segment(segment)
        assert result == "Unknown"

    @pytest.mark.asyncio
    async def test_get_tool_definition(self, server):
        """Test getting tool definition."""
        tool_def = await server.get_tool_definition()
        assert tool_def.name == "get_stakeholder_views"


class TestStakeholderSearchEngine:
    """Test cases for StakeholderSearchEngine."""

    @pytest.fixture
    def mock_transcript_store(self):
        """Create a mock transcript store."""
        return AsyncMock(spec=TranscriptStore)

    @pytest.fixture
    def search_engine(self, mock_transcript_store):
        """Create a search engine instance."""
        return StakeholderSearchEngine(mock_transcript_store)

    @pytest.mark.asyncio
    async def test_search_with_analysis(self, search_engine, mock_transcript_store):
        """Test search with analysis."""
        # Mock segment
        segment = TranscriptSegment(
            id=uuid4(),
            transcript_id=uuid4(),
            speaker_name="Test Speaker",
            content="This is a positive statement about governance",
            metadata={"stakeholder_group": "BankRep"},
        )
        mock_transcript_store.search_segments.return_value = [(segment, 0.7)]

        results = await search_engine.search_with_analysis(
            topic="governance", include_analysis=True
        )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.speaker_name == "Test Speaker"
        assert result.relevance_score > 0.7  # Should be enhanced
        assert result.confidence_level in ["high", "medium", "low", "very_low"]

    def test_find_topic_matches(self, search_engine):
        """Test topic keyword matching."""
        content = "We need better governance and regulation in this area"
        topic = "governance"

        matches = search_engine._find_topic_matches(content, topic)

        assert "governance" in matches
        assert "regulation" in matches  # Related keyword

    def test_calculate_sentiment_positive(self, search_engine):
        """Test positive sentiment calculation."""
        content = "This is a good and excellent solution that we support"
        sentiment = search_engine._calculate_sentiment(content)

        assert sentiment > 0  # Should be positive

    def test_calculate_sentiment_negative(self, search_engine):
        """Test negative sentiment calculation."""
        content = "This is a bad and problematic approach that we disagree with"
        sentiment = search_engine._calculate_sentiment(content)

        assert sentiment < 0  # Should be negative

    def test_calculate_sentiment_neutral(self, search_engine):
        """Test neutral sentiment calculation."""
        content = "This is a standard approach for implementation"
        sentiment = search_engine._calculate_sentiment(content)

        assert sentiment == 0  # Should be neutral

    def test_determine_confidence_high(self, search_engine):
        """Test high confidence determination."""
        confidence = search_engine._determine_confidence(
            base_score=0.9, topic_matches=4, sentiment_score=0.5
        )

        assert confidence == "high"

    def test_determine_confidence_medium(self, search_engine):
        """Test medium confidence determination."""
        confidence = search_engine._determine_confidence(
            base_score=0.7, topic_matches=2, sentiment_score=0.3
        )

        assert confidence == "medium"

    def test_determine_confidence_low(self, search_engine):
        """Test low confidence determination."""
        confidence = search_engine._determine_confidence(
            base_score=0.5, topic_matches=1, sentiment_score=0.1
        )

        assert confidence == "low"

    def test_determine_confidence_very_low(self, search_engine):
        """Test very low confidence determination."""
        confidence = search_engine._determine_confidence(
            base_score=0.3, topic_matches=0, sentiment_score=0.0
        )

        assert confidence == "very_low"

    def test_adjust_relevance_score(self, search_engine):
        """Test relevance score adjustment."""
        base_score = 0.6
        topic_matches = ["governance", "regulation"]
        sentiment_score = 0.4

        adjusted_score = search_engine._adjust_relevance_score(
            base_score, topic_matches, sentiment_score
        )

        assert adjusted_score > base_score  # Should be enhanced
        assert adjusted_score <= 1.0  # Should be capped at 1.0

    def test_load_topic_keywords(self, search_engine):
        """Test topic keywords loading."""
        keywords = search_engine._load_topic_keywords()

        assert "governance" in keywords
        assert "commercial sustainability" in keywords
        assert "cost" in keywords
        assert "interoperability" in keywords
        assert "technical feasibility" in keywords

        # Check specific keywords
        governance_keywords = keywords["governance"]
        assert "regulation" in governance_keywords
        assert "compliance" in governance_keywords

    def test_load_sentiment_keywords(self, search_engine):
        """Test sentiment keywords loading."""
        keywords = search_engine._load_sentiment_keywords()

        assert "positive" in keywords
        assert "negative" in keywords

        positive_words = keywords["positive"]
        assert "good" in positive_words
        assert "excellent" in positive_words

        negative_words = keywords["negative"]
        assert "bad" in negative_words
        assert "poor" in negative_words
