"""
Performance tests for governance evaluation framework.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock

from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
)
from ai_agent.core.evaluation.report_generator import (
    GovernanceReportGenerator,
    ReportConfig,
)
from ai_agent.core.agents.synthetic_representative import PersonaType


class TestGovernanceEvaluationPerformance:
    """Performance tests for governance evaluation system."""

    @pytest.fixture
    def mock_persona_service(self):
        """Create mock persona service for performance testing."""
        service = Mock()

        async def mock_process_query_all_personas(query, context=None):
            # Simulate realistic processing time
            await asyncio.sleep(0.1)  # 100ms per persona query

            responses = {}
            for persona_type in PersonaType:
                responses[
                    persona_type
                ] = f"""
                Score: 3
                Rationale: Performance test response for {persona_type}.
                This is a simulated response for performance testing purposes.
                Evidence: Simulated evidence from performance test.
                """

            return responses

        service.process_query_all_personas = mock_process_query_all_personas
        return service

    @pytest.fixture
    def sample_models(self):
        """Create sample models for performance testing."""
        models = []

        for i in range(10):
            model = GovernanceModel(
                name=f"Performance Test Model {i}",
                description=f"Model {i} for performance testing",
                model_type="Performance Test",
                key_features=[f"feature_{j}" for j in range(5)],
                proposed_by=f"Test User {i}",
                metadata={"test_id": i},
            )
            models.append(model)

        return models

    @pytest.mark.asyncio
    async def test_single_evaluation_performance(self, mock_persona_service):
        """Test performance of single evaluation."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        model = GovernanceModel(
            name="Single Evaluation Test",
            description="Model for single evaluation performance test",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Test User",
        )

        # Measure evaluation time
        start_time = time.time()
        evaluation = await evaluator.evaluate_governance_model(model)
        end_time = time.time()

        evaluation_time = end_time - start_time

        # Should complete within reasonable time (adjust based on mock delay)
        assert evaluation_time < 2.0  # Should be much faster than 2 seconds
        assert evaluation.evaluation_status == "completed"

        print(f"Single evaluation time: {evaluation_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_concurrent_evaluations_performance(
        self, mock_persona_service, sample_models
    ):
        """Test performance of concurrent evaluations."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        # Test with different numbers of concurrent evaluations
        test_cases = [1, 3, 5, 10]

        for num_evaluations in test_cases:
            models_subset = sample_models[:num_evaluations]

            start_time = time.time()

            # Run evaluations concurrently
            tasks = []
            for model in models_subset:
                task = evaluator.evaluate_governance_model(model)
                tasks.append(task)

            evaluations = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # All evaluations should complete successfully
            assert len(evaluations) == num_evaluations
            for evaluation in evaluations:
                assert evaluation.evaluation_status == "completed"

            # Performance should scale reasonably (not linearly due to concurrency)
            avg_time_per_evaluation = total_time / num_evaluations
            print(
                f"Concurrent evaluations ({num_evaluations}): {total_time:.2f}s total, {avg_time_per_evaluation:.2f}s avg"
            )

            # Average time per evaluation should not increase dramatically
            assert (
                avg_time_per_evaluation < 1.0
            )  # Should be under 1 second per evaluation

    @pytest.mark.asyncio
    async def test_report_generation_performance(self, mock_persona_service):
        """Test performance of report generation."""
        evaluator = GovernanceEvaluator(mock_persona_service)
        report_generator = GovernanceReportGenerator()

        # Create evaluation
        model = GovernanceModel(
            name="Report Performance Test",
            description="Model for report generation performance test",
            model_type="Test",
            key_features=["feature1", "feature2", "feature3"],
            proposed_by="Test User",
        )

        evaluation = await evaluator.evaluate_governance_model(model)

        # Test different report types
        report_types = [
            ("markdown", lambda: report_generator.generate_markdown_report(evaluation)),
            ("json", lambda: report_generator.generate_json_report(evaluation)),
            ("summary", lambda: report_generator.generate_summary_report(evaluation)),
        ]

        for report_type, generator_func in report_types:
            start_time = time.time()
            report = generator_func()
            end_time = time.time()

            generation_time = end_time - start_time

            # Report generation should be very fast
            assert generation_time < 0.1  # Should be under 100ms
            assert report is not None

            print(
                f"{report_type} report generation time: {generation_time:.3f} seconds"
            )

    @pytest.mark.asyncio
    async def test_large_model_evaluation_performance(self, mock_persona_service):
        """Test performance with large, complex models."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        # Create a large, complex model
        large_model = GovernanceModel(
            name="Large Complex Governance Model",
            description="A very detailed and complex governance model with extensive features and requirements for performance testing",
            model_type="Complex",
            key_features=[f"Complex feature {i}" for i in range(50)],  # 50 features
            proposed_by="Complex Test User",
            metadata={
                "complexity": "high",
                "features": 50,
                "requirements": "extensive",
                "stakeholders": "many",
                "sectors": "multiple",
            },
        )

        start_time = time.time()
        evaluation = await evaluator.evaluate_governance_model(large_model)
        end_time = time.time()

        evaluation_time = end_time - start_time

        # Should still complete within reasonable time
        assert evaluation_time < 3.0  # Should be under 3 seconds
        assert evaluation.evaluation_status == "completed"
        assert len(evaluation.factor_scores) == 6

        print(f"Large model evaluation time: {evaluation_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_memory_usage_during_evaluations(
        self, mock_persona_service, sample_models
    ):
        """Test memory usage during multiple evaluations."""
        import psutil
        import os

        evaluator = GovernanceEvaluator(mock_persona_service)

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run multiple evaluations
        evaluations = []
        for i, model in enumerate(sample_models[:5]):  # Test with 5 models
            evaluation = await evaluator.evaluate_governance_model(model)
            evaluations.append(evaluation)

            # Check memory usage after each evaluation
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory

            print(
                f"After evaluation {i+1}: Memory usage {current_memory:.1f}MB (+{memory_increase:.1f}MB)"
            )

            # Memory increase should be reasonable (not growing indefinitely)
            assert memory_increase < 100  # Should not increase by more than 100MB

        # All evaluations should complete successfully
        assert len(evaluations) == 5
        for evaluation in evaluations:
            assert evaluation.evaluation_status == "completed"

    @pytest.mark.asyncio
    async def test_evaluation_criteria_performance(self, mock_persona_service):
        """Test performance of evaluation criteria loading and processing."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        # Test criteria loading performance
        start_time = time.time()
        criteria = evaluator.evaluation_criteria
        end_time = time.time()

        criteria_loading_time = end_time - start_time

        # Criteria loading should be very fast
        assert criteria_loading_time < 0.01  # Should be under 10ms
        assert len(criteria) == 6

        # Test criteria processing performance
        model = GovernanceModel(
            name="Criteria Performance Test",
            description="Model for criteria processing performance test",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Test User",
        )

        start_time = time.time()
        evaluation = await evaluator.evaluate_governance_model(model)
        end_time = time.time()

        evaluation_time = end_time - start_time

        # Should process all criteria efficiently
        assert evaluation_time < 1.0  # Should be under 1 second
        assert len(evaluation.factor_scores) == 6

        print(f"Criteria loading time: {criteria_loading_time:.3f} seconds")
        print(f"Full evaluation time: {evaluation_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_stress_evaluation_performance(self, mock_persona_service):
        """Test performance under stress with many rapid evaluations."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        # Create many models for stress testing
        stress_models = []
        for i in range(20):  # 20 models for stress test
            model = GovernanceModel(
                name=f"Stress Test Model {i}",
                description=f"Model {i} for stress testing",
                model_type="Stress Test",
                key_features=[f"stress_feature_{j}" for j in range(3)],
                proposed_by=f"Stress Test User {i}",
            )
            stress_models.append(model)

        # Run all evaluations concurrently
        start_time = time.time()

        tasks = []
        for model in stress_models:
            task = evaluator.evaluate_governance_model(model)
            tasks.append(task)

        evaluations = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # All evaluations should complete successfully
        assert len(evaluations) == 20
        for evaluation in evaluations:
            assert evaluation.evaluation_status == "completed"

        # Should handle stress test efficiently
        avg_time_per_evaluation = total_time / 20
        print(
            f"Stress test (20 models): {total_time:.2f}s total, {avg_time_per_evaluation:.2f}s avg"
        )

        # Average time should still be reasonable
        assert avg_time_per_evaluation < 0.5  # Should be under 500ms per evaluation

    @pytest.mark.asyncio
    async def test_report_generation_with_large_data(self, mock_persona_service):
        """Test report generation performance with large evaluation data."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        # Create evaluation with extensive data
        model = GovernanceModel(
            name="Large Data Report Test",
            description="A model with extensive data for report generation performance testing",
            model_type="Large Data",
            key_features=[f"Feature {i}" for i in range(20)],
            proposed_by="Large Data Test User",
            metadata={
                "extensive": True,
                "data_size": "large",
                "features": 20,
                "complexity": "high",
            },
        )

        evaluation = await evaluator.evaluate_governance_model(model)

        # Test different report configurations with large data
        configs = [
            ReportConfig(
                include_evidence_citations=True, include_persona_perspectives=True
            ),
            ReportConfig(
                include_evidence_citations=True, include_persona_perspectives=False
            ),
            ReportConfig(
                include_evidence_citations=False, include_persona_perspectives=True
            ),
            ReportConfig(max_rationale_length=1000, include_detailed_rationales=True),
        ]

        for i, config in enumerate(configs):
            generator = GovernanceReportGenerator(config)

            start_time = time.time()
            report = generator.generate_markdown_report(evaluation)
            end_time = time.time()

            generation_time = end_time - start_time

            # Should still generate reports quickly even with large data
            assert generation_time < 0.2  # Should be under 200ms
            assert len(report) > 1000  # Should generate substantial report

            print(
                f"Large data report generation (config {i+1}): {generation_time:.3f} seconds"
            )

    def test_evaluation_criteria_memory_efficiency(self):
        """Test memory efficiency of evaluation criteria."""
        import sys

        # Measure memory usage of criteria loading

        evaluator = GovernanceEvaluator(Mock())
        criteria = evaluator.evaluation_criteria

        criteria_size = sys.getsizeof(criteria)

        # Criteria should not use excessive memory
        assert criteria_size < 10000  # Should be under 10KB

        # Check individual criteria size
        for _factor, criteria_data in criteria.items():
            criteria_data_size = sys.getsizeof(criteria_data)
            assert criteria_data_size < 2000  # Each criteria should be under 2KB

        print(f"Evaluation criteria memory usage: {criteria_size} bytes")

    @pytest.mark.asyncio
    async def test_async_performance_characteristics(self, mock_persona_service):
        """Test async performance characteristics."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        model = GovernanceModel(
            name="Async Performance Test",
            description="Model for async performance testing",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Test User",
        )

        # Test that async operations don't block
        start_time = time.time()

        # Start evaluation
        evaluation_task = asyncio.create_task(
            evaluator.evaluate_governance_model(model)
        )

        # Do other work while evaluation is running
        other_work_start = time.time()
        await asyncio.sleep(0.05)  # Simulate other work
        other_work_end = time.time()

        # Wait for evaluation to complete
        evaluation = await evaluation_task
        end_time = time.time()

        total_time = end_time - start_time
        other_work_time = other_work_end - other_work_start

        # Should be able to do other work concurrently
        assert other_work_time > 0.04  # Should have done other work
        assert evaluation.evaluation_status == "completed"

        print(f"Total time: {total_time:.2f}s, Other work time: {other_work_time:.2f}s")
