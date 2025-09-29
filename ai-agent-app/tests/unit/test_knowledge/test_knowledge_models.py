"""Unit tests for knowledge models."""

import pytest
from datetime import datetime
from uuid import uuid4

from ai_agent.domain.knowledge_models import (
    StakeholderGroup,
    TranscriptSource,
    TranscriptSegment,
    TranscriptMetadata,
    TopicTag,
    SegmentTopicMapping,
)


class TestKnowledgeModels:
    """Test knowledge model functionality."""

    def test_stakeholder_group_enum(self):
        """Test stakeholder group enum values."""
        assert StakeholderGroup.BANK_REP == "BankRep"
        assert StakeholderGroup.TRADE_BODY_REP == "TradeBodyRep"
        assert StakeholderGroup.PAYMENTS_ECOSYSTEM_REP == "PaymentsEcosystemRep"

    def test_transcript_source_enum(self):
        """Test transcript source enum values."""
        assert TranscriptSource.BANK_A == "Bank_A"
        assert TranscriptSource.TRADE_BODY_A == "Trade_Body_A"
        assert TranscriptSource.PAYMENTS_PROVIDER_A == "Payments_Provider_A"
        assert TranscriptSource.BANK_B == "Bank_B"
        assert TranscriptSource.BANK_C == "Bank_C"
        assert TranscriptSource.BANK_D == "Bank_D"

    def test_transcript_segment_creation(self):
        """Test transcript segment creation."""
        transcript_id = uuid4()
        segment = TranscriptSegment(
            transcript_id=transcript_id,
            speaker_name="Bank_Rep_A",
            content="Test content",
            segment_index=0,
        )

        assert segment.transcript_id == transcript_id
        assert segment.speaker_name == "Bank_Rep_A"
        assert segment.content == "Test content"
        assert segment.segment_index == 0
        assert segment.speaker_title is None
        assert segment.start_time is None
        assert segment.end_time is None
        assert isinstance(segment.metadata, dict)
        assert isinstance(segment.created_at, datetime)

    def test_transcript_segment_with_optional_fields(self):
        """Test transcript segment with optional fields."""
        transcript_id = uuid4()
        segment = TranscriptSegment(
            transcript_id=transcript_id,
            speaker_name="Bank_Rep_A",
            speaker_title="Senior Manager",
            content="Test content",
            start_time=10.5,
            end_time=15.2,
            segment_index=1,
            metadata={"test": "value"},
        )

        assert segment.speaker_title == "Senior Manager"
        assert segment.start_time == 10.5
        assert segment.end_time == 15.2
        assert segment.metadata == {"test": "value"}

    def test_transcript_metadata_creation(self):
        """Test transcript metadata creation."""
        metadata = TranscriptMetadata(
            filename="test.docx",
            source=TranscriptSource.BANK_A,
            stakeholder_group=StakeholderGroup.BANK_REP,
        )

        assert metadata.filename == "test.docx"
        assert metadata.source == TranscriptSource.BANK_A
        assert metadata.stakeholder_group == StakeholderGroup.BANK_REP
        assert metadata.interview_date is None
        assert isinstance(metadata.participants, list)
        assert metadata.total_segments == 0
        assert metadata.file_size_bytes == 0
        assert metadata.processing_status == "pending"
        assert isinstance(metadata.created_at, datetime)

    def test_transcript_metadata_with_optional_fields(self):
        """Test transcript metadata with optional fields."""
        interview_date = datetime(2024, 1, 15, 10, 30)
        metadata = TranscriptMetadata(
            filename="test.docx",
            source=TranscriptSource.BANK_A,
            stakeholder_group=StakeholderGroup.BANK_REP,
            interview_date=interview_date,
            participants=["Bank_Rep_A", "Interviewer"],
            total_segments=10,
            file_size_bytes=1024,
            processing_status="completed",
        )

        assert metadata.interview_date == interview_date
        assert metadata.participants == ["Bank_Rep_A", "Interviewer"]
        assert metadata.total_segments == 10
        assert metadata.file_size_bytes == 1024
        assert metadata.processing_status == "completed"

    def test_topic_tag_creation(self):
        """Test topic tag creation."""
        tag = TopicTag(
            name="commercial sustainability",
            description="Commercial viability aspects",
            category="business",
            confidence_score=0.9,
        )

        assert tag.name == "commercial sustainability"
        assert tag.description == "Commercial viability aspects"
        assert tag.category == "business"
        assert tag.confidence_score == 0.9
        assert isinstance(tag.created_at, datetime)

    def test_topic_tag_with_defaults(self):
        """Test topic tag with default values."""
        tag = TopicTag(name="test topic")

        assert tag.name == "test topic"
        assert tag.description is None
        assert tag.category == ""
        assert tag.confidence_score == 0.0

    def test_segment_topic_mapping_creation(self):
        """Test segment topic mapping creation."""
        segment_id = uuid4()
        topic_id = uuid4()
        mapping = SegmentTopicMapping(
            segment_id=segment_id, topic_id=topic_id, relevance_score=0.8
        )

        assert mapping.segment_id == segment_id
        assert mapping.topic_id == topic_id
        assert mapping.relevance_score == 0.8
        assert isinstance(mapping.created_at, datetime)

    def test_segment_topic_mapping_with_defaults(self):
        """Test segment topic mapping with default values."""
        segment_id = uuid4()
        topic_id = uuid4()
        mapping = SegmentTopicMapping(segment_id=segment_id, topic_id=topic_id)

        assert mapping.relevance_score == 0.0

    def test_model_immutability(self):
        """Test that models are properly immutable where expected."""
        # Test that we can't modify enum values
        with pytest.raises(AttributeError):
            StakeholderGroup.BANK_REP = "NewValue"

        with pytest.raises(AttributeError):
            TranscriptSource.BANK_A = "NewValue"

    def test_model_serialization(self):
        """Test that models can be serialized/deserialized."""
        segment = TranscriptSegment(
            transcript_id=uuid4(), speaker_name="Bank_Rep_A", content="Test content"
        )

        # Test that we can access all fields
        assert hasattr(segment, "id")
        assert hasattr(segment, "transcript_id")
        assert hasattr(segment, "speaker_name")
        assert hasattr(segment, "content")
        assert hasattr(segment, "created_at")

    def test_model_default_factory_behavior(self):
        """Test that default factory functions work correctly."""
        segment1 = TranscriptSegment(
            transcript_id=uuid4(), speaker_name="Speaker1", content="Content1"
        )
        segment2 = TranscriptSegment(
            transcript_id=uuid4(), speaker_name="Speaker2", content="Content2"
        )

        # IDs should be different
        assert segment1.id != segment2.id

        # Created times should be different (or very close)
        time_diff = abs((segment1.created_at - segment2.created_at).total_seconds())
        assert time_diff < 1.0  # Should be created within 1 second
