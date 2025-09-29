from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Any
from pydantic import BaseModel, Field
from uuid import UUID
import structlog
import re
import html

from ai_agent.core.evaluation.governance_evaluator import (
    GovernanceEvaluator,
    GovernanceModel,
    ModelEvaluation,
    CriticalSuccessFactor,
)
from ai_agent.core.agents.synthetic_representative import PersonaType
from ai_agent.core.evaluation.report_generator import (
    GovernanceReportGenerator,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/governance-evaluation", tags=["governance-evaluation"])


class InputValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


# Custom exceptions for better error handling
class PersonaServiceError(Exception):
    """Raised when persona service encounters an error."""

    pass


class EvaluationCriteriaError(Exception):
    """Raised when evaluation criteria encounters an error."""

    pass


class GovernanceModelRequest(BaseModel):
    """Request model for governance model evaluation."""

    name: str = Field(..., description="Name of the governance model")
    description: str = Field(..., description="Description of the governance model")
    model_type: str = Field(..., description="Type of governance model")
    key_features: list[str] = Field(..., description="Key features of the model")
    proposed_by: str = Field(..., description="Who proposed this model")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EvaluationRequest(BaseModel):
    """Request model for evaluation execution."""

    model: GovernanceModelRequest
    include_personas: list[str] | None = Field(
        None, description="Persona types to include"
    )
    report_config: dict[str, Any] | None = Field(
        None, description="Report generation configuration"
    )


class EvaluationResponse(BaseModel):
    """Response model for evaluation results."""

    evaluation_id: str
    model_name: str
    overall_score: float
    evaluation_status: str
    report_url: str | None = None


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
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator),
) -> EvaluationResponse:
    """Evaluate a governance model using synthetic agents."""
    try:
        # Validate and sanitize input
        validated_request = _validate_and_sanitize_request(request)

        # Convert request to governance model
        model = GovernanceModel(
            name=validated_request.model.name,
            description=validated_request.model.description,
            model_type=validated_request.model.model_type,
            key_features=validated_request.model.key_features,
            proposed_by=validated_request.model.proposed_by,
            metadata=validated_request.model.metadata,
        )

        # Convert persona types with validation
        include_personas = None
        if validated_request.include_personas:
            include_personas = _validate_persona_types(
                validated_request.include_personas
            )

        # Execute evaluation
        evaluation = await evaluator.evaluate_governance_model(model, include_personas)

        # Generate report in background
        background_tasks.add_task(generate_evaluation_report, evaluation)

        return EvaluationResponse(
            evaluation_id=str(evaluation.id),
            model_name=evaluation.model.name,
            overall_score=evaluation.overall_score,
            evaluation_status=evaluation.evaluation_status.value,
            report_url=f"/governance-evaluation/reports/{evaluation.id}",
        )

    except InputValidationError as e:
        logger.error("Input validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except PersonaServiceError as e:
        logger.error("Persona service failed during evaluation", error=str(e))
        raise HTTPException(status_code=503, detail="Persona service unavailable")
    except EvaluationCriteriaError as e:
        logger.error("Evaluation criteria error", error=str(e))
        raise HTTPException(status_code=500, detail="Evaluation criteria error")
    except Exception as e:
        logger.error("Governance model evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Evaluation failed")


@router.get("/reports/{evaluation_id}")
async def get_evaluation_report(
    evaluation_id: UUID,
    format: str = "markdown",
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator),
    report_generator: GovernanceReportGenerator = Depends(get_report_generator),
) -> dict[str, Any]:
    """Get evaluation report in specified format."""
    try:
        # Get evaluation from storage
        evaluation = evaluator.evaluation_storage.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        if format.lower() == "json":
            return {"report": report_generator.generate_json_report(evaluation)}
        elif format.lower() == "summary":
            return {"report": report_generator.generate_summary_report(evaluation)}
        else:  # markdown
            return {"report": report_generator.generate_markdown_report(evaluation)}

    except Exception as e:
        logger.error(
            "Failed to get evaluation report",
            evaluation_id=str(evaluation_id),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/evaluations")
async def list_evaluations(
    evaluator: GovernanceEvaluator = Depends(get_governance_evaluator),
) -> list[dict[str, Any]]:
    """List all evaluations."""
    try:
        evaluations = evaluator.evaluation_storage.list_evaluations()
        return [
            {
                "evaluation_id": str(evaluation.id),
                "model_name": evaluation.model.name,
                "overall_score": evaluation.overall_score,
                "evaluation_status": evaluation.evaluation_status.value,
                "created_at": evaluation.created_at.isoformat(),
            }
            for evaluation in evaluations
        ]

    except Exception as e:
        logger.error("Failed to list evaluations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list evaluations")


@router.get("/criteria")
async def get_evaluation_criteria() -> dict[str, Any]:
    """Get evaluation criteria for all critical success factors."""
    try:
        criteria = {}
        for factor in CriticalSuccessFactor:
            criteria[factor.value] = {
                "description": "Description of the factor",
                "evaluation_questions": ["Sample question 1", "Sample question 2"],
                "scoring_guidelines": {
                    "5": "Excellent",
                    "4": "Good",
                    "3": "Adequate",
                    "2": "Poor",
                    "1": "Very Poor",
                },
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
        logger.error(
            "Failed to generate evaluation report",
            evaluation_id=str(evaluation.id),
            error=str(e),
        )


def _validate_and_sanitize_request(request: EvaluationRequest) -> EvaluationRequest:
    """Validate and sanitize the evaluation request."""
    # Validate model name
    if not request.model.name or len(request.model.name.strip()) == 0:
        raise InputValidationError("Model name cannot be empty")

    if len(request.model.name) > 200:
        raise InputValidationError("Model name too long (max 200 characters)")

    # Validate description
    if not request.model.description or len(request.model.description.strip()) == 0:
        raise InputValidationError("Model description cannot be empty")

    if len(request.model.description) > 1000:
        raise InputValidationError("Model description too long (max 1000 characters)")

    # Validate key features
    if not request.model.key_features:
        raise InputValidationError("At least one key feature is required")

    if len(request.model.key_features) > 50:
        raise InputValidationError("Too many key features (max 50)")

    for feature in request.model.key_features:
        if len(feature) > 200:
            raise InputValidationError("Key feature too long (max 200 characters)")

    # Validate proposed_by
    if not request.model.proposed_by or len(request.model.proposed_by.strip()) == 0:
        raise InputValidationError("Proposed by field cannot be empty")

    if len(request.model.proposed_by) > 100:
        raise InputValidationError("Proposed by field too long (max 100 characters)")

    # Sanitize input
    sanitized_model = GovernanceModelRequest(
        name=_sanitize_text(request.model.name, max_length=200),
        description=_sanitize_text(request.model.description, max_length=1000),
        model_type=_sanitize_text(request.model.model_type, max_length=50),
        key_features=[
            _sanitize_text(feature, max_length=200)
            for feature in request.model.key_features
        ],
        proposed_by=_sanitize_text(request.model.proposed_by, max_length=100),
        metadata=_sanitize_metadata(request.model.metadata),
    )

    return EvaluationRequest(
        model=sanitized_model,
        include_personas=request.include_personas,
        report_config=request.report_config,
    )


def _sanitize_text(text: str, max_length: int) -> str:
    """Sanitize text input by escaping HTML and limiting length."""
    if not text:
        return ""

    # Strip whitespace and limit length
    sanitized = text.strip()[:max_length]

    # Remove any potential script tags or dangerous patterns first
    sanitized = re.sub(
        r"<script.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)

    # Escape HTML characters
    sanitized = html.escape(sanitized)

    return sanitized


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Sanitize metadata dictionary."""
    if not metadata:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        # Sanitize key
        sanitized_key = _sanitize_text(str(key), max_length=50)
        if not sanitized_key:
            continue

        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[sanitized_key] = _sanitize_text(value, max_length=500)
        elif isinstance(value, int | float | bool):
            sanitized[sanitized_key] = value
        elif isinstance(value, list):
            # Limit list size and sanitize string elements
            sanitized[sanitized_key] = [
                (
                    _sanitize_text(str(item), max_length=200)
                    if isinstance(item, str)
                    else item
                )
                for item in value[:10]  # Limit to 10 items
            ]
        else:
            # Convert other types to string and sanitize
            sanitized[sanitized_key] = _sanitize_text(str(value), max_length=500)

    return sanitized


def _validate_persona_types(persona_types: list[str]) -> list[PersonaType]:
    """Validate and convert persona type strings to PersonaType enum."""
    from ai_agent.core.agents.synthetic_representative import PersonaType

    valid_personas = []
    for persona_str in persona_types:
        try:
            persona_type = PersonaType(persona_str)
            valid_personas.append(persona_type)
        except ValueError:
            raise InputValidationError(f"Invalid persona type: {persona_str}")

    if not valid_personas:
        raise InputValidationError("At least one valid persona type is required")

    return valid_personas
