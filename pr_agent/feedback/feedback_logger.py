# AGPL-3.0 License

"""
Feedback event logging and storage.
"""

from pathlib import Path
from typing import Optional
import json

from pr_agent.feedback.feedback_event import FeedbackEvent, FeedbackEventData
from pr_agent.feedback.preference import Preference
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class FeedbackLogger:
    """
    Logs user feedback events and manages preference extraction.

    Stores feedback events locally and can aggregate them into
    preference models for tuning suggestions.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize feedback logger.

        Args:
            storage_path: Directory to store feedback data (defaults to config)
        """
        self.logger = get_logger()

        if storage_path is None:
            storage_path = get_settings().get("feedback", {}).get("storage_path", ".pr_agent_feedback")

        self.storage_path = Path(storage_path)
        self.events_dir = self.storage_path / "events"
        self.preferences_dir = self.storage_path / "preferences"

        # Create directories if they don't exist
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.preferences_dir.mkdir(parents=True, exist_ok=True)

    async def log_event(self, event: FeedbackEventData) -> None:
        """
        Log a feedback event.

        Args:
            event: Feedback event data to log
        """
        # Check if feedback is enabled
        if not get_settings().get("feedback", {}).get("enabled", False):
            self.logger.debug("Feedback logging is disabled")
            return

        try:
            # Create event file (one file per event for simplicity)
            timestamp_str = event.timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{event.repository.replace('/', '_')}_{timestamp_str}.json"
            filepath = self.events_dir / filename

            with open(filepath, "w") as f:
                json.dump(event.to_dict(), f, indent=2)

            self.logger.debug(f"Logged feedback event: {event.event_type.value}")

        except Exception as e:
            self.logger.error(f"Failed to log feedback event: {e}")

    async def load_preferences(self, repository: str) -> list[Preference]:
        """
        Load preferences for a repository.

        Args:
            repository: Repository identifier (e.g., "owner/repo")

        Returns:
            List of preferences
        """
        repo_safe = repository.replace("/", "_")
        filepath = self.preferences_dir / f"{repo_safe}.json"

        if not filepath.exists():
            return []

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return [Preference.from_dict(p) for p in data]
        except Exception as e:
            self.logger.error(f"Failed to load preferences for {repository}: {e}")
            return []

    async def save_preferences(self, repository: str, preferences: list[Preference]) -> None:
        """
        Save preferences for a repository.

        Args:
            repository: Repository identifier
            preferences: List of preferences to save
        """
        repo_safe = repository.replace("/", "_")
        filepath = self.preferences_dir / f"{repo_safe}.json"

        try:
            with open(filepath, "w") as f:
                json.dump([p.to_dict() for p in preferences], f, indent=2)
            self.logger.debug(f"Saved {len(preferences)} preferences for {repository}")
        except Exception as e:
            self.logger.error(f"Failed to save preferences for {repository}: {e}")

    async def extract_preferences(self, repository: str) -> list[Preference]:
        """
        Extract preferences from logged events for a repository.

        This analyzes feedback events to build a preference model.

        Args:
            repository: Repository identifier

        Returns:
            List of extracted preferences
        """
        # This is a placeholder for the actual preference extraction logic
        # which will be implemented in Feature 6
        self.logger.info(f"Extracting preferences for {repository}")

        # For now, just return empty list
        # TODO: Implement preference extraction algorithm
        return []
