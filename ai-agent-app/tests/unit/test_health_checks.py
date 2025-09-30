"""Test health checking functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from ai_agent.resilience.health import (
    HealthCheckResult,
    HealthStatus,
    DatabaseHealthChecker,
    HTTPHealthChecker,
    RedisHealthChecker,
    CustomHealthChecker,
    ServiceHealthMonitor,
)


class TestHealthCheckResult:
    """Test health check result functionality."""

    def test_health_check_result_creation(self):
        """Test creating health check result."""
        from datetime import datetime, UTC

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
        from datetime import datetime, UTC

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


class TestDatabaseHealthChecker:
    """Test database health checker functionality."""

    @pytest.fixture
    def db_checker(self):
        """Create database health checker for testing."""

        async def mock_connection():
            mock_conn = Mock()
            mock_conn.execute = AsyncMock()
            return mock_conn

        return DatabaseHealthChecker("test_db", mock_connection)

    @pytest.mark.asyncio
    async def test_database_health_check_success(self, db_checker):
        """Test successful database health check."""
        result = await db_checker.check_health()

        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "test_db"

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self, db_checker):
        """Test database health check failure."""

        # Create a checker that will fail
        async def failing_connection():
            raise Exception("Connection failed")

        failing_checker = DatabaseHealthChecker("test_db", failing_connection)
        result = await failing_checker.check_health()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.error

    @pytest.mark.asyncio
    async def test_database_health_check_timeout(self, db_checker):
        """Test database health check timeout."""

        # Create a checker that will timeout
        async def timeout_connection():
            await asyncio.sleep(10)  # This will timeout
            return Mock()

        timeout_checker = DatabaseHealthChecker(
            "test_db", timeout_connection, timeout=0.1
        )
        result = (
            await timeout_checker.run_check()
        )  # Use run_check instead of check_health

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.error.lower()


class TestHTTPHealthChecker:
    """Test HTTP health checker functionality."""

    @pytest.fixture
    def http_checker(self):
        """Create HTTP health checker for testing."""
        return HTTPHealthChecker("test_api", "http://test.com/health")

    @pytest.mark.asyncio
    async def test_http_health_check_success(self, http_checker):
        """Test successful HTTP health check."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await http_checker.run_check()

            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "test_api"

    @pytest.mark.asyncio
    async def test_http_health_check_wrong_status(self, http_checker):
        """Test HTTP health check with wrong status code."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.headers = {"content-type": "application/json"}

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await http_checker.run_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert result.details.get("status_code") == 500

    @pytest.mark.asyncio
    async def test_http_health_check_connection_error(self, http_checker):
        """Test HTTP health check with connection error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Connection error")
            )

            result = await http_checker.run_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert "Connection error" in result.error


class TestRedisHealthChecker:
    """Test Redis health checker functionality."""

    @pytest.fixture
    def redis_checker(self):
        """Create Redis health checker for testing."""
        mock_redis_client = Mock()
        return RedisHealthChecker("test_redis", mock_redis_client)

    @pytest.mark.asyncio
    async def test_redis_health_check_success(self, redis_checker):
        """Test successful Redis health check."""
        # Mock the redis client's ping method
        redis_checker.redis_client.ping = AsyncMock(return_value=True)
        redis_checker.redis_client.info = AsyncMock(
            return_value={"redis_version": "6.0"}
        )

        result = await redis_checker.run_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "test_redis"

    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self, redis_checker):
        """Test Redis health check failure."""
        # Mock the redis client's ping method to raise an exception
        redis_checker.redis_client.ping = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )

        result = await redis_checker.run_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Redis connection failed" in result.error


class TestCustomHealthChecker:
    """Test custom health checker functionality."""

    @pytest.mark.asyncio
    async def test_custom_health_check_success(self):
        """Test successful custom health check."""

        async def health_function():
            return {
                "healthy": True,
                "message": "All good",
                "details": {"status": "healthy"},
            }

        checker = CustomHealthChecker("custom_service", health_function)
        result = await checker.run_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "custom_service"
        assert result.details.get("status") == "healthy"

    @pytest.mark.asyncio
    async def test_custom_health_check_boolean_result(self):
        """Test custom health check with boolean result."""

        async def health_function():
            return True

        checker = CustomHealthChecker("boolean_service", health_function)
        result = await checker.run_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "boolean_service"

    @pytest.mark.asyncio
    async def test_custom_health_check_failure(self):
        """Test custom health check failure."""

        async def health_function():
            raise Exception("Service is down")

        checker = CustomHealthChecker("failing_service", health_function)
        result = await checker.run_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Service is down" in result.error


class TestServiceHealthMonitor:
    """Test service health monitor functionality."""

    @pytest.fixture
    def health_monitor(self):
        """Create service health monitor for testing."""
        from ai_agent.resilience.health import HealthMonitorConfig

        config = HealthMonitorConfig()
        return ServiceHealthMonitor(config)

    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization."""
        assert health_monitor is not None
        assert hasattr(health_monitor, "add_checker")

    def test_add_checker(self, health_monitor):
        """Test adding health checker."""
        checker = Mock()
        checker.service_name = "test_service"

        health_monitor.add_checker("test_service", checker)
        assert "test_service" in health_monitor.checkers

    def test_remove_checker(self, health_monitor):
        """Test removing health checker."""
        checker = Mock()
        checker.service_name = "test_service"

        health_monitor.add_checker("test_service", checker)
        health_monitor.remove_checker("test_service")
        assert "test_service" not in health_monitor.checkers

    @pytest.mark.asyncio
    async def test_check_service_now(self, health_monitor):
        """Test checking service immediately."""
        from datetime import datetime, UTC

        checker = AsyncMock()
        checker.service_name = "test_service"
        mock_result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=0.5,
            details={},
        )
        checker.run_check.return_value = mock_result

        health_monitor.add_checker("test_service", checker)
        result = await health_monitor.check_service_now("test_service")

        assert result.status == HealthStatus.HEALTHY
        checker.run_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_service_now_not_found(self, health_monitor):
        """Test checking non-existent service."""
        result = await health_monitor.check_service_now("nonexistent")
        assert result is None

    def test_get_service_health(self, health_monitor):
        """Test getting service health information."""
        from datetime import datetime, UTC

        checker = Mock()
        checker.service_name = "test_service"
        mock_result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=0.5,
            details={},
        )
        checker.run_check.return_value = mock_result

        health_monitor.add_checker("test_service", checker)
        # Add a check result to the metrics
        health_monitor.metrics["test_service"].add_check_result(mock_result)
        health = health_monitor.get_service_health("test_service")

        assert health is not None
        assert health["is_healthy"] is True

    def test_get_all_health(self, health_monitor):
        """Test getting all health information."""
        from datetime import datetime, UTC

        checker1 = Mock()
        checker1.service_name = "service1"
        mock_result1 = HealthCheckResult(
            service_name="service1",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=0.5,
            details={},
        )

        checker2 = Mock()
        checker2.service_name = "service2"
        mock_result2 = HealthCheckResult(
            service_name="service2",
            status=HealthStatus.UNHEALTHY,
            message="Service is unhealthy",
            timestamp=datetime.now(UTC),
            response_time_ms=1.0,
            details={},
        )

        health_monitor.add_checker("service1", checker1)
        health_monitor.add_checker("service2", checker2)

        # Add check results to the metrics
        health_monitor.metrics["service1"].add_check_result(mock_result1)
        health_monitor.metrics["service2"].add_check_result(mock_result2)

        all_health = health_monitor.get_all_health()
        assert len(all_health) == 2
        assert "service1" in all_health
        assert "service2" in all_health

    def test_get_global_health(self, health_monitor):
        """Test getting global health status."""
        from datetime import datetime, UTC

        checker1 = Mock()
        checker1.service_name = "service1"
        mock_result1 = HealthCheckResult(
            service_name="service1",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=0.5,
            details={},
        )

        checker2 = Mock()
        checker2.service_name = "service2"
        mock_result2 = HealthCheckResult(
            service_name="service2",
            status=HealthStatus.UNHEALTHY,
            message="Service is unhealthy",
            timestamp=datetime.now(UTC),
            response_time_ms=1.0,
            details={},
        )

        health_monitor.add_checker("service1", checker1)
        health_monitor.add_checker("service2", checker2)

        # Add check results to the metrics
        health_monitor.metrics["service1"].add_check_result(mock_result1)
        health_monitor.metrics["service2"].add_check_result(mock_result2)

        global_health = health_monitor.get_global_health()
        assert global_health["overall_status"] == "unhealthy"
        assert global_health["total_services"] == 2
        assert global_health["healthy_services"] == 1
        assert global_health["unhealthy_services"] == 1

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, health_monitor):
        """Test starting and stopping monitoring."""
        from datetime import datetime, UTC

        checker = AsyncMock()
        checker.service_name = "test_service"
        mock_result = HealthCheckResult(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            timestamp=datetime.now(UTC),
            response_time_ms=0.5,
            details={},
        )
        checker.run_check.return_value = mock_result

        health_monitor.add_checker("test_service", checker)

        # Start monitoring
        await health_monitor.start_monitoring()
        assert health_monitor._monitoring_task is not None

        # Wait a bit for monitoring to run
        await asyncio.sleep(0.2)

        # Stop monitoring
        await health_monitor.stop_monitoring()
        assert health_monitor._monitoring_task is None


# Note: ServiceHealthMetrics class is not available in the current implementation
# The health monitoring functionality is handled by ServiceHealthMonitor
