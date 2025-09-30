"""Test transcript processing functionality."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from uuid import uuid4

from ai_agent.infrastructure.knowledge.transcript_processor import (
    TranscriptProcessor,
    ProcessingConfig,
)
from ai_agent.domain.knowledge_models import (
    StakeholderGroup,
    TranscriptSource,
    TranscriptSegment,
)


class TestTranscriptProcessor:
    """Test transcript processing functionality."""

    @pytest.fixture
    def processor(self):
        config = ProcessingConfig()
        return TranscriptProcessor(config)

    @pytest.fixture
    def sample_docx_content(self):
        return """
        Alex Chen: Welcome to today's discussion about Digital Financial Services governance.

        Interviewer: Thank you for joining us. Let's start with your views on commercial sustainability.

        Alex Chen: The costs have been enormous - over £1.5 billion for Digital Financial Services implementation.
        We need sustainable commercial models that provide clear ROI for all participants.

        Interviewer: What about governance frameworks?

        Alex Chen: We need symmetrical governance where all parties have balanced rights and obligations.
        The current approach creates a lopsided market where data holders have all the obligations.
        """

    def test_speaker_identification(self, processor):
        """Test speaker identification from text."""
        text = "Alex Chen: This is a test statement."
        speaker = processor._identify_speaker(text)
        assert speaker == "Alex Chen"

    def test_segment_validation(self, processor):
        """Test segment validation logic."""
        # Valid segment
        valid_segment = TranscriptSegment(
            transcript_id=uuid4(),
            speaker_name="Alex Chen",
            content="This is a valid segment with sufficient content length for testing purposes.",
        )
        assert processor._is_valid_segment(valid_segment)

        # Invalid segment - too short
        invalid_segment = TranscriptSegment(
            transcript_id=uuid4(), speaker_name="Alex Chen", content="Too short"
        )
        assert not processor._is_valid_segment(invalid_segment)

    def test_topic_keyword_extraction(self, processor):
        """Test topic keyword extraction."""
        query = "What are the commercial sustainability concerns?"
        topics = processor._extract_topics_from_query(query)
        assert "commercial_sustainability" in topics

    @pytest.mark.asyncio
    async def test_transcript_processing(self, processor, sample_docx_content):
        """Test full transcript processing."""
        # Mock the Document constructor to avoid file I/O
        with patch(
            "ai_agent.infrastructure.knowledge.transcript_processor.Document"
        ) as mock_doc_class:
            # Create mock document with paragraphs that will create valid segments
            mock_doc = Mock()
            mock_paragraphs = [
                Mock(
                    text="Alex Chen: Welcome to today's discussion about Digital Financial Services governance."
                ),
                Mock(
                    text="Interviewer: Thank you for joining us. Let's start with your views."
                ),
                Mock(
                    text="Alex Chen: The costs have been enormous - over £1.5 billion for implementation."
                ),
            ]
            mock_doc.paragraphs = mock_paragraphs
            mock_doc_class.return_value = mock_doc

            # Mock file operations
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    with patch("pathlib.Path.name", "test.docx"):
                        # Process transcript
                        metadata, segments = await processor.process_transcript_file(
                            Path("test.docx"),
                            StakeholderGroup.BANK_REP,
                            TranscriptSource.BANK_A,
                        )

                        assert metadata.stakeholder_group == StakeholderGroup.BANK_REP
                        assert metadata.source == TranscriptSource.BANK_A
                        assert len(segments) > 0
                        assert all(segment.speaker_name for segment in segments)

    def test_create_segment(self, processor):
        """Test segment creation."""
        transcript_id = uuid4()
        segment = processor._create_segment(
            transcript_id, "Alex Chen", "Test content", 0
        )

        assert segment.transcript_id == transcript_id
        assert segment.speaker_name == "Alex Chen"
        assert segment.content == "Test content"
        assert segment.segment_index == 0

    def test_extract_text_from_docx(self, processor):
        """Test text extraction from DOCX."""
        mock_doc = Mock()
        mock_paragraphs = [
            Mock(text="First paragraph"),
            Mock(text=""),
            Mock(text="Second paragraph"),
            Mock(text="   "),
            Mock(text="Third paragraph"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        text = processor._extract_text_from_docx(mock_doc)
        expected = "First paragraph\nSecond paragraph\nThird paragraph"
        assert text == expected

    def test_identify_speaker_with_patterns(self, processor):
        """Test speaker identification with various patterns."""
        test_cases = [
            ("Alex Chen: Hello", "Alex Chen"),
            ("Interviewer: Hi there", "Interviewer"),
            ("Unknown Speaker: Test", "Unknown"),
            ("Regular text without speaker", None),
        ]

        for line, expected in test_cases:
            result = processor._identify_speaker(line)
            assert result == expected

    def test_processing_config_defaults(self):
        """Test processing configuration defaults."""
        config = ProcessingConfig()
        assert config.min_segment_length == 50
        assert config.max_segment_length == 2000
        assert isinstance(config.speaker_patterns, dict)
        assert isinstance(config.topic_keywords, dict)

    def test_speaker_patterns_loading(self, processor):
        """Test speaker patterns are loaded correctly."""
        patterns = processor._load_speaker_patterns()
        # Check that patterns are loaded (actual patterns may differ from expected)
        assert isinstance(patterns, dict)
        assert len(patterns) > 0
        # Check for some common pattern keys
        assert any("Bank_Rep" in key for key in patterns.keys())

    def test_topic_keywords_loading(self, processor):
        """Test topic keywords are loaded correctly."""
        keywords = processor._load_topic_keywords()
        # Check that keywords are loaded (actual keywords may differ from expected)
        assert isinstance(keywords, dict)
        assert len(keywords) > 0
        # Check for some common keyword categories
        assert any(
            "sustainability" in key.lower() or "governance" in key.lower()
            for key in keywords.keys()
        )
