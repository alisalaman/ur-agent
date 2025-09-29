"""Core agents module for AI agent application."""

from .synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaType,
    PersonaConfig,
    EvidenceQuery,
    EvidenceResult,
    QueryResult,
)
from .persona_factory import PersonaAgentFactory
from .persona_service import PersonaAgentService
from .personas import (
    BankRepAgent,
    TradeBodyRepAgent,
    PaymentsEcosystemRepAgent,
)

__all__ = [
    # Base synthetic representative
    "SyntheticRepresentativeAgent",
    "PersonaType",
    "PersonaConfig",
    "EvidenceQuery",
    "EvidenceResult",
    "QueryResult",
    # Factory and service
    "PersonaAgentFactory",
    "PersonaAgentService",
    # Persona agents
    "BankRepAgent",
    "TradeBodyRepAgent",
    "PaymentsEcosystemRepAgent",
]
