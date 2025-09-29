# Phase 3: Synthetic Representative Agent System

## Overview

This phase implements the synthetic representative agent system with three distinct personas (BankRep, TradeBodyRep, PaymentsEcosystemRep) that can query transcript data through the MCP server to provide evidence-based responses for governance model evaluation.

## Objectives

- Create synthetic representative agent framework
- Implement three stakeholder personas with distinct perspectives
- Integrate agents with stakeholder views MCP server
- Enable evidence-based response generation
- Build agent factory and management system

## Implementation Tasks

### 3.1 Persona Agent Base Class

**File**: `src/ai_agent/core/agents/synthetic_representative.py`

```python
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog
from uuid import UUID, uuid4

from ai_agent.domain.models import Agent, AgentStatus, Message, MessageRole
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry, ToolExecutionResult
from ai_agent.infrastructure.llm import BaseLLMProvider, LLMResponse

logger = structlog.get_logger()

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
    core_perspectives: List[str]
    tool_usage_patterns: Dict[str, Any]
    response_format: str
    evidence_requirements: Dict[str, Any]

@dataclass
class EvidenceQuery:
    """Query for evidence from stakeholder views."""
    topic: str
    stakeholder_group: Optional[PersonaType] = None
    limit: int = 10
    min_relevance_score: float = 0.3

@dataclass
class EvidenceResult:
    """Result from evidence query."""
    topic: str
    results_count: int
    evidence: List[Dict[str, Any]]
    confidence_level: str
    query_metadata: Dict[str, Any]

class SyntheticRepresentativeAgent(ABC):
    """Base class for synthetic representative agents."""
    
    def __init__(
        self,
        agent_id: UUID,
        persona_config: PersonaConfig,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry
    ):
        self.agent_id = agent_id
        self.persona_config = persona_config
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.status = AgentStatus.IDLE
        self.conversation_history: List[Message] = []
        self.evidence_cache: Dict[str, EvidenceResult] = {}
    
    async def process_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a query and return evidence-based response."""
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
            logger.error("Error processing query", agent_id=str(self.agent_id), error=str(e))
            self.status = AgentStatus.ERROR
            raise
    
    async def _identify_evidence_queries(self, query: str) -> List[EvidenceQuery]:
        """Identify what evidence needs to be gathered for the query."""
        # This is a simplified implementation
        # In practice, this could use an LLM to analyze the query
        evidence_queries = []
        
        # Extract topics from query using keyword matching
        topics = self._extract_topics_from_query(query)
        
        for topic in topics:
            evidence_queries.append(EvidenceQuery(
                topic=topic,
                stakeholder_group=self.persona_config.persona_type,
                limit=10,
                min_relevance_score=0.3
            ))
        
        return evidence_queries
    
    async def _gather_evidence(self, evidence_queries: List[EvidenceQuery]) -> List[EvidenceResult]:
        """Gather evidence using the stakeholder views tool."""
        evidence_results = []
        
        for query in evidence_queries:
            # Check cache first
            cache_key = f"{query.topic}_{query.stakeholder_group}_{query.limit}"
            if cache_key in self.evidence_cache:
                evidence_results.append(self.evidence_cache[cache_key])
                continue
            
            # Execute stakeholder views tool
            try:
                tool_result = await self.tool_registry.execute_tool(
                    tool_name="get_stakeholder_views",
                    arguments={
                        "topic": query.topic,
                        "stakeholder_group": query.stakeholder_group.value if query.stakeholder_group else None,
                        "limit": query.limit,
                        "min_relevance_score": query.min_relevance_score
                    }
                )
                
                if tool_result.success:
                    evidence_result = EvidenceResult(
                        topic=query.topic,
                        results_count=tool_result.result.get("results_count", 0),
                        evidence=tool_result.result.get("results", []),
                        confidence_level=self._calculate_confidence_level(tool_result.result),
                        query_metadata={
                            "stakeholder_group": query.stakeholder_group,
                            "limit": query.limit,
                            "min_relevance_score": query.min_relevance_score
                        }
                    )
                    evidence_results.append(evidence_result)
                    
                    # Cache the result
                    self.evidence_cache[cache_key] = evidence_result
                else:
                    logger.warning("Failed to gather evidence", topic=query.topic, error=tool_result.error)
                    
            except Exception as e:
                logger.error("Error gathering evidence", topic=query.topic, error=str(e))
        
        return evidence_results
    
    async def _generate_evidence_based_response(
        self,
        query: str,
        evidence_results: List[EvidenceResult],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate response based on evidence and persona."""
        # Prepare context for LLM
        system_prompt = self._build_system_prompt(evidence_results)
        user_prompt = self._build_user_prompt(query, evidence_results, context)
        
        # Generate response using LLM
        try:
            response = await self.llm_provider.generate_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.content
            
        except Exception as e:
            logger.error("Error generating response", error=str(e))
            return self._generate_fallback_response(query, evidence_results)
    
    def _build_system_prompt(self, evidence_results: List[EvidenceResult]) -> str:
        """Build system prompt with evidence context."""
        base_prompt = self.persona_config.system_prompt
        
        # Add evidence context
        evidence_context = self._format_evidence_for_prompt(evidence_results)
        
        return f"{base_prompt}\n\n{evidence_context}"
    
    def _build_user_prompt(
        self, 
        query: str, 
        evidence_results: List[EvidenceResult],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt with query and context."""
        prompt = f"Query: {query}\n\n"
        
        if context:
            prompt += f"Additional Context: {context}\n\n"
        
        prompt += "Please provide a response based on the evidence provided and your persona perspective."
        
        return prompt
    
    def _format_evidence_for_prompt(self, evidence_results: List[EvidenceResult]) -> str:
        """Format evidence results for inclusion in prompt."""
        if not evidence_results:
            return "No evidence available for this query."
        
        formatted_evidence = []
        for result in evidence_results:
            if result.evidence:
                evidence_text = f"Topic: {result.topic}\n"
                evidence_text += f"Confidence Level: {result.confidence_level}\n"
                evidence_text += f"Evidence Count: {result.results_count}\n\n"
                
                for i, evidence in enumerate(result.evidence[:5], 1):  # Limit to top 5
                    evidence_text += f"Evidence {i}:\n"
                    evidence_text += f"Speaker: {evidence.get('speaker_name', 'Unknown')}\n"
                    evidence_text += f"Content: {evidence.get('content', '')}\n"
                    evidence_text += f"Relevance Score: {evidence.get('relevance_score', 0)}\n\n"
                
                formatted_evidence.append(evidence_text)
        
        return "Evidence Available:\n\n" + "\n".join(formatted_evidence)
    
    def _calculate_confidence_level(self, tool_result: Dict[str, Any]) -> str:
        """Calculate confidence level based on tool results."""
        results_count = tool_result.get("results_count", 0)
        
        if results_count >= 5:
            return "high"
        elif results_count >= 3:
            return "medium"
        elif results_count >= 1:
            return "low"
        else:
            return "very_low"
    
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """Extract topics from query using keyword matching."""
        # This is a simplified implementation
        # In practice, this could use NLP or LLM-based topic extraction
        topic_keywords = {
            "commercial sustainability": ["commercial", "sustainability", "ROI", "revenue", "profit"],
            "governance": ["governance", "regulation", "compliance", "oversight"],
            "cost": ["cost", "expense", "investment", "budget", "price"],
            "interoperability": ["interoperability", "integration", "compatibility", "cross-sector"],
            "technical feasibility": ["technical", "implementation", "infrastructure", "architecture"]
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
    
    def _generate_fallback_response(
        self, 
        query: str, 
        evidence_results: List[EvidenceResult]
    ) -> str:
        """Generate fallback response when LLM fails."""
        if evidence_results:
            return f"Based on the available evidence, I cannot provide a complete response to '{query}' at this time. Please try rephrasing your question or check back later."
        else:
            return f"I don't have sufficient evidence to respond to '{query}' from my perspective as {self.persona_config.persona_type.value}."
    
    async def _update_conversation_history(self, query: str, response: str) -> None:
        """Update conversation history."""
        self.conversation_history.append(Message(
            id=uuid4(),
            session_id=uuid4(),  # This would be passed in from context
            role=MessageRole.USER,
            content=query,
            metadata={"agent_id": str(self.agent_id)}
        ))
        
        self.conversation_history.append(Message(
            id=uuid4(),
            session_id=uuid4(),  # This would be passed in from context
            role=MessageRole.ASSISTANT,
            content=response,
            metadata={"agent_id": str(self.agent_id)}
        ))
    
    @abstractmethod
    def get_persona_specific_insights(self, evidence: List[Dict[str, Any]]) -> str:
        """Get persona-specific insights from evidence."""
        pass
    
    def clear_cache(self) -> None:
        """Clear evidence cache."""
        self.evidence_cache.clear()
    
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status
```

### 3.2 Individual Persona Implementations

**File**: `src/ai_agent/core/agents/personas/bank_rep.py`

```python
from typing import List, Dict, Any
from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent, 
    PersonaConfig, 
    PersonaType
)

class BankRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for major UK banks."""
    
    def __init__(self, agent_id, llm_provider, tool_registry):
        persona_config = PersonaConfig(
            persona_type=PersonaType.BANK_REP,
            system_prompt=self._get_system_prompt(),
            core_perspectives=self._get_core_perspectives(),
            tool_usage_patterns=self._get_tool_usage_patterns(),
            response_format=self._get_response_format(),
            evidence_requirements=self._get_evidence_requirements()
        )
        super().__init__(agent_id, persona_config, llm_provider, tool_registry)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for BankRep persona."""
        return """You are BankRep, a synthetic representative embodying the composite views of senior leaders from major UK banks. Your perspective is grounded in the direct, and often costly, experience of implementing Open Banking. Your mandate is to analyse proposals for new Smart Data schemes through the lens of a mandated data holder.

**CRITICAL INSTRUCTION:** To form your responses, you MUST use the `get_stakeholder_views` tool to retrieve relevant evidence from the transcripts. You MUST NOT invent information, speculate, or use any general knowledge. Base all your reasoning on the output of the tool.

**Core Perspective to guide your analysis of tool outputs:**
- **Cost-Consciousness:** You consistently reference the vast costs of Open Banking (£1.5 billion to over £2 billion) and the need for sustainable commercial models.
- **Caution on Mandates:** You express scepticism towards mandated features that lack clear, proven consumer demand.
- **Governance and Liability:** You advocate strongly for symmetrical, enforceable governance to avoid a "lopsided market" where data holders have all the obligations.
- **Industry Co-creation:** You favour a collaborative approach to governance over rules imposed by a single entity with unchecked authority.

When responding, always:
1. Cite specific evidence from the transcripts
2. Reference actual costs and experiences mentioned
3. Express caution about mandates without proven demand
4. Advocate for balanced governance and liability frameworks
5. Emphasize the need for sustainable commercial models"""
    
    def _get_core_perspectives(self) -> List[str]:
        """Get core perspectives for BankRep."""
        return [
            "Cost-consciousness and ROI requirements",
            "Skepticism of mandated features without proven demand",
            "Advocacy for symmetrical governance and liability",
            "Preference for industry co-creation over top-down mandates",
            "Focus on sustainable commercial models"
        ]
    
    def _get_tool_usage_patterns(self) -> Dict[str, Any]:
        """Get tool usage patterns for BankRep."""
        return {
            "preferred_topics": [
                "commercial sustainability",
                "cost considerations",
                "governance models",
                "liability frameworks"
            ],
            "search_strategy": "comprehensive",
            "evidence_threshold": 0.4,
            "response_style": "analytical"
        }
    
    def _get_response_format(self) -> str:
        """Get response format for BankRep."""
        return """Your response should include:
1. **Evidence Summary**: Key findings from the transcripts
2. **Cost Analysis**: Specific cost references and ROI considerations
3. **Governance Assessment**: Views on governance and liability frameworks
4. **Risk Assessment**: Potential risks and concerns
5. **Recommendations**: Specific recommendations based on evidence"""
    
    def _get_evidence_requirements(self) -> Dict[str, Any]:
        """Get evidence requirements for BankRep."""
        return {
            "min_evidence_count": 3,
            "required_topics": ["commercial sustainability", "cost considerations"],
            "preferred_sources": ["BankRep", "TradeBodyRep"],
            "evidence_quality_threshold": 0.3
        }
    
    def get_persona_specific_insights(self, evidence: List[Dict[str, Any]]) -> str:
        """Get BankRep-specific insights from evidence."""
        insights = []
        
        # Look for cost-related evidence
        cost_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                      for keyword in ['cost', 'expense', 'investment', 'budget', 'price'])]
        
        if cost_evidence:
            insights.append(f"Cost considerations mentioned in {len(cost_evidence)} pieces of evidence")
        
        # Look for governance-related evidence
        governance_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                           for keyword in ['governance', 'regulation', 'compliance', 'oversight'])]
        
        if governance_evidence:
            insights.append(f"Governance perspectives found in {len(governance_evidence)} pieces of evidence")
        
        return "; ".join(insights) if insights else "Limited specific insights available"
```

**File**: `src/ai_agent/core/agents/personas/trade_body_rep.py`

```python
from typing import List, Dict, Any
from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent, 
    PersonaConfig, 
    PersonaType
)

class TradeBodyRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for UK Finance."""
    
    def __init__(self, agent_id, llm_provider, tool_registry):
        persona_config = PersonaConfig(
            persona_type=PersonaType.TRADE_BODY_REP,
            system_prompt=self._get_system_prompt(),
            core_perspectives=self._get_core_perspectives(),
            tool_usage_patterns=self._get_tool_usage_patterns(),
            response_format=self._get_response_format(),
            evidence_requirements=self._get_evidence_requirements()
        )
        super().__init__(agent_id, persona_config, llm_provider, tool_registry)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for TradeBodyRep persona."""
        return """You are TradeBodyRep, a synthetic representative for UK Finance. Your perspective is strategic, focusing on policy, the regulatory landscape, and the commercial viability of new schemes.

**CRITICAL INSTRUCTION:** To form your responses, you MUST use the `get_stakeholder_views` tool to retrieve relevant evidence from the transcripts. You MUST NOT invent information, speculate, or use any general knowledge. Base all your reasoning on the output of the tool.

**Core Perspective to guide your analysis of tool outputs:**
- **Primacy of the Business Case:** Your primary question is "Is there a commercial model?". You challenge the assumption that more data automatically creates value, arguing it's often marginal for core lending decisions.
- **Incentivisation over Compliance:** You argue that without a commercial foundation, schemes become a "compliance exercise," which disincentivises investment and leads to poor quality.
- **Holistic Cost View:** You emphasise the need to budget for a rulebook, liability framework, and commercial model, not just technical infrastructure.

When responding, always:
1. Focus on commercial viability and business case
2. Challenge assumptions about data value creation
3. Emphasize the importance of proper incentivization
4. Consider holistic cost implications
5. Advocate for quality over compliance-driven approaches"""
    
    def _get_core_perspectives(self) -> List[str]:
        """Get core perspectives for TradeBodyRep."""
        return [
            "Primacy of business case and commercial viability",
            "Challenge assumptions about data value creation",
            "Emphasis on incentivization over compliance",
            "Holistic view of costs and requirements",
            "Focus on quality and investment incentives"
        ]
    
    def _get_tool_usage_patterns(self) -> Dict[str, Any]:
        """Get tool usage patterns for TradeBodyRep."""
        return {
            "preferred_topics": [
                "commercial sustainability",
                "business case",
                "incentivization",
                "compliance vs quality"
            ],
            "search_strategy": "strategic",
            "evidence_threshold": 0.3,
            "response_style": "analytical"
        }
    
    def _get_response_format(self) -> str:
        """Get response format for TradeBodyRep."""
        return """Your response should include:
1. **Business Case Analysis**: Commercial viability assessment
2. **Value Proposition**: Data value creation potential
3. **Incentive Structure**: Recommendations for proper incentivization
4. **Cost-Benefit Analysis**: Holistic cost considerations
5. **Policy Recommendations**: Strategic policy recommendations"""
    
    def _get_evidence_requirements(self) -> Dict[str, Any]:
        """Get evidence requirements for TradeBodyRep."""
        return {
            "min_evidence_count": 2,
            "required_topics": ["commercial sustainability", "business case"],
            "preferred_sources": ["TradeBodyRep", "BankRep"],
            "evidence_quality_threshold": 0.3
        }
    
    def get_persona_specific_insights(self, evidence: List[Dict[str, Any]]) -> str:
        """Get TradeBodyRep-specific insights from evidence."""
        insights = []
        
        # Look for business case evidence
        business_case_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                           for keyword in ['business case', 'commercial model', 'viability', 'ROI'])]
        
        if business_case_evidence:
            insights.append(f"Business case considerations found in {len(business_case_evidence)} pieces of evidence")
        
        # Look for compliance vs quality evidence
        compliance_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                        for keyword in ['compliance', 'quality', 'incentive', 'investment'])]
        
        if compliance_evidence:
            insights.append(f"Compliance and quality perspectives in {len(compliance_evidence)} pieces of evidence")
        
        return "; ".join(insights) if insights else "Limited specific insights available"
```

**File**: `src/ai_agent/core/agents/personas/payments_ecosystem_rep.py`

```python
from typing import List, Dict, Any
from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent, 
    PersonaConfig, 
    PersonaType
)

class PaymentsEcosystemRepAgent(SyntheticRepresentativeAgent):
    """Synthetic representative for Mastercard."""
    
    def __init__(self, agent_id, llm_provider, tool_registry):
        persona_config = PersonaConfig(
            persona_type=PersonaType.PAYMENTS_ECOSYSTEM_REP,
            system_prompt=self._get_system_prompt(),
            core_perspectives=self._get_core_perspectives(),
            tool_usage_patterns=self._get_tool_usage_patterns(),
            response_format=self._get_response_format(),
            evidence_requirements=self._get_evidence_requirements()
        )
        super().__init__(agent_id, persona_config, llm_provider, tool_registry)
    
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
    
    def _get_core_perspectives(self) -> List[str]:
        """Get core perspectives for PaymentsEcosystemRep."""
        return [
            "Ecosystem health and competition at every level",
            "Value-based pricing over cost-plus models",
            "Cross-sector interoperability and scale",
            "Opposition to monopolistic approaches",
            "Importance of regulatory certainty"
        ]
    
    def _get_tool_usage_patterns(self) -> Dict[str, Any]:
        """Get tool usage patterns for PaymentsEcosystemRep."""
        return {
            "preferred_topics": [
                "interoperability",
                "ecosystem health",
                "competition",
                "cross-sector data sharing"
            ],
            "search_strategy": "comprehensive",
            "evidence_threshold": 0.3,
            "response_style": "strategic"
        }
    
    def _get_response_format(self) -> str:
        """Get response format for PaymentsEcosystemRep."""
        return """Your response should include:
1. **Ecosystem Analysis**: Health and competition assessment
2. **Interoperability Assessment**: Cross-sector integration potential
3. **Pricing Model Analysis**: Value-based vs cost-plus considerations
4. **Competition Analysis**: Monopoly risks and competitive dynamics
5. **Regulatory Recommendations**: Certainty and investment requirements"""
    
    def _get_evidence_requirements(self) -> Dict[str, Any]:
        """Get evidence requirements for PaymentsEcosystemRep."""
        return {
            "min_evidence_count": 2,
            "required_topics": ["interoperability", "ecosystem health"],
            "preferred_sources": ["PaymentsEcosystemRep", "TradeBodyRep"],
            "evidence_quality_threshold": 0.3
        }
    
    def get_persona_specific_insights(self, evidence: List[Dict[str, Any]]) -> str:
        """Get PaymentsEcosystemRep-specific insights from evidence."""
        insights = []
        
        # Look for interoperability evidence
        interoperability_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                           for keyword in ['interoperability', 'cross-sector', 'integration', 'compatibility'])]
        
        if interoperability_evidence:
            insights.append(f"Interoperability considerations in {len(interoperability_evidence)} pieces of evidence")
        
        # Look for competition evidence
        competition_evidence = [e for e in evidence if any(keyword in e.get('content', '').lower() 
                        for keyword in ['competition', 'monopoly', 'market', 'ecosystem'])]
        
        if competition_evidence:
            insights.append(f"Competition and ecosystem perspectives in {len(competition_evidence)} pieces of evidence")
        
        return "; ".join(insights) if insights else "Limited specific insights available"
```

### 3.3 Agent Factory

**File**: `src/ai_agent/core/agents/persona_factory.py`

```python
import asyncio
from typing import Dict, Optional, List
from uuid import UUID, uuid4
import structlog

from ai_agent.core.agents.synthetic_representative import (
    SyntheticRepresentativeAgent, 
    PersonaType
)
from ai_agent.core.agents.personas.bank_rep import BankRepAgent
from ai_agent.core.agents.personas.trade_body_rep import TradeBodyRepAgent
from ai_agent.core.agents.personas.payments_ecosystem_rep import PaymentsEcosystemRepAgent
from ai_agent.infrastructure.llm import BaseLLMProvider, get_llm_provider
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()

class PersonaAgentFactory:
    """Factory for creating synthetic representative agents."""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.agents: Dict[UUID, SyntheticRepresentativeAgent] = {}
        self.llm_provider: Optional[BaseLLMProvider] = None
    
    async def initialize(self, llm_provider_type: str = "anthropic") -> None:
        """Initialize the factory with LLM provider."""
        try:
            self.llm_provider = await get_llm_provider(llm_provider_type)
            logger.info("Persona agent factory initialized", provider=llm_provider_type)
        except Exception as e:
            logger.error("Failed to initialize persona agent factory", error=str(e))
            raise
    
    async def create_agent(self, persona_type: PersonaType) -> SyntheticRepresentativeAgent:
        """Create a synthetic representative agent."""
        if not self.llm_provider:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        
        agent_id = uuid4()
        
        try:
            if persona_type == PersonaType.BANK_REP:
                agent = BankRepAgent(agent_id, self.llm_provider, self.tool_registry)
            elif persona_type == PersonaType.TRADE_BODY_REP:
                agent = TradeBodyRepAgent(agent_id, self.llm_provider, self.tool_registry)
            elif persona_type == PersonaType.PAYMENTS_ECOSYSTEM_REP:
                agent = PaymentsEcosystemRepAgent(agent_id, self.llm_provider, self.tool_registry)
            else:
                raise ValueError(f"Unknown persona type: {persona_type}")
            
            self.agents[agent_id] = agent
            logger.info("Agent created", agent_id=str(agent_id), persona_type=persona_type.value)
            
            return agent
            
        except Exception as e:
            logger.error("Failed to create agent", persona_type=persona_type.value, error=str(e))
            raise
    
    async def create_all_personas(self) -> Dict[PersonaType, SyntheticRepresentativeAgent]:
        """Create all three persona agents."""
        agents = {}
        
        for persona_type in PersonaType:
            try:
                agent = await self.create_agent(persona_type)
                agents[persona_type] = agent
            except Exception as e:
                logger.error("Failed to create persona agent", persona_type=persona_type.value, error=str(e))
                raise
        
        logger.info("All persona agents created", count=len(agents))
        return agents
    
    async def get_agent(self, agent_id: UUID) -> Optional[SyntheticRepresentativeAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    async def get_agent_by_persona(self, persona_type: PersonaType) -> Optional[SyntheticRepresentativeAgent]:
        """Get agent by persona type."""
        for agent in self.agents.values():
            if agent.persona_config.persona_type == persona_type:
                return agent
        return None
    
    async def list_agents(self) -> List[SyntheticRepresentativeAgent]:
        """List all created agents."""
        return list(self.agents.values())
    
    async def remove_agent(self, agent_id: UUID) -> bool:
        """Remove an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info("Agent removed", agent_id=str(agent_id))
            return True
        return False
    
    async def clear_all_agents(self) -> None:
        """Clear all agents."""
        self.agents.clear()
        logger.info("All agents cleared")
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all agents."""
        health_status = {}
        
        for agent_id, agent in self.agents.items():
            try:
                # Simple health check - verify agent can process a basic query
                test_response = await agent.process_query("test query")
                health_status[str(agent_id)] = True
            except Exception as e:
                logger.warning("Agent health check failed", agent_id=str(agent_id), error=str(e))
                health_status[str(agent_id)] = False
        
        return health_status
```

### 3.4 Agent Management Service

**File**: `src/ai_agent/core/agents/persona_service.py`

```python
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID
import structlog

from ai_agent.core.agents.persona_factory import PersonaAgentFactory
from ai_agent.core.agents.synthetic_representative import SyntheticRepresentativeAgent, PersonaType
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry

logger = structlog.get_logger()

class PersonaAgentService:
    """Service for managing synthetic representative agents."""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.factory = PersonaAgentFactory(tool_registry)
        self.agents: Dict[PersonaType, SyntheticRepresentativeAgent] = {}
        self.initialized = False
    
    async def initialize(self, llm_provider_type: str = "anthropic") -> None:
        """Initialize the service and create all persona agents."""
        try:
            await self.factory.initialize(llm_provider_type)
            self.agents = await self.factory.create_all_personas()
            self.initialized = True
            logger.info("Persona agent service initialized", agent_count=len(self.agents))
        except Exception as e:
            logger.error("Failed to initialize persona agent service", error=str(e))
            raise
    
    async def process_query(
        self, 
        persona_type: PersonaType, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a query with a specific persona agent."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        
        agent = self.agents.get(persona_type)
        if not agent:
            raise ValueError(f"No agent available for persona type: {persona_type}")
        
        try:
            response = await agent.process_query(query, context)
            logger.info("Query processed", persona_type=persona_type.value, query_length=len(query))
            return response
        except Exception as e:
            logger.error("Failed to process query", persona_type=persona_type.value, error=str(e))
            raise
    
    async def process_query_all_personas(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[PersonaType, str]:
        """Process a query with all persona agents."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        
        responses = {}
        
        # Process query with all agents concurrently
        tasks = []
        for persona_type, agent in self.agents.items():
            task = asyncio.create_task(
                self._process_query_with_agent(persona_type, agent, query, context)
            )
            tasks.append((persona_type, task))
        
        # Wait for all tasks to complete
        for persona_type, task in tasks:
            try:
                response = await task
                responses[persona_type] = response
            except Exception as e:
                logger.error("Failed to process query with agent", persona_type=persona_type.value, error=str(e))
                responses[persona_type] = f"Error processing query: {str(e)}"
        
        return responses
    
    async def _process_query_with_agent(
        self,
        persona_type: PersonaType,
        agent: SyntheticRepresentativeAgent,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Process query with a specific agent."""
        return await agent.process_query(query, context)
    
    async def get_agent_status(self, persona_type: PersonaType) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        agent = self.agents.get(persona_type)
        if not agent:
            return None
        
        return {
            "persona_type": persona_type.value,
            "status": agent.get_status().value,
            "conversation_length": len(agent.conversation_history),
            "cache_size": len(agent.evidence_cache)
        }
    
    async def get_all_agent_status(self) -> Dict[PersonaType, Dict[str, Any]]:
        """Get status of all agents."""
        status = {}
        for persona_type, agent in self.agents.items():
            status[persona_type] = await self.get_agent_status(persona_type)
        return status
    
    async def clear_agent_cache(self, persona_type: Optional[PersonaType] = None) -> None:
        """Clear evidence cache for agents."""
        if persona_type:
            agent = self.agents.get(persona_type)
            if agent:
                agent.clear_cache()
                logger.info("Cache cleared", persona_type=persona_type.value)
        else:
            for agent in self.agents.values():
                agent.clear_cache()
            logger.info("All agent caches cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        if not self.initialized:
            return {"status": "not_initialized", "healthy": False}
        
        try:
            # Check factory health
            factory_health = await self.factory.health_check()
            
            # Check individual agents
            agent_health = {}
            for persona_type, agent in self.agents.items():
                try:
                    # Simple health check
                    test_response = await agent.process_query("health check")
                    agent_health[persona_type.value] = True
                except Exception as e:
                    agent_health[persona_type.value] = False
                    logger.warning("Agent health check failed", persona_type=persona_type.value, error=str(e))
            
            overall_healthy = all(agent_health.values())
            
            return {
                "status": "initialized",
                "healthy": overall_healthy,
                "factory_health": factory_health,
                "agent_health": agent_health,
                "agent_count": len(self.agents)
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"status": "error", "healthy": False, "error": str(e)}
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_synthetic_agents.py`
- Test persona agent creation and configuration
- Test evidence gathering and processing
- Test response generation
- Test agent factory functionality

### Integration Tests
- **File**: `tests/integration/test_persona_agents.py`
- Test agent-MCP server integration
- Test end-to-end query processing
- Test multi-agent query processing

### Performance Tests
- **File**: `tests/performance/test_persona_agents.py`
- Test concurrent agent processing
- Test memory usage with large evidence sets
- Test response time optimization

## Success Criteria

1. **Agent Creation**: All three persona agents created successfully
2. **Evidence Integration**: Agents successfully query stakeholder views tool
3. **Response Quality**: Evidence-based responses with proper citations
4. **Persona Distinction**: Clear differences in responses between personas
5. **Performance**: <2 second response time for typical queries

## Dependencies

This phase depends on:
- Phase 1: Transcript ingestion system
- Phase 2: Stakeholder views MCP server
- Existing LLM infrastructure
- Existing MCP tool registry

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 4: Governance evaluation framework that uses these agents
- Phase 5: API endpoints that expose agent functionality

The synthetic agent system must be fully functional and tested before proceeding to Phase 4.
