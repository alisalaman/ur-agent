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
from ai_agent.config.synthetic_agents import get_config

logger = structlog.get_logger()


async def initialize_transcripts():
    """Initialize transcript data."""
    try:
        config = get_config()

        # Create transcript processor
        processor_config = ProcessingConfig()
        processor = TranscriptProcessor(processor_config)

        # Create transcript store
        store = TranscriptStore()

        # Process all transcript files
        transcript_dir = config.transcript_processing.transcript_directory
        processed_count = 0

        for file_path in transcript_dir.glob("*.docx"):
            try:
                # Determine stakeholder group and source
                stakeholder_group = (
                    config.transcript_processing.stakeholder_group_mappings.get(
                        file_path.name, StakeholderGroup.BANK_REP
                    )
                )
                source = config.transcript_processing.source_mappings.get(
                    file_path.name, TranscriptSource.SANTANDER
                )

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
