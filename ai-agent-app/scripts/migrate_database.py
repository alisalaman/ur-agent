#!/usr/bin/env python3
"""Database migration runner for the synthetic agent system."""

import asyncio
import sys
from pathlib import Path
from typing import Any
import structlog
import asyncpg

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_agent.config.synthetic_agents import get_config

logger = structlog.get_logger()


class DatabaseMigrator:
    """Handles database migrations for the synthetic agent system."""

    def __init__(self):
        self.config = get_config()
        self.migrations_dir = Path("src/ai_agent/infrastructure/database/migrations")

    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection."""
        return await asyncpg.connect(
            host=self.config.database.host,
            port=self.config.database.port,
            database=self.config.database.database,
            user=self.config.database.username,
            password=self.config.database.password,
        )

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> list[str]:
        """Get list of applied migrations."""
        try:
            # Create migrations table if it doesn't exist
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Get applied migrations
            rows = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row["version"] for row in rows]
        except Exception as e:
            logger.error("Failed to get applied migrations", error=str(e))
            return []

    async def apply_migration(
        self, conn: asyncpg.Connection, migration_file: Path
    ) -> bool:
        """Apply a single migration file."""
        try:
            migration_sql = migration_file.read_text()
            migration_version = migration_file.stem

            logger.info("Applying migration", version=migration_version)

            # Execute migration
            await conn.execute(migration_sql)

            # Record migration as applied
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES ($1) ON CONFLICT (version) DO NOTHING",
                migration_version,
            )

            logger.info("Migration applied successfully", version=migration_version)
            return True

        except Exception as e:
            logger.error(
                "Failed to apply migration", version=migration_file.stem, error=str(e)
            )
            return False

    async def run_migrations(self) -> bool:
        """Run all pending migrations."""
        try:
            conn = await self.get_connection()

            try:
                # Get applied migrations
                applied_migrations = await self.get_applied_migrations(conn)
                logger.info("Applied migrations", migrations=applied_migrations)

                # Get all migration files
                migration_files = sorted(self.migrations_dir.glob("*.sql"))

                if not migration_files:
                    logger.warning(
                        "No migration files found", directory=str(self.migrations_dir)
                    )
                    return True

                # Apply pending migrations
                success_count = 0
                for migration_file in migration_files:
                    migration_version = migration_file.stem

                    if migration_version in applied_migrations:
                        logger.info(
                            "Migration already applied", version=migration_version
                        )
                        continue

                    success = await self.apply_migration(conn, migration_file)
                    if success:
                        success_count += 1
                    else:
                        logger.error("Migration failed", version=migration_version)
                        return False

                logger.info(
                    "Migrations completed",
                    applied=success_count,
                    total=len(migration_files),
                )
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error("Migration process failed", error=str(e))
            return False

    async def rollback_migration(self, target_version: str) -> bool:
        """Rollback to a specific migration version."""
        try:
            conn = await self.get_connection()

            try:
                # Get applied migrations
                applied_migrations = await self.get_applied_migrations(conn)

                if target_version not in applied_migrations:
                    logger.warning(
                        "Target version not found in applied migrations",
                        target_version=target_version,
                    )
                    return False

                # Get rollback files
                rollback_files = sorted(
                    self.migrations_dir.glob(f"{target_version}_rollback.sql")
                )

                if not rollback_files:
                    logger.error(
                        "No rollback file found", target_version=target_version
                    )
                    return False

                rollback_file = rollback_files[0]
                rollback_sql = rollback_file.read_text()

                logger.info("Rolling back migration", version=target_version)

                # Execute rollback
                await conn.execute(rollback_sql)

                # Remove migration record
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = $1", target_version
                )

                logger.info(
                    "Migration rolled back successfully", version=target_version
                )
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                "Migration rollback failed", target_version=target_version, error=str(e)
            )
            return False

    async def list_migrations(self) -> dict[str, Any]:
        """List all migrations and their status."""
        try:
            conn = await self.get_connection()

            try:
                applied_migrations = await self.get_applied_migrations(conn)
                migration_files = sorted(self.migrations_dir.glob("*.sql"))

                migrations = []
                for migration_file in migration_files:
                    version = migration_file.stem
                    status = "applied" if version in applied_migrations else "pending"
                    migrations.append(
                        {
                            "version": version,
                            "file": migration_file.name,
                            "status": status,
                        }
                    )

                return {
                    "migrations": migrations,
                    "total": len(migrations),
                    "applied": len(applied_migrations),
                    "pending": len(migrations) - len(applied_migrations),
                }

            finally:
                await conn.close()

        except Exception as e:
            logger.error("Failed to list migrations", error=str(e))
            return {"migrations": [], "total": 0, "applied": 0, "pending": 0}

    async def check_database_connection(self) -> bool:
        """Check if database is accessible."""
        try:
            conn = await self.get_connection()
            await conn.close()
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            return False


async def main():
    """Main migration function."""
    migrator = DatabaseMigrator()

    # Check database connection
    if not await migrator.check_database_connection():
        logger.error("Cannot connect to database. Exiting.")
        sys.exit(1)

    # Run migrations
    success = await migrator.run_migrations()

    if success:
        logger.info("Database migrations completed successfully")
        sys.exit(0)
    else:
        logger.error("Database migrations failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
