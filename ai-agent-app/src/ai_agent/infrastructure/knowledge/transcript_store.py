"""Storage and retrieval system for transcript data using pgvector."""

from typing import Any
import structlog
from sqlalchemy import text
from sentence_transformers import SentenceTransformer

from ai_agent.domain.knowledge_models import (
    TranscriptSegment,
    TranscriptMetadata,
    StakeholderGroup,
)

logger = structlog.get_logger()


class TranscriptStore:
    """Storage and retrieval system for transcript data using pgvector."""

    def __init__(self, repository: Any | None = None):
        self.repository = repository
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension

    async def store_transcript_data(
        self, metadata: TranscriptMetadata, segments: list[TranscriptSegment]
    ) -> bool:
        """Store transcript metadata and segments with embeddings."""
        try:
            # Store metadata in database if repository is available
            if self.repository:
                await self.repository.create_transcript_metadata(metadata)

            # Generate embeddings for segments
            texts = [segment.content for segment in segments]
            embeddings = self.embedding_model.encode(texts)

            # Store segments with embeddings in database
            for i, segment in enumerate(segments):
                segment.embedding = embeddings[i].tolist()
                if self.repository:
                    await self.repository.create_transcript_segment(segment)

            logger.info(
                "Transcript data stored successfully",
                transcript_id=str(metadata.id),
                segments=len(segments),
            )

            return True

        except Exception as e:
            logger.error("Failed to store transcript data", error=str(e))
            return False

    async def search_segments(
        self,
        query: str,
        stakeholder_group: StakeholderGroup | None = None,
        limit: int = 10,
    ) -> list[tuple[TranscriptSegment, float]]:
        """Search transcript segments by semantic similarity using pgvector."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()

            if not self.repository:
                # Mock implementation for testing without database
                logger.warning("No repository available, returning empty results")
                return []

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

            base_query += " ORDER BY ts.embedding <=> %s::vector LIMIT %s"
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
        stakeholder_group: StakeholderGroup | None = None,
        limit: int = 20,
    ) -> list[TranscriptSegment]:
        """Get segments related to a specific topic."""
        try:
            if not self.repository:
                # Mock implementation for testing without database
                logger.warning("No repository available, returning empty results")
                return []

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

            query += " ORDER BY ts.created_at DESC LIMIT %s"
            params.append(limit)

            # Execute the query
            result = await self.repository.execute_query(text(query), params)
            rows = result.fetchall()

            return [self._row_to_segment(row) for row in rows]

        except Exception as e:
            logger.error("Failed to get segments by topic", error=str(e))
            return []

    def _row_to_segment(self, row: Any) -> TranscriptSegment:
        """Convert database row to TranscriptSegment object."""
        return TranscriptSegment(
            id=row.id,
            transcript_id=row.transcript_id,
            speaker_name=row.speaker_name,
            speaker_title=row.speaker_title,
            content=row.content,
            embedding=(
                row.embedding.tolist()
                if hasattr(row.embedding, "tolist")
                else row.embedding
            ),
            start_time=row.start_time,
            end_time=row.end_time,
            segment_index=row.segment_index,
            metadata=row.metadata or {},
            created_at=row.created_at,
        )

    def _get_topic_keywords(self, topic: str) -> list[str]:
        """Get keywords for a specific topic."""
        topic_keywords = {
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

        return topic_keywords.get(topic.lower(), [topic])
