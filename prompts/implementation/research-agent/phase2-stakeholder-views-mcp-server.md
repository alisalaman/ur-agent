# Phase 2: Stakeholder Views MCP Server

## Overview

This phase implements an MCP server that provides the `get_stakeholder_views` tool, enabling AI agents to query transcript data for evidence-based responses. The server integrates with the transcript knowledge base from Phase 1 and exposes functionality through the existing MCP infrastructure.

## Objectives

- Create MCP server for stakeholder views tool
- Implement semantic search across transcript data
- Integrate with existing MCP infrastructure
- Provide evidence-based responses for agent consumption
- Enable stakeholder group filtering and topic-based queries

## Implementation Tasks

### 2.1 MCP Server Implementation

**File**: `src/ai_agent/infrastructure/mcp/servers/stakeholder_views_server.py`

```python
import asyncio
import json
from typing import Any, Dict, List, Optional
import structlog
from dataclasses import dataclass
from enum import Enum

from ai_agent.infrastructure.mcp.protocol import (
    MCPTool,
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPErrorCode
)
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.domain.knowledge_models import StakeholderGroup

logger = structlog.get_logger()

class StakeholderViewsServer:
    """MCP server for stakeholder views tool."""

    def __init__(self, transcript_store: TranscriptStore):
        self.transcript_store = transcript_store
        self.tool_definition = self._create_tool_definition()

    def _create_tool_definition(self) -> MCPTool:
        """Create the stakeholder views tool definition."""
        return MCPTool(
            name="get_stakeholder_views",
            description="Retrieves relevant opinions, statements, and data points from transcripts of stakeholder groups. Use this tool to gather evidence before answering any question about stakeholder perspectives.",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic to search for within the transcripts. For example: 'cost of open banking', 'governance models', 'commercial viability of Project Perseus', 'cross-sector interoperability'."
                    },
                    "stakeholder_group": {
                        "type": "string",
                        "enum": ["BankRep", "TradeBodyRep", "PaymentsEcosystemRep"],
                        "description": "Optional filter by stakeholder group. If not provided, searches across all groups."
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of results to return (1-50)."
                    },
                    "min_relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.3,
                        "description": "Minimum relevance score for results (0.0-1.0)."
                    }
                },
                "required": ["topic"]
            },
            metadata={
                "category": "research",
                "version": "1.0.0",
                "author": "AI Agent System"
            }
        )

    async def handle_tool_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tool call requests."""
        try:
            if request.method != "tools/call":
                raise MCPError(
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Invalid method for tool call"
                )

            params = request.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name != "get_stakeholder_views":
                raise MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Tool '{tool_name}' not found"
                )

            # Validate required parameters
            if "topic" not in arguments:
                raise MCPError(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message="Parameter 'topic' is required"
                )

            # Extract parameters
            topic = arguments["topic"]
            stakeholder_group = arguments.get("stakeholder_group")
            limit = min(arguments.get("limit", 10), 50)  # Cap at 50
            min_relevance_score = arguments.get("min_relevance_score", 0.3)

            # Convert stakeholder group string to enum
            stakeholder_group_enum = None
            if stakeholder_group:
                try:
                    stakeholder_group_enum = StakeholderGroup(stakeholder_group)
                except ValueError:
                    raise MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message=f"Invalid stakeholder group: {stakeholder_group}"
                    )

            # Execute search
            results = await self._search_stakeholder_views(
                topic=topic,
                stakeholder_group=stakeholder_group_enum,
                limit=limit,
                min_relevance_score=min_relevance_score
            )

            # Format response
            response_data = {
                "topic": topic,
                "stakeholder_group": stakeholder_group,
                "results_count": len(results),
                "results": results
            }

            return MCPResponse(
                id=request.id,
                result=response_data
            )

        except MCPError:
            raise
        except Exception as e:
            logger.error("Error handling tool call", error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}"
            )

    async def _search_stakeholder_views(
        self,
        topic: str,
        stakeholder_group: Optional[StakeholderGroup] = None,
        limit: int = 10,
        min_relevance_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search for stakeholder views on a topic."""
        try:
            # Perform semantic search
            segments_with_scores = await self.transcript_store.search_segments(
                query=topic,
                stakeholder_group=stakeholder_group,
                limit=limit * 2  # Get more results for filtering
            )

            # Filter by relevance score and format results
            filtered_results = []
            for segment, score in segments_with_scores:
                if score >= min_relevance_score:
                    result = {
                        "segment_id": str(segment.id),
                        "speaker_name": segment.speaker_name,
                        "speaker_title": segment.speaker_title,
                        "content": segment.content,
                        "relevance_score": round(score, 3),
                        "stakeholder_group": self._infer_stakeholder_group(segment),
                        "metadata": {
                            "transcript_id": str(segment.transcript_id),
                            "segment_index": segment.segment_index,
                            "created_at": segment.created_at.isoformat()
                        }
                    }
                    filtered_results.append(result)

                    if len(filtered_results) >= limit:
                        break

            # Sort by relevance score (descending)
            filtered_results.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info(
                "Stakeholder views search completed",
                topic=topic,
                stakeholder_group=stakeholder_group,
                results_count=len(filtered_results)
            )

            return filtered_results

        except Exception as e:
            logger.error("Error searching stakeholder views", error=str(e))
            return []

    def _infer_stakeholder_group(self, segment) -> str:
        """Infer stakeholder group from segment metadata."""
        # This would be populated during transcript processing
        return segment.metadata.get("stakeholder_group", "Unknown")

    async def get_tool_definition(self) -> MCPTool:
        """Get the tool definition."""
        return self.tool_definition
```

### 2.2 Search and Retrieval Logic

**File**: `src/ai_agent/infrastructure/mcp/servers/stakeholder_search.py`

```python
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import structlog
from dataclasses import dataclass
import re
from collections import Counter

from ai_agent.domain.knowledge_models import StakeholderGroup
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore

logger = structlog.get_logger()

@dataclass
class SearchResult:
    """Enhanced search result with additional metadata."""
    segment_id: str
    speaker_name: str
    content: str
    relevance_score: float
    stakeholder_group: str
    topic_matches: List[str]
    sentiment_score: float
    confidence_level: str
    metadata: Dict[str, Any]

class StakeholderSearchEngine:
    """Advanced search engine for stakeholder views."""

    def __init__(self, transcript_store: TranscriptStore):
        self.transcript_store = transcript_store
        self.topic_keywords = self._load_topic_keywords()
        self.sentiment_keywords = self._load_sentiment_keywords()

    async def search_with_analysis(
        self,
        topic: str,
        stakeholder_group: Optional[StakeholderGroup] = None,
        limit: int = 10,
        include_analysis: bool = True
    ) -> List[SearchResult]:
        """Search with enhanced analysis and scoring."""
        try:
            # Get basic search results
            segments_with_scores = await self.transcript_store.search_segments(
                query=topic,
                stakeholder_group=stakeholder_group,
                limit=limit * 2
            )

            # Enhance results with analysis
            enhanced_results = []
            for segment, base_score in segments_with_scores:
                enhanced_result = await self._enhance_search_result(
                    segment, base_score, topic, include_analysis
                )
                enhanced_results.append(enhanced_result)

            # Sort by enhanced relevance score
            enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)

            return enhanced_results[:limit]

        except Exception as e:
            logger.error("Error in enhanced search", error=str(e))
            return []

    async def _enhance_search_result(
        self,
        segment,
        base_score: float,
        topic: str,
        include_analysis: bool
    ) -> SearchResult:
        """Enhance search result with additional analysis."""
        # Find topic keyword matches
        topic_matches = self._find_topic_matches(segment.content, topic)

        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment(segment.content)

        # Determine confidence level
        confidence_level = self._determine_confidence(
            base_score, len(topic_matches), sentiment_score
        )

        # Adjust relevance score based on analysis
        enhanced_score = self._adjust_relevance_score(
            base_score, topic_matches, sentiment_score
        )

        return SearchResult(
            segment_id=str(segment.id),
            speaker_name=segment.speaker_name,
            content=segment.content,
            relevance_score=enhanced_score,
            stakeholder_group=segment.metadata.get("stakeholder_group", "Unknown"),
            topic_matches=topic_matches,
            sentiment_score=sentiment_score,
            confidence_level=confidence_level,
            metadata={
                "transcript_id": str(segment.transcript_id),
                "segment_index": segment.segment_index,
                "base_score": base_score,
                "analysis_included": include_analysis
            }
        )

    def _find_topic_matches(self, content: str, topic: str) -> List[str]:
        """Find specific topic keyword matches in content."""
        content_lower = content.lower()
        topic_lower = topic.lower()

        matches = []

        # Direct topic matches
        if topic_lower in content_lower:
            matches.append(topic)

        # Related keyword matches
        topic_keywords = self.topic_keywords.get(topic_lower, [])
        for keyword in topic_keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)

        # Extract quoted statements
        quoted_matches = re.findall(r'"([^"]*' + re.escape(topic_lower) + r'[^"]*)"', content_lower)
        matches.extend(quoted_matches)

        return list(set(matches))  # Remove duplicates

    def _calculate_sentiment(self, content: str) -> float:
        """Calculate sentiment score for content (-1.0 to 1.0)."""
        content_lower = content.lower()

        positive_words = self.sentiment_keywords["positive"]
        negative_words = self.sentiment_keywords["negative"]

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        total_words = len(content.split())
        if total_words == 0:
            return 0.0

        # Normalize by content length
        positive_score = positive_count / total_words
        negative_score = negative_count / total_words

        # Return sentiment score (-1.0 to 1.0)
        return positive_score - negative_score

    def _determine_confidence(
        self,
        base_score: float,
        topic_matches: int,
        sentiment_score: float
    ) -> str:
        """Determine confidence level for search result."""
        if base_score >= 0.8 and topic_matches >= 3:
            return "high"
        elif base_score >= 0.6 and topic_matches >= 2:
            return "medium"
        elif base_score >= 0.4 and topic_matches >= 1:
            return "low"
        else:
            return "very_low"

    def _adjust_relevance_score(
        self,
        base_score: float,
        topic_matches: List[str],
        sentiment_score: float
    ) -> float:
        """Adjust relevance score based on additional analysis."""
        # Boost score for topic keyword matches
        keyword_boost = min(len(topic_matches) * 0.1, 0.3)

        # Boost score for strong sentiment (either positive or negative)
        sentiment_boost = abs(sentiment_score) * 0.1

        # Combine scores
        enhanced_score = base_score + keyword_boost + sentiment_boost

        # Cap at 1.0
        return min(enhanced_score, 1.0)

    def _load_topic_keywords(self) -> Dict[str, List[str]]:
        """Load topic-specific keywords for matching."""
        return {
            "commercial sustainability": [
                "commercial", "sustainability", "ROI", "revenue", "profit",
                "business case", "commercial model", "viability", "economic"
            ],
            "governance": [
                "governance", "regulation", "compliance", "oversight",
                "authority", "mandate", "enforcement", "rules", "policy"
            ],
            "cost": [
                "cost", "expense", "investment", "budget", "price",
                "expensive", "affordable", "economic", "financial"
            ],
            "interoperability": [
                "interoperability", "integration", "compatibility",
                "cross-sector", "standardization", "unified", "connected"
            ],
            "technical feasibility": [
                "technical", "implementation", "infrastructure",
                "architecture", "system", "technology", "feasible"
            ]
        }

    def _load_sentiment_keywords(self) -> Dict[str, List[str]]:
        """Load sentiment analysis keywords."""
        return {
            "positive": [
                "good", "excellent", "beneficial", "positive", "support",
                "agree", "effective", "successful", "valuable", "important"
            ],
            "negative": [
                "bad", "poor", "problematic", "negative", "concern",
                "disagree", "ineffective", "failed", "risky", "expensive"
            ]
        }
```

### 2.3 MCP Server Registration

**File**: `src/ai_agent/infrastructure/mcp/servers/registry.py`

```python
import asyncio
from typing import Dict, Any, Optional
import structlog
from dataclasses import dataclass

from ai_agent.infrastructure.mcp.server_manager import MCPServerManager, MCPServerType
from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import StakeholderViewsServer
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore

logger = structlog.get_logger()

@dataclass
class ServerConfig:
    """Configuration for MCP server registration."""
    name: str
    description: str
    command: list[str]
    env: Dict[str, str]
    working_directory: Optional[str] = None

class StakeholderViewsServerRegistry:
    """Registry for stakeholder views MCP server."""

    def __init__(self, server_manager: MCPServerManager, transcript_store: TranscriptStore):
        self.server_manager = server_manager
        self.transcript_store = transcript_store
        self.server_id: Optional[str] = None
        self.server_instance: Optional[StakeholderViewsServer] = None

    async def register_server(self) -> str:
        """Register the stakeholder views MCP server."""
        try:
            # Create server configuration
            config = ServerConfig(
                name="stakeholder-views-server",
                description="MCP server for querying stakeholder views from transcripts",
                command=["python", "-m", "ai_agent.infrastructure.mcp.servers.stakeholder_views_server"],
                env={
                    "PYTHONPATH": ".",
                    "LOG_LEVEL": "INFO"
                },
                working_directory="."
            )

            # Register with server manager
            self.server_id = await self.server_manager.register_server(
                name=config.name,
                server_type=MCPServerType.PROCESS,
                endpoint="",  # Not used for process servers
                command=config.command,
                env=config.env,
                working_directory=config.working_directory,
                description=config.description
            )

            # Start the server
            success = await self.server_manager.start_server(self.server_id)
            if not success:
                raise RuntimeError("Failed to start stakeholder views server")

            # Create server instance for direct access
            self.server_instance = StakeholderViewsServer(self.transcript_store)

            logger.info(
                "Stakeholder views server registered and started",
                server_id=self.server_id
            )

            return self.server_id

        except Exception as e:
            logger.error("Failed to register stakeholder views server", error=str(e))
            raise

    async def unregister_server(self) -> bool:
        """Unregister the stakeholder views MCP server."""
        if not self.server_id:
            return False

        try:
            success = await self.server_manager.unregister_server(self.server_id)
            if success:
                self.server_id = None
                self.server_instance = None
                logger.info("Stakeholder views server unregistered")

            return success

        except Exception as e:
            logger.error("Failed to unregister stakeholder views server", error=str(e))
            return False

    async def get_server_status(self) -> Optional[str]:
        """Get server status."""
        if not self.server_id:
            return None

        return await self.server_manager.get_server_status(self.server_id)

    async def health_check(self) -> bool:
        """Perform health check on server."""
        if not self.server_id:
            return False

        return await self.server_manager.health_check_server(self.server_id)

    def get_server_instance(self) -> Optional[StakeholderViewsServer]:
        """Get direct access to server instance."""
        return self.server_instance
```

### 2.4 Integration with Existing MCP Infrastructure

**File**: `src/ai_agent/infrastructure/mcp/integration.py`

```python
import asyncio
from typing import Optional
import structlog

from ai_agent.infrastructure.mcp.server_manager import MCPServerManager
from ai_agent.infrastructure.mcp.tool_registry import ToolRegistry
from ai_agent.infrastructure.knowledge.transcript_store import TranscriptStore
from ai_agent.infrastructure.mcp.servers.registry import StakeholderViewsServerRegistry

logger = structlog.get_logger()

class MCPIntegrationManager:
    """Manages integration of new MCP servers with existing infrastructure."""

    def __init__(
        self,
        server_manager: MCPServerManager,
        tool_registry: ToolRegistry,
        transcript_store: TranscriptStore
    ):
        self.server_manager = server_manager
        self.tool_registry = tool_registry
        self.transcript_store = transcript_store
        self.stakeholder_views_registry: Optional[StakeholderViewsServerRegistry] = None

    async def initialize_stakeholder_views_server(self) -> bool:
        """Initialize and register the stakeholder views MCP server."""
        try:
            # Create registry
            self.stakeholder_views_registry = StakeholderViewsServerRegistry(
                self.server_manager,
                self.transcript_store
            )

            # Register server
            server_id = await self.stakeholder_views_registry.register_server()

            # Wait for server to be ready
            await asyncio.sleep(2)

            # Verify server is running
            if not await self.stakeholder_views_registry.health_check():
                raise RuntimeError("Stakeholder views server failed health check")

            # Register tools with tool registry
            await self._register_stakeholder_views_tools(server_id)

            logger.info("Stakeholder views MCP server initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize stakeholder views server", error=str(e))
            return False

    async def _register_stakeholder_views_tools(self, server_id: str) -> None:
        """Register stakeholder views tools with the tool registry."""
        try:
            # Get server instance
            server_instance = self.stakeholder_views_registry.get_server_instance()
            if not server_instance:
                raise RuntimeError("Server instance not available")

            # Get tool definition
            tool_definition = await server_instance.get_tool_definition()

            # Register with tool registry
            await self.tool_registry.register_tool(
                tool=tool_definition,
                server_id=server_id,
                metadata={
                    "category": "research",
                    "version": "1.0.0",
                    "description": "Query stakeholder views from transcripts"
                }
            )

            logger.info("Stakeholder views tools registered successfully")

        except Exception as e:
            logger.error("Failed to register stakeholder views tools", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Shutdown all registered servers."""
        try:
            if self.stakeholder_views_registry:
                await self.stakeholder_views_registry.unregister_server()

            logger.info("MCP integration manager shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
```

### 2.5 API Endpoints

**File**: `src/ai_agent/api/v1/stakeholder_views.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
import structlog

from ai_agent.infrastructure.mcp.servers.stakeholder_views_server import StakeholderViewsServer
from ai_agent.domain.knowledge_models import StakeholderGroup

logger = structlog.get_logger()
router = APIRouter(prefix="/stakeholder-views", tags=["stakeholder-views"])

class StakeholderViewsRequest(BaseModel):
    """Request model for stakeholder views search."""
    topic: str = Field(..., description="Topic to search for")
    stakeholder_group: Optional[StakeholderGroup] = Field(None, description="Filter by stakeholder group")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    min_relevance_score: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relevance score")

class StakeholderViewsResponse(BaseModel):
    """Response model for stakeholder views search."""
    topic: str
    stakeholder_group: Optional[str]
    results_count: int
    results: List[dict]

@router.post("/search", response_model=StakeholderViewsResponse)
async def search_stakeholder_views(
    request: StakeholderViewsRequest,
    server: StakeholderViewsServer = Depends(get_stakeholder_views_server)
) -> StakeholderViewsResponse:
    """Search for stakeholder views on a specific topic."""
    try:
        # Create mock MCP request
        from ai_agent.infrastructure.mcp.protocol import MCPRequest
        mcp_request = MCPRequest(
            method="tools/call",
            params={
                "name": "get_stakeholder_views",
                "arguments": {
                    "topic": request.topic,
                    "stakeholder_group": request.stakeholder_group.value if request.stakeholder_group else None,
                    "limit": request.limit,
                    "min_relevance_score": request.min_relevance_score
                }
            }
        )

        # Handle tool call
        response = await server.handle_tool_call(mcp_request)

        if response.error:
            raise HTTPException(
                status_code=400,
                detail=f"Search failed: {response.error.get('message', 'Unknown error')}"
            )

        return StakeholderViewsResponse(**response.result)

    except Exception as e:
        logger.error("Error searching stakeholder views", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check(
    server: StakeholderViewsServer = Depends(get_stakeholder_views_server)
) -> dict:
    """Health check for stakeholder views service."""
    return {"status": "healthy", "service": "stakeholder-views"}

def get_stakeholder_views_server() -> StakeholderViewsServer:
    """Dependency to get stakeholder views server instance."""
    # This would be injected from the application context
    # Implementation depends on your DI container setup
    pass
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_stakeholder_views_server.py`
- Test tool definition creation
- Test parameter validation
- Test search result formatting
- Test error handling

### Integration Tests
- **File**: `tests/integration/test_stakeholder_views_integration.py`
- Test MCP server registration
- Test tool discovery and execution
- Test end-to-end search functionality

### Performance Tests
- **File**: `tests/performance/test_stakeholder_views_performance.py`
- Test search response times
- Test concurrent request handling
- Test memory usage with large result sets

## Success Criteria

1. **Tool Discovery**: Stakeholder views tool discoverable through MCP protocol
2. **Search Accuracy**: >90% relevance score accuracy for topic-based searches
3. **Response Time**: <500ms average response time for search queries
4. **Integration**: Seamless integration with existing MCP infrastructure
5. **Reliability**: 99.9% uptime for tool execution

## Dependencies

This phase depends on:
- Phase 1: Transcript ingestion system must be completed
- Existing MCP infrastructure (server manager, tool registry)
- Vector database and embedding models

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 3: Synthetic representative agents that use this tool
- Phase 4: Evaluation framework that relies on agent responses

The stakeholder views MCP server must be fully functional and tested before proceeding to Phase 3.
