"""
Evaluation criteria loading and management.
"""

from ai_agent.core.evaluation.models import (
    EvaluationCriteria,
    CriticalSuccessFactor,
)


class EvaluationCriteriaLoader:
    """Handles loading and management of evaluation criteria."""

    def __init__(self) -> None:
        self._criteria_cache: dict[CriticalSuccessFactor, EvaluationCriteria] = {}
        self._load_criteria()

    def get_criteria(self) -> dict[CriticalSuccessFactor, EvaluationCriteria]:
        """Get all evaluation criteria."""
        return self._criteria_cache.copy()

    def get_criteria_for_factor(
        self, factor: CriticalSuccessFactor
    ) -> EvaluationCriteria:
        """Get criteria for a specific factor."""
        if factor not in self._criteria_cache:
            raise ValueError(f"No criteria found for factor: {factor}")
        return self._criteria_cache[factor]

    def _load_criteria(self) -> None:
        """Load evaluation criteria for all critical success factors."""
        criteria_data = {
            CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY: {
                "description": "The governance model demonstrates clear commercial viability and sustainable revenue streams",
                "questions": [
                    "Does the model provide clear commercial incentives for all participants?",
                    "Are there sustainable revenue streams that support long-term operation?",
                    "Is the cost structure reasonable and transparent?",
                    "Do participants have clear paths to profitability?",
                ],
                "weight": 1.2,
            },
            CriticalSuccessFactor.PROPORTIONALITY_AND_PROVEN_DEMAND: {
                "description": "The governance model is proportional to proven demand and avoids over-regulation",
                "questions": [
                    "Is the model proportional to actual market demand?",
                    "Are there clear indicators of proven consumer demand?",
                    "Does the model avoid unnecessary complexity or over-regulation?",
                    "Is there evidence of market readiness for this approach?",
                ],
                "weight": 1.0,
            },
            CriticalSuccessFactor.SYMMETRICAL_GOVERNANCE: {
                "description": "The governance model ensures balanced rights and obligations for all participants",
                "questions": [
                    "Are rights and obligations balanced across all participant types?",
                    "Is there fair representation in governance decisions?",
                    "Are liability frameworks symmetrical and enforceable?",
                    "Does the model avoid creating lopsided market dynamics?",
                ],
                "weight": 1.1,
            },
            CriticalSuccessFactor.CROSS_SECTOR_INTEROPERABILITY: {
                "description": "The governance model enables cross-sector data sharing and interoperability",
                "questions": [
                    "Does the model enable cross-sector data sharing?",
                    "Are there clear interoperability standards and protocols?",
                    "Does the model avoid creating sector-specific silos?",
                    "Is there a path to unified cross-sector governance?",
                ],
                "weight": 1.3,
            },
            CriticalSuccessFactor.EFFECTIVE_AND_STABLE_GOVERNANCE: {
                "description": "The governance model provides effective decision-making and long-term stability",
                "questions": [
                    "Are governance processes clear and efficient?",
                    "Is there effective dispute resolution and enforcement?",
                    "Does the model provide long-term stability and predictability?",
                    "Are there mechanisms for evolution and adaptation?",
                ],
                "weight": 1.0,
            },
            CriticalSuccessFactor.TECHNICAL_AND_FINANCIAL_FEASIBILITY: {
                "description": "The governance model is technically and financially feasible to implement",
                "questions": [
                    "Is the technical implementation feasible with current technology?",
                    "Are the financial requirements reasonable and achievable?",
                    "Is there a clear implementation roadmap?",
                    "Are there adequate resources and expertise available?",
                ],
                "weight": 0.9,
            },
        }

        for factor, data in criteria_data.items():
            self._criteria_cache[factor] = EvaluationCriteria(
                factor=factor,
                description=data["description"],
                evaluation_questions=data["questions"],
                scoring_guidelines=self._get_default_scoring_guidelines(),
                weight=data["weight"],
            )

    def _get_default_scoring_guidelines(self) -> dict[int, str]:
        """Get default scoring guidelines for all factors."""
        return {
            5: "Excellent performance with clear evidence and strong rationale",
            4: "Good performance with minor gaps or concerns",
            3: "Adequate performance with some areas for improvement",
            2: "Poor performance with significant gaps or issues",
            1: "Very poor performance with fundamental problems",
        }
