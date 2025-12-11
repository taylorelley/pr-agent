# AGPL-3.0 License

"""
Base class for all pre-merge checks.
"""

from abc import ABC, abstractmethod
from typing import Literal, Optional
import pathspec

from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.check_result import CheckResult


class BaseCheck(ABC):
    """
    Abstract base class for all pre-merge checks.

    Checks can be advisory (informational) or blocking (prevents merge).
    Each check can optionally filter by file paths using glob patterns.
    """

    def __init__(
        self,
        name: str,
        description: str,
        mode: Literal["advisory", "blocking"] = "advisory",
        paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize a check.

        Args:
            name: Unique identifier for the check
            description: Human-readable description
            mode: Check behavior - "advisory" or "blocking"
            paths: Glob patterns for files to include (None = all files)
            exclude_paths: Glob patterns for files to exclude
        """
        self.name = name
        self.description = description
        self.mode = mode
        self.paths = paths or ["**/*"]
        self.exclude_paths = exclude_paths or []

        # Compile path specs for efficient matching
        self._path_spec = pathspec.PathSpec.from_lines('gitwildmatch', self.paths)
        self._exclude_spec = pathspec.PathSpec.from_lines('gitwildmatch', self.exclude_paths) if self.exclude_paths else None

    def should_check_file(self, file_path: str) -> bool:
        """
        Determine if this check should run on the given file.

        Args:
            file_path: Path to check

        Returns:
            True if the file matches include patterns and doesn't match exclude patterns
        """
        # Check if file matches include patterns
        if not self._path_spec.match_file(file_path):
            return False

        # Check if file matches exclude patterns
        if self._exclude_spec and self._exclude_spec.match_file(file_path):
            return False

        return True

    def filter_context(self, context: CheckContext) -> CheckContext:
        """
        Filter the context to only include relevant files for this check.

        Args:
            context: Original check context

        Returns:
            New context with filtered_files populated
        """
        filtered_files = [
            file_path for file_path in context.files_changed
            if self.should_check_file(file_path)
        ]

        context.filtered_files = filtered_files
        return context

    @abstractmethod
    async def run(self, context: CheckContext) -> CheckResult:
        """
        Execute the check and return results.

        Args:
            context: Check context with PR information

        Returns:
            CheckResult indicating pass/fail and details
        """
        pass
