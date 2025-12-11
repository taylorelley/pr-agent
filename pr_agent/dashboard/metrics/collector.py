# AGPL-3.0 License

"""
Metrics collection and storage.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import aiosqlite

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


@dataclass
class MetricEvent:
    """
    A single metric event to be recorded.
    """
    timestamp: datetime
    repository: str
    metric_type: str  # e.g., "pr_reviewed", "check_run", "finding_created"
    metric_value: float
    metadata: dict


class MetricsCollector:
    """
    Collects and stores metrics for the dashboard.

    Uses SQLite for storage with async support via aiosqlite.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            db_url: Database URL (defaults to config)
        """
        self.logger = get_logger()

        if db_url is None:
            db_url = get_settings().get("dashboard", {}).get("database_url", "sqlite:///.pr_agent_metrics.db")

        # Extract path from sqlite:// URL
        if db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            self.db_path = ".pr_agent_metrics.db"

        self._initialized = False

    async def initialize(self):
        """
        Initialize database schema.

        Creates necessary tables if they don't exist.
        """
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Create metrics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metadata TEXT
                )
            """)

            # Create indices for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics(timestamp)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_repository
                ON metrics(repository)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type
                ON metrics(metric_type)
            """)

            await db.commit()

        self._initialized = True
        self.logger.info(f"Metrics database initialized at {self.db_path}")

    async def record_metric(self, event: MetricEvent):
        """
        Record a metric event.

        Args:
            event: Metric event to record
        """
        # Check if dashboard is enabled
        if not get_settings().get("dashboard", {}).get("enabled", False):
            self.logger.debug("Dashboard metrics collection is disabled")
            return

        await self.initialize()

        try:
            import json

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO metrics (timestamp, repository, metric_type, metric_value, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.timestamp.isoformat(),
                        event.repository,
                        event.metric_type,
                        event.metric_value,
                        json.dumps(event.metadata)
                    )
                )
                await db.commit()

            self.logger.debug(f"Recorded metric: {event.metric_type} for {event.repository}")

        except Exception as e:
            self.logger.error(f"Failed to record metric: {e}")

    async def get_metrics(
        self,
        repository: Optional[str] = None,
        metric_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> list[dict]:
        """
        Query metrics from database.

        Args:
            repository: Filter by repository
            metric_type: Filter by metric type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results

        Returns:
            List of metric records
        """
        await self.initialize()

        query = "SELECT * FROM metrics WHERE 1=1"
        params = []

        if repository:
            query += " AND repository = ?"
            params.append(repository)

        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to query metrics: {e}")
            return []
