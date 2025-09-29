"""Integration tests for transcript processing system."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from ai_agent.infrastructure.knowledge.transcript_processor import (
    TranscriptProcessor,
    ProcessingConfig,
)
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import StakeholderGroup, TranscriptSource


class TestTranscriptIntegration:
    """Integration tests for transcript processing system."""

    @pytest.fixture
    def mock_repository(self):
        repository = Mock()
        repository.create_transcript_metadata = AsyncMock()
        repository.create_transcript_segment = AsyncMock()
        return repository

    @pytest.fixture
    def processor(self):
        config = ProcessingConfig()
        return TranscriptProcessor(config)

    @pytest.fixture
    def store(self, mock_repository):
        return TranscriptStore(
            mock_repository
        )  # No vector_db_path needed with pgvector

    @pytest.fixture
    def sample_transcript_content(self):
        return """
        Bank_Rep_A: Welcome to today's discussion about Open Banking governance.

        Interviewer: Thank you for joining us. Let's start with your views on commercial sustainability.

        Bank_Rep_A: The costs have been enormous - over £1.5 billion for Open Banking implementation.
        We need sustainable commercial models that provide clear ROI for all participants.

        Interviewer: What about governance frameworks?

        Bank_Rep_A: We need symmetrical governance where all parties have balanced rights and obligations.
        The current approach creates a lopsided market where data holders have all the obligations.

        Interviewer: How do you see the future of Smart Data schemes?

        Bank_Rep_A: We need to learn from Open Banking. The commercial model must be clear from the start.
        Without proper incentivization, these schemes become compliance exercises rather than value creators.
        """

    @pytest.mark.asyncio
    async def test_end_to_end_transcript_processing(
        self, processor, store, sample_transcript_content
    ):
        """Test complete transcript processing workflow."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            # Create a mock DOCX file
            with patch(
                "ai_agent.infrastructure.knowledge.transcript_processor.Document"
            ) as mock_doc:
                # Split content into paragraphs
                paragraphs = [
                    line.strip()
                    for line in sample_transcript_content.split("\n")
                    if line.strip()
                ]
                mock_paragraphs = [Mock(text=para) for para in paragraphs]
                mock_doc.return_value.paragraphs = mock_paragraphs

                # Process transcript
                metadata, segments = await processor.process_transcript_file(
                    Path(tmp_file.name),
                    StakeholderGroup.BANK_REP,
                    TranscriptSource.BANK_A,
                )

                # Verify metadata
                assert metadata.stakeholder_group == StakeholderGroup.BANK_REP
                assert metadata.source == TranscriptSource.BANK_A
                assert metadata.filename == tmp_file.name.split("/")[-1]
                assert metadata.processing_status == "processing"

                # Verify segments
                assert len(segments) > 0
                assert all(segment.speaker_name for segment in segments)
                assert all(segment.content for segment in segments)

                # Verify speaker distribution
                speakers = [segment.speaker_name for segment in segments]
                assert "Bank_Rep_A" in speakers
                assert "Interviewer" in speakers

                # Store in database
                success = await store.store_transcript_data(metadata, segments)
                assert success

                # Verify repository calls
                store.repository.create_transcript_metadata.assert_called_once_with(
                    metadata
                )
                assert store.repository.create_transcript_segment.call_count == len(
                    segments
                )

    @pytest.mark.asyncio
    async def test_transcript_search_functionality(self, store):
        """Test transcript search functionality."""
        # Mock the repository execute_query method
        with patch.object(
            store.repository, "execute_query", new_callable=AsyncMock
        ) as mock_execute:
            # Mock search results
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id="segment1",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content about costs",
                    similarity_score=0.1,
                ),
                Mock(
                    id="segment2",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content about governance",
                    similarity_score=0.3,
                ),
                Mock(
                    id="segment3",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content about ROI",
                    similarity_score=0.5,
                ),
            ]
            mock_execute.return_value = mock_result

            # Test search without filters
            results = await store.search_segments("commercial sustainability", limit=5)
            assert len(results) == 3
            assert all(
                isinstance(result, tuple) and len(result) == 2 for result in results
            )

            # Test search with stakeholder group filter
            results_filtered = await store.search_segments(
                "governance", stakeholder_group=StakeholderGroup.BANK_REP, limit=3
            )
            assert len(results_filtered) == 3

            # Verify the query was called with correct parameters
            assert mock_execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_processing_configuration(self):
        """Test processing configuration affects behavior."""
        # Test with custom configuration
        config = ProcessingConfig(min_segment_length=100, max_segment_length=1000)
        processor = TranscriptProcessor(config)

        # Test segment validation with custom limits
        from ai_agent.domain.knowledge_models import TranscriptSegment

        # Valid segment (within limits)
        valid_segment = TranscriptSegment(
            transcript_id=uuid4(),
            speaker_name="Bank_Rep_A",
            content="This is a valid segment with sufficient content length for testing purposes and meets the minimum requirements.",
        )
        assert processor._is_valid_segment(valid_segment)

        # Invalid segment (too short)
        invalid_segment = TranscriptSegment(
            transcript_id=uuid4(), speaker_name="Gary Aydon", content="Too short"
        )
        assert not processor._is_valid_segment(invalid_segment)

    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self, processor):
        """Test error handling during transcript processing."""
        # Test with non-existent file
        with pytest.raises(
            (FileNotFoundError, Exception)
        ):  # Can be FileNotFoundError or PackageNotFoundError
            await processor.process_transcript_file(
                Path("non_existent_file.docx"),
                StakeholderGroup.BANK_REP,
                TranscriptSource.SANTANDER,
            )

    @pytest.mark.asyncio
    async def test_error_handling_in_storage(self, store):
        """Test error handling during storage."""
        from ai_agent.domain.knowledge_models import (
            TranscriptMetadata,
            TranscriptSegment,
        )

        metadata = TranscriptMetadata(
            filename="test.docx",
            source=TranscriptSource.BANK_A,
            stakeholder_group=StakeholderGroup.BANK_REP,
        )

        segments = [
            TranscriptSegment(
                transcript_id=uuid4(), speaker_name="Gary Aydon", content="Test content"
            )
        ]

        # Test repository error
        store.repository.create_transcript_metadata.side_effect = Exception(
            "Database error"
        )

        success = await store.store_transcript_data(metadata, segments)
        assert not success

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor):
        """Test concurrent transcript processing."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            with patch(
                "ai_agent.infrastructure.knowledge.transcript_processor.Document"
            ) as mock_doc:
                mock_paragraphs = [
                    Mock(
                        text="Bank_Rep_A: This is a longer test content that meets the minimum segment length requirements for proper transcript processing and validation."
                    )
                ]
                mock_doc.return_value.paragraphs = mock_paragraphs

                # Process multiple transcripts concurrently
                tasks = []
                for _ in range(3):
                    task = processor.process_transcript_file(
                        Path(tmp_file.name),
                        StakeholderGroup.BANK_REP,
                        TranscriptSource.BANK_A,
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)

                assert len(results) == 3
                for metadata, segments in results:
                    assert metadata.stakeholder_group == StakeholderGroup.BANK_REP
                    assert len(segments) > 0

    @pytest.mark.asyncio
    async def test_topic_keyword_extraction_integration(self, processor):
        """Test topic keyword extraction in realistic scenarios."""
        test_queries = [
            "What are the commercial sustainability concerns?",
            "How do governance frameworks work?",
            "What about cost considerations?",
            "Tell me about interoperability issues",
            "What are the technical feasibility challenges?",
        ]

        for query in test_queries:
            topics = processor._extract_topics_from_query(query)
            assert isinstance(topics, list)
            assert len(topics) > 0
            # At least one topic should be extracted
            assert any(topic in processor._load_topic_keywords() for topic in topics)

    @pytest.mark.asyncio
    async def test_speaker_identification_integration(self, processor):
        """Test speaker identification with realistic transcript content."""
        test_lines = [
            "Bank_Rep_A: Welcome to today's discussion about Open Banking governance.",
            "Interviewer: Thank you for joining us. Let's start with your views.",
            "Trade_Body_Rep_A: From Trade Body's perspective, we see several key issues.",
            "Payments_Rep_A: Payments Provider's view is that we need to focus on interoperability.",
            "Bank_Rep_B: Bank B has been working on these issues for some time.",
            "Bank_Rep_C: Bank C's experience with Open Banking has been challenging.",
            "Bank_Rep_D: Bank D has similar concerns.",
            "Bank_Rep_E: Bank E's approach has been more collaborative.",
            "Unknown Speaker: This should be identified as Unknown.",
            "Regular text without speaker identification.",
        ]

        expected_speakers = [
            "Bank_Rep_A",
            "Interviewer",
            "Trade_Body_Rep_A",
            "Payments_Rep_A",
            "Bank_Rep_B",
            "Bank_Rep_C",
            "Bank_Rep_D",
            "Bank_Rep_E",
            "Unknown",
            None,
        ]

        for line, expected in zip(test_lines, expected_speakers, strict=False):
            speaker = processor._identify_speaker(line)
            assert speaker == expected, f"Failed for line: {line[:50]}..."
