"""Shared utilities for stakeholder group handling."""

import re
from typing import Any
from dataclasses import dataclass

from ...domain.knowledge_models import StakeholderGroup
from ...config.stakeholder_views import config


@dataclass
class SegmentProtocol:
    """Protocol for transcript segment objects."""

    id: str
    speaker_name: str
    speaker_title: str
    content: str
    transcript_id: str
    segment_index: int
    created_at: Any
    metadata: dict[str, Any]


class StakeholderGroupInference:
    """Centralized stakeholder group inference logic."""

    @staticmethod
    def infer_from_segment(segment: Any) -> str:
        """
        Infer stakeholder group from segment metadata.

        Args:
            segment: Transcript segment object

        Returns:
            Inferred stakeholder group name
        """
        if hasattr(segment, "metadata") and segment.metadata:
            result = segment.metadata.get("stakeholder_group", "Unknown")
            return str(result)
        return "Unknown"

    @staticmethod
    def validate_group(group: str) -> StakeholderGroup | None:
        """
        Validate and convert stakeholder group string.

        Args:
            group: Stakeholder group string

        Returns:
            Validated StakeholderGroup enum or None if invalid
        """
        if not group:
            return None

        try:
            return StakeholderGroup(group)
        except ValueError:
            return None

    @staticmethod
    def get_available_groups() -> list[str]:
        """Get list of available stakeholder groups."""
        return [group.value for group in StakeholderGroup]


class InputValidator:
    """Input validation and sanitization utilities."""

    @staticmethod
    def validate_topic(topic: str) -> str:
        """
        Validate and sanitize search topic.

        Args:
            topic: Raw topic string

        Returns:
            Sanitized topic string

        Raises:
            ValueError: If topic is invalid
        """
        if not topic:
            raise ValueError("Topic cannot be empty")

        # Strip whitespace
        sanitized = topic.strip()

        # Check length constraints
        if len(sanitized) < config.min_topic_length:
            raise ValueError(
                f"Topic too short (minimum {config.min_topic_length} characters)"
            )

        if len(sanitized) > config.max_topic_length:
            raise ValueError(
                f"Topic too long (maximum {config.max_topic_length} characters)"
            )

        # Sanitize to prevent injection attacks
        # Allow alphanumeric, spaces, hyphens, periods, commas, and basic punctuation
        sanitized = re.sub(r"[^\w\s\-.,!?()]", "", sanitized)

        if not sanitized:
            raise ValueError("Topic contains no valid characters")

        return sanitized

    @staticmethod
    def validate_limit(limit: int) -> int:
        """
        Validate result limit.

        Args:
            limit: Requested limit

        Returns:
            Validated limit

        Raises:
            ValueError: If limit is invalid
        """
        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if limit > config.max_results:
            raise ValueError(f"Limit cannot exceed {config.max_results}")

        return limit

    @staticmethod
    def validate_relevance_score(score: float) -> float:
        """
        Validate relevance score.

        Args:
            score: Relevance score

        Returns:
            Validated score

        Raises:
            ValueError: If score is invalid
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError("Relevance score must be between 0.0 and 1.0")

        return score


class ContentSanitizer:
    """Utilities for sanitizing and formatting content to markdown."""

    @staticmethod
    def sanitize_to_markdown(content: str) -> str:
        """
        Sanitize content to ensure it's in markdown format.

        Args:
            content: Raw content that may contain HTML or other formatting

        Returns:
            Content sanitized to markdown format
        """
        if not content:
            return ""

        # Remove HTML tags but preserve their text content
        # This handles common HTML tags that might appear in transcript content
        content = re.sub(r"<[^>]+>", "", content)

        # Clean up extra whitespace
        content = re.sub(r"\s+", " ", content)

        # Remove any remaining HTML entities
        content = re.sub(r"&[a-zA-Z0-9#]+;", " ", content)

        # Ensure proper line breaks for markdown
        content = content.strip()

        return content

    @staticmethod
    def format_speaker_info(speaker_name: str, speaker_title: str) -> str:
        """
        Format speaker information in markdown.

        Args:
            speaker_name: Speaker's name
            speaker_title: Speaker's title

        Returns:
            Formatted speaker info in markdown
        """
        if not speaker_name:
            return ""

        if speaker_title:
            return f"**{speaker_name}** ({speaker_title})"
        else:
            return f"**{speaker_name}**"


class SearchResultFormatter:
    """Utilities for formatting search results."""

    @staticmethod
    def format_segment_result(segment: Any, score: float) -> dict[str, Any]:
        """
        Format a transcript segment into a search result.

        Args:
            segment: Transcript segment
            score: Relevance score

        Returns:
            Formatted result dictionary with markdown content
        """
        # Sanitize content to markdown format
        sanitized_content = ContentSanitizer.sanitize_to_markdown(segment.content)

        # Format speaker information
        speaker_info = ContentSanitizer.format_speaker_info(
            segment.speaker_name, segment.speaker_title
        )

        return {
            "segment_id": str(segment.id),
            "speaker_name": segment.speaker_name,
            "speaker_title": segment.speaker_title,
            "content": sanitized_content,
            "speaker_info": speaker_info,
            "relevance_score": round(score, 3),
            "stakeholder_group": StakeholderGroupInference.infer_from_segment(segment),
            "metadata": {
                "transcript_id": str(segment.transcript_id),
                "segment_index": segment.segment_index,
                "created_at": segment.created_at.isoformat(),
            },
        }

    @staticmethod
    def sort_by_relevance(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Sort results by relevance score (descending).

        Args:
            results: List of result dictionaries

        Returns:
            Sorted results
        """
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
