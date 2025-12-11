# AGPL-3.0 License

"""
Abstract state storage interface and implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import json
import aiosqlite

from pr_agent.state.pr_state import PRState
from pr_agent.log import get_logger


class StateStore(ABC):
    """
    Abstract base class for PR state persistence.

    Implementations can store state in files, databases,
    git notes, or other backends.
    """

    @abstractmethod
    async def load(self, pr_id: str) -> Optional[PRState]:
        """
        Load PR state from storage.

        Args:
            pr_id: Unique PR identifier

        Returns:
            PRState if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, state: PRState) -> None:
        """
        Save PR state to storage.

        Args:
            state: PRState to persist
        """
        pass

    @abstractmethod
    async def delete(self, pr_id: str) -> None:
        """
        Delete PR state from storage.

        Args:
            pr_id: Unique PR identifier
        """
        pass


class FileStateStore(StateStore):
    """
    File-based state storage implementation.

    Stores each PR's state as a JSON file in a directory.
    """

    def __init__(self, base_path: str = ".pr_agent_state"):
        """
        Initialize file-based state store.

        Args:
            base_path: Directory to store state files
        """
        self.base_path = Path(base_path)
        self.logger = get_logger()

    def _get_file_path(self, pr_id: str) -> Path:
        """Get file path for a PR's state."""
        # Sanitize pr_id for filesystem
        safe_id = pr_id.replace("/", "_").replace(":", "_")
        return self.base_path / f"{safe_id}.json"

    async def load(self, pr_id: str) -> Optional[PRState]:
        """Load PR state from JSON file."""
        file_path = self._get_file_path(pr_id)

        if not file_path.exists():
            self.logger.debug(f"No state file found for {pr_id}")
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return PRState.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load state for {pr_id}: {e}")
            return None

    async def save(self, state: PRState) -> None:
        """Save PR state to JSON file."""
        # Ensure directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        file_path = self._get_file_path(state.pr_id)

        try:
            with open(file_path, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            self.logger.debug(f"Saved state for {state.pr_id}")
        except Exception as e:
            self.logger.error(f"Failed to save state for {state.pr_id}: {e}")
            raise

    async def delete(self, pr_id: str) -> None:
        """Delete PR state file."""
        file_path = self._get_file_path(pr_id)

        if file_path.exists():
            try:
                file_path.unlink()
                self.logger.debug(f"Deleted state for {pr_id}")
            except Exception as e:
                self.logger.error(f"Failed to delete state for {pr_id}: {e}")
                raise
