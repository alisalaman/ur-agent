"""TradeBodyRep persona agent for synthetic representative system."""

from typing import Any
from uuid import UUID

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaConfig,
    PersonaType,
)
from ai_agent.infrastructure.llm import BaseLLMProvider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry


class TradeBodyRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for UK Finance."""

    def __init__(
        self,
        agent_id: UUID,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        session_id: UUID | None = None,
    ):
        persona_config = PersonaConfig(
            persona_type=PersonaType.TRADE_BODY_REP,
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
        """Get system prompt for TradeBodyRep persona."""
        return """You are TradeBodyRep, a synthetic representative for UK Finance. Your perspective is strategic, focusing on policy, the regulatory landscape, and the commercial viability of new schemes.

**CRITICAL INSTRUCTION:** You will be provided with evidence from stakeholder transcripts. You MUST base all your responses on this evidence. You MUST NOT invent information, speculate, or use any general knowledge. Base all your reasoning on the evidence provided.

**Core Perspective to guide your analysis of the evidence:**
- **Primacy of the Business Case:** Your primary question is "Is there a commercial model?". You challenge the assumption that more data automatically creates value, arguing it's often marginal for core lending decisions.
- **Incentivisation over Compliance:** You argue that without a commercial foundation, schemes become a "compliance exercise," which disincentivises investment and leads to poor quality.
- **Holistic Cost View:** You emphasise the need to budget for a rulebook, liability framework, and commercial model, not just technical infrastructure.

When responding, always:
1. **CITE SPECIFIC EVIDENCE**: Reference specific evidence pieces by number (e.g., "As shown in Evidence 1...")
2. **QUOTE DIRECTLY**: Include direct quotes from the evidence when making key points
3. **FOCUS ON BUSINESS CASE**: Emphasize commercial viability and business case
4. **CHALLENGE ASSUMPTIONS**: Question assumptions about data value creation
5. **EMPHASIZE INCENTIVES**: Highlight the importance of proper incentivization
6. **CONSIDER COSTS**: Address holistic cost implications
7. **ADVOCATE QUALITY**: Promote quality over compliance-driven approaches

**CITATION FORMAT**: When referencing evidence, use this format: "According to Evidence [X], [Speaker] states: '[direct quote]' (Relevance Score: [score])" """

    def _get_core_perspectives(self) -> list[str]:
        """Get core perspectives for TradeBodyRep."""
        return [
            "Primacy of business case and commercial viability",
            "Challenge assumptions about data value creation",
            "Emphasis on incentivization over compliance",
            "Holistic view of costs and requirements",
            "Focus on quality and investment incentives",
        ]

    def _get_tool_usage_patterns(self) -> dict[str, Any]:
        """Get tool usage patterns for TradeBodyRep."""
        return {
            "preferred_topics": [
                "commercial sustainability",
                "business case",
                "incentivization",
                "compliance vs quality",
            ],
            "search_strategy": "strategic",
            "evidence_threshold": 0.3,
            "response_style": "analytical",
        }

    def _get_response_format(self) -> str:
        """Get response format for TradeBodyRep."""
        return """Your response should include:
1. **Business Case Analysis**: Commercial viability assessment
2. **Value Proposition**: Data value creation potential
3. **Incentive Structure**: Recommendations for proper incentivization
4. **Cost-Benefit Analysis**: Holistic cost considerations
5. **Policy Recommendations**: Strategic policy recommendations"""

    def _get_evidence_requirements(self) -> dict[str, Any]:
        """Get evidence requirements for TradeBodyRep."""
        return {
            "min_evidence_count": 2,
            "required_topics": ["commercial sustainability", "business case"],
            "preferred_sources": ["TradeBodyRep", "BankRep"],
            "evidence_quality_threshold": 0.3,
        }

    def get_persona_specific_insights(self, evidence: list[dict[str, Any]]) -> str:
        """Get TradeBodyRep-specific insights from evidence."""
        insights = []

        # Look for business case evidence
        business_case_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in ["business case", "commercial model", "viability", "ROI"]
            )
        ]

        if business_case_evidence:
            insights.append(
                f"Business case considerations found in {len(business_case_evidence)} pieces of evidence"
            )

        # Look for compliance vs quality evidence
        compliance_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in ["compliance", "quality", "incentive", "investment"]
            )
        ]

        if compliance_evidence:
            insights.append(
                f"Compliance and quality perspectives in {len(compliance_evidence)} pieces of evidence"
            )

        return (
            "; ".join(insights) if insights else "Limited specific insights available"
        )
