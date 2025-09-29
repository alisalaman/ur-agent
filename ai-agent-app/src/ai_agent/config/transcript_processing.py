"""Configuration for transcript processing."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TranscriptProcessingConfig:
    """Configuration for transcript processing."""

    # File paths
    transcript_directory: Path = Path("docs/transcripts")

    # Processing parameters
    min_segment_length: int = 50
    max_segment_length: int = 2000

    # Embedding model
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 dimension

    # Search parameters
    default_search_limit: int = 10
    max_search_limit: int = 100

    # Vector similarity threshold
    similarity_threshold: float = 0.7

    # Stakeholder group mappings (anonymized)
    stakeholder_group_mappings: dict[str, str] = field(
        default_factory=lambda: {
            "transcript_001_bank_rep_gov_only.docx": "BankRep",
            "transcript_002_trade_body_rep_mixed.docx": "TradeBodyRep",
            "transcript_003_payments_ecosystem_rep_gov_only.docx": "PaymentsEcosystemRep",
            "transcript_004_bank_rep_mixed_gov.docx": "BankRep",
            "transcript_005_bank_rep_tech_gov.docx": "BankRep",
            "transcript_006_bank_rep_gov_only.docx": "BankRep",
            "transcript_007_bank_rep_mixed_gov.docx": "BankRep",
        }
    )

    # Source mappings (anonymized)
    source_mappings: dict[str, str] = field(
        default_factory=lambda: {
            "transcript_001_bank_rep_gov_only.docx": "Bank_A",
            "transcript_002_trade_body_rep_mixed.docx": "Trade_Body_A",
            "transcript_003_payments_ecosystem_rep_gov_only.docx": "Payments_Provider_A",
            "transcript_004_bank_rep_mixed_gov.docx": "Bank_B",
            "transcript_005_bank_rep_tech_gov.docx": "Bank_A",
            "transcript_006_bank_rep_gov_only.docx": "Bank_C",
            "transcript_007_bank_rep_mixed_gov.docx": "Bank_D",
        }
    )
