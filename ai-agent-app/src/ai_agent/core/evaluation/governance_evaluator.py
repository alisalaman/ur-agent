import asyncio
from typing import NamedTuple
import structlog

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType
from ai_agent.core.evaluation.criteria_loader import EvaluationCriteriaLoader
from ai_agent.core.evaluation.evaluation_storage import EvaluationStorage
from ai_agent.core.evaluation.models import (
    EvaluationStatus,
    CriticalSuccessFactor,
    GovernanceModel,
    EvaluationCriteria,
    FactorScore,
    ModelEvaluation,
    PersonaServiceError,
    EvaluationCriteriaError,
)

logger = structlog.get_logger()


class ParsedResponse(NamedTuple):
    """Parsed response from a persona agent."""

    score: int
    rationale: str
    citations: list[str]


class GovernanceEvaluator:
    """Orchestrates governance model evaluations using synthetic agents."""

    def __init__(
        self,
        persona_service: PersonaAgentService,
        criteria_loader: EvaluationCriteriaLoader | None = None,
        evaluation_storage: EvaluationStorage | None = None,
    ):
        self.persona_service = persona_service
        self.criteria_loader = criteria_loader or EvaluationCriteriaLoader()
        self.evaluation_storage = evaluation_storage or EvaluationStorage()
        self.evaluation_criteria = self.criteria_loader.get_criteria()

    async def evaluate_governance_model(
        self,
        model: GovernanceModel,
        include_personas: list[PersonaType] | None = None,
    ) -> ModelEvaluation:
        """Evaluate a governance model using synthetic agents."""
        from uuid import uuid4
        from datetime import datetime

        evaluation_id = uuid4()

        try:
            # Initialize evaluation
            evaluation = ModelEvaluation(
                id=evaluation_id,
                model=model,
                factor_scores={},
                overall_score=0.0,
                overall_assessment="",
                key_risks=[],
                key_benefits=[],
                recommendations=[],
                evaluation_status=EvaluationStatus.IN_PROGRESS,
            )

            # Store evaluation
            self.evaluation_storage.store_evaluation(evaluation)

            logger.info(
                "Starting governance model evaluation",
                evaluation_id=str(evaluation_id),
                model_name=model.name,
            )

            # Determine which personas to include
            if include_personas is None:
                include_personas = list(PersonaType)

            # Evaluate all critical success factors concurrently for better performance
            factor_tasks = [
                self._evaluate_factor(factor, model, include_personas)
                for factor in CriticalSuccessFactor
            ]
            factor_scores = await asyncio.gather(*factor_tasks)

            # Map scores to factors
            for factor, score in zip(
                CriticalSuccessFactor, factor_scores, strict=False
            ):
                evaluation.factor_scores[factor] = score

            # Calculate overall score and assessment
            evaluation.overall_score = self._calculate_overall_score(
                evaluation.factor_scores
            )
            evaluation.overall_assessment = await self._generate_overall_assessment(
                evaluation
            )
            evaluation.key_risks = self._extract_key_risks(evaluation.factor_scores)
            evaluation.key_benefits = self._extract_key_benefits(
                evaluation.factor_scores
            )
            evaluation.recommendations = await self._generate_recommendations(
                evaluation
            )

            # Mark as completed
            evaluation.evaluation_status = EvaluationStatus.COMPLETED
            evaluation.completed_at = datetime.utcnow()

            logger.info(
                "Governance model evaluation completed",
                evaluation_id=str(evaluation_id),
                overall_score=evaluation.overall_score,
            )

            return evaluation

        except PersonaServiceError as e:
            logger.error(
                "Persona service failed during evaluation",
                evaluation_id=str(evaluation_id),
                error=str(e),
            )
            evaluation.evaluation_status = EvaluationStatus.FAILED
            raise
        except EvaluationCriteriaError as e:
            logger.error(
                "Evaluation criteria error during evaluation",
                evaluation_id=str(evaluation_id),
                error=str(e),
            )
            evaluation.evaluation_status = EvaluationStatus.FAILED
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during governance model evaluation",
                evaluation_id=str(evaluation_id),
                error=str(e),
            )
            evaluation.evaluation_status = EvaluationStatus.FAILED
            raise

    async def _evaluate_factor(
        self,
        factor: CriticalSuccessFactor,
        model: GovernanceModel,
        personas: list[PersonaType],
    ) -> FactorScore:
        """Evaluate a specific critical success factor."""
        criteria = self.evaluation_criteria[factor]

        # Create evaluation query for this factor
        evaluation_query = self._create_factor_evaluation_query(factor, model, criteria)

        # Get responses from all personas
        try:
            persona_responses = await self.persona_service.process_query_all_personas(
                evaluation_query,
                context={
                    "governance_model": model.name,
                    "factor": factor.value,
                    "evaluation_questions": criteria.evaluation_questions,
                },
            )
        except Exception as e:
            logger.error(
                "Persona service failed during factor evaluation",
                factor=factor.value,
                error=str(e),
            )
            # Return default score for complete failure
            return FactorScore(
                factor=factor,
                score=1,
                rationale="Persona service failed - using default score",
                evidence_citations=[],
                confidence_level="very_low",
                persona_perspective="unknown",
            )

        # Analyze responses and determine score
        score, rationale, evidence_citations, confidence_level = (
            await self._analyze_factor_responses(factor, persona_responses, criteria)
        )

        # Determine primary persona perspective (highest confidence)
        primary_persona = self._determine_primary_persona_perspective(persona_responses)

        return FactorScore(
            factor=factor,
            score=score,
            rationale=rationale,
            evidence_citations=evidence_citations,
            confidence_level=confidence_level,
            persona_perspective=primary_persona,
        )

    def _create_factor_evaluation_query(
        self,
        factor: CriticalSuccessFactor,
        model: GovernanceModel,
        criteria: EvaluationCriteria,
    ) -> str:
        """Create evaluation query for a specific factor."""
        query = f"""Evaluate the governance model "{model.name}" against the critical success factor: {factor.value}

Model Description: {model.description}

Key Features: {', '.join(model.key_features)}

Evaluation Questions:
{chr(10).join(f"- {q}" for q in criteria.evaluation_questions)}

Scoring Guidelines:
{chr(10).join(f"- {score}: {desc}" for score, desc in criteria.scoring_guidelines.items())}

Please provide:
1. A score from 1-5 based on the guidelines
2. Detailed rationale for your score
3. Specific evidence from the transcripts to support your assessment
4. Key risks and benefits you identify
5. Recommendations for improvement

Focus on evidence-based analysis using the stakeholder views tool."""

        return query

    async def _analyze_factor_responses(
        self,
        factor: CriticalSuccessFactor,
        persona_responses: dict[PersonaType, str],
        criteria: EvaluationCriteria,
    ) -> tuple[int, str, list[str], str]:
        """Analyze responses from all personas to determine factor score."""
        parsed_responses = self._parse_all_persona_responses(persona_responses)

        if not parsed_responses:
            return 1, "No valid responses received", [], "very_low"

        scores = [r.score for r in parsed_responses]
        overall_score = self._calculate_average_score(scores)
        combined_rationale = self._combine_rationales(
            [r.rationale for r in parsed_responses], scores
        )
        evidence_citations = [
            citation for r in parsed_responses for citation in r.citations
        ]
        confidence_level = self._determine_confidence_level(
            scores, len(persona_responses)
        )

        return overall_score, combined_rationale, evidence_citations, confidence_level

    def _parse_all_persona_responses(
        self, persona_responses: dict[PersonaType, str]
    ) -> list[ParsedResponse]:
        """Parse all persona responses and return valid parsed responses."""
        parsed_responses = []

        for persona_type, response in persona_responses.items():
            try:
                score, rationale, citations = self._parse_persona_response(response)
                parsed_responses.append(ParsedResponse(score, rationale, citations))
            except Exception as e:
                logger.warning(
                    "Failed to parse persona response",
                    persona_type=persona_type.value,
                    error=str(e),
                )

        return parsed_responses

    def _calculate_average_score(self, scores: list[int]) -> int:
        """Calculate average score and clamp to 1-5 range."""
        if not scores:
            return 1

        overall_score = round(sum(scores) / len(scores))
        return max(1, min(5, overall_score))

    def _parse_persona_response(self, response: str) -> tuple[int, str, list[str]]:
        """Parse persona response to extract score, rationale, and citations."""
        import re

        # Look for score patterns
        score_match = re.search(r"score[:\s]*(\d+)", response.lower())
        score = int(score_match.group(1)) if score_match else 3

        # Extract rationale (everything after "rationale" or "reasoning")
        rationale_match = re.search(
            r"(?:rationale|reasoning)[:\s]*(.+?)(?:\n\n|\nEvidence|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        rationale = rationale_match.group(1).strip() if rationale_match else response

        # Extract evidence citations
        citation_patterns = [
            r"evidence[:\s]*(.+?)(?:\n|$)",
            r"citation[:\s]*(.+?)(?:\n|$)",
            r"from transcripts[:\s]*(.+?)(?:\n|$)",
        ]

        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            citations.extend(matches)

        return score, rationale, citations

    def _combine_rationales(self, rationales: list[str], scores: list[int]) -> str:
        """Combine rationales from multiple personas."""
        if not rationales:
            return "No rationale provided"

        if len(rationales) == 1:
            return rationales[0]

        # Create weighted combination based on scores
        combined = "Combined Assessment:\n\n"

        for i, (rationale, score) in enumerate(zip(rationales, scores, strict=False)):
            combined += f"Perspective {i+1} (Score: {score}): {rationale}\n\n"

        return combined.strip()

    def _determine_confidence_level(
        self, scores: list[int], response_count: int
    ) -> str:
        """Determine confidence level based on score consistency."""
        if response_count == 0:
            return "very_low"

        variance = self._calculate_score_variance(scores)

        confidence_rules = [
            (lambda v, c: v <= 0.5 and c >= 3, "high"),
            (lambda v, c: v <= 1.0 and c >= 2, "medium"),
            (lambda v, c: True, "low"),
        ]

        for rule, level in confidence_rules:
            if rule(variance, response_count):
                return level

        return "low"  # Fallback

    def _calculate_score_variance(self, scores: list[int]) -> float:
        """Calculate variance of scores."""
        if len(scores) <= 1:
            return 0.0

        mean_score = sum(scores) / len(scores)
        return sum((score - mean_score) ** 2 for score in scores) / len(scores)

    def _determine_primary_persona_perspective(
        self, persona_responses: dict[PersonaType, str]
    ) -> str:
        """Determine primary persona perspective based on response quality."""
        # This is a simplified implementation
        # In practice, this would analyze response quality and confidence

        if not persona_responses:
            return "unknown"

        # For now, return the first persona
        first_persona = list(persona_responses.keys())[0]
        return str(first_persona.value)

    def _calculate_overall_score(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> float:
        """Calculate overall weighted score."""
        if not factor_scores:
            return 0.0

        total_weighted_score = 0.0
        total_weight = 0.0

        for factor, score_data in factor_scores.items():
            criteria = self.evaluation_criteria[factor]
            weight = criteria.weight
            total_weighted_score += score_data.score * weight
            total_weight += weight

        return (
            round(total_weighted_score / total_weight, 2) if total_weight > 0 else 0.0
        )

    async def _generate_overall_assessment(self, evaluation: ModelEvaluation) -> str:
        """Generate overall assessment of the governance model."""
        # This would use an LLM to generate a comprehensive assessment
        # For now, create a structured summary

        assessment = f"Overall Assessment for {evaluation.model.name}:\n\n"
        assessment += f"Overall Score: {evaluation.overall_score}/5\n\n"

        # Factor breakdown
        assessment += "Factor Scores:\n"
        for factor, score_data in evaluation.factor_scores.items():
            assessment += f"- {factor.value}: {score_data.score}/5 ({score_data.confidence_level} confidence)\n"

        # Key insights
        assessment += f"\nKey Risks: {', '.join(evaluation.key_risks)}\n"
        assessment += f"Key Benefits: {', '.join(evaluation.key_benefits)}\n"

        return assessment

    def _extract_key_risks(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> list[str]:
        """Extract key risks from factor scores."""
        risks = []

        for factor, score_data in factor_scores.items():
            if score_data.score <= 2:
                risks.append(
                    f"Low score in {factor.value}: {score_data.rationale[:100]}..."
                )

        return risks[:5]  # Limit to top 5 risks

    def _extract_key_benefits(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> list[str]:
        """Extract key benefits from factor scores."""
        benefits = []

        for factor, score_data in factor_scores.items():
            if score_data.score >= 4:
                benefits.append(
                    f"Strong performance in {factor.value}: {score_data.rationale[:100]}..."
                )

        return benefits[:5]  # Limit to top 5 benefits

    async def _generate_recommendations(self, evaluation: ModelEvaluation) -> list[str]:
        """Generate recommendations based on evaluation results."""
        recommendations = []

        # Recommendations based on low-scoring factors
        for factor, score_data in evaluation.factor_scores.items():
            if score_data.score <= 2:
                recommendations.append(
                    f"Improve {factor.value}: {score_data.rationale[:100]}..."
                )

        # General recommendations
        if evaluation.overall_score < 3:
            recommendations.append(
                "Consider fundamental redesign of governance approach"
            )
        elif evaluation.overall_score < 4:
            recommendations.append("Address key weaknesses before implementation")
        else:
            recommendations.append("Model shows promise with minor improvements needed")

        return recommendations[:10]  # Limit to top 10 recommendations
