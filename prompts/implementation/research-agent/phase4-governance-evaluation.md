# Phase 4: Governance Evaluation Framework

## Overview

This phase implements the governance evaluation framework that orchestrates multi-agent evaluations of governance models. The system coordinates synthetic representative agents to provide structured scoring and rationale for governance proposals across six critical success factors.

## Objectives

- Create governance evaluation orchestration system
- Implement structured scoring framework (1-5 scale)
- Build multi-agent evaluation coordination
- Generate comprehensive evaluation reports
- Provide evidence-based governance recommendations

## Implementation Tasks

### 4.1 Evaluation Framework

**File**: `src/ai_agent/core/evaluation/governance_evaluator.py`

```python
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import structlog
from datetime import datetime

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType

logger = structlog.get_logger()

class EvaluationStatus(str, Enum):
    """Status of evaluation process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CriticalSuccessFactor(str, Enum):
    """Six critical success factors for governance evaluation."""
    COMMERCIAL_SUSTAINABILITY = "Commercial Sustainability"
    PROPORTIONALITY_AND_PROVEN_DEMAND = "Proportionality and Proven Demand"
    SYMMETRICAL_GOVERNANCE = "Symmetrical Governance"
    CROSS_SECTOR_INTEROPERABILITY = "Cross-Sector Interoperability"
    EFFECTIVE_AND_STABLE_GOVERNANCE = "Effective and Stable Governance"
    TECHNICAL_AND_FINANCIAL_FEASIBILITY = "Technical and Financial Feasibility"

@dataclass
class GovernanceModel:
    """Governance model to be evaluated."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    model_type: str = ""
    key_features: List[str] = field(default_factory=list)
    proposed_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationCriteria:
    """Criteria for evaluating governance models."""
    factor: CriticalSuccessFactor
    description: str
    evaluation_questions: List[str]
    scoring_guidelines: Dict[int, str]  # score -> description
    weight: float = 1.0  # Relative weight in overall scoring

@dataclass
class FactorScore:
    """Score for a specific critical success factor."""
    factor: CriticalSuccessFactor
    score: int  # 1-5 scale
    rationale: str
    evidence_citations: List[str]
    confidence_level: str  # high, medium, low
    persona_perspective: PersonaType
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ModelEvaluation:
    """Complete evaluation of a governance model."""
    id: UUID = field(default_factory=uuid4)
    model: GovernanceModel
    factor_scores: Dict[CriticalSuccessFactor, FactorScore]
    overall_score: float
    overall_assessment: str
    key_risks: List[str]
    key_benefits: List[str]
    recommendations: List[str]
    evaluation_status: EvaluationStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class GovernanceEvaluator:
    """Orchestrates governance model evaluations using synthetic agents."""

    def __init__(self, persona_service: PersonaAgentService):
        self.persona_service = persona_service
        self.evaluation_criteria = self._load_evaluation_criteria()
        self.active_evaluations: Dict[UUID, ModelEvaluation] = {}

    async def evaluate_governance_model(
        self,
        model: GovernanceModel,
        include_personas: Optional[List[PersonaType]] = None
    ) -> ModelEvaluation:
        """Evaluate a governance model using synthetic agents."""
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
                evaluation_status=EvaluationStatus.IN_PROGRESS
            )

            self.active_evaluations[evaluation_id] = evaluation

            logger.info("Starting governance model evaluation",
                       evaluation_id=str(evaluation_id),
                       model_name=model.name)

            # Determine which personas to include
            if include_personas is None:
                include_personas = list(PersonaType)

            # Evaluate each critical success factor
            for factor in CriticalSuccessFactor:
                factor_score = await self._evaluate_factor(
                    factor, model, include_personas
                )
                evaluation.factor_scores[factor] = factor_score

            # Calculate overall score and assessment
            evaluation.overall_score = self._calculate_overall_score(evaluation.factor_scores)
            evaluation.overall_assessment = await self._generate_overall_assessment(evaluation)
            evaluation.key_risks = self._extract_key_risks(evaluation.factor_scores)
            evaluation.key_benefits = self._extract_key_benefits(evaluation.factor_scores)
            evaluation.recommendations = await self._generate_recommendations(evaluation)

            # Mark as completed
            evaluation.evaluation_status = EvaluationStatus.COMPLETED
            evaluation.completed_at = datetime.utcnow()

            logger.info("Governance model evaluation completed",
                       evaluation_id=str(evaluation_id),
                       overall_score=evaluation.overall_score)

            return evaluation

        except Exception as e:
            logger.error("Governance model evaluation failed",
                        evaluation_id=str(evaluation_id),
                        error=str(e))
            evaluation.evaluation_status = EvaluationStatus.FAILED
            raise

    async def _evaluate_factor(
        self,
        factor: CriticalSuccessFactor,
        model: GovernanceModel,
        personas: List[PersonaType]
    ) -> FactorScore:
        """Evaluate a specific critical success factor."""
        criteria = self.evaluation_criteria[factor]

        # Create evaluation query for this factor
        evaluation_query = self._create_factor_evaluation_query(factor, model, criteria)

        # Get responses from all personas
        persona_responses = await self.persona_service.process_query_all_personas(
            evaluation_query,
            context={
                "governance_model": model.name,
                "factor": factor.value,
                "evaluation_questions": criteria.evaluation_questions
            }
        )

        # Analyze responses and determine score
        score, rationale, evidence_citations, confidence_level = await self._analyze_factor_responses(
            factor, persona_responses, criteria
        )

        # Determine primary persona perspective (highest confidence)
        primary_persona = self._determine_primary_persona_perspective(persona_responses)

        return FactorScore(
            factor=factor,
            score=score,
            rationale=rationale,
            evidence_citations=evidence_citations,
            confidence_level=confidence_level,
            persona_perspective=primary_persona
        )

    def _create_factor_evaluation_query(
        self,
        factor: CriticalSuccessFactor,
        model: GovernanceModel,
        criteria: EvaluationCriteria
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
        persona_responses: Dict[PersonaType, str],
        criteria: EvaluationCriteria
    ) -> Tuple[int, str, List[str], str]:
        """Analyze responses from all personas to determine factor score."""
        # Extract scores from responses
        scores = []
        rationales = []
        evidence_citations = []

        for persona_type, response in persona_responses.items():
            try:
                # Parse response to extract score and rationale
                score, rationale, citations = self._parse_persona_response(response)
                scores.append(score)
                rationales.append(rationale)
                evidence_citations.extend(citations)
            except Exception as e:
                logger.warning("Failed to parse persona response",
                             persona_type=persona_type.value,
                             error=str(e))

        if not scores:
            return 1, "No valid responses received", [], "very_low"

        # Calculate weighted average score
        overall_score = round(sum(scores) / len(scores))
        overall_score = max(1, min(5, overall_score))  # Clamp to 1-5 range

        # Combine rationales
        combined_rationale = self._combine_rationales(rationales, scores)

        # Determine confidence level
        confidence_level = self._determine_confidence_level(scores, len(persona_responses))

        return overall_score, combined_rationale, evidence_citations, confidence_level

    def _parse_persona_response(self, response: str) -> Tuple[int, str, List[str]]:
        """Parse persona response to extract score, rationale, and citations."""
        # This is a simplified implementation
        # In practice, this would use NLP or structured parsing

        # Look for score patterns
        import re
        score_match = re.search(r'score[:\s]*(\d+)', response.lower())
        score = int(score_match.group(1)) if score_match else 3

        # Extract rationale (everything after "rationale" or "reasoning")
        rationale_match = re.search(r'(?:rationale|reasoning)[:\s]*(.+?)(?:\n\n|\nEvidence|$)',
                                   response, re.DOTALL | re.IGNORECASE)
        rationale = rationale_match.group(1).strip() if rationale_match else response

        # Extract evidence citations
        citation_patterns = [
            r'evidence[:\s]*(.+?)(?:\n|$)',
            r'citation[:\s]*(.+?)(?:\n|$)',
            r'from transcripts[:\s]*(.+?)(?:\n|$)'
        ]

        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            citations.extend(matches)

        return score, rationale, citations

    def _combine_rationales(self, rationales: List[str], scores: List[int]) -> str:
        """Combine rationales from multiple personas."""
        if not rationales:
            return "No rationale provided"

        if len(rationales) == 1:
            return rationales[0]

        # Create weighted combination based on scores
        combined = "Combined Assessment:\n\n"

        for i, (rationale, score) in enumerate(zip(rationales, scores)):
            combined += f"Perspective {i+1} (Score: {score}): {rationale}\n\n"

        return combined.strip()

    def _determine_confidence_level(self, scores: List[int], response_count: int) -> str:
        """Determine confidence level based on score consistency."""
        if response_count == 0:
            return "very_low"

        # Calculate score variance
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)

        if variance <= 0.5 and response_count >= 3:
            return "high"
        elif variance <= 1.0 and response_count >= 2:
            return "medium"
        else:
            return "low"

    def _determine_primary_persona_perspective(
        self,
        persona_responses: Dict[PersonaType, str]
    ) -> PersonaType:
        """Determine primary persona perspective based on response quality."""
        # This is a simplified implementation
        # In practice, this would analyze response quality and confidence

        # For now, return the first persona
        return list(persona_responses.keys())[0]

    def _calculate_overall_score(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> float:
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

        return round(total_weighted_score / total_weight, 2) if total_weight > 0 else 0.0

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

    def _extract_key_risks(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> List[str]:
        """Extract key risks from factor scores."""
        risks = []

        for factor, score_data in factor_scores.items():
            if score_data.score <= 2:
                risks.append(f"Low score in {factor.value}: {score_data.rationale[:100]}...")

        return risks[:5]  # Limit to top 5 risks

    def _extract_key_benefits(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> List[str]:
        """Extract key benefits from factor scores."""
        benefits = []

        for factor, score_data in factor_scores.items():
            if score_data.score >= 4:
                benefits.append(f"Strong performance in {factor.value}: {score_data.rationale[:100]}...")

        return benefits[:5]  # Limit to top 5 benefits

    async def _generate_recommendations(self, evaluation: ModelEvaluation) -> List[str]:
        """Generate recommendations based on evaluation results."""
        recommendations = []

        # Recommendations based on low-scoring factors
        for factor, score_data in evaluation.factor_scores.items():
            if score_data.score <= 2:
                recommendations.append(f"Improve {factor.value}: {score_data.rationale[:100]}...")

        # General recommendations
        if evaluation.overall_score < 3:
            recommendations.append("Consider fundamental redesign of governance approach")
        elif evaluation.overall_score < 4:
            recommendations.append("Address key weaknesses before implementation")
        else:
            recommendations.append("Model shows promise with minor improvements needed")

        return recommendations[:10]  # Limit to top 10 recommendations

    def _load_evaluation_criteria(self) -> Dict[CriticalSuccessFactor, EvaluationCriteria]:
        """Load evaluation criteria for all critical success factors."""
        return {
            CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY: EvaluationCriteria(
                factor=CriticalSuccessFactor.COMMERCIAL_SUSTAINABILITY,
                description="The governance model demonstrates clear commercial viability and sustainable revenue streams",
                evaluation_questions=[
                    "Does the model provide clear commercial incentives for all participants?",
                    "Are there sustainable revenue streams that support long-term operation?",
                    "Is the cost structure reasonable and transparent?",
                    "Do participants have clear paths to profitability?"
                ],
                scoring_guidelines={
                    5: "Excellent commercial sustainability with clear incentives and sustainable revenue",
                    4: "Good commercial sustainability with minor gaps",
                    3: "Adequate commercial sustainability with some concerns",
                    2: "Poor commercial sustainability with significant gaps",
                    1: "Very poor commercial sustainability with fundamental flaws"
                },
                weight=1.2
            ),
            CriticalSuccessFactor.PROPORTIONALITY_AND_PROVEN_DEMAND: EvaluationCriteria(
                factor=CriticalSuccessFactor.PROPORTIONALITY_AND_PROVEN_DEMAND,
                description="The governance model is proportional to proven demand and avoids over-regulation",
                evaluation_questions=[
                    "Is the model proportional to actual market demand?",
                    "Are there clear indicators of proven consumer demand?",
                    "Does the model avoid unnecessary complexity or over-regulation?",
                    "Is there evidence of market readiness for this approach?"
                ],
                scoring_guidelines={
                    5: "Excellent proportionality with clear demand indicators",
                    4: "Good proportionality with minor demand concerns",
                    3: "Adequate proportionality with some demand uncertainty",
                    2: "Poor proportionality with significant demand gaps",
                    1: "Very poor proportionality with no proven demand"
                },
                weight=1.0
            ),
            CriticalSuccessFactor.SYMMETRICAL_GOVERNANCE: EvaluationCriteria(
                factor=CriticalSuccessFactor.SYMMETRICAL_GOVERNANCE,
                description="The governance model ensures balanced rights and obligations for all participants",
                evaluation_questions=[
                    "Are rights and obligations balanced across all participant types?",
                    "Is there fair representation in governance decisions?",
                    "Are liability frameworks symmetrical and enforceable?",
                    "Does the model avoid creating lopsided market dynamics?"
                ],
                scoring_guidelines={
                    5: "Excellent symmetrical governance with balanced rights and obligations",
                    4: "Good symmetrical governance with minor imbalances",
                    3: "Adequate symmetrical governance with some concerns",
                    2: "Poor symmetrical governance with significant imbalances",
                    1: "Very poor symmetrical governance with fundamental imbalances"
                },
                weight=1.1
            ),
            CriticalSuccessFactor.CROSS_SECTOR_INTEROPERABILITY: EvaluationCriteria(
                factor=CriticalSuccessFactor.CROSS_SECTOR_INTEROPERABILITY,
                description="The governance model enables cross-sector data sharing and interoperability",
                evaluation_questions=[
                    "Does the model enable cross-sector data sharing?",
                    "Are there clear interoperability standards and protocols?",
                    "Does the model avoid creating sector-specific silos?",
                    "Is there a path to unified cross-sector governance?"
                ],
                scoring_guidelines={
                    5: "Excellent cross-sector interoperability with unified approach",
                    4: "Good cross-sector interoperability with minor gaps",
                    3: "Adequate cross-sector interoperability with some limitations",
                    2: "Poor cross-sector interoperability with significant silos",
                    1: "Very poor cross-sector interoperability with no cross-sector capability"
                },
                weight=1.3
            ),
            CriticalSuccessFactor.EFFECTIVE_AND_STABLE_GOVERNANCE: EvaluationCriteria(
                factor=CriticalSuccessFactor.EFFECTIVE_AND_STABLE_GOVERNANCE,
                description="The governance model provides effective decision-making and long-term stability",
                evaluation_questions=[
                    "Are governance processes clear and efficient?",
                    "Is there effective dispute resolution and enforcement?",
                    "Does the model provide long-term stability and predictability?",
                    "Are there mechanisms for evolution and adaptation?"
                ],
                scoring_guidelines={
                    5: "Excellent governance effectiveness and stability",
                    4: "Good governance effectiveness with minor stability concerns",
                    3: "Adequate governance effectiveness with some stability issues",
                    2: "Poor governance effectiveness with significant stability problems",
                    1: "Very poor governance effectiveness with fundamental instability"
                },
                weight=1.0
            ),
            CriticalSuccessFactor.TECHNICAL_AND_FINANCIAL_FEASIBILITY: EvaluationCriteria(
                factor=CriticalSuccessFactor.TECHNICAL_AND_FINANCIAL_FEASIBILITY,
                description="The governance model is technically and financially feasible to implement",
                evaluation_questions=[
                    "Is the technical implementation feasible with current technology?",
                    "Are the financial requirements reasonable and achievable?",
                    "Is there a clear implementation roadmap?",
                    "Are there adequate resources and expertise available?"
                ],
                scoring_guidelines={
                    5: "Excellent technical and financial feasibility",
                    4: "Good technical and financial feasibility with minor concerns",
                    3: "Adequate technical and financial feasibility with some challenges",
                    2: "Poor technical and financial feasibility with significant barriers",
                    1: "Very poor technical and financial feasibility with fundamental obstacles"
                },
                weight=0.9
            )
        }
```

### 4.2 Report Generation

**File**: `src/ai_agent/core/evaluation/report_generator.py`

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

from ai_agent.core.evaluation.governance_evaluator import ModelEvaluation, FactorScore, CriticalSuccessFactor

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

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()

    def generate_markdown_report(self, evaluation: ModelEvaluation) -> str:
        """Generate a markdown-formatted evaluation report."""
        report = []

        # Header
        report.append(f"# Governance Model Evaluation Report")
        report.append(f"**Model:** {evaluation.model.name}")
        report.append(f"**Evaluation Date:** {evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
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
        report.append(f"*Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")

        return "\n".join(report)

    def _generate_scores_table(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> str:
        """Generate markdown table of factor scores."""
        table = []
        table.append("| Factor | Score | Confidence | Primary Perspective |")
        table.append("|--------|-------|------------|---------------------|")

        for factor, score_data in factor_scores.items():
            table.append(f"| {factor.value} | {score_data.score}/5 | {score_data.confidence_level} | {score_data.persona_perspective.value} |")

        return "\n".join(table)

    def _generate_factor_analysis(self, factor: CriticalSuccessFactor, score_data: FactorScore) -> str:
        """Generate detailed analysis for a specific factor."""
        analysis = []
        analysis.append(f"### {factor.value} - Score: {score_data.score}/5")
        analysis.append("")

        # Rationale
        if self.config.include_detailed_rationales:
            rationale = score_data.rationale
            if len(rationale) > self.config.max_rationale_length:
                rationale = rationale[:self.config.max_rationale_length] + "..."
            analysis.append(f"**Rationale:** {rationale}")
            analysis.append("")

        # Evidence Citations
        if score_data.evidence_citations and self.config.include_evidence_citations:
            analysis.append("**Evidence Citations:**")
            for i, citation in enumerate(score_data.evidence_citations[:5], 1):  # Limit to 5
                analysis.append(f"{i}. {citation}")
            analysis.append("")

        return "\n".join(analysis)

    def _generate_evidence_citations(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> str:
        """Generate comprehensive evidence citations section."""
        citations = []

        for factor, score_data in factor_scores.items():
            if score_data.evidence_citations:
                citations.append(f"**{factor.value}:**")
                for i, citation in enumerate(score_data.evidence_citations, 1):
                    citations.append(f"{i}. {citation}")
                citations.append("")

        return "\n".join(citations) if citations else "No evidence citations available."

    def _generate_persona_perspectives(self, factor_scores: Dict[CriticalSuccessFactor, FactorScore]) -> str:
        """Generate persona perspectives section."""
        perspectives = []

        # Group by persona
        persona_groups = {}
        for factor, score_data in factor_scores.items():
            persona = score_data.persona_perspective
            if persona not in persona_groups:
                persona_groups[persona] = []
            persona_groups[persona].append((factor, score_data))

        for persona, factors in persona_groups.items():
            perspectives.append(f"### {persona.value} Perspective")
            perspectives.append("")

            for factor, score_data in factors:
                perspectives.append(f"**{factor.value}:** {score_data.score}/5 - {score_data.rationale[:200]}...")
                perspectives.append("")

        return "\n".join(perspectives)

    def generate_json_report(self, evaluation: ModelEvaluation) -> Dict[str, any]:
        """Generate a JSON-formatted evaluation report."""
        return {
            "evaluation_id": str(evaluation.id),
            "model": {
                "id": str(evaluation.model.id),
                "name": evaluation.model.name,
                "description": evaluation.model.description,
                "model_type": evaluation.model.model_type,
                "key_features": evaluation.model.key_features,
                "proposed_by": evaluation.model.proposed_by
            },
            "overall_score": evaluation.overall_score,
            "overall_assessment": evaluation.overall_assessment,
            "factor_scores": {
                factor.value: {
                    "score": score_data.score,
                    "rationale": score_data.rationale,
                    "evidence_citations": score_data.evidence_citations,
                    "confidence_level": score_data.confidence_level,
                    "persona_perspective": score_data.persona_perspective.value
                }
                for factor, score_data in evaluation.factor_scores.items()
            },
            "key_risks": evaluation.key_risks,
            "key_benefits": evaluation.key_benefits,
            "recommendations": evaluation.recommendations,
            "evaluation_status": evaluation.evaluation_status.value,
            "created_at": evaluation.created_at.isoformat(),
            "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
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
```

### 4.3 API Endpoints

**File**: `src/ai_agent/api/v1/governance_evaluation.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
import structlog

from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
    ModelEvaluation,
    CriticalSuccessFactor
)
from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.evaluation.report_generator import GovernanceReportGenerator, ReportConfig

logger = structlog.get_logger()
router = APIRouter(prefix="/governance-evaluation", tags=["governance-evaluation"])

class GovernanceModelRequest(BaseModel):
    """Request model for governance model evaluation."""
    name: str = Field(..., description="Name of the governance model")
    description: str = Field(..., description="Description of the governance model")
    model_type: str = Field(..., description="Type of governance model")
    key_features: List[str] = Field(..., description="Key features of the model")
    proposed_by: str = Field(..., description="Who proposed this model")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class EvaluationRequest(BaseModel):
    """Request model for evaluation execution."""
    model: GovernanceModelRequest
    include_personas: Optional[List[str]] = Field(None, description="Persona types to include")
    report_config: Optional[Dict[str, Any]] = Field(None, description="Report generation configuration")

class EvaluationResponse(BaseModel):
    """Response model for evaluation results."""
    evaluation_id: str
    model_name: str
    overall_score: float
    evaluation_status: str
    report_url: Optional[str] = None

# Dependency injection
def get_governance_evaluator() -> GovernanceEvaluator:
    """Get governance evaluator instance."""
    # This would be injected from the application context
    pass

def get_report_generator() -> GovernanceReportGenerator:
    """Get report generator instance."""
    # This would be injected from the application context
    pass

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_governance_model(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator)
) -> EvaluationResponse:
    """Evaluate a governance model using synthetic agents."""
    try:
        # Convert request to governance model
        model = GovernanceModel(
            name=request.model.name,
            description=request.model.description,
            model_type=request.model.model_type,
            key_features=request.model.key_features,
            proposed_by=request.model.proposed_by,
            metadata=request.model.metadata
        )

        # Convert persona types
        include_personas = None
        if request.include_personas:
            include_personas = [CriticalSuccessFactor(p) for p in request.include_personas]

        # Execute evaluation
        evaluation = await evaluator.evaluate_governance_model(model, include_personas)

        # Generate report in background
        background_tasks.add_task(generate_evaluation_report, evaluation)

        return EvaluationResponse(
            evaluation_id=str(evaluation.id),
            model_name=evaluation.model.name,
            overall_score=evaluation.overall_score,
            evaluation_status=evaluation.evaluation_status.value,
            report_url=f"/governance-evaluation/reports/{evaluation.id}"
        )

    except Exception as e:
        logger.error("Governance model evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Evaluation failed")

@router.get("/reports/{evaluation_id}")
async def get_evaluation_report(
    evaluation_id: UUID,
    format: str = "markdown",
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator),
    report_generator: GovernanceReportGenerator = Depends(get_report_generator)
) -> Dict[str, Any]:
    """Get evaluation report in specified format."""
    try:
        # Get evaluation (this would be from a database in practice)
        evaluation = evaluator.active_evaluations.get(evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        if format.lower() == "json":
            return report_generator.generate_json_report(evaluation)
        elif format.lower() == "summary":
            return {"report": report_generator.generate_summary_report(evaluation)}
        else:  # markdown
            return {"report": report_generator.generate_markdown_report(evaluation)}

    except Exception as e:
        logger.error("Failed to get evaluation report", evaluation_id=str(evaluation_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate report")

@router.get("/evaluations")
async def list_evaluations(
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator)
) -> List[Dict[str, Any]]:
    """List all evaluations."""
    try:
        evaluations = []
        for evaluation in evaluator.active_evaluations.values():
            evaluations.append({
                "evaluation_id": str(evaluation.id),
                "model_name": evaluation.model.name,
                "overall_score": evaluation.overall_score,
                "evaluation_status": evaluation.evaluation_status.value,
                "created_at": evaluation.created_at.isoformat()
            })

        return evaluations

    except Exception as e:
        logger.error("Failed to list evaluations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list evaluations")

@router.get("/criteria")
async def get_evaluation_criteria() -> Dict[str, Any]:
    """Get evaluation criteria for all critical success factors."""
    try:
        criteria = {}
        for factor in CriticalSuccessFactor:
            criteria[factor.value] = {
                "description": "Description of the factor",
                "evaluation_questions": [
                    "Sample question 1",
                    "Sample question 2"
                ],
                "scoring_guidelines": {
                    "5": "Excellent",
                    "4": "Good",
                    "3": "Adequate",
                    "2": "Poor",
                    "1": "Very Poor"
                }
            }

        return criteria

    except Exception as e:
        logger.error("Failed to get evaluation criteria", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get criteria")

async def generate_evaluation_report(evaluation: ModelEvaluation) -> None:
    """Background task to generate evaluation report."""
    try:
        # This would save the report to storage
        logger.info("Generating evaluation report", evaluation_id=str(evaluation.id))
        # Implementation would depend on storage backend
    except Exception as e:
        logger.error("Failed to generate evaluation report", evaluation_id=str(evaluation.id), error=str(e))
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_governance_evaluation.py`
- Test evaluation criteria loading
- Test factor scoring logic
- Test report generation
- Test overall score calculation

### Integration Tests
- **File**: `tests/integration/test_governance_evaluation.py`
- Test end-to-end evaluation workflow
- Test multi-agent coordination
- Test report generation with real data

### Performance Tests
- **File**: `tests/performance/test_governance_evaluation.py`
- Test evaluation performance with multiple models
- Test concurrent evaluation handling
- Test report generation performance

## Success Criteria

1. **Evaluation Accuracy**: >90% consistency in scoring across multiple runs
2. **Report Quality**: Comprehensive, well-structured reports with evidence citations
3. **Performance**: <30 seconds for complete evaluation of a governance model
4. **Multi-Agent Coordination**: Successful coordination of all three persona agents
5. **Evidence Integration**: Proper integration of evidence from stakeholder views tool

## Dependencies

This phase depends on:
- Phase 1: Transcript ingestion system
- Phase 2: Stakeholder views MCP server
- Phase 3: Synthetic agent system
- Existing LLM infrastructure

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 5: API endpoints and web interface
- Phase 6: Configuration and deployment
- Phase 7: Testing and validation

The governance evaluation framework must be fully functional and tested before proceeding to Phase 5.
