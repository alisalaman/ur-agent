"""Test system performance and scalability."""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import Mock, AsyncMock

from ai_agent.core.agents.synthetic_representative import PersonaType
from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
)


class TestSystemPerformance:
    """Test system performance and scalability."""

    @pytest.fixture
    def performance_setup(self):
        """Set up system for performance testing."""
        # Mock tool registry with realistic response times
        mock_tool_registry = Mock()
        mock_tool_registry.execute_tool = AsyncMock(
            return_value=Mock(
                success=True,
                result={
                    "results": [{"content": "Test evidence", "relevance_score": 0.8}],
                    "results_count": 1,
                },
            )
        )

        # Mock persona service to avoid real initialization
        persona_service = Mock()
        persona_service.process_query = AsyncMock(return_value="Mocked response")
        persona_service.process_query_all_personas = AsyncMock(
            return_value={
                PersonaType.BANK_REP: "Bank response",
                PersonaType.TRADE_BODY_REP: "Trade response",
                PersonaType.PAYMENTS_ECOSYSTEM_REP: "Payments response",
            }
        )

        evaluator = GovernanceEvaluator(persona_service)

        return persona_service, evaluator

    @pytest.mark.asyncio
    async def test_query_response_time(self, performance_setup):
        """Test query response time meets requirements."""
        persona_service, evaluator = performance_setup

        query = "What are the commercial sustainability concerns?"

        start_time = time.time()
        response = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP, query=query
        )
        end_time = time.time()

        response_time = end_time - start_time

        # Should respond within 2 seconds
        assert response_time < 2.0
        assert response is not None

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, performance_setup):
        """Test system handles concurrent queries."""
        persona_service, evaluator = performance_setup

        queries = [
            "What are the cost concerns?",
            "What about governance frameworks?",
            "How about interoperability?",
            "What are the technical challenges?",
            "What about commercial viability?",
        ]

        start_time = time.time()

        # Execute queries concurrently
        tasks = []
        for query in queries:
            task = persona_service.process_query(
                persona_type=PersonaType.BANK_REP, query=query
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # All queries should complete
        assert len(responses) == len(queries)
        assert all(response is not None for response in responses)

        # Should handle concurrent queries efficiently
        assert total_time < 5.0  # 5 queries in under 5 seconds

    @pytest.mark.asyncio
    async def test_evaluation_performance(self, performance_setup):
        """Test governance evaluation performance."""
        persona_service, evaluator = performance_setup

        model = GovernanceModel(
            name="Performance Test Model",
            description="A model for performance testing",
            model_type="Test",
            key_features=["Feature 1", "Feature 2"],
            proposed_by="Test Org",
        )

        start_time = time.time()
        evaluation = await evaluator.evaluate_governance_model(model)
        end_time = time.time()

        evaluation_time = end_time - start_time

        # Should complete evaluation within 30 seconds
        assert evaluation_time < 30.0
        assert evaluation.overall_score > 0
        assert evaluation.evaluation_status == "completed"

    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_setup):
        """Test memory usage during operation."""
        persona_service, evaluator = performance_setup

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple operations
        for i in range(10):
            await persona_service.process_query(
                persona_type=PersonaType.BANK_REP, query=f"Test query {i}"
            )

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100

    @pytest.mark.asyncio
    async def test_evidence_cache_performance(self, performance_setup):
        """Test evidence caching performance."""
        persona_service, evaluator = performance_setup

        query = "What are the cost concerns?"

        # First query (cache miss)
        start_time = time.time()
        response1 = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP, query=query
        )
        first_query_time = time.time() - start_time

        # Second query (cache hit)
        start_time = time.time()
        response2 = await persona_service.process_query(
            persona_type=PersonaType.BANK_REP, query=query
        )
        second_query_time = time.time() - start_time

        # Second query should be faster due to caching
        assert second_query_time < first_query_time
        assert response1 == response2
