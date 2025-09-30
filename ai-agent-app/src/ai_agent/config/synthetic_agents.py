from dataclasses import dataclass
from pathlib import Path
import os
from enum import Enum


class Environment(str, Enum):
    """Deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class TranscriptProcessingConfig:
    """Configuration for transcript processing."""

    transcript_directory: Path = Path("docs/transcripts")
    min_segment_length: int = 50
    max_segment_length: int = 2000
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    default_search_limit: int = 10
    max_search_limit: int = 100
    similarity_threshold: float = 0.7
    processing_batch_size: int = 10
    enable_parallel_processing: bool = True
    stakeholder_group_mappings: dict[str, str] | None = None
    source_mappings: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.stakeholder_group_mappings is None:
            self.stakeholder_group_mappings = {
                "transcript_001_bank_rep_gov_only.docx": "BANK_REP",
                "transcript_002_trade_body_rep_mixed.docx": "TRADE_BODY_REP",
                "transcript_003_payments_ecosystem_rep_gov_only.docx": "PAYMENTS_ECOSYSTEM_REP",
                "transcript_004_bank_rep_mixed_gov.docx": "BANK_REP",
                "transcript_005_bank_rep_tech_gov.docx": "BANK_REP",
                "transcript_006_bank_rep_gov_only.docx": "BANK_REP",
                "transcript_007_bank_rep_mixed_gov.docx": "BANK_REP",
            }
        if self.source_mappings is None:
            self.source_mappings = {
                "transcript_001_bank_rep_gov_only.docx": "SANTANDER",
                "transcript_002_trade_body_rep_mixed.docx": "SANTANDER",
                "transcript_003_payments_ecosystem_rep_gov_only.docx": "SANTANDER",
                "transcript_004_bank_rep_mixed_gov.docx": "SANTANDER",
                "transcript_005_bank_rep_tech_gov.docx": "SANTANDER",
                "transcript_006_bank_rep_gov_only.docx": "SANTANDER",
                "transcript_007_bank_rep_mixed_gov.docx": "SANTANDER",
            }


@dataclass
class MCPConfig:
    """Configuration for MCP servers."""

    stakeholder_views_server_name: str = "stakeholder-views-server"
    stakeholder_views_server_description: str = (
        "MCP server for querying stakeholder views from transcripts"
    )
    server_startup_timeout: int = 30
    server_health_check_interval: int = 30
    max_retry_attempts: int = 3
    retry_delay: int = 5
    enable_auto_restart: bool = True


@dataclass
class AgentConfig:
    """Configuration for synthetic agents."""

    llm_provider: str = "anthropic"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    evidence_cache_size: int = 1000
    evidence_cache_ttl: int = 3600  # 1 hour
    max_conversation_history: int = 50
    enable_evidence_caching: bool = True
    persona_system_prompts: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.persona_system_prompts is None:
            self.persona_system_prompts = {
                "BANK_REP": "You are a bank representative with expertise in financial services and regulatory compliance.",
                "TRADE_BODY_REP": "You are a trade body representative advocating for industry interests and standards.",
                "PAYMENTS_ECOSYSTEM_REP": "You are a payments ecosystem representative focused on innovation and interoperability.",
                "GOVERNMENT_REP": "You are a government representative responsible for policy and regulation.",
                "TECH_REP": "You are a technology representative focused on technical implementation and standards.",
            }


@dataclass
class EvaluationConfig:
    """Configuration for governance evaluation."""

    evaluation_timeout: int = 300  # 5 minutes
    max_concurrent_evaluations: int = 5
    report_generation_timeout: int = 60
    enable_parallel_factor_evaluation: bool = True
    evidence_quality_threshold: float = 0.3
    min_evidence_count: int = 2
    max_evidence_count: int = 20


@dataclass
class APIConfig:
    """Configuration for API endpoints."""

    enable_websocket: bool = True
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10
    max_websocket_connections: int = 100
    api_rate_limit: int = 100  # requests per minute
    enable_cors: bool = True
    cors_origins: list[str] | None = None

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000", "http://localhost:8080"]


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and observability."""

    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_tracing: bool = True
    tracing_endpoint: str = "http://jaeger:14268/api/traces"
    enable_health_checks: bool = True
    health_check_interval: int = 30
    log_level: str = "INFO"
    enable_structured_logging: bool = True


@dataclass
class DatabaseConfig:
    """Configuration for database connections."""

    host: str = "localhost"
    port: int = 5432
    database: str = "ai_agent"
    username: str = "ai_agent"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    enable_ssl: bool = False


@dataclass
class SyntheticAgentConfig:
    """Main configuration class for synthetic agent system."""

    environment: Environment = Environment.DEVELOPMENT
    transcript_processing: TranscriptProcessingConfig | None = None
    mcp: MCPConfig | None = None
    agents: AgentConfig | None = None
    evaluation: EvaluationConfig | None = None
    api: APIConfig | None = None
    monitoring: MonitoringConfig | None = None
    database: DatabaseConfig | None = None

    def __post_init__(self) -> None:
        if self.transcript_processing is None:
            self.transcript_processing = TranscriptProcessingConfig()
        if self.mcp is None:
            self.mcp = MCPConfig()
        if self.agents is None:
            self.agents = AgentConfig()
        if self.evaluation is None:
            self.evaluation = EvaluationConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.database is None:
            self.database = DatabaseConfig()


def load_config(environment: str | None = None) -> SyntheticAgentConfig:
    """Load configuration based on environment."""
    env = environment or os.getenv("ENVIRONMENT", "development")

    config = SyntheticAgentConfig(environment=Environment(env))

    # Override with environment variables
    # The __post_init__ method ensures these are not None
    assert config.transcript_processing is not None
    assert config.agents is not None
    assert config.database is not None
    assert config.monitoring is not None
    config.transcript_processing.transcript_directory = Path(
        os.getenv(
            "TRANSCRIPT_DIRECTORY",
            str(config.transcript_processing.transcript_directory),
        )
    )
    config.transcript_processing.embedding_dimension = int(
        os.getenv(
            "EMBEDDING_DIMENSION", config.transcript_processing.embedding_dimension
        )
    )
    config.transcript_processing.embedding_model_name = os.getenv(
        "EMBEDDING_MODEL_NAME", config.transcript_processing.embedding_model_name
    )

    config.agents.llm_provider = os.getenv("LLM_PROVIDER", config.agents.llm_provider)
    config.agents.llm_temperature = float(
        os.getenv("LLM_TEMPERATURE", config.agents.llm_temperature)
    )
    config.agents.llm_max_tokens = int(
        os.getenv("LLM_MAX_TOKENS", config.agents.llm_max_tokens)
    )

    config.database.host = os.getenv("DATABASE_HOST", config.database.host)
    config.database.port = int(os.getenv("DATABASE_PORT", config.database.port))
    config.database.database = os.getenv("DATABASE_NAME", config.database.database)
    config.database.username = os.getenv("DATABASE_USERNAME", config.database.username)
    config.database.password = os.getenv("DATABASE_PASSWORD", config.database.password)

    config.monitoring.log_level = os.getenv("LOG_LEVEL", config.monitoring.log_level)
    config.monitoring.enable_metrics = (
        os.getenv("ENABLE_METRICS", "true").lower() == "true"
    )
    config.monitoring.enable_tracing = (
        os.getenv("ENABLE_TRACING", "true").lower() == "true"
    )

    return config


def get_config() -> SyntheticAgentConfig:
    """Get the current configuration."""
    return load_config()
