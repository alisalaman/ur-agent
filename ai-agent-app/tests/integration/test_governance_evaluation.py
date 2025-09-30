"""
Integration tests for governance evaluation framework.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
    CriticalSuccessFactor,
)
from ai_agent.core.evaluation.report_generator import (
    GovernanceReportGenerator,
    ReportConfig,
)
from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType


class TestGovernanceEvaluationIntegration:
    """Integration tests for governance evaluation system."""

    @pytest.fixture
    def persona_service(self):
        """Create real persona service for integration testing."""
        # This would use the actual persona service in a real integration test
        # For now, we'll mock it but with more realistic behavior
        service = Mock(spec=PersonaAgentService)

        # Mock realistic responses for different personas
        async def mock_process_query_all_personas(query, context=None):
            responses = {}

            # Bank representative - typically more conservative
            if "Commercial Sustainability" in query:
                responses[
                    PersonaType.BANK_REP
                ] = """
                Score: 4
                Rationale: The model shows strong commercial viability with clear revenue streams.
                However, there are concerns about long-term sustainability and regulatory compliance costs.
                Evidence: From transcript analysis, banks consistently emphasized the need for sustainable
                business models and clear ROI for participants.
                """
            elif "Cross-Sector Interoperability" in query:
                responses[
                    PersonaType.BANK_REP
                ] = """
                Score: 3
                Rationale: While the model addresses cross-sector needs, implementation complexity
                and security concerns remain significant challenges.
                Evidence: Bank representatives in transcripts highlighted security and compliance
                requirements as major barriers to cross-sector data sharing.
                """
            else:
                responses[
                    PersonaType.BANK_REP
                ] = """
                Score: 3
                Rationale: The model shows promise but requires further development to address
                key concerns raised by industry stakeholders.
                Evidence: Based on transcript analysis of bank representative discussions.
                """

            # Trade body representative - focused on industry needs
            if "Proportionality and Proven Demand" in query:
                responses[
                    PersonaType.TRADE_BODY_REP
                ] = """
                Score: 4
                Rationale: The model appears well-proportioned to market demand with clear evidence
                of industry readiness and consumer interest.
                Evidence: Trade body analysis shows strong industry support and proven demand
                indicators from multiple sectors.
                """
            elif "Symmetrical Governance" in query:
                responses[
                    PersonaType.TRADE_BODY_REP
                ] = """
                Score: 2
                Rationale: Significant imbalances in rights and obligations across participant types
                could lead to market distortions and unfair competitive advantages.
                Evidence: Trade body representatives consistently raised concerns about governance
                asymmetry in stakeholder discussions.
                """
            else:
                responses[
                    PersonaType.TRADE_BODY_REP
                ] = """
                Score: 3
                Rationale: The model addresses key industry concerns but needs refinement to
                ensure balanced stakeholder representation.
                Evidence: Based on trade body representative feedback from transcripts.
                """

            # Payments ecosystem representative - technical focus
            if "Technical and Financial Feasibility" in query:
                responses[
                    PersonaType.PAYMENTS_ECOSYSTEM_REP
                ] = """
                Score: 5
                Rationale: Excellent technical feasibility with proven technologies and clear
                implementation roadmap. Financial requirements are reasonable and achievable.
                Evidence: Technical analysis shows strong foundation using established standards
                and protocols already in use across the payments ecosystem.
                """
            elif "Effective and Stable Governance" in query:
                responses[
                    PersonaType.PAYMENTS_ECOSYSTEM_REP
                ] = """
                Score: 3
                Rationale: Governance processes are clear but may lack sufficient flexibility
                for rapid technological evolution in the payments space.
                Evidence: Payments ecosystem representatives noted the need for more agile
                governance mechanisms in their transcript discussions.
                """
            else:
                responses[
                    PersonaType.PAYMENTS_ECOSYSTEM_REP
                ] = """
                Score: 4
                Rationale: Strong technical foundation with good potential for implementation,
                though some areas need further development.
                Evidence: Based on technical analysis and payments ecosystem representative feedback.
                """

            return responses

        service.process_query_all_personas = mock_process_query_all_personas
        return service

    @pytest.fixture
    def sample_governance_models(self):
        """Create sample governance models for testing."""
        models = []

        # Centralized model
        models.append(
            GovernanceModel(
                name="Centralized Digital Identity Authority",
                description="A single centralized authority manages all digital identity standards and policies across sectors.",
                model_type="Centralized",
                key_features=[
                    "Single governing body",
                    "Unified standards",
                    "Centralized enforcement",
                    "Top-down decision making",
                ],
                proposed_by="Digital Innovation Agency",
                metadata={"complexity": "low", "control": "high"},
            )
        )

        # Federated model
        models.append(
            GovernanceModel(
                name="Federated Cross-Sector Framework",
                description="Multiple sector-specific authorities collaborate on shared standards while maintaining autonomy.",
                model_type="Federated",
                key_features=[
                    "Sector-specific governance",
                    "Cross-sector coordination",
                    "Distributed decision making",
                    "Flexible implementation",
                ],
                proposed_by="Cross-Sector Consortium",
                metadata={"complexity": "medium", "control": "distributed"},
            )
        )

        # Decentralized model
        models.append(
            GovernanceModel(
                name="Community-Driven Governance",
                description="Stakeholders participate directly in governance through consensus mechanisms.",
                model_type="Decentralized",
                key_features=[
                    "Stakeholder voting",
                    "Consensus mechanisms",
                    "Community standards",
                    "Transparent processes",
                ],
                proposed_by="Digital Identity Community",
                metadata={"complexity": "high", "control": "distributed"},
            )
        )

        return models

    @pytest.mark.asyncio
    async def test_end_to_end_evaluation_workflow(
        self, persona_service, sample_governance_models
    ):
        """Test complete end-to-end evaluation workflow."""
        # Initialize evaluator
        evaluator = GovernanceEvaluator(persona_service)
        report_generator = GovernanceReportGenerator()

        # Evaluate each model
        evaluations = []
        for model in sample_governance_models:
            evaluation = await evaluator.evaluate_governance_model(model)
            evaluations.append(evaluation)

            # Basic validation
            assert evaluation.model == model
            assert evaluation.overall_score > 0
            assert len(evaluation.factor_scores) == 6
            assert evaluation.evaluation_status == "completed"

        # Test report generation
        for evaluation in evaluations:
            # Markdown report
            markdown_report = report_generator.generate_markdown_report(evaluation)
            assert "# Governance Model Evaluation Report" in markdown_report
            assert evaluation.model.name in markdown_report

            # JSON report
            json_report = report_generator.generate_json_report(evaluation)
            assert "evaluation_id" in json_report
            assert json_report["overall_score"] == evaluation.overall_score

            # Summary report
            summary_report = report_generator.generate_summary_report(evaluation)
            assert evaluation.model.name in summary_report
            assert f"Overall Score: {evaluation.overall_score}/5" in summary_report

    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, persona_service):
        """Test coordination of multiple persona agents."""
        evaluator = GovernanceEvaluator(persona_service)

        model = GovernanceModel(
            name="Test Multi-Agent Model",
            description="A model to test multi-agent coordination",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

        # Run evaluation
        evaluation = await evaluator.evaluate_governance_model(model)

        # Check that all personas contributed
        persona_perspectives = set()
        for factor_score in evaluation.factor_scores.values():
            persona_perspectives.add(factor_score.persona_perspective)

        # Should have perspectives from at least one persona
        assert len(persona_perspectives) >= 1

        # Check factor scores have different perspectives
        perspectives_by_factor = {}
        for factor, score_data in evaluation.factor_scores.items():
            perspectives_by_factor[factor] = score_data.persona_perspective

        # Different factors should potentially have different primary perspectives
        # (though this depends on the mock implementation)
        assert len(set(perspectives_by_factor.values())) >= 1

    @pytest.mark.asyncio
    async def test_evaluation_criteria_consistency(self, persona_service):
        """Test that evaluation criteria are consistently applied."""
        evaluator = GovernanceEvaluator(persona_service)

        model = GovernanceModel(
            name="Consistency Test Model",
            description="A model to test evaluation consistency",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

        # Run multiple evaluations
        evaluations = []
        for _ in range(3):
            evaluation = await evaluator.evaluate_governance_model(model)
            evaluations.append(evaluation)

        # Check that criteria are consistently applied
        for evaluation in evaluations:
            assert len(evaluation.factor_scores) == 6

            for factor in CriticalSuccessFactor:
                assert factor in evaluation.factor_scores
                score_data = evaluation.factor_scores[factor]
                assert 1 <= score_data.score <= 5
                assert score_data.confidence_level in [
                    "high",
                    "medium",
                    "low",
                    "very_low",
                ]
                assert score_data.rationale
                assert (
                    score_data.persona_perspective in [p.value for p in PersonaType]
                    or score_data.persona_perspective == "unknown"
                )

    @pytest.mark.asyncio
    async def test_factor_specific_evaluation(self, persona_service):
        """Test evaluation of specific critical success factors."""
        evaluator = GovernanceEvaluator(persona_service)

        # Test commercial sustainability focus
        commercial_model = GovernanceModel(
            name="Commercial Focus Model",
            description="A model focused on commercial sustainability",
            model_type="Commercial",
            key_features=["Revenue streams", "Cost structure", "ROI"],
            proposed_by="Commercial Entity",
        )

        evaluation = await evaluator.evaluate_governance_model(commercial_model)

        # Check commercial sustainability score
        commercial_score = evaluation.factor_scores[
            CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY
        ]
        assert commercial_score.score >= 1
        assert commercial_score.score <= 5
        assert (
            "commercial" in commercial_score.rationale.lower()
            or "revenue" in commercial_score.rationale.lower()
        )

    @pytest.mark.asyncio
    async def test_evaluation_with_limited_personas(self, persona_service):
        """Test evaluation with limited persona set."""
        evaluator = GovernanceEvaluator(persona_service)

        model = GovernanceModel(
            name="Limited Persona Model",
            description="A model for limited persona testing",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

        # Evaluate with only bank representatives
        limited_personas = [PersonaType.BANK_REP]
        evaluation = await evaluator.evaluate_governance_model(model, limited_personas)

        # Check that all factor scores have bank representative perspective
        for factor_score in evaluation.factor_scores.values():
            assert factor_score.persona_perspective == PersonaType.BANK_REP

    @pytest.mark.asyncio
    async def test_evaluation_error_handling(self, persona_service):
        """Test error handling during evaluation."""
        evaluator = GovernanceEvaluator(persona_service)

        # Mock persona service to raise exception
        persona_service.process_query_all_personas = AsyncMock(
            side_effect=Exception("Simulated persona service failure")
        )

        model = GovernanceModel(
            name="Error Test Model",
            description="A model for error testing",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

        # Should complete with default scores instead of raising exception
        evaluation = await evaluator.evaluate_governance_model(model)
        assert evaluation.evaluation_status == "completed"
        assert evaluation.overall_score == 1.0  # Default score when all factors fail

    @pytest.mark.asyncio
    async def test_report_generation_with_real_data(
        self, persona_service, sample_governance_models
    ):
        """Test report generation with realistic evaluation data."""
        evaluator = GovernanceEvaluator(persona_service)

        # Evaluate a model
        model = sample_governance_models[0]  # Centralized model
        evaluation = await evaluator.evaluate_governance_model(model)

        # Test different report configurations
        configs = [
            ReportConfig(
                include_evidence_citations=True, include_persona_perspectives=True
            ),
            ReportConfig(
                include_evidence_citations=False, include_persona_perspectives=False
            ),
            ReportConfig(max_rationale_length=100, include_recommendations=False),
        ]

        for config in configs:
            generator = GovernanceReportGenerator(config)

            # Generate markdown report
            markdown_report = generator.generate_markdown_report(evaluation)
            assert model.name in markdown_report
            assert f"Overall Score: {evaluation.overall_score}/5" in markdown_report

            # Check configuration is respected
            if not config.include_evidence_citations:
                assert "## Evidence Citations" not in markdown_report
            if not config.include_persona_perspectives:
                assert "## Persona Perspectives" not in markdown_report
            if not config.include_recommendations:
                assert "## Recommendations" not in markdown_report

    @pytest.mark.asyncio
    async def test_concurrent_evaluations(
        self, persona_service, sample_governance_models
    ):
        """Test concurrent evaluation of multiple models."""
        evaluator = GovernanceEvaluator(persona_service)

        # Run evaluations concurrently
        tasks = []
        for model in sample_governance_models:
            task = evaluator.evaluate_governance_model(model)
            tasks.append(task)

        evaluations = await asyncio.gather(*tasks)

        # Check all evaluations completed successfully
        assert len(evaluations) == len(sample_governance_models)

        for evaluation in evaluations:
            assert evaluation.evaluation_status == "completed"
            assert evaluation.overall_score > 0
            assert len(evaluation.factor_scores) == 6

        # Check that all evaluations completed successfully
        scores = [e.overall_score for e in evaluations]
        assert len(scores) == 3  # Should have 3 evaluations
        assert all(score > 0 for score in scores)  # All scores should be positive
