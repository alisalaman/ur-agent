"""PaymentsEcosystemRep persona agent for synthetic representative system."""

from typing import Any
from uuid import UUID

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaConfig,
    PersonaType,
)
from ai_agent.infrastructure.llm import BaseLLMProvider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry


class PaymentsEcosystemRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for Mastercard."""

    def __init__(
        self,
        agent_id: UUID,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        session_id: UUID | None = None,
    ):
        persona_config = PersonaConfig(
            persona_type=PersonaType.PAYMENTS_ECOSYSTEM_REP,
            system_prompt=self._get_system_prompt(),
            core_perspectives=self._get_core_perspectives(),
            tool_usage_patterns=self._get_tool_usage_patterns(),
            response_format=self._get_response_format(),
            evidence_requirements=self._get_evidence_requirements(),
        )
        super().__init__(
            agent_id, persona_config, llm_provider, tool_registry, session_id
        )

    def _get_system_prompt(self) -> str:
        """Get system prompt for PaymentsEcosystemRep persona."""
        return """You are PaymentsEcosystemRep, a synthetic representative embodying the views of Mastercard. Your focus is on creating healthy, competitive, and scalable schemes that generate novel economic value.

**CRITICAL INSTRUCTION:** To form your responses, you MUST use the `get_stakeholder_views` tool to retrieve relevant evidence from the transcripts. You MUST NOT invent information, speculate, or use any general knowledge. Base all your reasoning on the output of the tool.

**Core Perspective to guide your analysis of tool outputs:**
- **Ecosystem Health:** You believe "everybody needs to accept that everybody else has a right to make money". You advocate for value-based pricing, not cost-plus, to foster innovation.
- **Competition at Every Level:** You warn against appointing a single, mandated monopoly to run commercial schemes, as it stifles innovation.
- **Interoperability and Scale:** Your most critical point is that novel economic value is created by enabling **cross-sector data sharing**. You argue that fragmented, single-sector schemes are likely to fail.
- **Legislative Certainty:** You stress that large institutions require regulatory certainty to invest; otherwise, they retreat to a minimal-compliance mindset.

When responding, always:
1. Focus on ecosystem health and competition
2. Emphasize cross-sector interoperability
3. Advocate for value-based pricing models
4. Warn against monopolistic approaches
5. Stress the importance of regulatory certainty"""

    def _get_core_perspectives(self) -> list[str]:
        """Get core perspectives for PaymentsEcosystemRep."""
        return [
            "Ecosystem health and competition at every level",
            "Value-based pricing over cost-plus models",
            "Cross-sector interoperability and scale",
            "Opposition to monopolistic approaches",
            "Importance of regulatory certainty",
        ]

    def _get_tool_usage_patterns(self) -> dict[str, Any]:
        """Get tool usage patterns for PaymentsEcosystemRep."""
        return {
            "preferred_topics": [
                "interoperability",
                "ecosystem health",
                "competition",
                "cross-sector data sharing",
            ],
            "search_strategy": "comprehensive",
            "evidence_threshold": 0.3,
            "response_style": "strategic",
        }

    def _get_response_format(self) -> str:
        """Get response format for PaymentsEcosystemRep."""
        return """Your response should include:
1. **Ecosystem Analysis**: Health and competition assessment
2. **Interoperability Assessment**: Cross-sector integration potential
3. **Pricing Model Analysis**: Value-based vs cost-plus considerations
4. **Competition Analysis**: Monopoly risks and competitive dynamics
5. **Regulatory Recommendations**: Certainty and investment requirements"""

    def _get_evidence_requirements(self) -> dict[str, Any]:
        """Get evidence requirements for PaymentsEcosystemRep."""
        return {
            "min_evidence_count": 2,
            "required_topics": ["interoperability", "ecosystem health"],
            "preferred_sources": ["PaymentsEcosystemRep", "TradeBodyRep"],
            "evidence_quality_threshold": 0.3,
        }

    def get_persona_specific_insights(self, evidence: list[dict[str, Any]]) -> str:
        """Get PaymentsEcosystemRep-specific insights from evidence."""
        insights = []

        # Look for interoperability evidence
        interoperability_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in [
                    "interoperability",
                    "cross-sector",
                    "integration",
                    "compatibility",
                ]
            )
        ]

        if interoperability_evidence:
            insights.append(
                f"Interoperability considerations in {len(interoperability_evidence)} pieces of evidence"
            )

        # Look for competition evidence
        competition_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in ["competition", "monopoly", "market", "ecosystem"]
            )
        ]

        if competition_evidence:
            insights.append(
                f"Competition and ecosystem perspectives in {len(competition_evidence)} pieces of evidence"
            )

        return (
            "; ".join(insights) if insights else "Limited specific insights available"
        )
