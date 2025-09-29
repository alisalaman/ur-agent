"""
Data models for governance evaluation framework.
"""

from typing import Any
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime


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
    key_features: list[str] = field(default_factory=list)
    proposed_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationCriteria:
    """Criteria for evaluating governance models."""

    factor: CriticalSuccessFactor
    description: str
    evaluation_questions: list[str]
    scoring_guidelines: dict[int, str]  # score -> description
    weight: float = 1.0  # Relative weight in overall scoring


@dataclass
class FactorScore:
    """Score for a specific critical success factor."""

    factor: CriticalSuccessFactor
    score: int  # 1-5 scale
    rationale: str
    evidence_citations: list[str]
    confidence_level: str  # high, medium, low
    persona_perspective: str  # PersonaType as string to avoid circular import
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelEvaluation:
    """Complete evaluation of a governance model."""

    model: GovernanceModel
    factor_scores: dict[CriticalSuccessFactor, FactorScore]
    overall_score: float
    overall_assessment: str
    key_risks: list[str]
    key_benefits: list[str]
    recommendations: list[str]
    evaluation_status: EvaluationStatus
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Custom exceptions for better error handling
class PersonaServiceError(Exception):
    """Raised when persona service encounters an error."""

    pass


class EvaluationCriteriaError(Exception):
    """Raised when evaluation criteria encounters an error."""

    pass
