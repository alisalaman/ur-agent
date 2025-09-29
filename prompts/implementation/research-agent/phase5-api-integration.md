# Phase 5: API Integration and Web Interface

## Overview

This phase implements the API endpoints and web interface for the synthetic representative agent system. It provides REST APIs for agent management, evaluation execution, and report generation, along with WebSocket support for real-time interactions.

## Objectives

- Create comprehensive REST API for the synthetic agent system
- Implement WebSocket support for real-time agent interactions
- Build web interface for governance model evaluation
- Integrate with existing API infrastructure
- Provide authentication and authorization

## Implementation Tasks

### 5.1 REST API Endpoints

**File**: `src/ai_agent/api/v1/synthetic_agents.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
import structlog

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType
from ai_agent.core.evaluation.governance_evaluator import GovernanceEvaluator
from ai_agent.core.evaluation.report_generator import GovernanceReportGenerator

logger = structlog.get_logger()
router = APIRouter(prefix="/synthetic-agents", tags=["synthetic-agents"])

class AgentQueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str = Field(..., description="Query to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    persona_type: str = Field(..., description="Persona type to use")

class AgentQueryResponse(BaseModel):
    """Response model for agent queries."""
    response: str
    persona_type: str
    evidence_count: int
    confidence_level: str
    processing_time_ms: int

class MultiAgentQueryRequest(BaseModel):
    """Request model for multi-agent queries."""
    query: str = Field(..., description="Query to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    include_personas: Optional[List[str]] = Field(None, description="Persona types to include")

class MultiAgentQueryResponse(BaseModel):
    """Response model for multi-agent queries."""
    responses: Dict[str, str]
    processing_time_ms: int
    total_evidence_count: int

class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    persona_type: str
    status: str
    conversation_length: int
    cache_size: int
    last_activity: Optional[str] = None

# Dependency injection
def get_persona_service() -> PersonaAgentService:
    """Get persona service instance."""
    # This would be injected from the application context
    pass

@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    request: AgentQueryRequest,
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> AgentQueryResponse:
    """Query a specific persona agent."""
    try:
        # Validate persona type
        try:
            persona_type = PersonaType(request.persona_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid persona type: {request.persona_type}")
        
        # Process query
        import time
        start_time = time.time()
        
        response = await persona_service.process_query(
            persona_type=persona_type,
            query=request.query,
            context=request.context
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Get agent status for additional metadata
        agent_status = await persona_service.get_agent_status(persona_type)
        
        return AgentQueryResponse(
            response=response,
            persona_type=persona_type.value,
            evidence_count=agent_status.get("cache_size", 0) if agent_status else 0,
            confidence_level="medium",  # This would be calculated from response analysis
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error("Agent query failed", error=str(e))
        raise HTTPException(status_code=500, detail="Query processing failed")

@router.post("/query-all", response_model=MultiAgentQueryResponse)
async def query_all_agents(
    request: MultiAgentQueryRequest,
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> MultiAgentQueryResponse:
    """Query all persona agents."""
    try:
        # Convert persona types
        include_personas = None
        if request.include_personas:
            include_personas = [PersonaType(p) for p in request.include_personas]
        
        # Process query with all agents
        import time
        start_time = time.time()
        
        responses = await persona_service.process_query_all_personas(
            query=request.query,
            context=request.context
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Calculate total evidence count
        total_evidence_count = 0
        for persona_type in responses.keys():
            agent_status = await persona_service.get_agent_status(persona_type)
            if agent_status:
                total_evidence_count += agent_status.get("cache_size", 0)
        
        return MultiAgentQueryResponse(
            responses={persona_type.value: response for persona_type, response in responses.items()},
            processing_time_ms=processing_time,
            total_evidence_count=total_evidence_count
        )
        
    except Exception as e:
        logger.error("Multi-agent query failed", error=str(e))
        raise HTTPException(status_code=500, detail="Multi-agent query processing failed")

@router.get("/status", response_model=List[AgentStatusResponse])
async def get_agent_status(
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> List[AgentStatusResponse]:
    """Get status of all agents."""
    try:
        status_data = await persona_service.get_all_agent_status()
        
        responses = []
        for persona_type, status in status_data.items():
            if status:
                responses.append(AgentStatusResponse(
                    persona_type=persona_type.value,
                    status=status.get("status", "unknown"),
                    conversation_length=status.get("conversation_length", 0),
                    cache_size=status.get("cache_size", 0),
                    last_activity=None  # This would be tracked in practice
                ))
        
        return responses
        
    except Exception as e:
        logger.error("Failed to get agent status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get agent status")

@router.post("/clear-cache")
async def clear_agent_cache(
    persona_type: Optional[str] = Query(None, description="Persona type to clear cache for"),
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> Dict[str, str]:
    """Clear evidence cache for agents."""
    try:
        if persona_type:
            try:
                persona_enum = PersonaType(persona_type)
                await persona_service.clear_agent_cache(persona_enum)
                return {"message": f"Cache cleared for {persona_type}"}
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid persona type: {persona_type}")
        else:
            await persona_service.clear_agent_cache()
            return {"message": "Cache cleared for all agents"}
        
    except Exception as e:
        logger.error("Failed to clear agent cache", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.get("/health")
async def health_check(
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> Dict[str, Any]:
    """Health check for synthetic agents service."""
    try:
        health_data = await persona_service.health_check()
        return health_data
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {"status": "error", "healthy": False, "error": str(e)}
```

### 5.2 WebSocket Support

**File**: `src/ai_agent/api/websocket/synthetic_agents.py`

```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Optional
import json
import asyncio
import structlog
from uuid import uuid4

from ai_agent.core.agents.persona_service import PersonaAgentService
from ai_agent.core.agents.synthetic_representative import PersonaType

logger = structlog.get_logger()

class SyntheticAgentConnectionManager:
    """Manages WebSocket connections for synthetic agents."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time()
        }
        logger.info("WebSocket connection established", connection_id=connection_id)
    
    def disconnect(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            del self.connection_metadata[connection_id]
            logger.info("WebSocket connection closed", connection_id=connection_id)
    
    async def send_message(self, connection_id: str, message: Dict[str, any]) -> None:
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
                self.connection_metadata[connection_id]["last_activity"] = asyncio.get_event_loop().time()
            except Exception as e:
                logger.error("Failed to send message", connection_id=connection_id, error=str(e))
                self.disconnect(connection_id)
    
    async def broadcast(self, message: Dict[str, any]) -> None:
        """Broadcast a message to all connections."""
        for connection_id in list(self.active_connections.keys()):
            await self.send_message(connection_id, message)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

# Global connection manager
connection_manager = SyntheticAgentConnectionManager()

async def websocket_endpoint(
    websocket: WebSocket,
    persona_service: PersonaAgentService = Depends(get_persona_service)
) -> None:
    """WebSocket endpoint for synthetic agent interactions."""
    connection_id = str(uuid4())
    
    try:
        await connection_manager.connect(websocket, connection_id)
        
        # Send welcome message
        await connection_manager.send_message(connection_id, {
            "type": "welcome",
            "message": "Connected to synthetic agent service",
            "connection_id": connection_id,
            "available_personas": [persona.value for persona in PersonaType]
        })
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process message based on type
                response = await process_websocket_message(message, persona_service, connection_id)
                
                # Send response back to client
                await connection_manager.send_message(connection_id, response)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await connection_manager.send_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON message"
                })
            except Exception as e:
                logger.error("WebSocket message processing error", error=str(e))
                await connection_manager.send_message(connection_id, {
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(connection_id)

async def process_websocket_message(
    message: Dict[str, any], 
    persona_service: PersonaAgentService,
    connection_id: str
) -> Dict[str, any]:
    """Process a WebSocket message."""
    message_type = message.get("type")
    
    if message_type == "query":
        return await handle_query_message(message, persona_service)
    elif message_type == "query_all":
        return await handle_query_all_message(message, persona_service)
    elif message_type == "status":
        return await handle_status_message(persona_service)
    elif message_type == "ping":
        return {"type": "pong", "timestamp": asyncio.get_event_loop().time()}
    else:
        return {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }

async def handle_query_message(
    message: Dict[str, any], 
    persona_service: PersonaAgentService
) -> Dict[str, any]:
    """Handle single agent query message."""
    try:
        query = message.get("query", "")
        persona_type_str = message.get("persona_type", "")
        context = message.get("context", {})
        
        if not query or not persona_type_str:
            return {
                "type": "error",
                "message": "Query and persona_type are required"
            }
        
        # Validate persona type
        try:
            persona_type = PersonaType(persona_type_str)
        except ValueError:
            return {
                "type": "error",
                "message": f"Invalid persona type: {persona_type_str}"
            }
        
        # Process query
        response = await persona_service.process_query(
            persona_type=persona_type,
            query=query,
            context=context
        )
        
        return {
            "type": "query_response",
            "persona_type": persona_type.value,
            "response": response,
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error("Query message handling failed", error=str(e))
        return {
            "type": "error",
            "message": f"Query processing failed: {str(e)}"
        }

async def handle_query_all_message(
    message: Dict[str, any], 
    persona_service: PersonaAgentService
) -> Dict[str, any]:
    """Handle multi-agent query message."""
    try:
        query = message.get("query", "")
        include_personas = message.get("include_personas", [])
        context = message.get("context", {})
        
        if not query:
            return {
                "type": "error",
                "message": "Query is required"
            }
        
        # Convert persona types
        persona_types = None
        if include_personas:
            try:
                persona_types = [PersonaType(p) for p in include_personas]
            except ValueError as e:
                return {
                    "type": "error",
                    "message": f"Invalid persona type in include_personas: {str(e)}"
                }
        
        # Process query with all agents
        responses = await persona_service.process_query_all_personas(
            query=query,
            context=context
        )
        
        return {
            "type": "query_all_response",
            "responses": {persona_type.value: response for persona_type, response in responses.items()},
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error("Query all message handling failed", error=str(e))
        return {
            "type": "error",
            "message": f"Multi-agent query processing failed: {str(e)}"
        }

async def handle_status_message(persona_service: PersonaAgentService) -> Dict[str, any]:
    """Handle status request message."""
    try:
        status_data = await persona_service.get_all_agent_status()
        
        return {
            "type": "status_response",
            "agents": {
                persona_type.value: status for persona_type, status in status_data.items()
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error("Status message handling failed", error=str(e))
        return {
            "type": "error",
            "message": f"Status retrieval failed: {str(e)}"
        }
```

### 5.3 Web Interface

**File**: `src/ai_agent/api/static/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synthetic Representative Agent System</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 20px;
        }
        .query-section {
            margin-bottom: 30px;
        }
        .query-form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .query-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .persona-select {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-secondary {
            background: #95a5a6;
            color: white;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .responses {
            display: grid;
            gap: 20px;
        }
        .response-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            background: #f9f9f9;
        }
        .response-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .persona-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .persona-bank { background: #e74c3c; color: white; }
        .persona-trade { background: #f39c12; color: white; }
        .persona-payments { background: #27ae60; color: white; }
        .response-content {
            line-height: 1.6;
        }
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-online { background: #27ae60; }
        .status-offline { background: #e74c3c; }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .error {
            background: #e74c3c;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="container">
            <div class="header">
                <h1>Synthetic Representative Agent System</h1>
                <p>Evidence-based governance model evaluation using AI personas</p>
            </div>
            
            <div class="content">
                <!-- Query Section -->
                <div class="query-section">
                    <h2>Query Agents</h2>
                    <div class="query-form">
                        <input 
                            v-model="query" 
                            @keyup.enter="querySingleAgent"
                            placeholder="Enter your question about governance models..."
                            class="query-input"
                        >
                        <select v-model="selectedPersona" class="persona-select">
                            <option value="BankRep">Bank Representative</option>
                            <option value="TradeBodyRep">Trade Body Representative</option>
                            <option value="PaymentsEcosystemRep">Payments Ecosystem Representative</option>
                        </select>
                        <button @click="querySingleAgent" class="btn btn-primary">Query Agent</button>
                        <button @click="queryAllAgents" class="btn btn-secondary">Query All</button>
                    </div>
                </div>
                
                <!-- Status Section -->
                <div class="status-section">
                    <h3>Agent Status</h3>
                    <div v-for="agent in agentStatus" :key="agent.persona_type" class="status-item">
                        <span class="status-indicator" :class="agent.status === 'idle' ? 'status-online' : 'status-offline'"></span>
                        {{ agent.persona_type }}: {{ agent.status }}
                    </div>
                </div>
                
                <!-- Loading Indicator -->
                <div v-if="loading" class="loading">
                    Processing query...
                </div>
                
                <!-- Error Display -->
                <div v-if="error" class="error">
                    {{ error }}
                </div>
                
                <!-- Responses -->
                <div v-if="responses.length > 0" class="responses">
                    <h3>Responses</h3>
                    <div v-for="response in responses" :key="response.id" class="response-card">
                        <div class="response-header">
                            <span class="persona-badge" :class="'persona-' + response.persona_type.toLowerCase().replace('rep', '')">
                                {{ response.persona_type }}
                            </span>
                            <span class="response-meta">
                                {{ response.processing_time_ms }}ms | 
                                Evidence: {{ response.evidence_count }}
                            </span>
                        </div>
                        <div class="response-content" v-html="formatResponse(response.response)"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    query: '',
                    selectedPersona: 'BankRep',
                    responses: [],
                    agentStatus: [],
                    loading: false,
                    error: null,
                    ws: null
                }
            },
            mounted() {
                this.initializeWebSocket();
                this.loadAgentStatus();
            },
            methods: {
                async initializeWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws/synthetic-agents`;
                    
                    try {
                        this.ws = new WebSocket(wsUrl);
                        
                        this.ws.onopen = () => {
                            console.log('WebSocket connected');
                        };
                        
                        this.ws.onmessage = (event) => {
                            const message = JSON.parse(event.data);
                            this.handleWebSocketMessage(message);
                        };
                        
                        this.ws.onclose = () => {
                            console.log('WebSocket disconnected');
                        };
                        
                        this.ws.onerror = (error) => {
                            console.error('WebSocket error:', error);
                        };
                    } catch (error) {
                        console.error('Failed to initialize WebSocket:', error);
                    }
                },
                
                handleWebSocketMessage(message) {
                    if (message.type === 'query_response') {
                        this.responses.push({
                            id: Date.now(),
                            persona_type: message.persona_type,
                            response: message.response,
                            processing_time_ms: 0,
                            evidence_count: 0
                        });
                    } else if (message.type === 'query_all_response') {
                        this.responses = [];
                        for (const [personaType, response] of Object.entries(message.responses)) {
                            this.responses.push({
                                id: Date.now() + Math.random(),
                                persona_type: personaType,
                                response: response,
                                processing_time_ms: 0,
                                evidence_count: 0
                            });
                        }
                    } else if (message.type === 'status_response') {
                        this.agentStatus = Object.entries(message.agents).map(([personaType, status]) => ({
                            persona_type: personaType,
                            status: status.status || 'unknown'
                        }));
                    }
                },
                
                async querySingleAgent() {
                    if (!this.query.trim()) return;
                    
                    this.loading = true;
                    this.error = null;
                    
                    try {
                        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                            this.ws.send(JSON.stringify({
                                type: 'query',
                                query: this.query,
                                persona_type: this.selectedPersona
                            }));
                        } else {
                            const response = await axios.post('/api/v1/synthetic-agents/query', {
                                query: this.query,
                                persona_type: this.selectedPersona
                            });
                            
                            this.responses = [response.data];
                        }
                    } catch (error) {
                        this.error = error.response?.data?.detail || 'Query failed';
                    } finally {
                        this.loading = false;
                    }
                },
                
                async queryAllAgents() {
                    if (!this.query.trim()) return;
                    
                    this.loading = true;
                    this.error = null;
                    
                    try {
                        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                            this.ws.send(JSON.stringify({
                                type: 'query_all',
                                query: this.query
                            }));
                        } else {
                            const response = await axios.post('/api/v1/synthetic-agents/query-all', {
                                query: this.query
                            });
                            
                            this.responses = Object.entries(response.data.responses).map(([personaType, response]) => ({
                                id: Date.now() + Math.random(),
                                persona_type: personaType,
                                response: response,
                                processing_time_ms: response.data.processing_time_ms,
                                evidence_count: response.data.evidence_count
                            }));
                        }
                    } catch (error) {
                        this.error = error.response?.data?.detail || 'Query failed';
                    } finally {
                        this.loading = false;
                    }
                },
                
                async loadAgentStatus() {
                    try {
                        const response = await axios.get('/api/v1/synthetic-agents/status');
                        this.agentStatus = response.data;
                    } catch (error) {
                        console.error('Failed to load agent status:', error);
                    }
                },
                
                formatResponse(response) {
                    // Simple formatting for display
                    return response.replace(/\n/g, '<br>');
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
```

### 5.4 Integration with Existing API

**File**: `src/ai_agent/api/v1/router.py`

```python
from fastapi import APIRouter
from ai_agent.api.v1.synthetic_agents import router as synthetic_agents_router
from ai_agent.api.v1.governance_evaluation import router as governance_evaluation_router
from ai_agent.api.v1.stakeholder_views import router as stakeholder_views_router

# Include new routers
router = APIRouter()
router.include_router(synthetic_agents_router)
router.include_router(governance_evaluation_router)
router.include_router(stakeholder_views_router)
```

### 5.5 WebSocket Router

**File**: `src/ai_agent/api/websocket/router.py`

```python
from fastapi import APIRouter, WebSocket
from ai_agent.api.websocket.synthetic_agents import websocket_endpoint

router = APIRouter()

@router.websocket("/synthetic-agents")
async def synthetic_agents_websocket(websocket: WebSocket):
    """WebSocket endpoint for synthetic agents."""
    await websocket_endpoint(websocket)
```

### 5.6 Authentication and Authorization

**File**: `src/ai_agent/api/middleware/auth.py`

```python
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

logger = structlog.get_logger()

security = HTTPBearer()

class SyntheticAgentAuth:
    """Authentication for synthetic agent endpoints."""
    
    def __init__(self):
        self.allowed_roles = ["admin", "researcher", "evaluator"]
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """Verify JWT token and return user ID."""
        try:
            # This would integrate with your existing auth system
            # For now, return a mock user ID
            token = credentials.credentials
            
            # Validate token (implement based on your auth system)
            user_id = await self._validate_token(token)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            return user_id
            
        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def _validate_token(self, token: str) -> Optional[str]:
        """Validate JWT token and return user ID."""
        # Implement token validation logic
        # This would integrate with your existing auth system
        return "user_123"  # Mock implementation
    
    async def check_permissions(self, user_id: str, required_role: str = "researcher") -> bool:
        """Check if user has required permissions."""
        # Implement permission checking logic
        # This would integrate with your existing auth system
        return True  # Mock implementation

# Global auth instance
synthetic_auth = SyntheticAgentAuth()

# Dependency for protected endpoints
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated user."""
    return await synthetic_auth.verify_token(credentials)
```

## Testing Strategy

### Unit Tests
- **File**: `tests/unit/test_api_synthetic_agents.py`
- Test API endpoint functionality
- Test request/response models
- Test error handling
- Test authentication

### Integration Tests
- **File**: `tests/integration/test_api_integration.py`
- Test end-to-end API workflows
- Test WebSocket functionality
- Test multi-agent coordination

### Performance Tests
- **File**: `tests/performance/test_api_performance.py`
- Test API response times
- Test concurrent request handling
- Test WebSocket connection limits

## Success Criteria

1. **API Functionality**: All endpoints working correctly with proper error handling
2. **WebSocket Support**: Real-time communication working reliably
3. **Web Interface**: User-friendly interface for agent interactions
4. **Authentication**: Proper security and access control
5. **Performance**: <2 second response times for typical queries

## Dependencies

This phase depends on:
- Phase 1: Transcript ingestion system
- Phase 2: Stakeholder views MCP server
- Phase 3: Synthetic agent system
- Phase 4: Governance evaluation framework
- Existing API infrastructure

## Next Phase Dependencies

This phase creates the foundation for:
- Phase 6: Configuration and deployment
- Phase 7: Testing and validation

The API integration must be fully functional and tested before proceeding to Phase 6.
