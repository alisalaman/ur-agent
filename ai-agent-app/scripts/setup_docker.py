#!/usr/bin/env python3
"""
Simplified Docker setup script for AI Agent application.

This script handles the unique setup tasks that Docker Compose doesn't:
- pgvector extension installation
- Environment file configuration
- Service health validation
"""

import subprocess
import sys
import time
from pathlib import Path


# Colors for output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_step(message: str):
    """Print a step message."""
    print(f"{Colors.BLUE}{Colors.BOLD}==> {message}{Colors.END}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def run_command(
    cmd: list[str], check: bool = True, capture: bool = False
) -> str | None:
    """Run a command and return output if requested."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {' '.join(cmd)}")
            if capture and e.stderr:
                print_error(f"Error: {e.stderr.strip()}")
            raise
        return None


def check_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        run_command(["docker", "--version"], capture=True)
        print_success("Docker is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker is not available. Please install Docker Desktop")
        return False


def check_service_health(service_name: str, max_attempts: int = 30) -> bool:
    """Check if a service is healthy."""
    print_step(f"Checking health of {service_name}")

    for attempt in range(max_attempts):
        try:
            result = run_command(
                ["docker", "compose", "ps", "--format", "json", service_name],
                capture=True,
                check=False,
            )

            if result and '"Health"' in result and '"healthy"' in result:
                print_success(f"{service_name} is healthy")
                return True

            print(
                f"  Attempt {attempt + 1}/{max_attempts}: Waiting for {service_name}..."
            )
            time.sleep(2)

        except Exception:
            pass

    print_warning(f"{service_name} health check timed out")
    return False


def ensure_pgvector_extension(environment: str = "development"):
    """Ensure pgvector extension is installed in PostgreSQL."""
    print_step("Installing pgvector extension")

    # Get database connection details
    if environment == "development":
        db_name = "ai_agent_dev"
    else:
        db_name = "ai_agent_prod"

    try:
        # Connect to PostgreSQL and install pgvector extension
        cmd = [
            "docker",
            "exec",
            "ai-agent-postgres",
            "psql",
            "-U",
            "postgres",
            "-d",
            db_name,
            "-c",
            "CREATE EXTENSION IF NOT EXISTS vector;",
        ]

        result = run_command(cmd, capture=True, check=False)
        if result and ("CREATE EXTENSION" in result or "already exists" in result):
            print_success("pgvector extension installed successfully")
            return True
        else:
            print_warning("pgvector extension may not be available")
            return False

    except Exception as e:
        print_warning(f"Could not install pgvector extension: {e}")
        return False


def update_env_file(environment: str = "development"):
    """Update .env file with Docker service configuration."""
    print_step("Configuring environment file")

    env_file = Path(".env")
    if not env_file.exists():
        print_warning(".env file not found, creating from template")
        template_file = Path("env-templates/env.example")
        if template_file.exists():
            env_file.write_text(template_file.read_text())
        else:
            print_error("No .env template found")
            return False

    # Read current .env content
    content = env_file.read_text()

    # Update database settings
    if environment == "development":
        db_host = "localhost"
        db_port = "5433"
        db_name = "ai_agent_dev"
        redis_host = "localhost"
        redis_port = "6380"
    else:
        db_host = "localhost"
        db_port = "5432"
        db_name = "ai_agent_prod"
        redis_host = "localhost"
        redis_port = "6379"

    # Update or add database settings
    lines = content.split("\n")
    updated_lines = []
    db_updated = False
    redis_updated = False

    for line in lines:
        if line.startswith("DB_HOST="):
            updated_lines.append(f"DB_HOST={db_host}")
            db_updated = True
        elif line.startswith("DB_PORT="):
            updated_lines.append(f"DB_PORT={db_port}")
        elif line.startswith("DB_NAME="):
            updated_lines.append(f"DB_NAME={db_name}")
        elif line.startswith("REDIS_HOST="):
            updated_lines.append(f"REDIS_HOST={redis_host}")
            redis_updated = True
        elif line.startswith("REDIS_PORT="):
            updated_lines.append(f"REDIS_PORT={redis_port}")
        elif line.startswith("USE_DATABASE="):
            updated_lines.append("USE_DATABASE=true")
        elif line.startswith("USE_REDIS="):
            updated_lines.append("USE_REDIS=true")
        else:
            updated_lines.append(line)

    # Add missing settings if not found
    if not db_updated:
        updated_lines.append(f"DB_HOST={db_host}")
        updated_lines.append(f"DB_PORT={db_port}")
        updated_lines.append(f"DB_NAME={db_name}")
        updated_lines.append("DB_USER=postgres")
        updated_lines.append("DB_PASSWORD=password")
        updated_lines.append("USE_DATABASE=true")

    if not redis_updated:
        updated_lines.append(f"REDIS_HOST={redis_host}")
        updated_lines.append(f"REDIS_PORT={redis_port}")
        updated_lines.append("REDIS_DB=0")
        updated_lines.append("USE_REDIS=true")

    # Write updated content
    env_file.write_text("\n".join(updated_lines))
    print_success("Environment file configured")


def main():
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup AI Agent Docker services")
    parser.add_argument(
        "--environment",
        "-e",
        default="development",
        choices=["development", "production"],
        help="Environment to configure (default: development)",
    )

    args = parser.parse_args()

    print(f"{Colors.BOLD}AI Agent Docker Setup{Colors.END}")
    print(f"Environment: {args.environment}")
    print()

    # Check prerequisites
    if not check_docker_available():
        sys.exit(1)

    # Check if we're in the right directory
    if not Path("docker-compose.yml").exists():
        print_error("Please run this script from the ai-agent-app directory")
        sys.exit(1)

    try:
        # Wait for services to be healthy
        print_step("Waiting for services to be ready...")
        check_service_health("postgres")
        check_service_health("redis")

        # Update .env file
        update_env_file(args.environment)

        # Ensure pgvector extension is available
        ensure_pgvector_extension(args.environment)

        print()
        print_success("Docker setup completed!")
        print()
        print("Next steps:")
        print(
            "  1. Run database migrations: python scripts/migrate_database.py migrate"
        )
        print(
            "  2. Initialise transcript data: python scripts/initialize_transcripts.py"
        )
        print("  3. Verify setup: python scripts/verify_setup.py")

    except KeyboardInterrupt:
        print()
        print_warning("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
