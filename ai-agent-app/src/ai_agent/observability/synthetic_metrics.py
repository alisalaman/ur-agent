import structlog
from prometheus_client import Counter, Histogram, Gauge, Info
import time

logger = structlog.get_logger()

# Metrics for transcript processing
transcript_processing_duration = Histogram(
    "transcript_processing_duration_seconds",
    "Time spent processing transcript files",
    ["filename", "status"],
)

transcript_segments_processed = Counter(
    "transcript_segments_processed_total",
    "Total number of transcript segments processed",
    ["stakeholder_group"],
)

# Metrics for MCP server operations
mcp_tool_calls = Counter(
    "mcp_tool_calls_total", "Total number of MCP tool calls", ["tool_name", "status"]
)

mcp_tool_duration = Histogram(
    "mcp_tool_duration_seconds", "Time spent executing MCP tools", ["tool_name"]
)

# Metrics for agent operations
agent_queries = Counter(
    "agent_queries_total", "Total number of agent queries", ["persona_type", "status"]
)

agent_query_duration = Histogram(
    "agent_query_duration_seconds",
    "Time spent processing agent queries",
    ["persona_type"],
)

agent_evidence_cache_hits = Counter(
    "agent_evidence_cache_hits_total",
    "Total number of evidence cache hits",
    ["persona_type"],
)

agent_evidence_cache_misses = Counter(
    "agent_evidence_cache_misses_total",
    "Total number of evidence cache misses",
    ["persona_type"],
)

# Metrics for evaluation operations
evaluation_duration = Histogram(
    "evaluation_duration_seconds",
    "Time spent evaluating governance models",
    ["model_type", "status"],
)

evaluation_scores = Histogram(
    "evaluation_scores", "Distribution of evaluation scores", ["factor_name"]
)

# Metrics for API operations
api_requests = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "Time spent processing API requests",
    ["method", "endpoint"],
)

# Metrics for WebSocket operations
websocket_connections = Gauge(
    "websocket_connections_active", "Number of active WebSocket connections"
)

websocket_messages = Counter(
    "websocket_messages_total", "Total number of WebSocket messages", ["message_type"]
)

# System information
system_info = Info(
    "synthetic_agent_system_info", "Information about the synthetic agent system"
)


class SyntheticAgentMetrics:
    """Metrics collector for synthetic agent system."""

    def __init__(self) -> None:
        self.start_time = time.time()
        system_info.info({"version": "1.0.0", "start_time": str(self.start_time)})

    def record_transcript_processing(
        self, filename: str, duration: float, status: str
    ) -> None:
        """Record transcript processing metrics."""
        transcript_processing_duration.labels(filename=filename, status=status).observe(
            duration
        )

    def record_segments_processed(self, stakeholder_group: str, count: int) -> None:
        """Record segments processed metrics."""
        transcript_segments_processed.labels(stakeholder_group=stakeholder_group).inc(
            count
        )

    def record_mcp_tool_call(
        self, tool_name: str, duration: float, status: str
    ) -> None:
        """Record MCP tool call metrics."""
        mcp_tool_calls.labels(tool_name=tool_name, status=status).inc()
        mcp_tool_duration.labels(tool_name=tool_name).observe(duration)

    def record_agent_query(
        self, persona_type: str, duration: float, status: str
    ) -> None:
        """Record agent query metrics."""
        agent_queries.labels(persona_type=persona_type, status=status).inc()
        agent_query_duration.labels(persona_type=persona_type).observe(duration)

    def record_evidence_cache_hit(self, persona_type: str) -> None:
        """Record evidence cache hit."""
        agent_evidence_cache_hits.labels(persona_type=persona_type).inc()

    def record_evidence_cache_miss(self, persona_type: str) -> None:
        """Record evidence cache miss."""
        agent_evidence_cache_misses.labels(persona_type=persona_type).inc()

    def record_evaluation(self, model_type: str, duration: float, status: str) -> None:
        """Record evaluation metrics."""
        evaluation_duration.labels(model_type=model_type, status=status).observe(
            duration
        )

    def record_evaluation_score(self, factor_name: str, score: float) -> None:
        """Record evaluation score."""
        evaluation_scores.labels(factor_name=factor_name).observe(score)

    def record_api_request(
        self, method: str, endpoint: str, duration: float, status_code: int
    ) -> None:
        """Record API request metrics."""
        api_requests.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()
        api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def record_websocket_connection(self, count: int) -> None:
        """Record WebSocket connection count."""
        websocket_connections.set(count)

    def record_websocket_message(self, message_type: str) -> None:
        """Record WebSocket message."""
        websocket_messages.labels(message_type=message_type).inc()


# Global metrics instance
metrics = SyntheticAgentMetrics()
