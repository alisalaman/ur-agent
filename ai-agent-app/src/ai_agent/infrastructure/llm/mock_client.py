"""Mock LLM provider for demo purposes."""

import asyncio
from typing import Any
from collections.abc import AsyncGenerator
import structlog

from .base import (
    BaseLLMProvider,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMModelType,
    ModelInfo,
)

logger = structlog.get_logger()


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for demo purposes."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.default_model = config.get("default_model", "mock-model")
        self.max_tokens = config.get("max_tokens", 1000)

    def _get_provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.ANTHROPIC  # Use Anthropic type for compatibility

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock completion response."""
        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Extract the query from the last user message
        user_message = ""
        system_message = ""
        for message in reversed(request.messages):
            if message.get("role") == "user":
                user_message = message.get("content", "")
            elif message.get("role") == "system":
                system_message = message.get("content", "")

        # Debug logging
        logger.info(
            "Mock LLM request",
            user_message_length=len(user_message),
            system_message_length=len(system_message),
        )
        logger.info(
            "System message content",
            system_message=(
                system_message[:200] + "..."
                if len(system_message) > 200
                else system_message
            ),
        )

        # Generate a mock response based on the query and system message
        mock_response = self._generate_mock_response(
            system_message + "\n\n" + user_message
        )

        return LLMResponse(
            content=mock_response,
            model=request.model or self.default_model,
            provider="mock",
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(mock_response.split()),
                "total_tokens": len(user_message.split()) + len(mock_response.split()),
            },
            metadata={"finish_reason": "stop"},
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk]:
        """Generate a mock streaming response."""
        mock_response = self._generate_mock_response(
            request.messages[-1].get("content", "") if request.messages else ""
        )

        # Stream the response word by word
        words = mock_response.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Simulate streaming delay
            yield LLMStreamChunk(
                content=word + (" " if i < len(words) - 1 else ""),
                model=request.model or self.default_model,
                provider="mock",
                is_final=i == len(words) - 1,
            )

    async def get_models(self) -> list[ModelInfo]:
        """Get available models."""
        return [
            ModelInfo(
                id="mock-model",
                name="Mock Model",
                provider="mock",
                type=LLMModelType.CHAT,
                max_tokens=self.max_tokens,
                cost_per_token=0.0,
                description="Mock model for demo purposes",
            )
        ]

    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        return True

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate response for compatibility with the agent system."""
        # Convert to LLMRequest format
        request = LLMRequest(
            messages=messages,
            model=self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return await self.generate(request)

    async def execute_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Mock tool execution for compatibility."""
        if tool_name == "get_stakeholder_views":
            # Return mock evidence data
            topic = arguments.get("topic", "").lower()

            mock_evidence = {
                "success": True,
                "result": {
                    "results_count": 3,
                    "results": [
                        {
                            "speaker_name": "BankRep",
                            "content": f"Based on the evidence from transcripts, {topic} is a critical consideration for our organization.",
                            "relevance_score": 0.95,
                            "stakeholder_group": "BankRep",
                            "topic": topic,
                        },
                        {
                            "speaker_name": "TradeBodyRep",
                            "content": f"From a policy perspective, {topic} requires careful analysis and stakeholder consultation.",
                            "relevance_score": 0.88,
                            "stakeholder_group": "TradeBodyRep",
                            "topic": topic,
                        },
                        {
                            "speaker_name": "PaymentsEcosystemRep",
                            "content": f"Ecosystem considerations around {topic} are essential for sustainable implementation.",
                            "relevance_score": 0.92,
                            "stakeholder_group": "PaymentsEcosystemRep",
                            "topic": topic,
                        },
                    ],
                },
            }
            return mock_evidence
        else:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

    def _generate_mock_response(self, query: str) -> str:
        """Generate a mock response based on the query and evidence."""
        query_lower = query.lower()

        # Debug logging to see what's being passed
        logger.info(
            "Mock LLM generating response",
            query_length=len(query),
            has_evidence="Evidence Available:" in query,
        )
        logger.info(
            "Query content",
            query_content=query[:500] + "..." if len(query) > 500 else query,
        )

        # Check if there's evidence in the system prompt by looking for "Evidence Available:"
        # This is a simple way to detect if evidence was provided
        if "Evidence Available:" in query:
            # Extract evidence from the query (this is a simplified approach)
            # In a real implementation, this would be more sophisticated
            if "BANK PERSPECTIVE" in query or "Speaker: BankRep" in query:
                return """Based on the evidence provided, as a major UK bank representative, I need to emphasize our critical concerns about governance models:

**Regulatory Compliance**: We require strict regulatory compliance frameworks with clear liability structures. Our £2+ billion investment in Open Banking shows we cannot afford another mandated scheme without proven commercial viability.

**Operational Costs**: Customer data security and service continuity are paramount. The governance model must include symmetrical obligations for all participants and enforceable penalties for non-compliance.

**Commercial Viability**: We need clear evidence of commercial returns before supporting any new governance framework. Without this, schemes become compliance exercises that drain resources."""

            elif "TRADE BODY PERSPECTIVE" in query or "Speaker: TradeBodyRep" in query:
                return """Based on the evidence provided, from UK Finance's perspective, the fundamental question for governance is 'Is there a commercial model?'

**Business Case Validation**: We challenge the assumption that more data automatically creates value. Without proper incentivization, schemes become compliance exercises that disincentivize investment and lead to poor quality implementations.

**Policy Development**: The business case must be compelling and sustainable. We need balanced policy development that promotes innovation while ensuring consumer protection and market fairness for all participants.

**Investment Incentives**: Quality implementations require proper incentivization. Without commercial foundations, we get minimal compliance approaches that fail to deliver real value."""

            elif (
                "ECOSYSTEM PERSPECTIVE" in query
                or "Speaker: PaymentsEcosystemRep" in query
            ):
                return """Based on the evidence provided, from Mastercard's perspective, governance must create novel economic value through cross-sector data sharing.

**Value Creation**: We believe 'everybody needs to accept that everybody else has a right to make money.' The governance model should use value-based pricing, not cost-plus, to foster innovation.

**Competition**: We strongly oppose single mandated monopolies that stifle competition. Interoperability and scale are critical - fragmented single-sector schemes are likely to fail.

**Regulatory Certainty**: Large institutions need regulatory certainty to invest; otherwise they retreat to minimal-compliance approaches."""

        # Fallback to keyword-based responses if no evidence detected
        if "cost" in query_lower or "commercial" in query_lower:
            return """Based on the available evidence from the transcripts, I need to emphasize the critical importance of sustainable commercial models and balanced governance for any new Smart Data schemes.

As a representative of major UK banks, our primary concerns are:
1. **Cost Management**: We cannot repeat the £2+ billion burden of Open Banking without clear commercial returns
2. **Governance Balance**: We need symmetrical frameworks where all participants share obligations and benefits
3. **Industry Collaboration**: Rules should be co-created rather than imposed unilaterally
4. **Proven Demand**: Mandates should only be implemented where there's clear, demonstrated consumer demand

The evidence shows that without these principles, schemes become compliance exercises that drain resources and create market distortions."""

        elif "governance" in query_lower:
            return """From a governance perspective, the evidence points to several critical factors for successful Smart Data schemes:

**Primacy of Business Case**: The fundamental question must always be "Is there a commercial model?" Without this foundation, schemes become compliance exercises that disincentivize investment.

**Value Creation Challenge**: The evidence challenges the assumption that more data automatically creates value. We need to focus on meaningful value creation rather than data collection for its own sake.

**Incentivization over Compliance**: Quality implementations require proper incentivization. Without commercial foundations, we get minimal compliance approaches that fail to deliver real value.

**Holistic Cost View**: Success requires budgeting for the complete ecosystem: technical infrastructure, rulebook development, liability frameworks, and sustainable commercial models."""

        elif "interoperability" in query_lower or "cross-sector" in query_lower:
            return """From an ecosystem perspective, the evidence points to several key principles for successful Smart Data schemes:

**Ecosystem Health**: Everyone needs to accept that everyone else has a right to make money. This requires value-based pricing models that foster innovation and participation.

**Competition at Every Level**: We must avoid appointing single, mandated monopolies to run commercial schemes, as this stifles innovation and creates market distortions.

**Cross-Sector Interoperability**: The most critical factor is enabling cross-sector data sharing, where novel economic value is created. Single-sector schemes are likely to fail because they don't unlock the full potential.

**Regulatory Certainty**: Large institutions require regulatory certainty to invest meaningfully. Without it, they retreat to minimal compliance approaches that don't deliver real value."""

        else:
            return """Based on the available evidence from the transcripts, I need to emphasize the critical importance of sustainable commercial models and balanced governance for any new Smart Data schemes.

The evidence shows that successful schemes require:
1. Clear commercial viability before implementation
2. Symmetrical governance frameworks where all participants share obligations and benefits
3. Industry co-creation of rules rather than top-down mandates
4. Focus on value creation rather than data collection for its own sake

Without these principles, schemes become compliance exercises that drain resources and create market distortions."""
