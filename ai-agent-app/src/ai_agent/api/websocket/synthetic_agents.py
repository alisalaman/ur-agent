"""WebSocket endpoints for synthetic agent interactions."""

import asyncio
import json
import time
from typing import Any
from uuid import uuid4
from collections import defaultdict, deque

from fastapi import WebSocket, WebSocketDisconnect
import structlog

# Import from shared dependencies to avoid circular imports
from ai_agent.api.dependencies import get_persona_service
from ai_agent.api.validation.synthetic_agents import (
    validate_websocket_message_size,
    validate_websocket_message_content,
    validate_persona_type_string,
    sanitize_error_message,
)

logger = structlog.get_logger()

# Security constants
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MAX_MESSAGES_PER_MINUTE = 60
RATE_LIMIT_WINDOW = 60  # seconds


class SyntheticAgentConnectionManager:
    """Manages WebSocket connections for synthetic agents with security features."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_metadata: dict[str, dict[str, Any]] = {}
        self.rate_limits: dict[str, deque[float]] = defaultdict(lambda: deque())
        self._lock = asyncio.Lock()

    async def connect(
        self, websocket: WebSocket, connection_id: str, user_id: str
    ) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time(),
        }
        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            user_id=user_id,
        )

    def disconnect(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            logger.info("WebSocket connection closed", connection_id=connection_id)

    async def send_message(self, connection_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(
                    json.dumps(message)
                )
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id][
                        "last_activity"
                    ] = asyncio.get_event_loop().time()
            except Exception as e:
                logger.error(
                    "Failed to send message", connection_id=connection_id, error=str(e)
                )
                self.disconnect(connection_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        for connection_id in list(self.active_connections.keys()):
            await self.send_message(connection_id, message)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_user_connections(self, user_id: str) -> list[str]:
        """Get connection IDs for a specific user."""
        return [
            conn_id
            for conn_id, metadata in self.connection_metadata.items()
            if metadata.get("user_id") == user_id
        ]

    async def check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection is within rate limits."""
        async with self._lock:
            now = time.time()
            message_times = self.rate_limits[connection_id]

            # Remove old messages outside the window
            while message_times and now - message_times[0] > RATE_LIMIT_WINDOW:
                message_times.popleft()

            # Check if under limit
            if len(message_times) >= MAX_MESSAGES_PER_MINUTE:
                return False

            # Add current message time
            message_times.append(now)
            return True

    async def cleanup_old_rate_limits(self) -> None:
        """Clean up old rate limit data."""
        async with self._lock:
            now = time.time()
            connections_to_remove = []

            for conn_id, message_times in self.rate_limits.items():
                # Remove old messages
                while message_times and now - message_times[0] > RATE_LIMIT_WINDOW:
                    message_times.popleft()

                # Remove empty rate limit entries
                if not message_times and conn_id not in self.active_connections:
                    connections_to_remove.append(conn_id)

            for conn_id in connections_to_remove:
                del self.rate_limits[conn_id]


# Global connection manager
connection_manager = SyntheticAgentConnectionManager()


async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    """WebSocket endpoint for synthetic agent interactions."""
    connection_id = str(uuid4())

    try:
        await connection_manager.connect(websocket, connection_id, user_id)

        # Send welcome message
        await connection_manager.send_message(
            connection_id,
            {
                "type": "welcome",
                "message": "Connected to synthetic agent service",
                "connection_id": connection_id,
                "available_personas": [
                    "BankRep",
                    "TradeBodyRep",
                    "PaymentsEcosystemRep",
                ],
            },
        )

        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()

                # Validate message size
                try:
                    validate_websocket_message_size(data, MAX_MESSAGE_SIZE)
                except ValueError as e:
                    await connection_manager.send_message(
                        connection_id, {"type": "error", "message": str(e)}
                    )
                    continue

                # Check rate limit
                if not await connection_manager.check_rate_limit(connection_id):
                    await connection_manager.send_message(
                        connection_id,
                        {
                            "type": "error",
                            "message": "Rate limit exceeded. Please slow down.",
                        },
                    )
                    continue

                # Parse and validate message content
                try:
                    message = json.loads(data)
                    validate_websocket_message_content(message)
                except (json.JSONDecodeError, ValueError) as e:
                    await connection_manager.send_message(
                        connection_id,
                        {"type": "error", "message": f"Invalid message: {str(e)}"},
                    )
                    continue

                # Process message based on type
                print(f"🔍 Processing message type: {message.get('type', 'unknown')}")
                print(f"🔍 Full message: {message}")

                try:
                    response = await process_websocket_message(
                        message, connection_id, user_id
                    )
                    print(f"🔍 Response generated: {response.get('type', 'unknown')}")
                    print(f"🔍 Full response: {response}")

                    # Send response back to client
                    await connection_manager.send_message(connection_id, response)
                    print("🔍 Response sent to client")
                except Exception as e:
                    print(f"❌ Error in message processing: {e}")
                    import traceback

                    traceback.print_exc()
                    # Send error response
                    error_response = {
                        "type": "error",
                        "message": f"Processing failed: {str(e)}",
                    }
                    await connection_manager.send_message(connection_id, error_response)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "WebSocket message processing error",
                    error=str(e),
                    connection_id=connection_id,
                )
                await connection_manager.send_message(
                    connection_id,
                    {"type": "error", "message": sanitize_error_message(e)},
                )

    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(connection_id)


async def process_websocket_message(
    message: dict[str, Any], connection_id: str, user_id: str
) -> dict[str, Any]:
    """Process a WebSocket message."""
    try:
        message_type = message.get("type")
        print(f"🔍 Processing message type: {message_type}")

        if message_type == "query":
            # Default to query_all behavior for single query messages
            print("🔍 Converting single query to query_all")
            response = await handle_query_all_message(message, connection_id, user_id)
            # Keep the original message type in response for frontend compatibility
            if response.get("type") == "query_all_response":
                response["type"] = "query_response"
            return response
        elif message_type == "query_all":
            return await handle_query_all_message(message, connection_id, user_id)
        elif message_type == "status":
            return await handle_status_message(connection_id, user_id)
        elif message_type == "ping":
            return {"type": "pong", "timestamp": asyncio.get_event_loop().time()}
        else:
            return {"type": "error", "message": f"Unknown message type: {message_type}"}
    except Exception as e:
        print(f"❌ Error processing WebSocket message: {e}")
        import traceback

        traceback.print_exc()
        return {"type": "error", "message": f"Error processing message: {str(e)}"}


async def handle_query_message(
    message: dict[str, Any], connection_id: str, user_id: str
) -> dict[str, Any]:
    """Handle single agent query message."""
    try:
        # Handle both frontend format (content) and backend format (query)
        query = message.get("query", "") or message.get("content", "")
        persona_type_str = message.get("persona_type", "")
        context = message.get("context", {})

        print(
            f"🔍 Message fields: query='{query}', persona_type='{persona_type_str}', content='{message.get('content', '')}'"
        )

        if not query:
            return {"type": "error", "message": "Query is required"}

        # If no persona_type provided, use a default one
        if not persona_type_str:
            persona_type_str = "BankRep"  # Default persona type
            print(f"🔍 No persona_type provided, using default: {persona_type_str}")

        # Validate persona type using secure validation
        try:
            persona_type = validate_persona_type_string(persona_type_str)
        except ValueError as e:
            return {"type": "error", "message": str(e)}

        # Get persona service
        persona_service = await get_persona_service()

        # Process query
        start_time = time.time()
        print(f"🔍 Processing query with persona_type: {persona_type}")
        print(f"🔍 Query: {query[:100]}...")
        print(f"🔍 Persona service initialized: {persona_service.initialized}")
        print(f"🔍 Available agents: {list(persona_service.agents.keys())}")

        response = await persona_service.process_query(
            persona_type=persona_type, query=query, context=context
        )
        processing_time = int((time.time() - start_time) * 1000)

        print(f"🔍 Response received: {response[:100] if response else 'None'}...")

        # Get agent status for metadata
        agent_status = await persona_service.get_agent_status(persona_type)

        return {
            "type": "query_response",
            "persona_type": persona_type,
            "response": response,
            "processing_time_ms": processing_time,
            "evidence_count": agent_status.get("cache_size", 0) if agent_status else 0,
            "timestamp": asyncio.get_event_loop().time(),
        }

    except Exception as e:
        logger.error(
            "Query message handling failed",
            error=str(e),
            connection_id=connection_id,
            user_id=user_id,
        )
        return {"type": "error", "message": sanitize_error_message(e)}


async def handle_query_all_message(
    message: dict[str, Any], connection_id: str, user_id: str
) -> dict[str, Any]:
    """Handle multi-agent query message."""
    print(f"🔍 handle_query_all_message called with message: {message}")
    try:
        # Handle both frontend format (content) and backend format (query)
        query = message.get("query", "") or message.get("content", "")
        include_personas = message.get("include_personas", [])
        context = message.get("context", {})

        print(
            f"🔍 Query all message fields: query='{query}', include_personas={include_personas}, content='{message.get('content', '')}'"
        )

        if not query:
            return {"type": "error", "message": "Query is required"}

        # Convert persona types if specified using secure validation
        if include_personas:
            try:
                # Validate persona types
                for p in include_personas:
                    validate_persona_type_string(p)
            except ValueError as e:
                return {"type": "error", "message": str(e)}

        # Get persona service
        print("🔍 Getting persona service...")
        persona_service = await get_persona_service()
        print(f"🔍 Persona service obtained: {persona_service}")
        print(f"🔍 Persona service initialized: {persona_service.initialized}")

        # Process query with all agents
        start_time = time.time()
        print(f"🔍 Calling process_query_all_personas with query: '{query}'")
        responses = await persona_service.process_query_all_personas(
            query=query, context=context
        )
        print(f"🔍 Got responses from process_query_all_personas: {responses}")
        processing_time = int((time.time() - start_time) * 1000)

        # Format responses
        formatted_responses = {}
        total_evidence_count = 0

        for persona_type, query_result in responses.items():
            if query_result.success:
                formatted_responses[persona_type] = query_result.response
                # Get evidence count for this agent
                agent_status = await persona_service.get_agent_status(persona_type)
                if agent_status:
                    total_evidence_count += agent_status.get("cache_size", 0)
            else:
                formatted_responses[persona_type] = f"Error: {query_result.error}"

        return {
            "type": "query_all_response",
            "responses": formatted_responses,
            "processing_time_ms": processing_time,
            "total_evidence_count": total_evidence_count,
            "timestamp": asyncio.get_event_loop().time(),
        }

    except Exception as e:
        logger.error(
            "Query all message handling failed",
            error=str(e),
            connection_id=connection_id,
            user_id=user_id,
        )
        return {"type": "error", "message": sanitize_error_message(e)}


async def handle_status_message(connection_id: str, user_id: str) -> dict[str, Any]:
    """Handle status request message."""
    try:
        # Get persona service
        persona_service = await get_persona_service()
        status_data = await persona_service.get_all_agent_status()

        return {
            "type": "status_response",
            "agents": dict(status_data.items()),
            "timestamp": asyncio.get_event_loop().time(),
        }

    except Exception as e:
        logger.error(
            "Status message handling failed",
            error=str(e),
            connection_id=connection_id,
            user_id=user_id,
        )
        return {"type": "error", "message": sanitize_error_message(e)}
