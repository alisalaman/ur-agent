"""
Unit tests for governance evaluation framework.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from uuid import UUID

from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
    ModelEvaluation,
    FactorScore,
    EvaluationCriteria,
    CriticalSuccessFactor,
    EvaluationStatus,
)
from ai_agent.core.evaluation.report_generator import (
    GovernanceReportGenerator,
    ReportConfig,
)
from ai_agent.core.agents.synthetic_representative import PersonaType


class TestGovernanceModel:
    """Test GovernanceModel dataclass."""

    def test_governance_model_creation(self):
        """Test creating a governance model."""
        model = GovernanceModel(
            name="Test Model",
            description="A test governance model",
            model_type="Test",
            key_features=["feature1", "feature2"],
            proposed_by="Dr. Sarah Kim",
        )

        assert model.name == "Test Model"
        assert model.description == "A test governance model"
        assert model.model_type == "Test"
        assert model.key_features == ["feature1", "feature2"]
        assert model.proposed_by == "Dr. Sarah Kim"
        assert isinstance(model.id, UUID)
        assert isinstance(model.created_at, datetime)


class TestEvaluationCriteria:
    """Test EvaluationCriteria dataclass."""

    def test_evaluation_criteria_creation(self):
        """Test creating evaluation criteria."""
        criteria = EvaluationCriteria(
            factor=CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY,
            description="Test description",
            evaluation_questions=["Question 1", "Question 2"],
            scoring_guidelines={5: "Excellent", 4: "Good", 3: "Adequate"},
            weight=1.2,
        )

        assert criteria.factor == CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY
        assert criteria.description == "Test description"
        assert criteria.evaluation_questions == ["Question 1", "Question 2"]
        assert criteria.scoring_guidelines == {5: "Excellent", 4: "Good", 3: "Adequate"}
        assert criteria.weight == 1.2


class TestFactorScore:
    """Test FactorScore dataclass."""

    def test_factor_score_creation(self):
        """Test creating a factor score."""
        score = FactorScore(
            factor=CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY,
            score=4,
            rationale="Test rationale",
            evidence_citations=["Citation 1", "Citation 2"],
            confidence_level="high",
            persona_perspective=PersonaType.BANK_REP,
        )

        assert score.factor == CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY
        assert score.score == 4
        assert score.rationale == "Test rationale"
        assert score.evidence_citations == ["Citation 1", "Citation 2"]
        assert score.confidence_level == "high"
        assert score.persona_perspective == PersonaType.BANK_REP
        assert isinstance(score.created_at, datetime)


class TestGovernanceEvaluator:
    """Test GovernanceEvaluator class."""

    @pytest.fixture
    def mock_persona_service(self):
        """Create mock persona service."""
        service = Mock()
        service.process_query_all_personas = AsyncMock()
        return service

    @pytest.fixture
    def evaluator(self, mock_persona_service):
        """Create evaluator with mock service."""
        return GovernanceEvaluator(mock_persona_service)

    @pytest.fixture
    def sample_model(self):
        """Create sample governance model."""
        return GovernanceModel(
            name="Test Model",
            description="A test model",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

    def test_evaluator_initialization(self, mock_persona_service):
        """Test evaluator initialization."""
        evaluator = GovernanceEvaluator(mock_persona_service)

        assert evaluator.persona_service == mock_persona_service
        assert len(evaluator.evaluation_criteria) == 6
        assert evaluator.evaluation_storage is not None

        # Check all critical success factors are loaded
        for factor in CriticalSuccessFactor:
            assert factor in evaluator.evaluation_criteria

    def test_load_evaluation_criteria(self, evaluator):
        """Test evaluation criteria loading."""
        criteria = evaluator.evaluation_criteria

        # Check all factors are present
        assert len(criteria) == 6
        for factor in CriticalSuccessFactor:
            assert factor in criteria

        # Check specific criteria
        commercial_criteria = criteria[CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY]
        assert (
            commercial_criteria.factor
            == CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY
        )
        assert commercial_criteria.weight == 1.2
        assert len(commercial_criteria.evaluation_questions) > 0
        assert len(commercial_criteria.scoring_guidelines) == 5

    def test_calculate_overall_score(self, evaluator):
        """Test overall score calculation."""
        # Create mock factor scores
        factor_scores = {}
        for factor in CriticalSuccessFactor:
            factor_scores[factor] = FactorScore(
                factor=factor,
                score=3,
                rationale="Test",
                evidence_citations=[],
                confidence_level="medium",
                persona_perspective=PersonaType.BANK_REP,
            )

        score = evaluator._calculate_overall_score(factor_scores)
        assert score == 3.0  # Should be 3.0 for all scores of 3

    def test_calculate_overall_score_with_weights(self, evaluator):
        """Test overall score calculation with different weights."""
        # Create factor scores with different scores
        factor_scores = {}
        scores = [5, 4, 3, 2, 1, 5]  # Different scores for each factor

        for i, factor in enumerate(CriticalSuccessFactor):
            factor_scores[factor] = FactorScore(
                factor=factor,
                score=scores[i],
                rationale="Test",
                evidence_citations=[],
                confidence_level="medium",
                persona_perspective=PersonaType.BANK_REP,
            )

        score = evaluator._calculate_overall_score(factor_scores)
        # Should be weighted average, not simple average
        assert 1.0 <= score <= 5.0

    def test_calculate_overall_score_empty(self, evaluator):
        """Test overall score calculation with empty scores."""
        score = evaluator._calculate_overall_score({})
        assert score == 0.0

    def test_determine_confidence_level(self, evaluator):
        """Test confidence level determination."""
        # High confidence - low variance, many responses
        scores = [4, 4, 4, 4]
        confidence = evaluator._determine_confidence_level(scores, 4)
        assert confidence == "high"

        # Medium confidence - moderate variance
        scores = [3, 3, 4, 5]
        confidence = evaluator._determine_confidence_level(scores, 4)
        assert confidence == "medium"

        # Low confidence - high variance
        scores = [1, 2, 4, 5]
        confidence = evaluator._determine_confidence_level(scores, 4)
        assert confidence == "low"

        # Very low confidence - no responses
        confidence = evaluator._determine_confidence_level([], 0)
        assert confidence == "very_low"

    def test_parse_persona_response(self, evaluator):
        """Test parsing persona responses."""
        # Test with score and rationale
        response = "Score: 4\nRationale: This is a good model with some concerns."
        score, rationale, citations = evaluator._parse_persona_response(response)

        assert score == 4
        assert "good model" in rationale.lower()

    def test_parse_persona_response_no_score(self, evaluator):
        """Test parsing response without explicit score."""
        response = "This model has some issues but is generally acceptable."
        score, rationale, citations = evaluator._parse_persona_response(response)

        assert score == 3  # Default score
        assert rationale == response

    def test_combine_rationales(self, evaluator):
        """Test combining rationales from multiple personas."""
        rationales = ["First rationale", "Second rationale"]
        scores = [4, 3]

        combined = evaluator._combine_rationales(rationales, scores)

        assert "Combined Assessment" in combined
        assert "First rationale" in combined
        assert "Second rationale" in combined
        assert "Score: 4" in combined
        assert "Score: 3" in combined

    def test_combine_rationales_single(self, evaluator):
        """Test combining single rationale."""
        rationales = ["Single rationale"]
        scores = [4]

        combined = evaluator._combine_rationales(rationales, scores)
        assert combined == "Single rationale"

    def test_combine_rationales_empty(self, evaluator):
        """Test combining empty rationales."""
        combined = evaluator._combine_rationales([], [])
        assert combined == "No rationale provided"

    def test_extract_key_risks(self, evaluator):
        """Test extracting key risks from factor scores."""
        factor_scores = {}

        # Add some low-scoring factors
        for i, factor in enumerate(CriticalSuccessFactor):
            score = 1 if i < 2 else 4  # First two factors are low-scoring
            factor_scores[factor] = FactorScore(
                factor=factor,
                score=score,
                rationale=f"Risk rationale for {factor.value}",
                evidence_citations=[],
                confidence_level="medium",
                persona_perspective=PersonaType.BANK_REP,
            )

        risks = evaluator._extract_key_risks(factor_scores)

        assert len(risks) == 2  # Two low-scoring factors
        assert all("Low score" in risk for risk in risks)

    def test_extract_key_benefits(self, evaluator):
        """Test extracting key benefits from factor scores."""
        factor_scores = {}

        # Add some high-scoring factors
        for i, factor in enumerate(CriticalSuccessFactor):
            score = 5 if i < 2 else 3  # First two factors are high-scoring
            factor_scores[factor] = FactorScore(
                factor=factor,
                score=score,
                rationale=f"Benefit rationale for {factor.value}",
                evidence_citations=[],
                confidence_level="medium",
                persona_perspective=PersonaType.BANK_REP,
            )

        benefits = evaluator._extract_key_benefits(factor_scores)

        assert len(benefits) == 2  # Two high-scoring factors
        assert all("Strong performance" in benefit for benefit in benefits)

    @pytest.mark.asyncio
    async def test_evaluate_governance_model(self, evaluator, sample_model):
        """Test complete governance model evaluation."""
        # Mock persona service responses
        mock_responses = {
            PersonaType.BANK_REP: "Score: 4\nRationale: Good commercial viability",
            PersonaType.TRADE_BODY_REP: "Score: 3\nRationale: Adequate but needs improvement",
            PersonaType.PAYMENTS_ECOSYSTEM_REP: "Score: 4\nRationale: Strong technical foundation",
        }

        evaluator.persona_service.process_query_all_personas = AsyncMock(
            return_value=mock_responses
        )

        # Run evaluation
        evaluation = await evaluator.evaluate_governance_model(sample_model)

        # Check evaluation structure
        assert evaluation.model == sample_model
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED
        assert evaluation.overall_score > 0
        assert len(evaluation.factor_scores) == 6
        assert evaluation.completed_at is not None

        # Check factor scores
        for factor, score_data in evaluation.factor_scores.items():
            assert isinstance(score_data, FactorScore)
            assert 1 <= score_data.score <= 5
            assert score_data.factor == factor
            assert score_data.rationale
            assert score_data.confidence_level in ["high", "medium", "low", "very_low"]

    @pytest.mark.asyncio
    async def test_evaluate_governance_model_failure(self, evaluator, sample_model):
        """Test evaluation failure handling."""
        # Mock persona service to raise exception
        evaluator.persona_service.process_query_all_personas = AsyncMock(
            side_effect=Exception("Test error")
        )

        # Should complete with default scores instead of raising exception
        evaluation = await evaluator.evaluate_governance_model(sample_model)
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED
        # All scores should be 1 (default) due to failures
        for factor_score in evaluation.factor_scores.values():
            assert factor_score.score == 1
            assert factor_score.confidence_level == "very_low"

    def test_parse_all_persona_responses(self, evaluator):
        """Test parsing all persona responses."""
        persona_responses = {
            PersonaType.BANK_REP: "Score: 4\nRationale: Good model",
            PersonaType.TRADE_BODY_REP: "Score: 3\nRationale: Adequate model",
            PersonaType.PAYMENTS_ECOSYSTEM_REP: "Invalid response",
        }

        parsed_responses = evaluator._parse_all_persona_responses(persona_responses)

        # Should parse all 3 responses (invalid response gets default score 3)
        assert len(parsed_responses) == 3
        assert parsed_responses[0].score == 4
        assert parsed_responses[1].score == 3

    def test_calculate_average_score(self, evaluator):
        """Test average score calculation."""
        # Test normal scores
        scores = [3, 4, 5]
        assert evaluator._calculate_average_score(scores) == 4

        # Test empty scores
        assert evaluator._calculate_average_score([]) == 1

        # Test scores that need clamping
        scores = [1, 1, 1]  # Should stay at 1
        assert evaluator._calculate_average_score(scores) == 1

        scores = [5, 5, 5]  # Should stay at 5
        assert evaluator._calculate_average_score(scores) == 5

    def test_calculate_score_variance(self, evaluator):
        """Test score variance calculation."""
        # Test identical scores (zero variance)
        scores = [3, 3, 3]
        assert evaluator._calculate_score_variance(scores) == 0.0

        # Test different scores
        scores = [1, 3, 5]
        variance = evaluator._calculate_score_variance(scores)
        assert variance > 0

        # Test single score
        scores = [4]
        assert evaluator._calculate_score_variance(scores) == 0.0

        # Test empty scores
        assert evaluator._calculate_score_variance([]) == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_governance_model_partial_failure(
        self, evaluator, sample_model
    ):
        """Test evaluation with partial persona failures."""

        # Mock some personas to fail
        async def partial_failure_responses(query, context=None):
            responses = {}
            for i, persona_type in enumerate(PersonaType):
                if i == 0:  # First persona fails
                    raise Exception("Persona service error")
                responses[persona_type] = "Score: 3\nRationale: Test response"
            return responses

        evaluator.persona_service.process_query_all_personas = partial_failure_responses

        # Should still complete with remaining personas
        evaluation = await evaluator.evaluate_governance_model(sample_model)
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_evaluate_governance_model_empty_responses(
        self, evaluator, sample_model
    ):
        """Test evaluation with empty persona responses."""
        # Mock empty responses
        evaluator.persona_service.process_query_all_personas = AsyncMock(
            return_value={}
        )

        evaluation = await evaluator.evaluate_governance_model(sample_model)

        # Should complete but with low scores
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED
        for factor_score in evaluation.factor_scores.values():
            assert factor_score.score == 1  # Default low score
            assert factor_score.confidence_level == "very_low"

    @pytest.mark.asyncio
    async def test_evaluate_governance_model_malformed_responses(
        self, evaluator, sample_model
    ):
        """Test evaluation with malformed persona responses."""
        # Mock malformed responses
        malformed_responses = {
            PersonaType.BANK_REP: "Invalid response without score",
            PersonaType.TRADE_BODY_REP: "Score: invalid\nRationale: Test",
            PersonaType.PAYMENTS_ECOSYSTEM_REP: "Score: 4\nRationale: Valid response",
        }

        evaluator.persona_service.process_query_all_personas = AsyncMock(
            return_value=malformed_responses
        )

        evaluation = await evaluator.evaluate_governance_model(sample_model)

        # Should complete with default scores for malformed responses
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED
        assert len(evaluation.factor_scores) == 6

    @pytest.mark.asyncio
    async def test_evaluate_governance_model_extreme_scores(
        self, evaluator, sample_model
    ):
        """Test evaluation with extreme score values."""
        # Mock responses with extreme scores
        extreme_responses = {
            PersonaType.BANK_REP: "Score: 1\nRationale: Very poor",
            PersonaType.TRADE_BODY_REP: "Score: 5\nRationale: Excellent",
            PersonaType.PAYMENTS_ECOSYSTEM_REP: "Score: 1\nRationale: Very poor",
        }

        evaluator.persona_service.process_query_all_personas = AsyncMock(
            return_value=extreme_responses
        )

        evaluation = await evaluator.evaluate_governance_model(sample_model)

        # Should handle extreme scores appropriately
        assert evaluation.evaluation_status == EvaluationStatus.COMPLETED
        for factor_score in evaluation.factor_scores.values():
            assert 1 <= factor_score.score <= 5
            assert factor_score.confidence_level in [
                "high",
                "medium",
                "low",
                "very_low",
            ]


class TestGovernanceReportGenerator:
    """Test GovernanceReportGenerator class."""

    @pytest.fixture
    def sample_evaluation(self):
        """Create sample evaluation for testing."""
        model = GovernanceModel(
            name="Test Model",
            description="A test model",
            model_type="Test",
            key_features=["feature1"],
            proposed_by="Dr. Sarah Kim",
        )

        # Create factor scores
        factor_scores = {}
        for factor in CriticalSuccessFactor:
            factor_scores[factor] = FactorScore(
                factor=factor,
                score=3,
                rationale=f"Test rationale for {factor.value}",
                evidence_citations=[f"Citation for {factor.value}"],
                confidence_level="medium",
                persona_perspective=PersonaType.BANK_REP.value,
            )

        return ModelEvaluation(
            model=model,
            factor_scores=factor_scores,
            overall_score=3.0,
            overall_assessment="Test assessment",
            key_risks=["Risk 1", "Risk 2"],
            key_benefits=["Benefit 1", "Benefit 2"],
            recommendations=["Recommendation 1", "Recommendation 2"],
            evaluation_status=EvaluationStatus.COMPLETED,
        )

    def test_report_generator_initialization(self):
        """Test report generator initialization."""
        generator = GovernanceReportGenerator()
        assert isinstance(generator.config, ReportConfig)

    def test_report_generator_with_config(self):
        """Test report generator with custom config."""
        config = ReportConfig(
            include_evidence_citations=False, max_rationale_length=100
        )
        generator = GovernanceReportGenerator(config)
        assert not generator.config.include_evidence_citations
        assert generator.config.max_rationale_length == 100

    def test_generate_markdown_report(self, sample_evaluation):
        """Test markdown report generation."""
        generator = GovernanceReportGenerator()
        report = generator.generate_markdown_report(sample_evaluation)

        assert "# Governance Model Evaluation Report" in report
        assert "Test Model" in report
        assert "Overall Score:" in report
        assert "3.0/5" in report
        assert "## Executive Summary" in report
        assert "## Critical Success Factor Scores" in report
        assert "## Detailed Factor Analysis" in report
        assert "## Key Risks and Benefits" in report
        assert "## Recommendations" in report

    def test_generate_json_report(self, sample_evaluation):
        """Test JSON report generation."""
        generator = GovernanceReportGenerator()
        report = generator.generate_json_report(sample_evaluation)

        assert "evaluation_id" in report
        assert "model" in report
        assert "overall_score" in report
        assert "factor_scores" in report
        assert "key_risks" in report
        assert "key_benefits" in report
        assert "recommendations" in report

        assert report["overall_score"] == 3.0
        assert len(report["factor_scores"]) == 6

    def test_generate_summary_report(self, sample_evaluation):
        """Test summary report generation."""
        generator = GovernanceReportGenerator()
        report = generator.generate_summary_report(sample_evaluation)

        assert "Test Model" in report
        assert "Overall Score: 3.0/5" in report
        assert "Factor Scores:" in report
        assert "Key Risks:" in report
        assert "Key Benefits:" in report
        assert "Top Recommendations:" in report

    def test_generate_scores_table(self, sample_evaluation):
        """Test scores table generation."""
        generator = GovernanceReportGenerator()
        table = generator._generate_scores_table(sample_evaluation.factor_scores)

        assert "| Factor | Score | Confidence | Primary Perspective |" in table
        assert "|--------|-------|------------|---------------------|" in table
        assert "3/5" in table
        assert "medium" in table

    def test_generate_factor_analysis(self, sample_evaluation):
        """Test factor analysis generation."""
        generator = GovernanceReportGenerator()
        factor = CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY
        score_data = sample_evaluation.factor_scores[factor]

        analysis = generator._generate_factor_analysis(factor, score_data)

        assert f"### {factor.value} - Score: 3/5" in analysis
        assert "**Rationale:**" in analysis
        assert "**Evidence Citations:**" in analysis

    def test_generate_evidence_citations(self, sample_evaluation):
        """Test evidence citations generation."""
        generator = GovernanceReportGenerator()
        citations = generator._generate_evidence_citations(
            sample_evaluation.factor_scores
        )

        assert "Commercial Sustainability:" in citations
        assert "Citation for Commercial Sustainability" in citations

    def test_generate_persona_perspectives(self, sample_evaluation):
        """Test persona perspectives generation."""
        generator = GovernanceReportGenerator()
        perspectives = generator._generate_persona_perspectives(
            sample_evaluation.factor_scores
        )

        assert "### BankRep Perspective" in perspectives
        assert "Commercial Sustainability:" in perspectives
        assert "3/5" in perspectives


class TestReportConfig:
    """Test ReportConfig dataclass."""

    def test_default_config(self):
        """Test default report config."""
        config = ReportConfig()

        assert config.include_evidence_citations
        assert config.include_persona_perspectives
        assert config.include_detailed_rationales
        assert config.max_rationale_length == 500
        assert config.include_recommendations

    def test_custom_config(self):
        """Test custom report config."""
        config = ReportConfig(
            include_evidence_citations=False,
            include_persona_perspectives=False,
            max_rationale_length=200,
        )

        assert not config.include_evidence_citations
        assert not config.include_persona_perspectives
        assert config.max_rationale_length == 200
