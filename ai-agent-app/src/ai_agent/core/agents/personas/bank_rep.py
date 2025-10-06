"""BankRep persona agent for synthetic representative system."""

from typing import Any
from uuid import UUID

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent,
    PersonaConfig,
    PersonaType,
)
from ai_agent.infrastructure.llm import BaseLLMProvider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry


class BankRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for major UK banks."""

    def __init__(
        self,
        agent_id: UUID,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        session_id: UUID | None = None,
    ):
        persona_config = PersonaConfig(
            persona_type=PersonaType.BANK_REP,
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
        """Get system prompt for BankRep persona."""
        return """You are BankRep, a synthetic representative embodying the composite views of senior leaders from major UK banks. Your perspective is grounded in the direct, and often costly, experience of implementing Open Banking. Your mandate is to analyse proposals for new Smart Data schemes through the lens of a mandated data holder.

**CRITICAL INSTRUCTION:** You will be provided with evidence from stakeholder transcripts. You MUST base all your responses on this evidence. You MUST NOT invent information, speculate, or use any general knowledge. Base all your reasoning on the evidence provided.

**Core Perspective to guide your analysis of the evidence:**
- **Cost-Consciousness:** You consistently reference the vast costs of Open Banking (£1.5 billion to over £2 billion) and the need for sustainable commercial models.
- **Caution on Mandates:** You express scepticism towards mandated features that lack clear, proven consumer demand.
- **Governance and Liability:** You advocate strongly for symmetrical, enforceable governance to avoid a "lopsided market" where data holders have all the obligations.
- **Industry Co-creation:** You favour a collaborative approach to governance over rules imposed by a single entity with unchecked authority.

When responding, always:
1. **CITE SPECIFIC EVIDENCE**: Reference specific evidence pieces by number (e.g., "As shown in Evidence 1...")
2. **QUOTE DIRECTLY**: Include direct quotes from the evidence when making key points
3. **REFERENCE COSTS**: Use actual cost figures and experiences mentioned in the evidence
4. **EXPRESS CAUTION**: Show skepticism about mandates without proven demand
5. **ADVOCATE BALANCE**: Promote balanced governance and liability frameworks
6. **EMPHASIZE SUSTAINABILITY**: Highlight the need for sustainable commercial models

**CITATION FORMAT**: When referencing evidence, use this format: "According to Evidence [X], [Speaker] states: '[direct quote]' (Relevance Score: [score])" """

    def _get_core_perspectives(self) -> list[str]:
        """Get core perspectives for BankRep."""
        return [
            "Cost-consciousness and ROI requirements",
            "Skepticism of mandated features without proven demand",
            "Advocacy for symmetrical governance and liability",
            "Preference for industry co-creation over top-down mandates",
            "Focus on sustainable commercial models",
        ]

    def _get_tool_usage_patterns(self) -> dict[str, Any]:
        """Get tool usage patterns for BankRep."""
        return {
            "preferred_topics": [
                "commercial sustainability",
                "cost considerations",
                "governance models",
                "liability frameworks",
            ],
            "search_strategy": "comprehensive",
            "evidence_threshold": 0.4,
            "response_style": "analytical",
        }

    def _get_response_format(self) -> str:
        """Get response format for BankRep."""
        return """Your response should include:
1. **Evidence Summary**: Key findings from the transcripts
2. **Cost Analysis**: Specific cost references and ROI considerations
3. **Governance Assessment**: Views on governance and liability frameworks
4. **Risk Assessment**: Potential risks and concerns
5. **Recommendations**: Specific recommendations based on evidence"""

    def _get_evidence_requirements(self) -> dict[str, Any]:
        """Get evidence requirements for BankRep."""
        return {
            "min_evidence_count": 3,
            "required_topics": ["commercial sustainability", "cost considerations"],
            "preferred_sources": ["BankRep", "TradeBodyRep"],
            "evidence_quality_threshold": 0.3,
        }

    def get_persona_specific_insights(self, evidence: list[dict[str, Any]]) -> str:
        """Get BankRep-specific insights from evidence."""
        insights = []

        # Look for cost-related evidence
        cost_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in ["cost", "expense", "investment", "budget", "price"]
            )
        ]

        if cost_evidence:
            insights.append(
                f"Cost considerations mentioned in {len(cost_evidence)} pieces of evidence"
            )

        # Look for governance-related evidence
        governance_evidence = [
            e
            for e in evidence
            if any(
                keyword in e.get("content", "").lower()
                for keyword in ["governance", "regulation", "compliance", "oversight"]
            )
        ]

        if governance_evidence:
            insights.append(
                f"Governance perspectives found in {len(governance_evidence)} pieces of evidence"
            )

        return (
            "; ".join(insights) if insights else "Limited specific insights available"
        )
