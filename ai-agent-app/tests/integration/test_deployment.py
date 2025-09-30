"""Integration tests for deployment configuration."""

import pytest
import subprocess
from pathlib import Path

from ai_agent.config.synthetic_agents import get_config


class TestDockerConfiguration:
    """Test Docker configuration and deployment."""

    def test_docker_compose_file_exists(self):
        """Test that docker-compose.synthetic.yml exists."""
        compose_file = Path("docker-compose.synthetic.yml")
        assert compose_file.exists()

    def test_dockerfile_exists(self):
        """Test that Dockerfile.synthetic exists."""
        dockerfile = Path("Dockerfile.synthetic")
        assert dockerfile.exists()

    def test_docker_compose_syntax(self):
        """Test docker-compose file syntax."""
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.synthetic.yml", "config"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Docker compose syntax error: {result.stderr}"

    def test_dockerfile_syntax(self):
        """Test Dockerfile syntax by building a test image."""
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile.synthetic",
                "-t",
                "test-synthetic-agent",
                ".",
            ],
            capture_output=True,
            text=True,
        )
        # Clean up test image
        subprocess.run(["docker", "rmi", "test-synthetic-agent"], capture_output=True)
        assert result.returncode == 0, f"Dockerfile build error: {result.stderr}"


class TestDatabaseMigrations:
    """Test database migration files."""

    def test_migration_file_exists(self):
        """Test that migration file exists."""
        migration_file = Path(
            "src/ai_agent/infrastructure/database/migrations/001_add_synthetic_agents.sql"
        )
        assert migration_file.exists()

    def test_migration_syntax(self):
        """Test SQL migration syntax."""
        migration_file = Path(
            "src/ai_agent/infrastructure/database/migrations/001_add_synthetic_agents.sql"
        )
        content = migration_file.read_text()

        # Basic syntax checks
        assert "CREATE TABLE" in content
        assert "CREATE INDEX" in content
        assert "CREATE OR REPLACE VIEW" in content
        assert "INSERT INTO" in content

    def test_migration_tables(self):
        """Test that all required tables are defined."""
        migration_file = Path(
            "src/ai_agent/infrastructure/database/migrations/001_add_synthetic_agents.sql"
        )
        content = migration_file.read_text()

        required_tables = [
            "transcript_metadata",
            "transcript_segments",
            "topic_tags",
            "segment_topic_mappings",
            "governance_models",
            "evaluation_results",
            "factor_scores",
            "agent_sessions",
            "agent_conversations",
        ]

        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content

    def test_migration_indexes(self):
        """Test that required indexes are defined."""
        migration_file = Path(
            "src/ai_agent/infrastructure/database/migrations/001_add_synthetic_agents.sql"
        )
        content = migration_file.read_text()

        required_indexes = [
            "idx_transcript_segments_content",
            "idx_transcript_metadata_source",
            "idx_evaluation_results_model_id",
            "idx_factor_scores_evaluation_id",
            "idx_agent_sessions_agent_type",
        ]

        for index in required_indexes:
            assert f"CREATE INDEX IF NOT EXISTS {index}" in content


class TestMonitoringConfiguration:
    """Test monitoring and observability configuration."""

    def test_prometheus_config_exists(self):
        """Test that Prometheus configuration exists."""
        prometheus_file = Path("prometheus.yml")
        assert prometheus_file.exists()

    def test_nginx_config_exists(self):
        """Test that Nginx configuration exists."""
        nginx_file = Path("nginx.conf")
        assert nginx_file.exists()

    def test_grafana_config_exists(self):
        """Test that Grafana configuration exists."""
        grafana_datasource = Path("grafana/datasources/prometheus.yml")
        grafana_dashboard = Path("grafana/dashboards/synthetic-agents.json")

        assert grafana_datasource.exists()
        assert grafana_dashboard.exists()

    def test_metrics_module_exists(self):
        """Test that metrics module exists."""
        metrics_file = Path("src/ai_agent/observability/synthetic_metrics.py")
        assert metrics_file.exists()


class TestDeploymentScripts:
    """Test deployment scripts."""

    def test_deploy_script_exists(self):
        """Test that deployment script exists."""
        deploy_script = Path("scripts/deploy.sh")
        assert deploy_script.exists()

    def test_deploy_script_executable(self):
        """Test that deployment script is executable."""
        deploy_script = Path("scripts/deploy.sh")
        assert deploy_script.stat().st_mode & 0o111  # Check executable bit

    def test_initialize_transcripts_script_exists(self):
        """Test that transcript initialization script exists."""
        init_script = Path("scripts/initialize_transcripts.py")
        assert init_script.exists()


class TestConfigurationIntegration:
    """Test configuration integration with deployment."""

    def test_config_loading_in_deployment_context(self):
        """Test that configuration loads correctly in deployment context."""
        # Simulate deployment environment variables

        with pytest.MonkeyPatch().context() as m:
            m.setenv("ENVIRONMENT", "production")
            m.setenv("DATABASE_HOST", "postgres")
            m.setenv("DATABASE_NAME", "ai_agent")
            m.setenv("DATABASE_USERNAME", "ai_agent")
            m.setenv("DATABASE_PASSWORD", "ai_agent_password")

            config = get_config()

            assert config.environment.value == "production"
            assert config.database.host == "postgres"
            assert config.database.database == "ai_agent"
            assert config.database.username == "ai_agent"
            assert config.database.password == "ai_agent_password"

    def test_docker_environment_variables(self):
        """Test that Docker environment variables are properly configured."""
        compose_file = Path("docker-compose.synthetic.yml")
        content = compose_file.read_text()

        required_env_vars = [
            "ENVIRONMENT",
            "DATABASE_HOST",
            "DATABASE_NAME",
            "DATABASE_USERNAME",
            "DATABASE_PASSWORD",
            "REDIS_HOST",
            "EMBEDDING_DIMENSION",
            "TRANSCRIPT_DIRECTORY",
            "LLM_PROVIDER",
            "LOG_LEVEL",
            "ENABLE_METRICS",
            "ENABLE_TRACING",
        ]

        for env_var in required_env_vars:
            assert f"- {env_var}=" in content


class TestServiceHealthChecks:
    """Test service health check configurations."""

    def test_ai_agent_health_check(self):
        """Test AI agent health check configuration."""
        compose_file = Path("docker-compose.synthetic.yml")
        content = compose_file.read_text()

        assert "healthcheck:" in content
        assert "http://localhost:8000/health" in content
        assert "interval: 30s" in content
        assert "timeout: 10s" in content
        assert "retries: 3" in content

    def test_postgres_health_check(self):
        """Test PostgreSQL health check configuration."""
        compose_file = Path("docker-compose.synthetic.yml")
        content = compose_file.read_text()

        assert "pg_isready" in content
        assert "-U ai_agent -d ai_agent" in content

    def test_redis_health_check(self):
        """Test Redis health check configuration."""
        compose_file = Path("docker-compose.synthetic.yml")
        content = compose_file.read_text()

        assert "redis-cli" in content
        assert "ping" in content


@pytest.mark.slow
class TestFullDeployment:
    """Test full deployment (marked as slow)."""

    def test_services_start_successfully(self):
        """Test that all services start successfully."""
        # This test would require Docker to be running
        # and would actually start the services
        pytest.skip("Requires Docker and full environment setup")

    def test_health_endpoints_respond(self):
        """Test that health endpoints respond correctly."""
        # This test would require services to be running
        pytest.skip("Requires services to be running")

    def test_metrics_endpoint_accessible(self):
        """Test that metrics endpoint is accessible."""
        # This test would require services to be running
        pytest.skip("Requires services to be running")
