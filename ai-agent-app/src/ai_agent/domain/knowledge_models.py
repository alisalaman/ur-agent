"""Knowledge models for transcript data and stakeholder information."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from uuid import UUID, uuid4


class StakeholderGroup(str, Enum):
    """Stakeholder group categorization."""

    BANK_REP = "BankRep"
    TRADE_BODY_REP = "TradeBodyRep"
    PAYMENTS_ECOSYSTEM_REP = "PaymentsEcosystemRep"


class TranscriptSource(str, Enum):
    """Source of transcript data (anonymized)."""

    BANK_A = "Bank_A"
    TRADE_BODY_A = "Trade_Body_A"
    PAYMENTS_PROVIDER_A = "Payments_Provider_A"
    BANK_B = "Bank_B"
    BANK_C = "Bank_C"
    BANK_D = "Bank_D"


@dataclass
class TranscriptSegment:
    """Individual speaker segment from transcript."""

    transcript_id: UUID
    speaker_name: str = ""
    content: str = ""
    id: UUID = field(default_factory=uuid4)
    speaker_title: str | None = None
    embedding: list[float] | None = None  # Vector embedding for semantic search
    start_time: float | None = None
    end_time: float | None = None
    segment_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TranscriptMetadata:
    """Metadata for a complete transcript."""

    source: TranscriptSource
    stakeholder_group: StakeholderGroup
    filename: str = ""
    id: UUID = field(default_factory=uuid4)
    interview_date: datetime | None = None
    participants: list[str] = field(default_factory=list)
    total_segments: int = 0
    file_size_bytes: int = 0
    processing_status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TopicTag:
    """Topic classification for transcript segments."""

    name: str = ""
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    category: str = ""
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SegmentTopicMapping:
    """Mapping between segments and topics."""

    segment_id: UUID
    topic_id: UUID
    relevance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
