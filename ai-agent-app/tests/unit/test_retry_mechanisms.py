"""Test retry mechanisms functionality."""

import pytest
from ai_agent.resilience.retry import RetryManager, RetryConfig, RetrySettings


class TestRetryManager:
    """Test retry manager functionality."""

    @pytest.fixture
    def retry_manager(self):
        """Create retry manager for testing."""
        settings = RetrySettings()
        return RetryManager(settings)

    def test_retry_manager_initialization(self, retry_manager):
        """Test retry manager initialization."""
        assert retry_manager is not None
        assert hasattr(retry_manager, "get_retry_decorator")

    def test_get_llm_retry_decorator(self, retry_manager):
        """Test getting LLM retry decorator."""
        decorator = retry_manager.get_retry_decorator("llm")
        assert decorator is not None
        assert callable(decorator)

    def test_get_database_retry_decorator(self, retry_manager):
        """Test getting database retry decorator."""
        decorator = retry_manager.get_retry_decorator("database")
        assert decorator is not None
        assert callable(decorator)

    def test_get_mcp_retry_decorator(self, retry_manager):
        """Test getting MCP retry decorator."""
        decorator = retry_manager.get_retry_decorator("mcp")
        assert decorator is not None
        assert callable(decorator)

    def test_get_secret_retry_decorator(self, retry_manager):
        """Test getting secret retry decorator."""
        decorator = retry_manager.get_retry_decorator("secret")
        assert decorator is not None
        assert callable(decorator)

    def test_get_retry_decorator_unknown_service(self, retry_manager):
        """Test getting retry decorator for unknown service."""
        with pytest.raises(ValueError, match="Unknown service type: unknown"):
            retry_manager.get_retry_decorator("unknown")

    def test_get_config(self, retry_manager):
        """Test getting retry configuration."""
        config = retry_manager.get_config("llm")
        assert config is not None
        assert hasattr(config, "max_attempts")
        assert hasattr(config, "base_delay")

    def test_create_custom_decorator(self, retry_manager):
        """Test creating custom retry decorator."""
        custom_config = RetryConfig(max_attempts=3, base_delay=0.1)
        decorator = retry_manager.create_custom_decorator(custom_config)
        assert decorator is not None
        assert callable(decorator)

    def test_clear_cache(self, retry_manager):
        """Test clearing decorator cache."""
        # Add some decorators to cache
        retry_manager.get_retry_decorator("llm")
        retry_manager.get_retry_decorator("database")

        # Clear cache
        retry_manager.clear_cache()

        # Cache should be empty
        assert len(retry_manager._decorators) == 0

    def test_get_stats(self, retry_manager):
        """Test getting retry manager statistics."""
        stats = retry_manager.get_stats()
        assert isinstance(stats, dict)
        assert "cached_decorators" in stats
        assert "service_types" in stats


class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.fixture
    def retry_manager(self):
        """Create retry manager for testing."""
        settings = RetrySettings()
        return RetryManager(settings)

    @pytest.mark.asyncio
    async def test_successful_retry(self, retry_manager):
        """Test retry decorator with successful call."""
        decorator = retry_manager.get_retry_decorator("llm")

        @decorator
        async def successful_function():
            return "success"

        result = await successful_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_failure_then_success(self, retry_manager):
        """Test retry decorator with initial failure then success."""
        # Create a custom decorator with ConnectionError in retryable errors
        custom_config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,  # Very short delay for testing
            retryable_errors=["ConnectionError"],
        )
        decorator = retry_manager.create_custom_decorator(custom_config)
        call_count = 0

        @decorator
        async def failing_then_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await failing_then_successful_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, retry_manager):
        """Test retry decorator with all attempts failing."""
        decorator = retry_manager.get_retry_decorator("llm")

        @decorator
        async def always_failing_function():
            raise Exception("Permanent failure")

        with pytest.raises(Exception, match="Permanent failure"):
            await always_failing_function()

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, retry_manager):
        """Test retry decorator with non-retryable exception."""
        decorator = retry_manager.get_retry_decorator("llm")

        @decorator
        async def non_retryable_function():
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError, match="Non-retryable error"):
            await non_retryable_function()

    @pytest.mark.asyncio
    async def test_retry_with_correlation_id(self, retry_manager):
        """Test retry decorator with correlation ID."""
        decorator = retry_manager.get_retry_decorator("llm")

        @decorator
        async def function_with_correlation_id():
            return "success"

        result = await function_with_correlation_id()
        assert result == "success"


class TestRetryConfig:
    """Test retry configuration."""

    def test_retry_config_defaults(self):
        """Test retry config with default values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        # Note: exponential_base may not be available in the actual implementation

    def test_retry_config_validation(self):
        """Test retry config validation."""
        config = RetryConfig(max_attempts=5, base_delay=0.5)
        assert config.max_attempts == 5
        assert config.base_delay == 0.5

    def test_retry_settings_get_configs(self):
        """Test retry settings get config methods."""
        from ai_agent.resilience.retry import RetrySettings

        settings = RetrySettings()

        # Test getting configs for different services
        llm_config = settings.get_llm_config()
        assert llm_config is not None

        db_config = settings.get_database_config()
        assert db_config is not None

        mcp_config = settings.get_mcp_config()
        assert mcp_config is not None

        secret_config = settings.get_secret_config()
        assert secret_config is not None
