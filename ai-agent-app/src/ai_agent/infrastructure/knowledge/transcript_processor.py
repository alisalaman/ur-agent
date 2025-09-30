"""Transcript processing infrastructure for DOCX files."""

from pathlib import Path
import structlog
from docx import Document
from docx.document import Document as DocumentType
import re
from dataclasses import dataclass, field
from uuid import UUID

from ai_agent.domain.knowledge_models import (
    TranscriptSegment,
    TranscriptMetadata,
    StakeholderGroup,
    TranscriptSource,
)

logger = structlog.get_logger()


@dataclass
class ProcessingConfig:
    """Configuration for transcript processing."""

    min_segment_length: int = 50
    max_segment_length: int = 2000
    speaker_patterns: dict[str, str] = field(default_factory=dict)
    topic_keywords: dict[str, list[str]] = field(default_factory=dict)


class TranscriptProcessor:
    """Processes DOCX transcript files into structured data."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.speaker_patterns = self._load_speaker_patterns()
        self.topic_keywords = self._load_topic_keywords()

    async def process_transcript_file(
        self,
        file_path: Path,
        stakeholder_group: StakeholderGroup,
        source: TranscriptSource,
    ) -> tuple[TranscriptMetadata, list[TranscriptSegment]]:
        """Process a single transcript file."""
        logger.info("Processing transcript file", file_path=str(file_path))

        try:
            # Load DOCX document
            doc = Document(str(file_path))

            # Extract text and metadata
            full_text = self._extract_text_from_docx(doc)
            metadata = self._create_transcript_metadata(
                file_path, stakeholder_group, source, full_text
            )

            # Segment the text
            segments = await self._segment_transcript(full_text, metadata.id)

            # Update metadata with segment count
            metadata.total_segments = len(segments)

            logger.info(
                "Transcript processed successfully",
                file_path=str(file_path),
                segments=len(segments),
            )

            return metadata, segments

        except Exception as e:
            logger.error(
                "Failed to process transcript", file_path=str(file_path), error=str(e)
            )
            raise

    def _extract_text_from_docx(self, doc: DocumentType) -> str:
        """Extract text content from DOCX document."""
        paragraphs = []
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)

    async def _segment_transcript(
        self, text: str, transcript_id: UUID
    ) -> list[TranscriptSegment]:
        """Segment transcript into speaker segments."""
        segments = []
        current_segment = ""
        current_speaker = None
        segment_index = 0

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line indicates a new speaker
            speaker_match = self._identify_speaker(line)

            if speaker_match:
                # Save previous segment if it exists
                if current_segment and current_speaker:
                    segment = self._create_segment(
                        transcript_id, current_speaker, current_segment, segment_index
                    )
                    if self._is_valid_segment(segment):
                        segments.append(segment)
                        segment_index += 1

                # Start new segment
                current_speaker = speaker_match
                current_segment = line
            else:
                # Continue current segment
                if current_segment:
                    current_segment += " " + line
                else:
                    current_segment = line

        # Add final segment
        if current_segment and current_speaker:
            segment = self._create_segment(
                transcript_id, current_speaker, current_segment, segment_index
            )
            if self._is_valid_segment(segment):
                segments.append(segment)

        return segments

    def _identify_speaker(self, line: str) -> str | None:
        """Identify speaker from line text."""
        for pattern_name, pattern in self.speaker_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return pattern_name
        return None

    def _create_segment(
        self, transcript_id: UUID, speaker: str, content: str, index: int
    ) -> TranscriptSegment:
        """Create a transcript segment."""
        return TranscriptSegment(
            transcript_id=transcript_id,
            speaker_name=speaker,
            content=content.strip(),
            segment_index=index,
            metadata={"raw_content": content},
        )

    def _is_valid_segment(self, segment: TranscriptSegment) -> bool:
        """Validate segment meets quality criteria."""
        content_length = len(segment.content)
        return (
            content_length >= self.config.min_segment_length
            and content_length <= self.config.max_segment_length
            and segment.speaker_name is not None
        )

    def _create_transcript_metadata(
        self,
        file_path: Path,
        stakeholder_group: StakeholderGroup,
        source: TranscriptSource,
        full_text: str,
    ) -> TranscriptMetadata:
        """Create transcript metadata."""
        return TranscriptMetadata(
            filename=file_path.name,
            source=source,
            stakeholder_group=stakeholder_group,
            file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            processing_status="processing",
        )

    def _load_speaker_patterns(self) -> dict[str, str]:
        """Load speaker identification patterns (anonymized)."""
        return {
            "Bank_Rep_A": r"Bank_Rep_A|Speaker_A|Participant_A",
            "Trade_Body_Rep_A": r"Trade_Body_Rep_A|Speaker_B|Participant_B",
            "Payments_Rep_A": r"Payments_Rep_A|Speaker_C|Participant_C",
            "Bank_Rep_B": r"Bank_Rep_B|Speaker_D|Participant_D",
            "Bank_Rep_C": r"Bank_Rep_C|Speaker_E|Participant_E",
            "Bank_Rep_D": r"Bank_Rep_D|Speaker_F|Participant_F",
            "Bank_Rep_E": r"Bank_Rep_E|Speaker_G|Participant_G",
            "Alex Chen": r"Alex Chen",
            "Interviewer": r"(Interviewer|Moderator|Facilitator)",
            "Unknown": r"^[A-Z][a-z]+\s+[A-Z][a-z]+:",
        }

    def _extract_topics_from_query(self, query: str) -> list[str]:
        """Extract topics from query using keyword matching."""
        topic_keywords = self._load_topic_keywords()
        query_lower = query.lower()
        topics = []

        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)

        # If no specific topics found, use the query itself
        if not topics:
            topics = [query]

        return topics

    def _load_topic_keywords(self) -> dict[str, list[str]]:
        """Load topic classification keywords."""
        return {
            "commercial_sustainability": [
                "commercial",
                "sustainability",
                "ROI",
                "revenue",
                "profit",
                "business case",
                "commercial model",
                "viability",
            ],
            "governance": [
                "governance",
                "regulation",
                "compliance",
                "oversight",
                "authority",
                "mandate",
                "enforcement",
            ],
            "cost_considerations": [
                "cost",
                "expense",
                "investment",
                "budget",
                "price",
                "expensive",
                "affordable",
                "economic",
            ],
            "interoperability": [
                "interoperability",
                "integration",
                "compatibility",
                "cross-sector",
                "standardization",
                "unified",
            ],
            "technical_feasibility": [
                "technical",
                "implementation",
                "infrastructure",
                "architecture",
                "system",
                "technology",
            ],
        }
