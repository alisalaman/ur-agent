"""Advanced search engine for stakeholder views."""

from typing import Any
import structlog
from dataclasses import dataclass
import re

from ....domain.knowledge_models import StakeholderGroup
from ...knowledge.transcript_store import TranscriptStore
from ...knowledge.stakeholder_utils import StakeholderGroupInference
from ....config.stakeholder_views import config

logger = structlog.get_logger()


@dataclass
class SearchResult:
    """Enhanced search result with additional metadata."""

    segment_id: str
    speaker_name: str
    content: str
    relevance_score: float
    stakeholder_group: str
    topic_matches: list[str]
    sentiment_score: float
    confidence_level: str
    metadata: dict[str, Any]


class StakeholderSearchEngine:
    """Advanced search engine for stakeholder views."""

    def __init__(self, transcript_store: TranscriptStore):
        self.transcript_store = transcript_store
        self.topic_keywords = self._load_topic_keywords()
        self.sentiment_keywords = self._load_sentiment_keywords()

    async def search_with_analysis(
        self,
        topic: str,
        stakeholder_group: StakeholderGroup | None = None,
        limit: int = 10,
        include_analysis: bool = True,
    ) -> list[SearchResult]:
        """Search with enhanced analysis and scoring."""
        try:
            # Get basic search results
            segments_with_scores = await self.transcript_store.search_segments(
                query=topic, stakeholder_group=stakeholder_group, limit=limit * 2
            )

            # Enhance results with analysis
            enhanced_results = []
            for segment, base_score in segments_with_scores:
                enhanced_result = await self._enhance_search_result(
                    segment, base_score, topic, include_analysis
                )
                enhanced_results.append(enhanced_result)

            # Sort by enhanced relevance score
            enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)

            return enhanced_results[:limit]

        except Exception as e:
            logger.error("Error in enhanced search", error=str(e))
            return []

    async def _enhance_search_result(
        self, segment: Any, base_score: float, topic: str, include_analysis: bool
    ) -> SearchResult:
        """Enhance search result with additional analysis."""
        # Find topic keyword matches
        topic_matches = self._find_topic_matches(segment.content, topic)

        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment(segment.content)

        # Determine confidence level
        confidence_level = self._determine_confidence(
            base_score, len(topic_matches), sentiment_score
        )

        # Adjust relevance score based on analysis
        enhanced_score = self._adjust_relevance_score(
            base_score, topic_matches, sentiment_score
        )

        return SearchResult(
            segment_id=str(segment.id),
            speaker_name=segment.speaker_name,
            content=segment.content,
            relevance_score=enhanced_score,
            stakeholder_group=StakeholderGroupInference.infer_from_segment(segment),
            topic_matches=topic_matches,
            sentiment_score=sentiment_score,
            confidence_level=confidence_level,
            metadata={
                "transcript_id": str(segment.transcript_id),
                "segment_index": segment.segment_index,
                "base_score": base_score,
                "analysis_included": include_analysis,
            },
        )

    def _find_topic_matches(self, content: str, topic: str) -> list[str]:
        """Find specific topic keyword matches in content."""
        content_lower = content.lower()
        topic_lower = topic.lower()

        matches = []

        # Direct topic matches
        if topic_lower in content_lower:
            matches.append(topic)

        # Related keyword matches
        topic_keywords = self.topic_keywords.get(topic_lower, [])
        for keyword in topic_keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)

        # Extract quoted statements
        quoted_matches = re.findall(
            r'"([^"]*' + re.escape(topic_lower) + r'[^"]*)"', content_lower
        )
        matches.extend(quoted_matches)

        return list(set(matches))  # Remove duplicates

    def _calculate_sentiment(self, content: str) -> float:
        """Calculate sentiment score for content (-1.0 to 1.0)."""
        content_lower = content.lower()

        positive_words = self.sentiment_keywords["positive"]
        negative_words = self.sentiment_keywords["negative"]

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        total_words = len(content.split())
        if total_words == 0:
            return 0.0

        # Normalize by content length
        positive_score = positive_count / total_words
        negative_score = negative_count / total_words

        # Return sentiment score (-1.0 to 1.0)
        return positive_score - negative_score

    def _determine_confidence(
        self, base_score: float, topic_matches: int, sentiment_score: float
    ) -> str:
        """Determine confidence level for search result."""
        if base_score >= 0.8 and topic_matches >= 3:
            return "high"
        elif base_score >= 0.6 and topic_matches >= 2:
            return "medium"
        elif base_score >= 0.4 and topic_matches >= 1:
            return "low"
        else:
            return "very_low"

    def _adjust_relevance_score(
        self, base_score: float, topic_matches: list[str], sentiment_score: float
    ) -> float:
        """Adjust relevance score based on additional analysis."""
        # Boost score for topic keyword matches
        keyword_boost = min(
            len(topic_matches) * config.keyword_boost_factor, config.max_keyword_boost
        )

        # Boost score for strong sentiment (either positive or negative)
        sentiment_boost = abs(sentiment_score) * config.sentiment_boost_factor

        # Combine scores
        enhanced_score = base_score + keyword_boost + sentiment_boost

        # Cap at 1.0
        return min(enhanced_score, 1.0)

    def _load_topic_keywords(self) -> dict[str, list[str]]:
        """Load topic-specific keywords for matching."""
        return {
            "commercial sustainability": [
                "commercial",
                "sustainability",
                "ROI",
                "revenue",
                "profit",
                "business case",
                "commercial model",
                "viability",
                "economic",
            ],
            "governance": [
                "governance",
                "regulation",
                "compliance",
                "oversight",
                "authority",
                "mandate",
                "enforcement",
                "rules",
                "policy",
            ],
            "cost": [
                "cost",
                "expense",
                "investment",
                "budget",
                "price",
                "expensive",
                "affordable",
                "economic",
                "financial",
            ],
            "interoperability": [
                "interoperability",
                "integration",
                "compatibility",
                "cross-sector",
                "standardization",
                "unified",
                "connected",
            ],
            "technical feasibility": [
                "technical",
                "implementation",
                "infrastructure",
                "architecture",
                "system",
                "technology",
                "feasible",
            ],
        }

    def _load_sentiment_keywords(self) -> dict[str, list[str]]:
        """Load sentiment analysis keywords."""
        return {
            "positive": [
                "good",
                "excellent",
                "beneficial",
                "positive",
                "support",
                "agree",
                "effective",
                "successful",
                "valuable",
                "important",
            ],
            "negative": [
                "bad",
                "poor",
                "problematic",
                "negative",
                "concern",
                "disagree",
                "ineffective",
                "failed",
                "risky",
                "expensive",
            ],
        }
