"""Unit tests for configuration management."""

import pytest
import os
from unittest.mock import patch
from pathlib import Path

from ai_agent.config.synthetic_agents import (
    SyntheticAgentConfig,
    TranscriptProcessingConfig,
    MCPConfig,
    AgentConfig,
    EvaluationConfig,
    APIConfig,
    MonitoringConfig,
    DatabaseConfig,
    Environment,
    load_config,
    get_config,
)


class TestTranscriptProcessingConfig:
    """Test transcript processing configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TranscriptProcessingConfig()

        assert config.transcript_directory == Path("docs/transcripts")
        assert config.min_segment_length == 50
        assert config.max_segment_length == 2000
        assert config.embedding_model_name == "all-MiniLM-L6-v2"
        assert config.embedding_dimension == 384
        assert config.similarity_threshold == 0.7
        assert config.enable_parallel_processing is True

    def test_stakeholder_group_mappings(self):
        """Test stakeholder group mappings are initialized."""
        config = TranscriptProcessingConfig()

        assert config.stakeholder_group_mappings is not None
        assert (
            "transcript_001_bank_rep_gov_only.docx" in config.stakeholder_group_mappings
        )
        assert (
            config.stakeholder_group_mappings["transcript_001_bank_rep_gov_only.docx"]
            == "BANK_REP"
        )

    def test_source_mappings(self):
        """Test source mappings are initialized."""
        config = TranscriptProcessingConfig()

        assert config.source_mappings is not None
        assert "transcript_001_bank_rep_gov_only.docx" in config.source_mappings
        assert (
            config.source_mappings["transcript_001_bank_rep_gov_only.docx"]
            == "SANTANDER"
        )


class TestAgentConfig:
    """Test agent configuration."""

    def test_default_values(self):
        """Test default agent configuration values."""
        config = AgentConfig()

        assert config.llm_provider == "anthropic"
        assert config.llm_temperature == 0.7
        assert config.llm_max_tokens == 1000
        assert config.evidence_cache_size == 1000
        assert config.evidence_cache_ttl == 3600
        assert config.enable_evidence_caching is True

    def test_persona_system_prompts(self):
        """Test persona system prompts are initialized."""
        config = AgentConfig()

        assert config.persona_system_prompts is not None
        assert "BANK_REP" in config.persona_system_prompts
        assert "TRADE_BODY_REP" in config.persona_system_prompts
        assert "PAYMENTS_ECOSYSTEM_REP" in config.persona_system_prompts


class TestSyntheticAgentConfig:
    """Test main configuration class."""

    def test_default_initialization(self):
        """Test default configuration initialization."""
        config = SyntheticAgentConfig()

        assert config.environment == Environment.DEVELOPMENT
        assert isinstance(config.transcript_processing, TranscriptProcessingConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert isinstance(config.agents, AgentConfig)
        assert isinstance(config.evaluation, EvaluationConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert isinstance(config.database, DatabaseConfig)

    def test_environment_enum(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"


class TestConfigurationLoading:
    """Test configuration loading functions."""

    def test_load_config_default(self):
        """Test loading configuration with default environment."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            assert config.environment == Environment.DEVELOPMENT

    def test_load_config_environment_override(self):
        """Test loading configuration with environment override."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = load_config()
            assert config.environment == Environment.PRODUCTION

    def test_load_config_environment_variables(self):
        """Test configuration loading with environment variables."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "DATABASE_HOST": "test-host",
            "DATABASE_PORT": "5433",
            "DATABASE_NAME": "test_db",
            "DATABASE_USERNAME": "test_user",
            "DATABASE_PASSWORD": "test_pass",
            "LLM_PROVIDER": "openai",
            "LLM_TEMPERATURE": "0.5",
            "LLM_MAX_TOKENS": "2000",
            "LOG_LEVEL": "DEBUG",
            "ENABLE_METRICS": "false",
            "ENABLE_TRACING": "false",
            "TRANSCRIPT_DIRECTORY": "/custom/transcripts",
            "EMBEDDING_DIMENSION": "512",
            "EMBEDDING_MODEL_NAME": "custom-model",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()

            assert config.environment == Environment.STAGING
            assert config.database.host == "test-host"
            assert config.database.port == 5433
            assert config.database.database == "test_db"
            assert config.database.username == "test_user"
            assert config.database.password == "test_pass"
            assert config.agents.llm_provider == "openai"
            assert config.agents.llm_temperature == 0.5
            assert config.agents.llm_max_tokens == 2000
            assert config.monitoring.log_level == "DEBUG"
            assert config.monitoring.enable_metrics is False
            assert config.monitoring.enable_tracing is False
            assert config.transcript_processing.transcript_directory == Path(
                "/custom/transcripts"
            )
            assert config.transcript_processing.embedding_dimension == 512
            assert config.transcript_processing.embedding_model_name == "custom-model"

    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        assert isinstance(config, SyntheticAgentConfig)

    def test_boolean_environment_variables(self):
        """Test boolean environment variable parsing."""
        with patch.dict(
            os.environ,
            {"ENABLE_METRICS": "true", "ENABLE_TRACING": "false"},
            clear=True,
        ):
            config = load_config()
            assert config.monitoring.enable_metrics is True
            assert config.monitoring.enable_tracing is False

    def test_numeric_environment_variables(self):
        """Test numeric environment variable parsing."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_PORT": "5433",
                "LLM_TEMPERATURE": "0.8",
                "LLM_MAX_TOKENS": "1500",
                "EMBEDDING_DIMENSION": "256",
            },
            clear=True,
        ):
            config = load_config()
            assert config.database.port == 5433
            assert config.agents.llm_temperature == 0.8
            assert config.agents.llm_max_tokens == 1500
            assert config.transcript_processing.embedding_dimension == 256


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_invalid_environment(self):
        """Test handling of invalid environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}, clear=True):
            with pytest.raises(ValueError):
                load_config()

    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric values."""
        with patch.dict(os.environ, {"DATABASE_PORT": "invalid"}, clear=True):
            with pytest.raises(ValueError):
                load_config()

    def test_invalid_float_values(self):
        """Test handling of invalid float values."""
        with patch.dict(os.environ, {"LLM_TEMPERATURE": "invalid"}, clear=True):
            with pytest.raises(ValueError):
                load_config()
