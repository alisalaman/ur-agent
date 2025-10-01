"""Synthetic representative agent system for governance evaluation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog

from ai_agent.domain.models import AgentStatus, Message, MessageRole
from ai_agent.infrastructure.llm import BaseLLMProvider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()

# Type definitions
ConfidenceLevel = Literal["high", "medium", "low", "very_low"]


class AgentConfig:
    """Configuration constants for synthetic representative agents."""

    # Evidence gathering defaults
    DEFAULT_EVIDENCE_LIMIT = 10
    DEFAULT_RELEVANCE_THRESHOLD = 0.3
    MAX_EVIDENCE_PER_RESULT = 5

    # Confidence level thresholds
    CONFIDENCE_THRESHOLDS = {"high": 5, "medium": 3, "low": 1}

    # Query validation
    MAX_QUERY_LENGTH = 10000
    MIN_QUERY_LENGTH = 1

    # LLM parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1000


class PersonaType(str, Enum):
    """Types of synthetic representative personas."""

    BANK_REP = "BankRep"
    TRADE_BODY_REP = "TradeBodyRep"
    PAYMENTS_ECOSYSTEM_REP = "PaymentsEcosystemRep"


@dataclass
class PersonaConfig:
    """Configuration for a synthetic representative persona."""

    persona_type: PersonaType
    system_prompt: str
    core_perspectives: list[str]
    tool_usage_patterns: dict[str, Any]
    response_format: str
    evidence_requirements: dict[str, Any]


@dataclass
class EvidenceQuery:
    """Query for evidence from stakeholder views."""

    topic: str
    stakeholder_group: PersonaType | None = None
    limit: int = 10
    min_relevance_score: float = 0.3


@dataclass
class EvidenceResult:
    """Result from evidence query."""

    topic: str
    results_count: int
    evidence: list[dict[str, Any]]
    confidence_level: str
    query_metadata: dict[str, Any]


@dataclass
class QueryResult:
    """Result from query processing."""

    success: bool
    response: str | None = None
    error: str | None = None
    persona_type: str | None = None


class SyntheticRepresentativeAgent(ABC):
    """Base class for synthetic representative agents."""

    def __init__(
        self,
        agent_id: UUID,
        persona_config: PersonaConfig,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        session_id: UUID | None = None,
    ):
        self.agent_id = agent_id
        self.persona_config = persona_config
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.session_id = session_id or uuid4()
        self.status = AgentStatus.IDLE
        self.conversation_history: list[Message] = []
        self.evidence_cache: dict[str, EvidenceResult] = {}

    async def process_query(
        self, query: str, context: dict[str, Any] | None = None
    ) -> str:
        """Process a query and return evidence-based response."""
        # Input validation
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if len(query) > AgentConfig.MAX_QUERY_LENGTH:
            raise ValueError(
                f"Query too long (max {AgentConfig.MAX_QUERY_LENGTH} characters)"
            )

        try:
            self.status = AgentStatus.PROCESSING

            # Step 1: Analyze query and identify evidence needs
            evidence_queries = await self._identify_evidence_queries(query)

            # Step 2: Gather evidence from stakeholder views
            evidence_results = await self._gather_evidence(evidence_queries)

            # Step 3: Generate response based on evidence and persona
            response = await self._generate_evidence_based_response(
                query, evidence_results, context
            )

            # Step 4: Update conversation history
            await self._update_conversation_history(query, response)

            self.status = AgentStatus.COMPLETED
            return response

        except Exception as e:
            logger.error(
                "Error processing query", agent_id=str(self.agent_id), error=str(e)
            )
            self.status = AgentStatus.ERROR
            raise

    async def _identify_evidence_queries(self, query: str) -> list[EvidenceQuery]:
        """Identify what evidence needs to be gathered for the query."""
        # This is a simplified implementation
        # In practice, this could use an LLM to analyze the query
        evidence_queries = []

        # Extract topics from query using keyword matching
        topics = self._extract_topics_from_query(query)

        for topic in topics:
            evidence_queries.append(
                EvidenceQuery(
                    topic=topic,
                    stakeholder_group=self.persona_config.persona_type,
                    limit=AgentConfig.DEFAULT_EVIDENCE_LIMIT,
                    min_relevance_score=AgentConfig.DEFAULT_RELEVANCE_THRESHOLD,
                )
            )

        return evidence_queries

    async def _gather_evidence(
        self, evidence_queries: list[EvidenceQuery]
    ) -> list[EvidenceResult]:
        """Gather evidence using the stakeholder views tool."""
        evidence_results = []

        for query in evidence_queries:
            # Check cache first
            cache_key = self._generate_cache_key(query)
            if cache_key in self.evidence_cache:
                evidence_results.append(self.evidence_cache[cache_key])
                continue

            # Execute stakeholder views tool
            try:
                logger.info(
                    "Calling mock tool",
                    topic=query.topic,
                    stakeholder_group=query.stakeholder_group,
                    stakeholder_group_value=(
                        query.stakeholder_group.value
                        if query.stakeholder_group
                        else None
                    ),
                )

                tool_result = await self.tool_registry.execute_tool(
                    tool_name="get_stakeholder_views",
                    arguments={
                        "topic": query.topic,
                        "stakeholder_group": (
                            query.stakeholder_group.value
                            if query.stakeholder_group
                            else None
                        ),
                        "limit": query.limit,
                        "min_relevance_score": query.min_relevance_score,
                    },
                )

                logger.info(
                    "Mock tool result",
                    success=tool_result.success,
                    result=tool_result.result,
                )

                if tool_result.success:
                    evidence_result = EvidenceResult(
                        topic=query.topic,
                        results_count=tool_result.result.get("results_count", 0),
                        evidence=tool_result.result.get("results", []),
                        confidence_level=self._calculate_confidence_level(
                            tool_result.result
                        ),
                        query_metadata={
                            "stakeholder_group": query.stakeholder_group,
                            "limit": query.limit,
                            "min_relevance_score": query.min_relevance_score,
                        },
                    )
                    evidence_results.append(evidence_result)

                    # Cache the result
                    self.evidence_cache[cache_key] = evidence_result
                else:
                    logger.warning(
                        "Failed to gather evidence",
                        topic=query.topic,
                        error=tool_result.error,
                    )

            except Exception as e:
                logger.error(
                    "Error gathering evidence", topic=query.topic, error=str(e)
                )

        return evidence_results

    async def _generate_evidence_based_response(
        self,
        query: str,
        evidence_results: list[EvidenceResult],
        context: dict[str, Any] | None,
    ) -> str:
        """Generate response based on evidence and persona."""
        # Prepare context for LLM
        system_prompt = self._build_system_prompt(evidence_results)
        user_prompt = self._build_user_prompt(query, evidence_results, context)

        # Generate response using LLM
        try:
            from ai_agent.infrastructure.llm.base import LLMRequest

            request = LLMRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.llm_provider.default_model,
                temperature=AgentConfig.DEFAULT_TEMPERATURE,
                max_tokens=AgentConfig.DEFAULT_MAX_TOKENS,
            )

            response = await self.llm_provider.generate(request)

            return str(response.content)

        except Exception as e:
            logger.error("Error generating response", error=str(e))
            return self._generate_fallback_response(query, evidence_results)

    def _build_system_prompt(self, evidence_results: list[EvidenceResult]) -> str:
        """Build system prompt with evidence context."""
        base_prompt = self.persona_config.system_prompt

        # Add evidence context
        evidence_context = self._format_evidence_for_prompt(evidence_results)

        return f"{base_prompt}\n\n{evidence_context}"

    def _build_user_prompt(
        self,
        query: str,
        evidence_results: list[EvidenceResult],
        context: dict[str, Any] | None,
    ) -> str:
        """Build user prompt with query and context."""
        prompt = f"Query: {query}\n\n"

        if context:
            prompt += f"Additional Context: {context}\n\n"

        prompt += "Please provide a response based on the evidence provided and your persona perspective."

        return prompt

    def _format_evidence_for_prompt(
        self, evidence_results: list[EvidenceResult]
    ) -> str:
        """Format evidence results for inclusion in prompt."""
        if not evidence_results:
            return "No evidence available for this query."

        formatted_evidence = []
        for result in evidence_results:
            if result.evidence:
                evidence_text = f"Topic: {result.topic}\n"
                evidence_text += f"Confidence Level: {result.confidence_level}\n"
                evidence_text += f"Evidence Count: {result.results_count}\n\n"

                for i, evidence in enumerate(
                    result.evidence[: AgentConfig.MAX_EVIDENCE_PER_RESULT], 1
                ):
                    evidence_text += self._format_single_evidence(evidence, i)

                formatted_evidence.append(evidence_text)

        return "Evidence Available:\n\n" + "\n".join(formatted_evidence)

    def _format_single_evidence(self, evidence: dict[str, Any], index: int) -> str:
        """Format a single piece of evidence."""
        return f"""Evidence {index}:
Speaker: {evidence.get("speaker_name", "Unknown")}
Content: {evidence.get("content", "")}
Relevance Score: {evidence.get("relevance_score", 0)}

"""

    def _calculate_confidence_level(
        self, tool_result: dict[str, Any]
    ) -> ConfidenceLevel:
        """Calculate confidence level based on tool results."""
        results_count = tool_result.get("results_count", 0)

        # Use configuration thresholds for maintainability
        thresholds = [
            (AgentConfig.CONFIDENCE_THRESHOLDS["high"], "high"),
            (AgentConfig.CONFIDENCE_THRESHOLDS["medium"], "medium"),
            (AgentConfig.CONFIDENCE_THRESHOLDS["low"], "low"),
        ]

        for threshold, level in thresholds:
            if results_count >= threshold:
                return level  # type: ignore[return-value]
        return "very_low"

    def _extract_topics_from_query(self, query: str) -> list[str]:
        """Extract topics from query using keyword matching."""
        # This is a simplified implementation
        # In practice, this could use NLP or LLM-based topic extraction
        topic_keywords = {
            "commercial sustainability": [
                "commercial",
                "sustainability",
                "ROI",
                "revenue",
                "profit",
            ],
            "governance": ["governance", "regulation", "compliance", "oversight"],
            "cost": ["cost", "expense", "investment", "budget", "price"],
            "interoperability": [
                "interoperability",
                "integration",
                "compatibility",
                "cross-sector",
            ],
            "technical feasibility": [
                "technical",
                "implementation",
                "infrastructure",
                "architecture",
            ],
        }

        query_lower = query.lower()
        topics = []

        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)

        # If no specific topics found, use the query itself
        if not topics:
            topics = [query]

        return topics

    def _generate_cache_key(self, query: EvidenceQuery) -> str:
        """Generate a cache key for evidence query."""
        return f"{query.topic}:{query.stakeholder_group}:{query.limit}:{query.min_relevance_score}"

    def _generate_fallback_response(
        self, query: str, evidence_results: list[EvidenceResult]
    ) -> str:
        """Generate fallback response when LLM fails."""
        if evidence_results:
            return f"Based on the available evidence, I cannot provide a complete response to '{query}' at this time. Please try rephrasing your question or check back later."
        else:
            return f"I don't have sufficient evidence to respond to '{query}' from my perspective as {self.persona_config.persona_type}."

    async def _update_conversation_history(self, query: str, response: str) -> None:
        """Update conversation history."""
        self.conversation_history.append(
            Message(
                id=uuid4(),
                session_id=self.session_id,
                role=MessageRole.USER,
                content=query,
                metadata={"agent_id": str(self.agent_id)},
            )
        )

        self.conversation_history.append(
            Message(
                id=uuid4(),
                session_id=self.session_id,
                role=MessageRole.ASSISTANT,
                content=response,
                metadata={"agent_id": str(self.agent_id)},
            )
        )

    @abstractmethod
    def get_persona_specific_insights(self, evidence: list[dict[str, Any]]) -> str:
        """Get persona-specific insights from evidence."""
        pass

    def clear_cache(self) -> None:
        """Clear evidence cache."""
        self.evidence_cache.clear()

    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status
