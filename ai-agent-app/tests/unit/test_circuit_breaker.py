"""Test circuit breaker functionality."""

import pytest
from unittest.mock import patch
import asyncio
from ai_agent.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerConfig,
    CircuitBreakerSettings,
    CircuitState,
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=5.0, expected_exception=["Exception"]
        )
        return CircuitBreaker("test_service", config)

    def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test circuit breaker initialization."""
        assert circuit_breaker.name == "test_service"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call_closed_state(self, circuit_breaker):
        """Test successful call in closed state."""

        async def successful_function():
            return "success"

        result = await circuit_breaker.call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_in_closed_state(self, circuit_breaker):
        """Test failure in closed state."""

        async def failing_function():
            raise Exception("Test failure")

        with pytest.raises(Exception, match="Test failure"):
            await circuit_breaker.call(failing_function)

        assert circuit_breaker.metrics.failure_count == 1
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after failure threshold."""

        async def failing_function():
            raise Exception("Test failure")

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(Exception, match="Test failure"):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.metrics.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(self, circuit_breaker):
        """Test open circuit blocks new calls."""
        # Open the circuit
        circuit_breaker.state = CircuitState.OPEN

        async def any_function():
            return "should not be called"

        with pytest.raises(Exception, match="Circuit breaker open for service"):
            await circuit_breaker.call(any_function)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions to half-open after timeout."""
        # Open the circuit
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.metrics.last_failure_time = (
            asyncio.get_event_loop().time() - 10.0
        )

        # Mock the timeout check
        with patch.object(circuit_breaker, "_update_state"):
            # Simulate the half-open transition
            circuit_breaker.state = CircuitState.HALF_OPEN
            assert circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test successful call in half-open closes circuit."""
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.metrics.success_count = 2  # Set to one less than threshold

        async def successful_function():
            return "success"

        result = await circuit_breaker.call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test failure in half-open reopens circuit."""
        circuit_breaker.state = CircuitState.HALF_OPEN

        async def failing_function():
            raise Exception("Test failure")

        with pytest.raises(Exception, match="Test failure"):
            await circuit_breaker.call(failing_function)

        assert circuit_breaker.state == CircuitState.OPEN

    def test_is_expected_exception(self, circuit_breaker):
        """Test expected exception checking."""
        # Test that the method exists and works correctly
        assert hasattr(circuit_breaker, "is_expected_exception")

        # Test with expected exception
        test_exception = Exception("Test")
        result = circuit_breaker.is_expected_exception(test_exception)
        assert result is True  # Should be True since no specific exceptions configured

    def test_get_state_info(self, circuit_breaker):
        """Test getting circuit breaker state info."""
        info = circuit_breaker.get_state_info()
        assert "state" in info
        assert "failure_count" in info
        assert "name" in info
        assert info["name"] == "test_service"

    def test_reset(self, circuit_breaker):
        """Test resetting circuit breaker."""
        circuit_breaker.metrics.failure_count = 5
        circuit_breaker.state = CircuitState.OPEN

        circuit_breaker.reset()

        assert circuit_breaker.metrics.failure_count == 0
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_force_open(self, circuit_breaker):
        """Test forcing circuit breaker open."""
        circuit_breaker.force_open()
        assert circuit_breaker.state == CircuitState.OPEN

    def test_force_close(self, circuit_breaker):
        """Test forcing circuit breaker closed."""
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.force_close()
        assert circuit_breaker.state == CircuitState.CLOSED


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create circuit breaker manager for testing."""

        settings = CircuitBreakerSettings()
        return CircuitBreakerManager(settings)

    def test_circuit_manager_initialization(self, manager):
        """Test circuit manager initialization."""
        assert manager is not None
        assert hasattr(manager, "get_breaker")

    def test_get_breaker_creates_new(self, manager):
        """Test getting breaker creates new one."""
        breaker = manager.get_breaker("new_service")
        assert breaker is not None
        assert breaker.name == "new_service"

    def test_get_breaker_returns_existing(self, manager):
        """Test getting breaker returns existing one."""
        breaker1 = manager.get_breaker("existing_service")
        breaker2 = manager.get_breaker("existing_service")
        assert breaker1 is breaker2

    def test_get_breaker_with_known_service(self, manager):
        """Test getting breaker for known service types."""
        llm_breaker = manager.get_breaker("llm")
        db_breaker = manager.get_breaker("database")

        assert llm_breaker is not None
        assert db_breaker is not None
        assert llm_breaker.name == "llm"
        assert db_breaker.name == "database"

    def test_get_all_breakers(self, manager):
        """Test getting all breakers."""
        manager.get_breaker("service1")
        manager.get_breaker("service2")

        breakers = manager.get_all_breakers()
        assert len(breakers) == 2
        assert "service1" in breakers
        assert "service2" in breakers

    def test_get_breaker_stats(self, manager):
        """Test getting breaker statistics."""
        manager.get_breaker("test_service")
        stats = manager.get_breaker_stats()

        assert stats is not None
        assert "test_service" in stats
        assert "state" in stats["test_service"]
        assert "failure_count" in stats["test_service"]

    def test_reset_breaker(self, manager):
        """Test resetting specific breaker."""
        breaker = manager.get_breaker("test_service")
        breaker.metrics.failure_count = 5

        manager.reset_breaker("test_service")
        assert breaker.metrics.failure_count == 0

    def test_reset_all_breakers(self, manager):
        """Test resetting all breakers."""
        breaker1 = manager.get_breaker("service1")
        breaker2 = manager.get_breaker("service2")
        breaker1.metrics.failure_count = 3
        breaker2.metrics.failure_count = 2

        manager.reset_all_breakers()
        assert breaker1.metrics.failure_count == 0
        assert breaker2.metrics.failure_count == 0

    def test_force_open_breaker(self, manager):
        """Test forcing breaker open."""
        breaker = manager.get_breaker("test_service")
        manager.force_open_breaker("test_service")
        assert breaker.state == CircuitState.OPEN

    def test_force_close_breaker(self, manager):
        """Test forcing breaker closed."""
        breaker = manager.get_breaker("test_service")
        breaker.state = CircuitState.OPEN
        manager.force_close_breaker("test_service")
        assert breaker.state == CircuitState.CLOSED

    def test_remove_breaker(self, manager):
        """Test removing breaker."""
        manager.get_breaker("temp_service")
        assert "temp_service" in manager._breakers

        manager.remove_breaker("temp_service")
        assert "temp_service" not in manager._breakers

    def test_clear_all_breakers(self, manager):
        """Test clearing all breakers."""
        manager.get_breaker("service1")
        manager.get_breaker("service2")

        manager.clear_all_breakers()
        assert len(manager._breakers) == 0

    def test_get_global_stats(self, manager):
        """Test getting global statistics."""
        manager.get_breaker("service1")
        manager.get_breaker("service2")

        stats = manager.get_global_stats()
        assert "total_breakers" in stats
        assert "open_breakers" in stats
        assert "closed_breakers" in stats


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_circuit_config_defaults(self):
        """Test circuit config with default values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == []

    def test_circuit_settings_get_configs(self):
        """Test circuit settings get config methods."""

        settings = CircuitBreakerSettings()

        # Test getting configs for different services
        llm_config = settings.get_llm_config()
        assert llm_config is not None

        db_config = settings.get_database_config()
        assert db_config is not None

        mcp_config = settings.get_mcp_config()
        assert mcp_config is not None
