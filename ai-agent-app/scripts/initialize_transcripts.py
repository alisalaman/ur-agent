#!/usr/bin/env python3
"""Initialize transcript data for the synthetic agent system."""

import asyncio
import sys
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_agent.infrastructure.knowledge.transcript_processor import (
    TranscriptProcessor,
    ProcessingConfig,
)
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import StakeholderGroup, TranscriptSource
from ai_agent.config.transcript_processing import TranscriptProcessingConfig

logger = structlog.get_logger()


async def initialize_transcripts():
    """Initialize transcript data."""
    try:
        config = TranscriptProcessingConfig()

        # Create transcript processor
        processor_config = ProcessingConfig()
        processor = TranscriptProcessor(processor_config)

        # Create transcript store
        store = TranscriptStore(None, str(config.vector_db_path))

        # Process all transcript files
        transcript_dir = config.transcript_directory
        processed_count = 0

        if not transcript_dir.exists():
            logger.error(
                "Transcript directory does not exist", path=str(transcript_dir)
            )
            return

        for file_path in transcript_dir.glob("*.docx"):
            try:
                # Determine stakeholder group and source
                stakeholder_group_str = config.stakeholder_group_mappings.get(
                    file_path.name, "BankRep"
                )
                source_str = config.source_mappings.get(file_path.name, "Bank_A")

                # Convert to enums
                try:
                    stakeholder_group = StakeholderGroup(stakeholder_group_str)
                    source = TranscriptSource(source_str)
                except ValueError as e:
                    logger.warning(
                        "Invalid enum value",
                        file_path=file_path.name,
                        stakeholder_group=stakeholder_group_str,
                        source=source_str,
                        error=str(e),
                    )
                    continue

                logger.info("Processing transcript", file_path=file_path.name)

                # Process transcript
                metadata, segments = await processor.process_transcript_file(
                    file_path, stakeholder_group, source
                )

                # Store in database
                success = await store.store_transcript_data(metadata, segments)

                if success:
                    processed_count += 1
                    logger.info(
                        "Transcript processed successfully",
                        file_path=file_path.name,
                        segments=len(segments),
                    )
                else:
                    logger.error(
                        "Failed to store transcript data", file_path=file_path.name
                    )

            except Exception as e:
                logger.error(
                    "Failed to process transcript",
                    file_path=file_path.name,
                    error=str(e),
                )

        logger.info(
            "Transcript initialization completed", processed_count=processed_count
        )

    except Exception as e:
        logger.error("Transcript initialization failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(initialize_transcripts())
