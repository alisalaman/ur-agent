"""
Unit tests for API validation functions.
"""

import pytest

from ai_agent.api.v1.governance_evaluation import (
    _validate_and_sanitize_request,
    _sanitize_text,
    _sanitize_metadata,
    _validate_persona_types,
    InputValidationError,
    EvaluationRequest,
    GovernanceModelRequest,
)
from ai_agent.core.agents.synthetic_representative import PersonaType


class TestInputValidation:
    """Test input validation and sanitization functions."""

    def test_validate_and_sanitize_request_valid(self):
        """Test validation with valid request."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="A test model",
                model_type="Test",
                key_features=["feature1", "feature2"],
                proposed_by="Test User",
                metadata={"key": "value"},
            ),
            include_personas=["BANK_REPRESENTATIVE"],
            report_config={"format": "markdown"},
        )

        validated = _validate_and_sanitize_request(request)

        assert validated.model.name == "Test Model"
        assert validated.model.description == "A test model"
        assert len(validated.model.key_features) == 2
        assert validated.include_personas == ["BANK_REPRESENTATIVE"]

    def test_validate_and_sanitize_request_empty_name(self):
        """Test validation with empty model name."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="",
                description="A test model",
                model_type="Test",
                key_features=["feature1"],
                proposed_by="Test User",
            )
        )

        with pytest.raises(InputValidationError, match="Model name cannot be empty"):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_name_too_long(self):
        """Test validation with name too long."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="x" * 201,  # Too long
                description="A test model",
                model_type="Test",
                key_features=["feature1"],
                proposed_by="Test User",
            )
        )

        with pytest.raises(InputValidationError, match="Model name too long"):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_empty_description(self):
        """Test validation with empty description."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="",
                model_type="Test",
                key_features=["feature1"],
                proposed_by="Test User",
            )
        )

        with pytest.raises(
            InputValidationError, match="Model description cannot be empty"
        ):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_no_key_features(self):
        """Test validation with no key features."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="A test model",
                model_type="Test",
                key_features=[],
                proposed_by="Test User",
            )
        )

        with pytest.raises(
            InputValidationError, match="At least one key feature is required"
        ):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_too_many_features(self):
        """Test validation with too many key features."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="A test model",
                model_type="Test",
                key_features=[f"feature{i}" for i in range(51)],  # Too many
                proposed_by="Test User",
            )
        )

        with pytest.raises(InputValidationError, match="Too many key features"):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_feature_too_long(self):
        """Test validation with key feature too long."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="A test model",
                model_type="Test",
                key_features=["x" * 201],  # Too long
                proposed_by="Test User",
            )
        )

        with pytest.raises(InputValidationError, match="Key feature too long"):
            _validate_and_sanitize_request(request)

    def test_validate_and_sanitize_request_empty_proposed_by(self):
        """Test validation with empty proposed_by."""
        request = EvaluationRequest(
            model=GovernanceModelRequest(
                name="Test Model",
                description="A test model",
                model_type="Test",
                key_features=["feature1"],
                proposed_by="",
            )
        )

        with pytest.raises(
            InputValidationError, match="Proposed by field cannot be empty"
        ):
            _validate_and_sanitize_request(request)


class TestTextSanitization:
    """Test text sanitization functions."""

    def test_sanitize_text_normal(self):
        """Test sanitization of normal text."""
        text = "Normal text with <b>HTML</b> tags"
        sanitized = _sanitize_text(text, max_length=100)

        assert sanitized == "Normal text with &lt;b&gt;HTML&lt;/b&gt; tags"
        assert len(sanitized) <= 100

    def test_sanitize_text_with_script(self):
        """Test sanitization of text with script tags."""
        text = "Text with <script>alert('xss')</script> dangerous content"
        sanitized = _sanitize_text(text, max_length=100)

        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Text with" in sanitized

    def test_sanitize_text_with_javascript(self):
        """Test sanitization of text with javascript: protocol."""
        text = "Link: javascript:alert('xss')"
        sanitized = _sanitize_text(text, max_length=100)

        assert "javascript:" not in sanitized
        assert "Link:" in sanitized

    def test_sanitize_text_length_limit(self):
        """Test sanitization with length limit."""
        text = "x" * 150
        sanitized = _sanitize_text(text, max_length=100)

        assert len(sanitized) == 100
        assert sanitized == "x" * 100

    def test_sanitize_text_empty(self):
        """Test sanitization of empty text."""
        sanitized = _sanitize_text("", max_length=100)
        assert sanitized == ""

    def test_sanitize_text_whitespace(self):
        """Test sanitization of whitespace-only text."""
        sanitized = _sanitize_text("   ", max_length=100)
        assert sanitized == ""


class TestMetadataSanitization:
    """Test metadata sanitization functions."""

    def test_sanitize_metadata_normal(self):
        """Test sanitization of normal metadata."""
        metadata = {
            "key1": "value1",
            "key2": 123,
            "key3": True,
            "key4": ["item1", "item2"],
        }

        sanitized = _sanitize_metadata(metadata)

        assert sanitized["key1"] == "value1"
        assert sanitized["key2"] == 123
        assert sanitized["key3"]
        assert sanitized["key4"] == ["item1", "item2"]

    def test_sanitize_metadata_with_html(self):
        """Test sanitization of metadata with HTML."""
        metadata = {
            "html_key": "<script>alert('xss')</script>",
            "normal_key": "normal value",
        }

        sanitized = _sanitize_metadata(metadata)

        assert "<script>" not in sanitized["html_key"]
        assert sanitized["normal_key"] == "normal value"

    def test_sanitize_metadata_long_list(self):
        """Test sanitization of metadata with long list."""
        metadata = {"long_list": [f"item{i}" for i in range(20)]}  # More than 10 items

        sanitized = _sanitize_metadata(metadata)

        assert len(sanitized["long_list"]) == 10  # Should be limited to 10

    def test_sanitize_metadata_empty(self):
        """Test sanitization of empty metadata."""
        sanitized = _sanitize_metadata({})
        assert sanitized == {}

    def test_sanitize_metadata_none(self):
        """Test sanitization of None metadata."""
        sanitized = _sanitize_metadata(None)
        assert sanitized == {}


class TestPersonaTypeValidation:
    """Test persona type validation functions."""

    def test_validate_persona_types_valid(self):
        """Test validation with valid persona types."""
        persona_types = ["BankRep", "TradeBodyRep"]
        validated = _validate_persona_types(persona_types)

        assert len(validated) == 2
        assert PersonaType.BANK_REP in validated
        assert PersonaType.TRADE_BODY_REP in validated

    def test_validate_persona_types_invalid(self):
        """Test validation with invalid persona type."""
        persona_types = ["INVALID_PERSONA"]

        with pytest.raises(InputValidationError, match="Invalid persona type"):
            _validate_persona_types(persona_types)

    def test_validate_persona_types_mixed(self):
        """Test validation with mixed valid and invalid types."""
        persona_types = ["BANK_REPRESENTATIVE", "INVALID_PERSONA"]

        with pytest.raises(InputValidationError, match="Invalid persona type"):
            _validate_persona_types(persona_types)

    def test_validate_persona_types_empty(self):
        """Test validation with empty persona types."""
        with pytest.raises(
            InputValidationError, match="At least one valid persona type is required"
        ):
            _validate_persona_types([])

    def test_validate_persona_types_all_valid(self):
        """Test validation with all valid persona types."""
        persona_types = [persona.value for persona in PersonaType]
        validated = _validate_persona_types(persona_types)

        assert len(validated) == len(PersonaType)
        for persona_type in PersonaType:
            assert persona_type in validated
