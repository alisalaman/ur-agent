"""Unit tests for transcript store functionality."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
import numpy as np

from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import (
    TranscriptSegment,
    TranscriptMetadata,
    StakeholderGroup,
    TranscriptSource,
)


class TestTranscriptStore:
    """Test transcript store functionality."""

    @pytest.fixture
    def mock_repository(self):
        repository = Mock()
        repository.create_transcript_metadata = AsyncMock()
        repository.create_transcript_segment = AsyncMock()
        repository.execute_query = AsyncMock()
        return repository

    @pytest.fixture
    def store(self, mock_repository):
        return TranscriptStore(
            mock_repository
        )  # No vector_db_path needed with pgvector

    @pytest.fixture
    def sample_metadata(self):
        return TranscriptMetadata(
            filename="test.docx",
            source=TranscriptSource.BANK_A,
            stakeholder_group=StakeholderGroup.BANK_REP,
        )

    @pytest.fixture
    def sample_segments(self):
        return [
            TranscriptSegment(
                transcript_id=uuid4(),
                speaker_name="Bank_Rep_A",
                content="The costs have been enormous - over £1.5 billion",
            ),
            TranscriptSegment(
                transcript_id=uuid4(),
                speaker_name="Bank_Rep_A",
                content="We need sustainable commercial models",
            ),
        ]

    @pytest.mark.asyncio
    async def test_store_transcript_data_success(
        self, store, sample_metadata, sample_segments
    ):
        """Test successful storage of transcript data."""
        result = await store.store_transcript_data(sample_metadata, sample_segments)

        assert result
        store.repository.create_transcript_metadata.assert_called_once_with(
            sample_metadata
        )
        assert store.repository.create_transcript_segment.call_count == len(
            sample_segments
        )

    @pytest.mark.asyncio
    async def test_store_transcript_data_without_repository(
        self, sample_metadata, sample_segments
    ):
        """Test storage when repository is not available."""
        store = TranscriptStore(None)
        result = await store.store_transcript_data(sample_metadata, sample_segments)

        assert result  # Should still succeed for demo purposes

    @pytest.mark.asyncio
    async def test_store_transcript_data_failure(
        self, store, sample_metadata, sample_segments
    ):
        """Test failure during storage."""
        store.repository.create_transcript_metadata.side_effect = Exception("DB error")
        result = await store.store_transcript_data(sample_metadata, sample_segments)

        assert not result

    @pytest.mark.asyncio
    async def test_search_segments(self, store):
        """Test segment search functionality."""
        # Mock database query result
        mock_row1 = Mock()
        mock_row1.id = "segment1"
        mock_row1.transcript_id = "transcript1"
        mock_row1.speaker_name = "Bank_Rep_A"
        mock_row1.speaker_title = None
        mock_row1.content = "Content 1"
        mock_row1.embedding = np.array([0.1, 0.2, 0.3])
        mock_row1.start_time = None
        mock_row1.end_time = None
        mock_row1.segment_index = 0
        mock_row1.metadata = {}
        mock_row1.created_at = "2024-01-01"
        mock_row1.similarity_score = 0.9

        mock_row2 = Mock()
        mock_row2.id = "segment2"
        mock_row2.transcript_id = "transcript1"
        mock_row2.speaker_name = "Bank_Rep_A"
        mock_row2.speaker_title = None
        mock_row2.content = "Content 2"
        mock_row2.embedding = np.array([0.4, 0.5, 0.6])
        mock_row2.start_time = None
        mock_row2.end_time = None
        mock_row2.segment_index = 1
        mock_row2.metadata = {}
        mock_row2.created_at = "2024-01-01"
        mock_row2.similarity_score = 0.7

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        store.repository.execute_query.return_value = mock_result

        results = await store.search_segments("test query", limit=5)

        assert len(results) == 2
        assert all(isinstance(result, tuple) and len(result) == 2 for result in results)
        store.repository.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_segments_with_stakeholder_group(self, store):
        """Test segment search with stakeholder group filter."""
        # Mock database query result
        mock_row = Mock()
        mock_row.id = "segment1"
        mock_row.transcript_id = "transcript1"
        mock_row.speaker_name = "Bank_Rep_A"
        mock_row.speaker_title = None
        mock_row.content = "Content 1"
        mock_row.embedding = np.array([0.1, 0.2, 0.3])
        mock_row.start_time = None
        mock_row.end_time = None
        mock_row.segment_index = 0
        mock_row.metadata = {}
        mock_row.created_at = "2024-01-01"
        mock_row.similarity_score = 0.8

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        store.repository.execute_query.return_value = mock_result

        results = await store.search_segments(
            "test query", stakeholder_group=StakeholderGroup.BANK_REP, limit=5
        )

        assert len(results) == 1
        store.repository.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_segments_error_handling(self, store):
        """Test search segments error handling."""
        store.repository.execute_query.side_effect = Exception("Search error")

        results = await store.search_segments("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_segments_by_topic(self, store):
        """Test topic-based segment retrieval."""
        # Mock database query result
        mock_row = Mock()
        mock_row.id = "segment1"
        mock_row.transcript_id = "transcript1"
        mock_row.speaker_name = "Bank_Rep_A"
        mock_row.speaker_title = None
        mock_row.content = "Content about governance"
        mock_row.embedding = np.array([0.1, 0.2, 0.3])
        mock_row.start_time = None
        mock_row.end_time = None
        mock_row.segment_index = 0
        mock_row.metadata = {}
        mock_row.created_at = "2024-01-01"

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        store.repository.execute_query.return_value = mock_result

        results = await store.get_segments_by_topic("governance")

        assert len(results) == 1
        assert results[0].content == "Content about governance"
        store.repository.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_segments_by_topic_with_stakeholder_group(self, store):
        """Test topic-based segment retrieval with stakeholder group filter."""
        # Mock database query result
        mock_row = Mock()
        mock_row.id = "segment1"
        mock_row.transcript_id = "transcript1"
        mock_row.speaker_name = "Bank_Rep_A"
        mock_row.speaker_title = None
        mock_row.content = "Content about governance"
        mock_row.embedding = np.array([0.1, 0.2, 0.3])
        mock_row.start_time = None
        mock_row.end_time = None
        mock_row.segment_index = 0
        mock_row.metadata = {}
        mock_row.created_at = "2024-01-01"

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        store.repository.execute_query.return_value = mock_result

        results = await store.get_segments_by_topic(
            "governance", stakeholder_group=StakeholderGroup.BANK_REP
        )

        assert len(results) == 1
        store.repository.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_segments_by_topic_error_handling(self, store):
        """Test topic-based segment retrieval error handling."""
        store.repository.execute_query.side_effect = Exception("Query error")

        results = await store.get_segments_by_topic("governance")

        assert results == []

    def test_get_topic_keywords(self, store):
        """Test topic keyword retrieval."""
        keywords = store._get_topic_keywords("governance")

        assert "governance" in keywords
        assert "regulation" in keywords
        assert "compliance" in keywords

    def test_get_topic_keywords_unknown_topic(self, store):
        """Test topic keyword retrieval for unknown topic."""
        keywords = store._get_topic_keywords("unknown_topic")

        assert keywords == ["unknown_topic"]

    def test_row_to_segment_conversion(self, store):
        """Test database row to segment conversion."""
        mock_row = Mock()
        mock_row.id = "segment1"
        mock_row.transcript_id = "transcript1"
        mock_row.speaker_name = "Bank_Rep_A"
        mock_row.speaker_title = "Bank Rep"
        mock_row.content = "Test content"
        mock_row.embedding = np.array([0.1, 0.2, 0.3])
        mock_row.start_time = 10.5
        mock_row.end_time = 15.2
        mock_row.segment_index = 0
        mock_row.metadata = {"test": "value"}
        mock_row.created_at = "2024-01-01"

        segment = store._row_to_segment(mock_row)

        assert segment.id == "segment1"
        assert segment.transcript_id == "transcript1"
        assert segment.speaker_name == "Bank_Rep_A"
        assert segment.speaker_title == "Bank Rep"
        assert segment.content == "Test content"
        assert segment.embedding == [0.1, 0.2, 0.3]
        assert segment.start_time == 10.5
        assert segment.end_time == 15.2
        assert segment.segment_index == 0
        assert segment.metadata == {"test": "value"}
        assert segment.created_at == "2024-01-01"
