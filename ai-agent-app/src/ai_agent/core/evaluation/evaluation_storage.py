"""
Evaluation storage and retrieval management.
"""

from uuid import UUID
from typing import Any
from datetime import datetime
import structlog

from ai_agent.core.evaluation.models import ModelEvaluation, EvaluationStatus

logger = structlog.get_logger()


class EvaluationStorage:
    """Handles storage and retrieval of evaluations."""

    def __init__(self) -> None:
        self._evaluations: dict[UUID, ModelEvaluation] = {}
        self._evaluation_history: list[ModelEvaluation] = []

    def store_evaluation(self, evaluation: ModelEvaluation) -> None:
        """Store an evaluation."""
        self._evaluations[evaluation.id] = evaluation
        self._evaluation_history.append(evaluation)

        logger.info(
            "Evaluation stored",
            evaluation_id=str(evaluation.id),
            model_name=evaluation.model.name,
            status=evaluation.evaluation_status.value,
        )

    def get_evaluation(self, evaluation_id: UUID) -> ModelEvaluation | None:
        """Get an evaluation by ID."""
        return self._evaluations.get(evaluation_id)

    def list_evaluations(
        self, status: EvaluationStatus | None = None, limit: int | None = None
    ) -> list[ModelEvaluation]:
        """List evaluations with optional filtering."""
        evaluations = list(self._evaluations.values())

        if status:
            evaluations = [e for e in evaluations if e.evaluation_status == status]

        # Sort by creation date (newest first)
        evaluations.sort(key=lambda e: e.created_at, reverse=True)

        if limit:
            evaluations = evaluations[:limit]

        return evaluations

    def get_evaluation_summary(self, evaluation_id: UUID) -> dict[str, Any] | None:
        """Get a summary of an evaluation."""
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation:
            return None

        return {
            "evaluation_id": str(evaluation.id),
            "model_name": evaluation.model.name,
            "model_type": evaluation.model.model_type,
            "overall_score": evaluation.overall_score,
            "evaluation_status": evaluation.evaluation_status.value,
            "created_at": evaluation.created_at.isoformat(),
            "completed_at": (
                evaluation.completed_at.isoformat() if evaluation.completed_at else None
            ),
            "factor_count": len(evaluation.factor_scores),
            "risk_count": len(evaluation.key_risks),
            "benefit_count": len(evaluation.key_benefits),
        }

    def get_evaluation_statistics(self) -> dict[str, Any]:
        """Get statistics about stored evaluations."""
        total_evaluations = len(self._evaluations)

        if total_evaluations == 0:
            return {
                "total_evaluations": 0,
                "status_counts": {},
                "average_score": 0.0,
                "score_distribution": {},
            }

        # Count by status
        status_counts: dict[str, int] = {}
        for evaluation in self._evaluations.values():
            status = evaluation.evaluation_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate average score
        completed_evaluations = [
            e
            for e in self._evaluations.values()
            if e.evaluation_status == EvaluationStatus.COMPLETED
        ]

        if completed_evaluations:
            average_score = sum(e.overall_score for e in completed_evaluations) / len(
                completed_evaluations
            )
        else:
            average_score = 0.0

        # Score distribution
        score_distribution: dict[str, int] = {}
        for evaluation in completed_evaluations:
            score_range = (
                f"{int(evaluation.overall_score)}-{int(evaluation.overall_score) + 1}"
            )
            score_distribution[score_range] = score_distribution.get(score_range, 0) + 1

        return {
            "total_evaluations": total_evaluations,
            "status_counts": status_counts,
            "average_score": round(average_score, 2),
            "score_distribution": score_distribution,
        }

    def cleanup_old_evaluations(self, days_old: int = 30) -> int:
        """Clean up evaluations older than specified days."""
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)

        evaluations_to_remove = []
        for evaluation_id, evaluation in self._evaluations.items():
            if evaluation.created_at < cutoff_date:
                evaluations_to_remove.append(evaluation_id)

        for evaluation_id in evaluations_to_remove:
            del self._evaluations[evaluation_id]

        logger.info(
            "Cleaned up old evaluations",
            removed_count=len(evaluations_to_remove),
            cutoff_date=cutoff_date.isoformat(),
        )

        return len(evaluations_to_remove)
