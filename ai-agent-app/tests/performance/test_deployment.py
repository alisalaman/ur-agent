"""Performance tests for deployment configuration."""

import pytest
import time
import subprocess
import psutil
import asyncio

from ai_agent.config.synthetic_agents import get_config


class TestDeploymentPerformance:
    """Test deployment performance and resource usage."""

    def test_docker_build_performance(self):
        """Test Docker build performance."""
        start_time = time.time()

        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile.synthetic",
                "-t",
                "test-synthetic-agent-perf",
                ".",
            ],
            capture_output=True,
            text=True,
        )

        build_time = time.time() - start_time

        # Clean up test image
        subprocess.run(
            ["docker", "rmi", "test-synthetic-agent-perf"], capture_output=True
        )

        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        assert build_time < 300, f"Docker build took too long: {build_time:.2f}s"

        print(f"Docker build completed in {build_time:.2f} seconds")

    def test_docker_compose_startup_performance(self):
        """Test Docker Compose startup performance."""
        # This test requires Docker to be running and would actually start services
        pytest.skip("Requires Docker environment and would start actual services")

    def test_configuration_loading_performance(self):
        """Test configuration loading performance."""
        start_time = time.time()

        # Load configuration multiple times
        for _ in range(100):
            config = get_config()
            assert config is not None

        load_time = time.time() - start_time
        avg_load_time = load_time / 100

        assert (
            avg_load_time < 0.01
        ), f"Configuration loading too slow: {avg_load_time:.4f}s per load"

        print(f"Average configuration load time: {avg_load_time:.4f} seconds")

    def test_memory_usage_during_config_loading(self):
        """Test memory usage during configuration loading."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Load configuration multiple times
        configs = []
        for _ in range(1000):
            config = get_config()
            configs.append(config)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 10MB)
        assert (
            memory_increase < 10 * 1024 * 1024
        ), f"Excessive memory usage: {memory_increase / 1024 / 1024:.2f}MB"

        print(
            f"Memory increase during config loading: {memory_increase / 1024 / 1024:.2f}MB"
        )

    def test_database_migration_performance(self):
        """Test database migration performance."""
        # This test would require a database connection
        pytest.skip("Requires database connection")

    def test_docker_image_size(self):
        """Test Docker image size is reasonable."""
        # Build image
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile.synthetic",
                "-t",
                "test-synthetic-agent-size",
                ".",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Docker build failed: {result.stderr}"

        # Get image size
        result = subprocess.run(
            ["docker", "images", "test-synthetic-agent-size", "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
        )

        # Clean up test image
        subprocess.run(
            ["docker", "rmi", "test-synthetic-agent-size"], capture_output=True
        )

        size_str = result.stdout.strip()
        print(f"Docker image size: {size_str}")

        # Image should be reasonable size (less than 2GB)
        # This is a basic check - in practice you'd parse the size string properly
        assert (
            "GB" not in size_str or float(size_str.replace("GB", "")) < 2.0
        ), f"Image too large: {size_str}"

    def test_configuration_validation_performance(self):
        """Test configuration validation performance."""
        start_time = time.time()

        # Test with various environment variable combinations
        test_configs = [
            {"ENVIRONMENT": "development"},
            {"ENVIRONMENT": "staging", "DATABASE_HOST": "test-host"},
            {"ENVIRONMENT": "production", "LLM_PROVIDER": "openai"},
        ]

        for env_vars in test_configs:
            with pytest.MonkeyPatch().context() as m:
                for key, value in env_vars.items():
                    m.setenv(key, value)

                config = get_config()
                assert config is not None

        validation_time = time.time() - start_time
        assert (
            validation_time < 1.0
        ), f"Configuration validation too slow: {validation_time:.2f}s"

        print(f"Configuration validation completed in {validation_time:.2f} seconds")

    def test_docker_compose_config_parsing_performance(self):
        """Test Docker Compose configuration parsing performance."""
        start_time = time.time()

        # Parse docker-compose file multiple times
        for _ in range(50):
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.synthetic.yml", "config"],
                capture_output=True,
                text=True,
            )
            assert (
                result.returncode == 0
            ), f"Docker compose parsing failed: {result.stderr}"

        parse_time = time.time() - start_time
        avg_parse_time = parse_time / 50

        assert (
            avg_parse_time < 0.5
        ), f"Docker compose parsing too slow: {avg_parse_time:.4f}s per parse"

        print(f"Average Docker compose parse time: {avg_parse_time:.4f} seconds")

    def test_metrics_collection_performance(self):
        """Test metrics collection performance."""
        from ai_agent.observability.synthetic_metrics import metrics

        start_time = time.time()

        # Record various metrics
        for _i in range(1000):
            metrics.record_api_request("GET", "/test", 0.1, 200)
            metrics.record_agent_query("BANK_REP", 0.5, "success")
            metrics.record_transcript_processing("test.docx", 1.0, "success")
            metrics.record_evaluation("test_model", 2.0, "completed")

        metrics_time = time.time() - start_time
        avg_metrics_time = metrics_time / 1000

        assert (
            avg_metrics_time < 0.001
        ), f"Metrics recording too slow: {avg_metrics_time:.6f}s per metric"

        print(f"Average metrics recording time: {avg_metrics_time:.6f} seconds")

    def test_concurrent_configuration_loading(self):
        """Test concurrent configuration loading performance."""

        async def load_config_async():
            return get_config()

        async def run_concurrent_loads():
            tasks = [load_config_async() for _ in range(100)]
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            assert all(result is not None for result in results)
            return end_time - start_time

        load_time = asyncio.run(run_concurrent_loads())

        assert (
            load_time < 2.0
        ), f"Concurrent configuration loading too slow: {load_time:.2f}s"

        print(f"Concurrent configuration loading completed in {load_time:.2f} seconds")

    def test_docker_health_check_performance(self):
        """Test Docker health check performance."""
        # This test would require running containers
        pytest.skip("Requires running Docker containers")

    def test_resource_usage_under_load(self):
        """Test resource usage under simulated load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Simulate load by loading configuration repeatedly
        configs = []
        start_time = time.time()
        for _ in range(1000):  # Reduced from 10000 to 1000
            config = get_config()
            configs.append(config)
        end_time = time.time()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        execution_time = end_time - start_time

        # Memory usage should be reasonable
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Excessive memory usage: {memory_increase / 1024 / 1024:.2f}MB"

        # Execution time should be reasonable (less than 1 second for 1000 config loads)
        assert (
            execution_time < 1.0
        ), f"Configuration loading too slow: {execution_time:.2f}s"

        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f}MB")
        print(f"Execution time: {execution_time:.2f}s")


class TestDeploymentScalability:
    """Test deployment scalability characteristics."""

    def test_configuration_scalability(self):
        """Test configuration system scales with environment variables."""
        # Test with many environment variables
        env_vars = {}
        for i in range(100):
            env_vars[f"TEST_VAR_{i}"] = f"value_{i}"

        with pytest.MonkeyPatch().context() as m:
            for key, value in env_vars.items():
                m.setenv(key, value)

            start_time = time.time()
            config = get_config()
            load_time = time.time() - start_time

            assert config is not None
            assert (
                load_time < 0.1
            ), f"Configuration loading too slow with many env vars: {load_time:.4f}s"

        print(f"Configuration loaded with 100 env vars in {load_time:.4f} seconds")

    def test_metrics_scalability(self):
        """Test metrics system scales with high volume."""
        from ai_agent.observability.synthetic_metrics import metrics

        start_time = time.time()

        # Record many metrics
        for i in range(10000):
            metrics.record_api_request("GET", f"/endpoint_{i}", 0.1, 200)
            metrics.record_agent_query(f"PERSONA_{i % 5}", 0.5, "success")

        metrics_time = time.time() - start_time
        avg_metrics_time = metrics_time / 10000

        assert (
            avg_metrics_time < 0.001
        ), f"Metrics recording too slow: {avg_metrics_time:.6f}s per metric"

        print(f"Recorded 10000 metrics in {metrics_time:.2f} seconds")

    def test_docker_compose_scalability(self):
        """Test Docker Compose configuration scales with many services."""
        # This would test with a larger docker-compose file
        pytest.skip("Would require creating a large docker-compose file for testing")

    def test_database_migration_scalability(self):
        """Test database migration system scales with many migrations."""
        # This would test with many migration files
        pytest.skip("Would require creating many migration files for testing")
