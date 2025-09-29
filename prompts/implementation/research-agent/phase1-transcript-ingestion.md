# Phase 1: Transcript Ingestion System

## Overview

This phase implements the foundation for processing and storing transcript data from stakeholder interviews. The system will parse DOCX files, extract structured data, and create a searchable knowledge base that can be queried by the MCP servers in subsequent phases.

## Objectives

- Parse and process 7 DOCX transcript files (~3.5MB total)
- Extract speaker segments and metadata
- Create searchable knowledge base with vector embeddings
- Implement stakeholder group categorization
- Build foundation for evidence-based agent responses

## Implementation Tasks

### 1.1 Data Models and Domain Layer

**File**: `src/ai_agent/domain/knowledge_models.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

class StakeholderGroup(str, Enum):
    """Stakeholder group categorization."""
    BANK_REP = "BankRep"
    TRADE_BODY_REP = "TradeBodyRep" 
    PAYMENTS_ECOSYSTEM_REP = "PaymentsEcosystemRep"

class TranscriptSource(str, Enum):
    """Source of transcript data."""
    SANTANDER = "Santander"
    UK_FINANCE = "UK Finance"
    MASTERCARD = "Mastercard"
    HSBC = "HSBC"
    LLOYDS = "Lloyds"
    NATWEST = "NatWest"

@dataclass
class TranscriptSegment:
    """Individual speaker segment from transcript."""
    id: UUID = field(default_factory=uuid4)
    transcript_id: UUID
    speaker_name: str
    speaker_title: Optional[str] = None
    content: str
    embedding: Optional[List[float]] = None  # Vector embedding for semantic search
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    segment_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TranscriptMetadata:
    """Metadata for a complete transcript."""
    id: UUID = field(default_factory=uuid4)
    filename: str
    source: TranscriptSource
    stakeholder_group: StakeholderGroup
    interview_date: Optional[datetime] = None
    participants: List[str] = field(default_factory=list)
    total_segments: int = 0
    file_size_bytes: int = 0
    processing_status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TopicTag:
    """Topic classification for transcript segments."""
    id: UUID = field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    category: str
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SegmentTopicMapping:
    """Mapping between segments and topics."""
    segment_id: UUID
    topic_id: UUID
    relevance_score: float
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 1.2 Transcript Processing Infrastructure

**File**: `src/ai_agent/infrastructure/knowledge/transcript_processor.py`

```python
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from docx import Document
import re
from dataclasses import dataclass

from ai_agent.domain.knowledge_models import (
    TranscriptSegment, 
    TranscriptMetadata, 
    StakeholderGroup, 
    TranscriptSource
)

logger = structlog.get_logger()

@dataclass
class ProcessingConfig:
    """Configuration for transcript processing."""
    min_segment_length: int = 50
    max_segment_length: int = 2000
    speaker_patterns: Dict[str, str] = field(default_factory=dict)
    topic_keywords: Dict[str, List[str]] = field(default_factory=dict)

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
        source: TranscriptSource
    ) -> tuple[TranscriptMetadata, List[TranscriptSegment]]:
        """Process a single transcript file."""
        logger.info("Processing transcript file", file_path=str(file_path))
        
        try:
            # Load DOCX document
            doc = Document(file_path)
            
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
                segments=len(segments)
            )
            
            return metadata, segments
            
        except Exception as e:
            logger.error("Failed to process transcript", file_path=str(file_path), error=str(e))
            raise
    
    def _extract_text_from_docx(self, doc: Document) -> str:
        """Extract text content from DOCX document."""
        paragraphs = []
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)
    
    async def _segment_transcript(
        self, 
        text: str, 
        transcript_id: UUID
    ) -> List[TranscriptSegment]:
        """Segment transcript into speaker segments."""
        segments = []
        current_segment = ""
        current_speaker = None
        segment_index = 0
        
        lines = text.split('\n')
        
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
    
    def _identify_speaker(self, line: str) -> Optional[str]:
        """Identify speaker from line text."""
        for pattern_name, pattern in self.speaker_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return pattern_name
        return None
    
    def _create_segment(
        self, 
        transcript_id: UUID, 
        speaker: str, 
        content: str, 
        index: int
    ) -> TranscriptSegment:
        """Create a transcript segment."""
        return TranscriptSegment(
            transcript_id=transcript_id,
            speaker_name=speaker,
            content=content.strip(),
            segment_index=index,
            metadata={"raw_content": content}
        )
    
    def _is_valid_segment(self, segment: TranscriptSegment) -> bool:
        """Validate segment meets quality criteria."""
        content_length = len(segment.content)
        return (
            content_length >= self.config.min_segment_length and
            content_length <= self.config.max_segment_length and
            segment.speaker_name is not None
        )
    
    def _load_speaker_patterns(self) -> Dict[str, str]:
        """Load speaker identification patterns."""
        return {
            "Gary Aydon": r"Gary\s+Aydon",
            "Phillip Mind": r"Phillip\s+Mind", 
            "Louise Beaumont": r"Louise\s+Beaumont",
            "Hetal Popat": r"Hetal\s+Popat",
            "Glen Wetherill": r"Glen\s+Wetherill",
            "Archi Shrimpton": r"Archi\s+Shrimpton",
            "Stephen Wright": r"Stephen\s+Wright",
            "Interviewer": r"(Interviewer|Moderator|Facilitator)",
            "Unknown": r"^[A-Z][a-z]+\s+[A-Z][a-z]+:"
        }
    
    def _load_topic_keywords(self) -> Dict[str, List[str]]:
        """Load topic classification keywords."""
        return {
            "commercial_sustainability": [
                "commercial", "sustainability", "ROI", "revenue", "profit",
                "business case", "commercial model", "viability"
            ],
            "governance": [
                "governance", "regulation", "compliance", "oversight",
                "authority", "mandate", "enforcement"
            ],
            "cost_considerations": [
                "cost", "expense", "investment", "budget", "price",
                "expensive", "affordable", "economic"
            ],
            "interoperability": [
                "interoperability", "integration", "compatibility",
                "cross-sector", "standardization", "unified"
            ],
            "technical_feasibility": [
                "technical", "implementation", "infrastructure",
                "architecture", "system", "technology"
            ]
        }
```

### 1.3 Knowledge Base Storage

**File**: `src/ai_agent/infrastructure/knowledge/transcript_store.py`

```python
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text
from sqlalchemy.dialects.postgresql import ARRAY
import numpy as np
from sentence_transformers import SentenceTransformer

from ai_agent.domain.knowledge_models import (
    TranscriptSegment, 
    TranscriptMetadata, 
    StakeholderGroup,
    TopicTag
)
from ai_agent.infrastructure.database.base import Repository

logger = structlog.get_logger()

class TranscriptStore:
    """Storage and retrieval system for transcript data using pgvector."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
    
    async def store_transcript_data(
        self, 
        metadata: TranscriptMetadata, 
        segments: List[TranscriptSegment]
    ) -> bool:
        """Store transcript metadata and segments with embeddings."""
        try:
            # Store metadata in database
            await self.repository.create_transcript_metadata(metadata)
            
            # Generate embeddings for segments
            texts = [segment.content for segment in segments]
            embeddings = self.embedding_model.encode(texts)
            
            # Store segments with embeddings in database
            for i, segment in enumerate(segments):
                segment.embedding = embeddings[i].tolist()
                await self.repository.create_transcript_segment(segment)
            
            logger.info(
                "Transcript data stored successfully",
                transcript_id=str(metadata.id),
                segments=len(segments)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to store transcript data", error=str(e))
            return False
    
    async def search_segments(
        self, 
        query: str, 
        stakeholder_group: Optional[StakeholderGroup] = None,
        limit: int = 10
    ) -> List[Tuple[TranscriptSegment, float]]:
        """Search transcript segments by semantic similarity using pgvector."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Build the vector similarity query
            base_query = """
                SELECT 
                    ts.*,
                    1 - (ts.embedding <=> %s::vector) as similarity_score
                FROM transcript_segments ts
                JOIN transcript_metadata tm ON ts.transcript_id = tm.id
            """
            
            params = [query_embedding]
            where_conditions = []
            
            if stakeholder_group:
                where_conditions.append("tm.stakeholder_group = %s")
                params.append(stakeholder_group.value)
            
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            
            base_query += f" ORDER BY ts.embedding <=> %s::vector LIMIT %s"
            params.extend([query_embedding, limit])
            
            # Execute the query
            result = await self.repository.execute_query(text(base_query), params)
            rows = result.fetchall()
            
            # Convert results to TranscriptSegment objects with similarity scores
            segments_with_scores = []
            for row in rows:
                segment = self._row_to_segment(row)
                similarity_score = float(row.similarity_score)
                segments_with_scores.append((segment, similarity_score))
            
            return segments_with_scores
            
        except Exception as e:
            logger.error("Failed to search segments", error=str(e))
            return []
    
    async def get_segments_by_topic(
        self, 
        topic: str, 
        stakeholder_group: Optional[StakeholderGroup] = None,
        limit: int = 20
    ) -> List[TranscriptSegment]:
        """Get segments related to a specific topic."""
        try:
            # Build query conditions
            conditions = []
            if stakeholder_group:
                conditions.append("tm.stakeholder_group = %s")
            
            # Search for topic keywords in content
            topic_keywords = self._get_topic_keywords(topic)
            keyword_conditions = []
            params = []
            
            if stakeholder_group:
                params.append(stakeholder_group.value)
            
            for keyword in topic_keywords:
                keyword_conditions.append("ts.content ILIKE %s")
                params.append(f"%{keyword}%")
            
            if keyword_conditions:
                conditions.append(f"({' OR '.join(keyword_conditions)})")
            
            # Build the query
            query = """
                SELECT ts.*
                FROM transcript_segments ts
                JOIN transcript_metadata tm ON ts.transcript_id = tm.id
            """
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY ts.created_at DESC LIMIT %s"
            params.append(limit)
            
            # Execute the query
            result = await self.repository.execute_query(text(query), params)
            rows = result.fetchall()
            
            return [self._row_to_segment(row) for row in rows]
            
        except Exception as e:
            logger.error("Failed to get segments by topic", error=str(e))
            return []
    
    def _row_to_segment(self, row) -> TranscriptSegment:
        """Convert database row to TranscriptSegment object."""
        return TranscriptSegment(
            id=row.id,
            transcript_id=row.transcript_id,
            speaker_name=row.speaker_name,
            speaker_title=row.speaker_title,
            content=row.content,
            start_time=row.start_time,
            end_time=row.end_time,
            segment_index=row.segment_index,
            metadata=row.metadata or {},
            created_at=row.created_at
        )
    
    def _get_topic_keywords(self, topic: str) -> List[str]:
        """Get keywords for a specific topic."""
        topic_keywords = {
            "commercial_sustainability": [
                "commercial", "sustainability", "ROI", "revenue", "profit",
                "business case", "commercial model", "viability"
            ],
            "governance": [
                "governance", "regulation", "compliance", "oversight",
                "authority", "mandate", "enforcement"
            ],
            "cost_considerations": [
                "cost", "expense", "investment", "budget", "price",
                "expensive", "affordable", "economic"
            ],
            "interoperability": [
                "interoperability", "integration", "compatibility",
                "cross-sector", "standardization", "unified"
            ],
            "technical_feasibility": [
                "technical", "implementation", "infrastructure",
                "architecture", "system", "technology"
            ]
        }
        
        return topic_keywords.get(topic.lower(), [topic])
```

### 1.4 Database Schema Extensions

**File**: `src/ai_agent/infrastructure/database/migrations/001_add_transcript_tables.sql`

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Transcript metadata table
CREATE TABLE IF NOT EXISTS transcript_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    stakeholder_group VARCHAR(50) NOT NULL,
    interview_date TIMESTAMP,
    participants TEXT[],
    total_segments INTEGER DEFAULT 0,
    file_size_bytes INTEGER DEFAULT 0,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transcript segments table with vector embedding
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcript_metadata(id) ON DELETE CASCADE,
    speaker_name VARCHAR(255) NOT NULL,
    speaker_title VARCHAR(255),
    content TEXT NOT NULL,
    embedding vector(384), -- all-MiniLM-L6-v2 dimension
    start_time FLOAT,
    end_time FLOAT,
    segment_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Topic tags table
CREATE TABLE IF NOT EXISTS topic_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Segment topic mappings
CREATE TABLE IF NOT EXISTS segment_topic_mappings (
    segment_id UUID NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topic_tags(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (segment_id, topic_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content ON transcript_segments USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker_name);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_stakeholder ON transcript_segments(metadata->>'stakeholder_group');
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_source ON transcript_metadata(source);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_stakeholder_group ON transcript_metadata(stakeholder_group);

-- Vector similarity index for fast semantic search
CREATE INDEX IF NOT EXISTS idx_transcript_segments_embedding ON transcript_segments 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 1.5 Configuration

**File**: `src/ai_agent/config/transcript_processing.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

@dataclass
class TranscriptProcessingConfig:
    """Configuration for transcript processing."""
    
    # File paths
    transcript_directory: Path = Path("docs/transcripts")
    
    # Processing parameters
    min_segment_length: int = 50
    max_segment_length: int = 2000
    
    # Embedding model
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 dimension
    
    # Search parameters
    default_search_limit: int = 10
    max_search_limit: int = 100
    
    # Vector similarity threshold
    similarity_threshold: float = 0.7
    
    # Stakeholder group mappings
    stakeholder_group_mappings: Dict[str, str] = {
        "250211 Gary Aydon, Santander UK_Gov only.docx": "BankRep",
        "250211 Phillip Mind, UK Finance_Gov + Perseus (1).docx": "TradeBodyRep",
        "250212 Louise Beaumont, Mastercard_Gov only (1).docx": "PaymentsEcosystemRep",
        "250305 Hetal Popat, HSBC_ Mixed + Gov.docx": "BankRep",
        "250310 Glen Wetherill, Santander_Ubiquitech + gov (1).docx": "BankRep",
        "250314 Archi Shrimpton, Lloyds_ Gov only (1).docx": "BankRep",
        "250314 Stephen Wright, Natwest_ Mixed + gov (1).docx": "BankRep"
    }
    
    # Source mappings
    source_mappings: Dict[str, str] = {
        "250211 Gary Aydon, Santander UK_Gov only.docx": "Santander",
        "250211 Phillip Mind, UK Finance_Gov + Perseus (1).docx": "UK Finance",
        "250212 Louise Beaumont, Mastercard_Gov only (1).docx": "Mastercard",
        "250305 Hetal Popat, HSBC_ Mixed + Gov.docx": "HSBC",
        "250310 Glen Wetherill, Santander_Ubiquitech + gov (1).docx": "Santander",
        "250314 Archi Shrimpton, Lloyds_ Gov only (1).docx": "Lloyds",
        "250314 Stephen Wright, Natwest_ Mixed + gov (1).docx": "NatWest"
    }
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_transcript_processing.py`
- Test transcript parsing accuracy
- Test speaker identification
- Test segment validation
- Test metadata extraction

### Integration Tests
- **File**: `tests/integration/test_transcript_store.py`
- Test database operations
- Test vector search functionality
- Test end-to-end processing pipeline

### Performance Tests
- **File**: `tests/performance/test_transcript_processing.py`
- Test processing speed with large files
- Test search performance with large datasets
- Test memory usage optimization

## Success Criteria

1. **Data Quality**: All 7 transcript files processed successfully with >95% accuracy
2. **Search Performance**: Sub-second response times for semantic search queries
3. **Storage Efficiency**: Vector embeddings stored efficiently with <1GB total size
4. **Reliability**: 99.9% uptime for search operations
5. **Scalability**: System handles 10x current data volume without performance degradation

## Dependencies

```toml
# Add to pyproject.toml
python-docx = "^0.8.11"
sentence-transformers = "^2.2.2"
numpy = "^1.24.0"
psycopg2-binary = "^2.9.9"  # PostgreSQL adapter
```

**PostgreSQL Extension Required:**
```sql
-- Install pgvector extension in PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;
```

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 2: MCP server that queries this knowledge base
- Phase 3: Agent personas that use the MCP server for evidence-based responses
- Phase 4: Evaluation framework that relies on agent responses

The transcript ingestion system must be completed and validated before proceeding to Phase 2.
