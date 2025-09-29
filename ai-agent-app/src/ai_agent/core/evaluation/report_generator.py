from dataclasses import dataclass
from datetime import datetime
from typing import Any
import structlog

from ai_agent.core.evaluation.models import (
    ModelEvaluation,
    FactorScore,
    CriticalSuccessFactor,
)

logger = structlog.get_logger()


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    include_evidence_citations: bool = True
    include_persona_perspectives: bool = True
    include_detailed_rationales: bool = True
    max_rationale_length: int = 500
    include_recommendations: bool = True


class GovernanceReportGenerator:
    """Generates comprehensive evaluation reports."""

    def __init__(self, config: ReportConfig | None = None):
        self.config = config or ReportConfig()

    def generate_markdown_report(self, evaluation: ModelEvaluation) -> str:
        """Generate a markdown-formatted evaluation report."""
        report = []

        # Header
        report.append("# Governance Model Evaluation Report")
        report.append(f"**Model:** {evaluation.model.name}")
        report.append(
            f"**Evaluation Date:** {evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report.append(f"**Overall Score:** {evaluation.overall_score}/5")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append(evaluation.overall_assessment)
        report.append("")

        # Factor Scores Table
        report.append("## Critical Success Factor Scores")
        report.append(self._generate_scores_table(evaluation.factor_scores))
        report.append("")

        # Detailed Factor Analysis
        report.append("## Detailed Factor Analysis")
        for factor, score_data in evaluation.factor_scores.items():
            report.append(self._generate_factor_analysis(factor, score_data))
            report.append("")

        # Key Risks and Benefits
        if evaluation.key_risks or evaluation.key_benefits:
            report.append("## Key Risks and Benefits")

            if evaluation.key_risks:
                report.append("### Key Risks")
                for i, risk in enumerate(evaluation.key_risks, 1):
                    report.append(f"{i}. {risk}")
                report.append("")

            if evaluation.key_benefits:
                report.append("### Key Benefits")
                for i, benefit in enumerate(evaluation.key_benefits, 1):
                    report.append(f"{i}. {benefit}")
                report.append("")

        # Recommendations
        if evaluation.recommendations and self.config.include_recommendations:
            report.append("## Recommendations")
            for i, recommendation in enumerate(evaluation.recommendations, 1):
                report.append(f"{i}. {recommendation}")
            report.append("")

        # Evidence Citations
        if self.config.include_evidence_citations:
            report.append("## Evidence Citations")
            report.append(self._generate_evidence_citations(evaluation.factor_scores))
            report.append("")

        # Persona Perspectives
        if self.config.include_persona_perspectives:
            report.append("## Persona Perspectives")
            report.append(self._generate_persona_perspectives(evaluation.factor_scores))
            report.append("")

        # Footer
        report.append("---")
        report.append(
            f"*Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
        )

        return "\n".join(report)

    def _generate_scores_table(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> str:
        """Generate markdown table of factor scores."""
        table = []
        table.append("| Factor | Score | Confidence | Primary Perspective |")
        table.append("|--------|-------|------------|---------------------|")

        for factor, score_data in factor_scores.items():
            table.append(
                f"| {factor.value} | {score_data.score}/5 | {score_data.confidence_level} | {score_data.persona_perspective} |"
            )

        return "\n".join(table)

    def _generate_factor_analysis(
        self, factor: CriticalSuccessFactor, score_data: FactorScore
    ) -> str:
        """Generate detailed analysis for a specific factor."""
        analysis = []
        analysis.append(f"### {factor.value} - Score: {score_data.score}/5")
        analysis.append("")

        # Rationale
        if self.config.include_detailed_rationales:
            rationale = score_data.rationale
            if len(rationale) > self.config.max_rationale_length:
                rationale = rationale[: self.config.max_rationale_length] + "..."
            analysis.append(f"**Rationale:** {rationale}")
            analysis.append("")

        # Evidence Citations
        if score_data.evidence_citations and self.config.include_evidence_citations:
            analysis.append("**Evidence Citations:**")
            for i, citation in enumerate(
                score_data.evidence_citations[:5], 1
            ):  # Limit to 5
                analysis.append(f"{i}. {citation}")
            analysis.append("")

        return "\n".join(analysis)

    def _generate_evidence_citations(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> str:
        """Generate comprehensive evidence citations section."""
        citations = []

        for factor, score_data in factor_scores.items():
            if score_data.evidence_citations:
                citations.append(f"**{factor.value}:**")
                for i, citation in enumerate(score_data.evidence_citations, 1):
                    citations.append(f"{i}. {citation}")
                citations.append("")

        return "\n".join(citations) if citations else "No evidence citations available."

    def _generate_persona_perspectives(
        self, factor_scores: dict[CriticalSuccessFactor, FactorScore]
    ) -> str:
        """Generate persona perspectives section."""
        perspectives = []

        # Group by persona
        persona_groups: dict[str, list[tuple[CriticalSuccessFactor, FactorScore]]] = {}
        for factor, score_data in factor_scores.items():
            persona = score_data.persona_perspective
            if persona not in persona_groups:
                persona_groups[persona] = []
            persona_groups[persona].append((factor, score_data))

        for persona, factors in persona_groups.items():
            perspectives.append(f"### {persona} Perspective")
            perspectives.append("")

            for factor, score_data in factors:
                perspectives.append(
                    f"**{factor.value}:** {score_data.score}/5 - {score_data.rationale[:200]}..."
                )
                perspectives.append("")

        return "\n".join(perspectives)

    def generate_json_report(self, evaluation: ModelEvaluation) -> dict[str, Any]:
        """Generate a JSON-formatted evaluation report."""
        return {
            "evaluation_id": str(evaluation.id),
            "model": {
                "id": str(evaluation.model.id),
                "name": evaluation.model.name,
                "description": evaluation.model.description,
                "model_type": evaluation.model.model_type,
                "key_features": evaluation.model.key_features,
                "proposed_by": evaluation.model.proposed_by,
            },
            "overall_score": evaluation.overall_score,
            "overall_assessment": evaluation.overall_assessment,
            "factor_scores": {
                factor.value: {
                    "score": score_data.score,
                    "rationale": score_data.rationale,
                    "evidence_citations": score_data.evidence_citations,
                    "confidence_level": score_data.confidence_level,
                    "persona_perspective": score_data.persona_perspective,
                }
                for factor, score_data in evaluation.factor_scores.items()
            },
            "key_risks": evaluation.key_risks,
            "key_benefits": evaluation.key_benefits,
            "recommendations": evaluation.recommendations,
            "evaluation_status": evaluation.evaluation_status,
            "created_at": evaluation.created_at.isoformat(),
            "completed_at": (
                evaluation.completed_at.isoformat() if evaluation.completed_at else None
            ),
        }

    def generate_summary_report(self, evaluation: ModelEvaluation) -> str:
        """Generate a concise summary report."""
        summary = []

        summary.append(f"Governance Model: {evaluation.model.name}")
        summary.append(f"Overall Score: {evaluation.overall_score}/5")
        summary.append("")

        summary.append("Factor Scores:")
        for factor, score_data in evaluation.factor_scores.items():
            summary.append(f"- {factor.value}: {score_data.score}/5")

        summary.append("")

        if evaluation.key_risks:
            summary.append("Key Risks:")
            for risk in evaluation.key_risks[:3]:  # Top 3
                summary.append(f"- {risk}")
            summary.append("")

        if evaluation.key_benefits:
            summary.append("Key Benefits:")
            for benefit in evaluation.key_benefits[:3]:  # Top 3
                summary.append(f"- {benefit}")
            summary.append("")

        if evaluation.recommendations:
            summary.append("Top Recommendations:")
            for rec in evaluation.recommendations[:3]:  # Top 3
                summary.append(f"- {rec}")

        return "\n".join(summary)
