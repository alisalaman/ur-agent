"""Simple health check tests that work with the actual implementation."""

from datetime import datetime, UTC
from ai_agent.resilience.health import HealthCheckResult, HealthStatus


class TestHealthCheckResultSimple:
    """Test health check result functionality with actual implementation."""

    def test_health_check_result_creation(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=500.0,
            details={"status": "ok"},
        )

        assert result.service_name == "test_service"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 500.0
        assert result.details == {"status": "ok"}

    def test_health_check_result_to_dict(self):
        """Test converting health check result to dictionary."""
        result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=500.0,
            details={"status": "ok"},
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["service_name"] == "test_service"
        assert result_dict["status"] == "healthy"
        assert result_dict["response_time_ms"] == 500.0

    def test_health_status_enum(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_check_result_with_error(self):
        """Test health check result with error."""
        result = HealthCheckResult(
            service_name="failing_service",
            status=HealthStatus.UNHEALTHY,
            message="Service is down",
            timestamp=datetime.now(UTC),
            response_time_ms=1000.0,
            details={"error": "Connection timeout"},
            error="Connection timeout",
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Connection timeout"
        assert result.details["error"] == "Connection timeout"

    def test_health_check_result_different_statuses(self):
        """Test health check result with different statuses."""
        # Test healthy status
        healthy_result = HealthCheckResult(
            service_name="healthy_service",
            status=HealthStatus.HEALTHY,
            message="All good",
            timestamp=datetime.now(UTC),
            response_time_ms=100.0,
            details={},
        )
        assert healthy_result.status == HealthStatus.HEALTHY

        # Test degraded status
        degraded_result = HealthCheckResult(
            service_name="degraded_service",
            status=HealthStatus.DEGRADED,
            message="Performance issues",
            timestamp=datetime.now(UTC),
            response_time_ms=2000.0,
            details={"warning": "High latency"},
        )
        assert degraded_result.status == HealthStatus.DEGRADED

        # Test unknown status
        unknown_result = HealthCheckResult(
            service_name="unknown_service",
            status=HealthStatus.UNKNOWN,
            message="Status unclear",
            timestamp=datetime.now(UTC),
            response_time_ms=0.0,
            details={},
        )
        assert unknown_result.status == HealthStatus.UNKNOWN
