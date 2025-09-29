"""Performance tests for transcript processing system."""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from ai_agent.infrastructure.knowledge.transcript_processor import (
    TranscriptProcessor,
    ProcessingConfig,
)
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import (
    StakeholderGroup,
    TranscriptSource,
    TranscriptSegment,
)


class TestTranscriptPerformance:
    """Performance tests for transcript processing system."""

    @pytest.fixture
    def processor(self):
        config = ProcessingConfig()
        return TranscriptProcessor(config)

    @pytest.fixture
    def store(self):
        mock_repository = Mock()
        mock_repository.execute_query = AsyncMock()
        mock_repository.create_transcript_segment = AsyncMock()
        return TranscriptStore(
            mock_repository
        )  # No vector_db_path needed with pgvector

    @pytest.fixture
    def large_transcript_content(self):
        """Generate a large transcript for performance testing."""
        content = []
        speakers = ["Bank_Rep_A", "Interviewer", "Trade_Body_Rep_A", "Payments_Rep_A"]

        for i in range(100):  # 100 segments
            speaker = speakers[i % len(speakers)]
            segment_text = f"{speaker}: This is segment {i} with substantial content that meets the minimum length requirements for testing purposes. "
            segment_text += f"It contains detailed information about topic {i % 5} and provides comprehensive analysis of the subject matter. "
            segment_text += "The content is designed to test performance with realistic data volumes and processing requirements."
            content.append(segment_text)

        return "\n".join(content)

    @pytest.mark.asyncio
    async def test_processing_speed_large_transcript(
        self, processor, large_transcript_content
    ):
        """Test processing speed with large transcript."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            with patch(
                "ai_agent.infrastructure.knowledge.transcript_processor.Document"
            ) as mock_doc:
                # Split content into paragraphs
                paragraphs = [
                    line.strip()
                    for line in large_transcript_content.split("\n")
                    if line.strip()
                ]
                mock_paragraphs = [Mock(text=para) for para in paragraphs]
                mock_doc.return_value.paragraphs = mock_paragraphs

                start_time = time.time()

                metadata, segments = await processor.process_transcript_file(
                    Path(tmp_file.name),
                    StakeholderGroup.BANK_REP,
                    TranscriptSource.BANK_A,
                )

                end_time = time.time()
                processing_time = end_time - start_time

                # Should process 100 segments in under 5 seconds
                assert processing_time < 5.0
                assert len(segments) == 100

                print(
                    f"Processed {len(segments)} segments in {processing_time:.2f} seconds"
                )

    @pytest.mark.asyncio
    async def test_search_performance(self, store):
        """Test search performance with multiple queries."""
        # Mock the repository execute_query method
        with patch.object(
            store.repository, "execute_query", new_callable=AsyncMock
        ) as mock_execute:
            # Mock search results
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id="segment1",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content 1",
                    similarity_score=0.1,
                ),
                Mock(
                    id="segment2",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content 2",
                    similarity_score=0.2,
                ),
                Mock(
                    id="segment3",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content 3",
                    similarity_score=0.3,
                ),
                Mock(
                    id="segment4",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content 4",
                    similarity_score=0.4,
                ),
                Mock(
                    id="segment5",
                    transcript_id="transcript1",
                    speaker_name="Speaker1",
                    content="Content 5",
                    similarity_score=0.5,
                ),
            ]
            mock_execute.return_value = mock_result

            queries = [
                "commercial sustainability",
                "governance frameworks",
                "cost considerations",
                "interoperability issues",
                "technical feasibility",
            ]

            start_time = time.time()

            # Execute multiple searches concurrently
            tasks = []
            for query in queries:
                task = store.search_segments(query, limit=10)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # Should complete all searches in under 2 seconds
            assert total_time < 2.0
            assert len(results) == len(queries)

            print(f"Completed {len(queries)} searches in {total_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, processor):
        """Test concurrent processing performance."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            with patch(
                "ai_agent.infrastructure.knowledge.transcript_processor.Document"
            ) as mock_doc:
                mock_paragraphs = [
                    Mock(text="Bank_Rep_A: Test content for performance testing.")
                ]
                mock_doc.return_value.paragraphs = mock_paragraphs

                # Test with different numbers of concurrent processes
                for num_processes in [1, 5, 10]:
                    start_time = time.time()

                    tasks = []
                    for _ in range(num_processes):
                        task = processor.process_transcript_file(
                            Path(tmp_file.name),
                            StakeholderGroup.BANK_REP,
                            TranscriptSource.BANK_A,
                        )
                        tasks.append(task)

                    results = await asyncio.gather(*tasks)

                    end_time = time.time()
                    processing_time = end_time - start_time

                    # Should complete all processes
                    assert len(results) == num_processes

                    print(
                        f"Processed {num_processes} transcripts concurrently in {processing_time:.2f} seconds"
                    )

    @pytest.mark.asyncio
    async def test_memory_usage_during_processing(self, processor):
        """Test memory usage during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
            with patch(
                "ai_agent.infrastructure.knowledge.transcript_processor.Document"
            ) as mock_doc:
                # Create a large transcript
                large_content = []
                for i in range(50):
                    large_content.append(
                        f"Bank_Rep_A: This is segment {i} with substantial content for memory testing. "
                        * 10
                    )

                mock_paragraphs = [Mock(text=content) for content in large_content]
                mock_doc.return_value.paragraphs = mock_paragraphs

                # Process transcript
                metadata, segments = await processor.process_transcript_file(
                    Path(tmp_file.name),
                    StakeholderGroup.BANK_REP,
                    TranscriptSource.BANK_A,
                )

                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory

                # Memory increase should be reasonable (< 100MB)
                assert memory_increase < 100

                print(
                    f"Memory usage increased by {memory_increase:.2f} MB during processing"
                )

    @pytest.mark.asyncio
    async def test_embedding_generation_performance(self, store):
        """Test embedding generation performance."""
        # Create test segments
        segments = []
        for i in range(20):
            segment = TranscriptSegment(
                transcript_id=uuid4(),
                speaker_name="Bank_Rep_A",
                content=f"This is test segment {i} with content for embedding generation performance testing.",
            )
            segments.append(segment)

        start_time = time.time()

        # Generate embeddings
        texts = [segment.content for segment in segments]
        embeddings = store.embedding_model.encode(texts)

        end_time = time.time()
        embedding_time = end_time - start_time

        # Should generate embeddings for 20 segments in under 2 seconds
        assert embedding_time < 2.0
        assert len(embeddings) == len(segments)

        print(
            f"Generated embeddings for {len(segments)} segments in {embedding_time:.2f} seconds"
        )

    @pytest.mark.asyncio
    async def test_vector_database_storage_performance(self, store):
        """Test vector database storage performance."""
        # Mock the repository methods
        with patch.object(
            store.repository, "create_transcript_segment", new_callable=AsyncMock
        ) as mock_create:
            # Create test segments
            segments = []
            for i in range(50):
                segment = TranscriptSegment(
                    transcript_id=uuid4(),
                    speaker_name="Bank_Rep_A",
                    content=f"This is test segment {i} for vector database storage performance testing.",
                )
                segments.append(segment)

            start_time = time.time()

            # Store segments (this will generate embeddings and store them)
            for segment in segments:
                # Generate embedding for the segment
                embedding = store.embedding_model.encode([segment.content])[0].tolist()
                segment.embedding = embedding
                await store.repository.create_transcript_segment(segment)

            end_time = time.time()
            storage_time = end_time - start_time

            # Should store 50 segments in under 3 seconds
            assert storage_time < 3.0
            assert mock_create.call_count == 50

            print(
                f"Stored {len(segments)} segments in vector database in {storage_time:.2f} seconds"
            )

    @pytest.mark.asyncio
    async def test_speaker_identification_performance(self, processor):
        """Test speaker identification performance."""
        # Create test lines
        test_lines = []
        speakers = [
            "Bank_Rep_A",
            "Trade_Body_Rep_A",
            "Payments_Rep_A",
            "Interviewer",
            "Unknown Speaker",
        ]

        for i in range(1000):
            speaker = speakers[i % len(speakers)]
            test_lines.append(
                f"{speaker}: This is test line {i} for speaker identification performance testing."
            )

        start_time = time.time()

        # Process all lines
        for line in test_lines:
            processor._identify_speaker(line)

        end_time = time.time()
        identification_time = end_time - start_time

        # Should process 1000 lines in under 1 second
        assert identification_time < 1.0

        print(
            f"Identified speakers for {len(test_lines)} lines in {identification_time:.2f} seconds"
        )

    @pytest.mark.asyncio
    async def test_topic_extraction_performance(self, processor):
        """Test topic extraction performance."""
        # Create test queries
        test_queries = []
        topics = [
            "commercial sustainability",
            "governance frameworks",
            "cost considerations",
            "interoperability issues",
            "technical feasibility",
        ]

        for i in range(500):
            topic = topics[i % len(topics)]
            test_queries.append(f"What are the {topic} concerns with this approach?")

        start_time = time.time()

        # Process all queries
        for query in test_queries:
            processor._extract_topics_from_query(query)

        end_time = time.time()
        extraction_time = end_time - start_time

        # Should process 500 queries in under 1 second
        assert extraction_time < 1.0

        print(
            f"Extracted topics from {len(test_queries)} queries in {extraction_time:.2f} seconds"
        )
